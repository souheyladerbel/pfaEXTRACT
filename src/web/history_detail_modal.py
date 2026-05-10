"""Modale de détail d'extraction (Historique) — contenu riche en onglets."""

from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from src.config import AppConfig
from src.services import extraction_history as extraction_history_service
from src.web.history_entry_utils import (
    entry_payload_for_report,
    history_json_path,
    merge_meta_from_disk_json,
    pdf_bytes_for_source_path,
    pdf_first_page_preview,
    resolve_archived_source_path,
)
from src.web.history_views import load_json_file

HIST_MODAL_ENTRY_KEY = "hist_modal_entry_key"
HIST_MODAL_SHOULD_OPEN = "hist_modal_should_open"

_KIND_LABELS_FR: dict[str, str] = {
    "steg_ocr": "Facture STEG (OCR Tesseract)",
    "steg_gemini": "Facture STEG",
    "medical_ocr": "Analyse médicale (OCR structuré)",
    "medical_gemini": "Analyse médicale",
    "receipt": "Ticket de caisse",
    "supplier_invoice": "Facture fournisseur (générique)",
}


def _kind_label_fr(slug: str) -> str:
    return _KIND_LABELS_FR.get(slug, slug or "—")


def _method_label(kind: str) -> str:
    k = str(kind)
    if k.endswith("_gemini") or k in ("receipt", "supplier_invoice"):
        return "Gemini"
    if k.endswith("_ocr"):
        return "OCR local"
    return "Mixte"


def history_modal_entry_key(entry: dict[str, Any]) -> str:
    """Clé stable pour rouvrir la modale après rerun (confirmation suppression, etc.)."""
    return f"{entry.get('id')}|{entry.get('relative')}|{entry.get('kind')}|{entry.get('saved_at')}"


def _clear_history_modal_session() -> None:
    st.session_state.pop(HIST_MODAL_ENTRY_KEY, None)
    st.session_state.pop(HIST_MODAL_SHOULD_OPEN, None)


def _keep_modal_open_next_run() -> None:
    """Après interaction dans la modale, rouvrir au prochain run sans boucle si l'utilisateur ferme avec ✕."""
    st.session_state[HIST_MODAL_SHOULD_OPEN] = True


def _stable_entry_key(entry: dict) -> str:
    rel = str(entry.get("relative") or "")
    eid = entry.get("id")
    raw = rel if rel else f"id:{eid}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:20]


def _format_saved_at(raw: str | None) -> str:
    if not raw:
        return "—"
    s = raw.strip()
    try:
        iso = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%d/%m/%Y %H:%M:%S")
    except ValueError:
        return s[:19] if len(s) >= 19 else s


def _error_display(data: dict[str, Any]) -> str:
    err = data.get("error")
    if err is None:
        return ""
    if isinstance(err, str):
        return err.strip() or "Erreur inconnue"
    if isinstance(err, dict):
        return str(err.get("message") or err.get("detail") or json.dumps(err, ensure_ascii=False))
    return str(err)


def _count_leaf_values(obj: Any, depth: int = 0) -> int:
    if depth > 12:
        return 0
    if obj is None or obj == "" or obj == [] or obj == {}:
        return 0
    if isinstance(obj, dict):
        return sum(_count_leaf_values(v, depth + 1) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        if obj and isinstance(obj[0], dict):
            return sum(_count_leaf_values(item, depth + 1) for item in obj)
        return len(obj)
    return 1


def _extracted_fields_count(body: dict[str, Any], kind: str) -> int:
    """Nombre indicatif de champs / lignes utiles pour les cartes Résumé."""
    if not isinstance(body, dict):
        return 0
    core = {k: v for k, v in body.items() if k not in ("warnings",)}
    n = _count_leaf_values(core)
    if kind == "medical_gemini":
        n = max(n, len(body.get("analyses") or []))
    elif kind == "medical_ocr":
        n = max(n, len(body.get("tests") or []))
    elif kind == "receipt":
        n = max(n, len(body.get("items") or []))
    elif kind == "supplier_invoice":
        n = max(n, len(body.get("items") or []))
    return int(n)


def _confidence_pct(body: dict[str, Any]) -> tuple[str | None, float | None]:
    q = body.get("extraction_quality")
    if isinstance(q, (int, float)) and not isinstance(q, bool):
        v = float(q)
        if 0.0 <= v <= 1.0:
            return f"{v * 100:.1f}%", v
        if 0.0 <= v <= 100.0:
            return f"{v:.1f}%", v / 100.0
    note = body.get("confidence_note")
    if note:
        return str(note).strip(), None
    return None, None


def _intelligent_summary(kind: str, is_error: bool) -> str:
    if is_error:
        return (
            "Le traitement de ce document n'a pas pu être terminé correctement. "
            "Vérifiez la qualité du fichier et relancez une extraction si nécessaire."
        )
    if kind in ("medical_gemini", "medical_ocr"):
        return (
            "Ce document est une analyse médicale contenant les informations du patient, "
            "du médecin et les résultats biologiques."
        )
    if kind in ("steg_gemini", "steg_ocr"):
        return (
            "Ce document est une facture STEG avec les références de facturation, la période "
            "de consommation et les montants à payer."
        )
    if kind == "receipt":
        return (
            "Ce document est un ticket de caisse listant le commerce, la date, les articles "
            "achetés et le total payé."
        )
    if kind == "supplier_invoice":
        return (
            "Ce document est une facture fournisseur (vente, achat ou services) avec vendeur, "
            "client, lignes et totaux structurés."
        )
    return "Document traité : données structurées disponibles dans les onglets ci-dessous."


def _analysis_status_cell(a: dict[str, Any]) -> str:
    for key in ("status", "statut", "flag", "interpretation", "interpretation_fr"):
        v = a.get(key)
        if v not in (None, ""):
            return str(v).strip()
    ref = a.get("reference_range")
    if ref not in (None, ""):
        return str(ref).strip()
    return "—"


def _medical_table_gemini(analyses: list[Any]) -> pd.DataFrame:
    """Aligné sur ``medical_gemini_analyses_for_display`` + colonne Statut."""
    rows: list[dict[str, Any]] = []
    for a in analyses:
        if not isinstance(a, dict):
            continue
        nm = (
            a.get("test_name")
            or a.get("raw_test_name")
            or a.get("name")
            or a.get("Analyse")
        )
        val = a.get("value")
        if val is None:
            val = a.get("value_text")
        if val is None:
            val = a.get("Valeur")
        unit = a.get("unit")
        if unit in (None, ""):
            unit = a.get("Unité")
        rows.append(
            {
                "Analyse": nm if nm not in (None, "") else "—",
                "Valeur": val if val not in (None, "") else "—",
                "Unité": unit if unit not in (None, "") else "—",
                "Statut": _analysis_status_cell(a),
            }
        )
    return pd.DataFrame(rows)


def _medical_table_ocr(tests: list[Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for t in tests:
        if not isinstance(t, dict):
            continue
        val = t.get("value")
        if val is None:
            val = t.get("value_text")
        rows.append(
            {
                "Analyse": t.get("raw_test_name") or "—",
                "Valeur": val if val not in (None, "") else "—",
                "Unité": t.get("unit") or "—",
                "Statut": str(t.get("status") or t.get("flag") or "—"),
            }
        )
    return pd.DataFrame(rows)


def _steg_consumption_df(body: dict[str, Any]) -> pd.DataFrame | None:
    for key in ("consommations", "consumptions", "lignes_consommation", "consumption_lines", "details_consommation"):
        rows = body.get(key)
        if isinstance(rows, list) and rows:
            norm: list[dict[str, Any]] = []
            for r in rows:
                if not isinstance(r, dict):
                    continue
                norm.append({str(k): v for k, v in r.items()})
            if norm:
                return pd.DataFrame(norm)
    return None


def _supplier_invoice_items_df(items: list[Any]) -> pd.DataFrame:
    keys = [
        "description",
        "quantity",
        "unit",
        "unit_price",
        "net_amount",
        "tax_rate",
        "tax_amount",
        "gross_amount",
    ]
    rows: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        rows.append({k: item.get(k) or "—" for k in keys})
    return pd.DataFrame(rows)


def _receipt_items_df(items: list[Any]) -> pd.DataFrame:
    out: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        price = item.get("unit_price")
        if price in (None, ""):
            price = item.get("line_total")
        out.append(
            {
                "Produit": item.get("description") or item.get("name") or "—",
                "Quantité": item.get("quantity") if item.get("quantity") not in (None, "") else "—",
                "Prix": price if price not in (None, "") else "—",
            }
        )
    return pd.DataFrame(out)


def _modal_metric_card(label: str, value: str) -> None:
    st.markdown(
        f"""
        <div class="hx-modal-metric">
            <div class="hx-modal-metric-label">{label}</div>
            <div class="hx-modal-metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _inject_modal_css() -> None:
    if st.session_state.get("_hx_modal_css"):
        return
    st.markdown(
        """
        <style>
        @keyframes hxModalFadeIn {
            from { opacity: 0; transform: translateY(10px) scale(0.985); }
            to { opacity: 1; transform: translateY(0) scale(1); }
        }
        div[data-testid="stDialog"] > div {
            animation: hxModalFadeIn 0.22s ease-out;
        }
        .hx-modal-head {
            border-bottom: 1px solid #e2e8f0;
            padding-bottom: 12px;
            margin-bottom: 12px;
        }
        .hx-modal-title {
            font-size: 1.15rem;
            font-weight: 700;
            color: #0f172a;
            margin: 0;
            word-break: break-word;
        }
        .hx-modal-sub {
            color: #64748b;
            font-size: 0.88rem;
            margin-top: 6px;
        }
        .hx-badge-ok {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
            background: #dcfce7;
            color: #166534;
            border: 1px solid #86efac;
        }
        .hx-badge-err {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
            background: #fee2e2;
            color: #991b1b;
            border: 1px solid #fca5a5;
        }
        .hx-badge-ver {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
            background: #e0f2fe;
            color: #0369a1;
            border: 1px solid #7dd3fc;
            margin-left: 8px;
        }
        .hx-modal-metric {
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 12px 14px;
            background: #ffffff;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06);
            min-height: 72px;
            margin-bottom: 10px;
        }
        .hx-modal-metric-label {
            font-size: 0.78rem;
            font-weight: 600;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }
        .hx-modal-metric-value {
            font-size: 1rem;
            font-weight: 700;
            color: #1e293b;
            margin-top: 6px;
            word-break: break-word;
        }
        .hx-smart-box {
            border-radius: 12px;
            padding: 14px 16px;
            background: linear-gradient(135deg, #eff6ff 0%, #f8fafc 100%);
            border: 1px solid #bfdbfe;
            color: #1e3a5f;
            font-size: 0.95rem;
            line-height: 1.45;
            margin-top: 8px;
        }
        .hx-empty {
            text-align: center;
            padding: 28px 16px;
            color: #64748b;
            border: 1px dashed #cbd5e1;
            border-radius: 12px;
            background: #f8fafc;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.session_state["_hx_modal_css"] = True


def _copy_json_component(json_text: str, html_key: str) -> None:
    b64 = base64.b64encode(json_text.encode("utf-8")).decode("ascii")
    safe_key = "".join(c if c.isalnum() else "_" for c in html_key)[:40]
    components.html(
        f"""
        <div style="font-family: system-ui, sans-serif;">
          <button id="hxbtn_{safe_key}" style="padding:8px 16px;border-radius:10px;background:#1d4ed8;color:white;
            border:none;cursor:pointer;font-weight:600;font-size:14px;">
            Copier JSON
          </button>
          <span id="hxmsg_{safe_key}" style="margin-left:12px;color:#15803d;font-size:13px;"></span>
          <script>
            const b64 = "{b64}";
            const btn = document.getElementById("hxbtn_{safe_key}");
            const msg = document.getElementById("hxmsg_{safe_key}");
            btn.addEventListener("click", async () => {{
              try {{
                const binary = atob(b64);
                const bytes = new Uint8Array(binary.length);
                for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
                const txt = new TextDecoder("utf-8").decode(bytes);
                await navigator.clipboard.writeText(txt);
                msg.textContent = "Copié dans le presse-papiers";
              }} catch (e) {{
                msg.textContent = "Copie impossible (navigateur)";
              }}
            }});
          </script>
        </div>
        """,
        height=52,
    )


def _render_modal_tabs(
    *,
    data: dict[str, Any],
    kind: str,
    saved_at_disp: str,
    is_error: bool,
    stable_key: str,
) -> None:
    body = {k: v for k, v in data.items() if k != "_meta"}

    tab_summary, tab_data, tab_json = st.tabs(["Résumé", "Données extraites", "JSON brut"])

    with tab_summary:
        if is_error:
            st.markdown(
                """
                <div class="hx-empty">
                  <div style="font-size:2rem;">❌</div>
                  <div style="font-weight:700;color:#991b1b;margin-top:8px;">Extraction échouée</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            err_txt = _error_display(data)
            if err_txt:
                st.markdown("**Détails de l'erreur**")
                st.warning(err_txt)
            st.info(
                "**Conseils :** vérifiez le format du fichier (image lisible, PDF supporté selon le flux), "
                "la clé API Gemini si nécessaire, puis réessayez depuis la page Extraction."
            )
        else:
            conf_str, conf_float = _confidence_pct(body)
            n_fields = _extracted_fields_count(body, kind)
            m1, m2, m3 = st.columns(3)
            with m1:
                _modal_metric_card("Type de document", _kind_label_fr(kind))
                _modal_metric_card("Méthode utilisée", _method_label(kind))
            with m2:
                _modal_metric_card("Date d'extraction", saved_at_disp)
                _modal_metric_card("Champs / lignes (indicatif)", str(max(1, n_fields)))
            with m3:
                _modal_metric_card(
                    "Score / confiance",
                    conf_str if conf_str else ("—" if not is_error else "N/A"),
                )
                if conf_float is not None:
                    st.progress(min(1.0, max(0.0, conf_float)))

            st.markdown("**Résumé intelligent**")
            st.markdown(
                f'<div class="hx-smart-box">{_intelligent_summary(kind, is_error)}</div>',
                unsafe_allow_html=True,
            )

            st.markdown("**Aperçu des données**")
            preview_cols = st.columns(2)
            with preview_cols[0]:
                if kind in ("medical_gemini", "medical_ocr"):
                    pn = body.get("patient_name") or (body.get("patient_info") or {}).get("patient_name")
                    st.caption("Patient")
                    st.write(pn or "—")
                elif kind in ("steg_gemini", "steg_ocr"):
                    st.caption("Référence")
                    st.write(body.get("reference") or "—")
                elif kind == "receipt":
                    st.caption("Magasin")
                    st.write(body.get("store_name") or "—")
                elif kind == "supplier_invoice":
                    st.caption("N° facture")
                    st.write(body.get("invoice_number") or "—")
            with preview_cols[1]:
                if kind in ("medical_gemini", "medical_ocr"):
                    st.caption("Médecin / laboratoire")
                    dn = body.get("doctor_name") or (body.get("lab_info") or {}).get("doctor_name")
                    st.write(dn or "—")
                elif kind in ("steg_gemini", "steg_ocr"):
                    st.caption("Montant à payer")
                    st.write(body.get("montant_a_payer") or "—")
                elif kind == "receipt":
                    st.caption("Total")
                    st.write(body.get("total") or "—")
                elif kind == "supplier_invoice":
                    summ = body.get("summary") if isinstance(body.get("summary"), dict) else {}
                    st.caption("Total")
                    st.write(summ.get("total_amount") or summ.get("amount_due") or "—")

    with tab_data:
        if is_error:
            st.markdown('<div class="hx-empty">Données extraites non disponibles (erreur).</div>', unsafe_allow_html=True)
        elif kind in ("steg_gemini", "steg_ocr"):
            st.markdown("##### Facture STEG")
            client = body.get("nom_client") or body.get("client") or body.get("subscriber_name")
            addr = body.get("adresse") or body.get("adresse_client") or body.get("address")
            info_rows = [
                {"Champ": "Référence", "Valeur": body.get("reference") or "—"},
                {"Champ": "Client", "Valeur": client or "—"},
                {"Champ": "Adresse", "Valeur": addr or "—"},
                {
                    "Champ": "Période",
                    "Valeur": f"{body.get('periode_du') or '—'} → {body.get('periode_au') or '—'}",
                },
                {"Champ": "Montant total / à payer", "Valeur": body.get("montant_a_payer") or "—"},
                {"Champ": "Date limite de paiement", "Valeur": body.get("date_limite_paiement") or "—"},
            ]
            st.dataframe(info_rows, width="stretch", hide_index=True, height=220)
            cdf = _steg_consumption_df(body)
            st.markdown("##### Consommations")
            if cdf is not None and not cdf.empty:
                st.dataframe(cdf, width="stretch", hide_index=True, height=280)
            else:
                st.caption("Aucune ligne de consommation structurée dans ce JSON.")
        elif kind == "receipt":
            st.markdown("##### Ticket de caisse")
            st.dataframe(
                [
                    {"Champ": "Magasin", "Valeur": body.get("store_name") or "—"},
                    {"Champ": "Date", "Valeur": body.get("date") or "—"},
                    {"Champ": "Total", "Valeur": body.get("total") or "—"},
                    {"Champ": "Mode de paiement", "Valeur": body.get("payment_method") or "—"},
                ],
                width="stretch",
                hide_index=True,
            )
            st.markdown("##### Articles")
            items = body.get("items") or []
            if items:
                st.dataframe(_receipt_items_df(items), width="stretch", hide_index=True, height=320)
            else:
                st.info("Aucun article listé.")
        elif kind == "supplier_invoice":
            st.markdown("##### Informations générales")
            rtl = body.get("ocr_rtl_text_ratio")
            rows_gen = [
                {"Champ": "N° facture", "Valeur": body.get("invoice_number") or "—"},
                {"Champ": "Date facture", "Valeur": body.get("invoice_date") or "—"},
                {"Champ": "Échéance", "Valeur": body.get("due_date") or "—"},
                {"Champ": "Devise", "Valeur": body.get("currency") or "—"},
                {"Champ": "Confiance", "Valeur": body.get("confidence") or "—"},
            ]
            if rtl is not None:
                rows_gen.append({"Champ": "Indice RTL (OCR)", "Valeur": str(rtl)})
            st.dataframe(rows_gen, width="stretch", hide_index=True)
            seller = body.get("seller") if isinstance(body.get("seller"), dict) else {}
            client = body.get("client") if isinstance(body.get("client"), dict) else {}
            st.markdown("##### Fournisseur")
            st.dataframe(
                [
                    {"Champ": "Nom", "Valeur": seller.get("name") or "—"},
                    {"Champ": "Adresse", "Valeur": seller.get("address") or "—"},
                    {"Champ": "Identifiant fiscal", "Valeur": seller.get("tax_id") or "—"},
                    {"Champ": "IBAN", "Valeur": seller.get("iban") or "—"},
                    {"Champ": "Email", "Valeur": seller.get("email") or "—"},
                    {"Champ": "Téléphone", "Valeur": seller.get("phone") or "—"},
                ],
                width="stretch",
                hide_index=True,
            )
            st.markdown("##### Client")
            st.dataframe(
                [
                    {"Champ": "Nom", "Valeur": client.get("name") or "—"},
                    {"Champ": "Adresse", "Valeur": client.get("address") or "—"},
                    {"Champ": "Identifiant fiscal", "Valeur": client.get("tax_id") or "—"},
                    {"Champ": "Email", "Valeur": client.get("email") or "—"},
                    {"Champ": "Téléphone", "Valeur": client.get("phone") or "—"},
                ],
                width="stretch",
                hide_index=True,
            )
            items_si = body.get("items") or []
            st.markdown("##### Articles")
            if items_si:
                st.dataframe(_supplier_invoice_items_df(items_si), width="stretch", hide_index=True, height=320)
            else:
                st.info("Aucune ligne article.")
            summary = body.get("summary") if isinstance(body.get("summary"), dict) else {}
            st.markdown("##### Résumé")
            st.dataframe(
                [
                    {"Champ": "Sous-total", "Valeur": summary.get("subtotal") or "—"},
                    {"Champ": "Total TVA", "Valeur": summary.get("tax_total") or "—"},
                    {"Champ": "Remise", "Valeur": summary.get("discount") or "—"},
                    {"Champ": "Livraison", "Valeur": summary.get("shipping") or "—"},
                    {"Champ": "Total", "Valeur": summary.get("total_amount") or "—"},
                    {"Champ": "Montant dû", "Valeur": summary.get("amount_due") or "—"},
                ],
                width="stretch",
                hide_index=True,
            )
        elif kind == "medical_gemini":
            st.markdown("##### Analyse médicale")
            st.dataframe(
                [
                    {"Champ": "Patient", "Valeur": body.get("patient_name") or "—"},
                    {"Champ": "Médecin", "Valeur": body.get("doctor_name") or "—"},
                    {"Champ": "Date", "Valeur": body.get("date") or "—"},
                ],
                width="stretch",
                hide_index=True,
            )
            analyses = body.get("analyses") or []
            st.markdown("##### Résultats des analyses")
            if analyses:
                st.dataframe(_medical_table_gemini(analyses), width="stretch", hide_index=True, height=340)
            else:
                st.info("Aucune analyse dans ce rapport.")
        elif kind == "medical_ocr":
            st.markdown("##### Analyse médicale (OCR)")
            lab = body.get("lab_info") or {}
            patient = body.get("patient_info") or {}
            docmeta = body.get("document_metadata") or {}
            st.dataframe(
                [
                    {"Champ": "Patient", "Valeur": patient.get("patient_name") or "—"},
                    {"Champ": "Médecin / labo", "Valeur": lab.get("doctor_name") or lab.get("lab_name") or "—"},
                    {
                        "Champ": "Date",
                        "Valeur": docmeta.get("report_date") or docmeta.get("sample_date") or "—",
                    },
                ],
                width="stretch",
                hide_index=True,
            )
            tests = body.get("tests") or []
            st.markdown("##### Résultats des analyses")
            if tests:
                st.dataframe(_medical_table_ocr(tests), width="stretch", hide_index=True, height=340)
            else:
                st.info("Aucune ligne d'analyse.")
        else:
            if body:
                st.json(body)
            else:
                st.markdown('<div class="hx-empty">Aucune donnée structurée.</div>', unsafe_allow_html=True)

    raw_json = json.dumps(data, ensure_ascii=False, indent=2)
    with tab_json:
        _copy_json_component(raw_json, f"j_{stable_key}")
        st.download_button(
            "Télécharger JSON",
            data=raw_json.encode("utf-8"),
            file_name=f"extraction_{stable_key}.json",
            mime="application/json",
            key=f"hx_dl_json_{stable_key}",
            use_container_width=True,
        )
        st.code(raw_json, language="json")

def _render_source_panel(entry: dict[str, Any], data: dict[str, Any], cfg: AppConfig, stable_key: str) -> None:
    st.markdown("#### Document source")
    meta = data.get("_meta") if isinstance(data.get("_meta"), dict) else {}
    source_path = resolve_archived_source_path(entry, cfg, data)
    meta_fn = meta.get("source_filename") if isinstance(meta, dict) else None
    source_name = str(meta_fn or (source_path.name if source_path else "") or "document")
    if source_path is None or not source_path.is_file():
        st.markdown(
            '<div class="hx-empty">Aucun aperçu disponible<br/><span style="font-size:0.9rem;">'
            "Le fichier source n'a pas été archivé pour cette extraction.</span></div>",
            unsafe_allow_html=True,
        )
        return
    suffix = source_path.suffix.lower()
    img_exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
    try:
        raw_bytes = source_path.read_bytes()
    except Exception:
        raw_bytes = None
    if raw_bytes:
        st.download_button(
            "Télécharger document source",
            data=raw_bytes,
            file_name=source_name,
            mime="application/octet-stream",
            key=f"hx_src_orig_{stable_key}",
            use_container_width=True,
        )
    pdf_bytes, pdf_name = pdf_bytes_for_source_path(source_path, source_name)
    if pdf_bytes:
        st.download_button(
            "Télécharger en PDF",
            data=pdf_bytes,
            file_name=pdf_name,
            mime="application/pdf",
            key=f"hx_src_pdf_{stable_key}",
            use_container_width=True,
        )
    if suffix == ".pdf" and pdf_bytes:
        prev = pdf_first_page_preview(pdf_bytes)
        if prev:
            st.image(prev, use_container_width=True)
        else:
            st.warning("Aperçu PDF indisponible.")
    elif suffix in img_exts:
        st.image(str(source_path), use_container_width=True)
    elif pdf_bytes:
        prev = pdf_first_page_preview(pdf_bytes)
        if prev:
            st.image(prev, use_container_width=True)
        else:
            st.warning("Aperçu indisponible pour ce format.")
    else:
        st.info("Aperçu non disponible pour ce type de fichier.")


@st.dialog("Détail de l'extraction", width="large")
def open_history_detail_modal(entry: dict[str, Any], cfg: AppConfig) -> None:
    """Ouvre la modale de détail (à invoquer depuis le gestionnaire du bouton « Voir détail »)."""
    _inject_modal_css()
    stable_key = _stable_entry_key(entry)

    with st.spinner("Chargement du détail…"):
        data = entry_payload_for_report(entry, cfg)
        jp = history_json_path(entry, cfg)
        path_obj = entry.get("path")

    if not isinstance(data, dict):
        data = {}

    if not data:
        load_err: str | None = None
        if path_obj is not None:
            loaded, load_err = load_json_file(path_obj)
            data = loaded if isinstance(loaded, dict) else {}
        elif jp is not None:
            loaded, load_err = load_json_file(jp)
            data = loaded if isinstance(loaded, dict) else {}
        else:
            load_err = "aucun fichier JSON sur disque"
        if not data:
            st.error(f"Lecture impossible : {load_err or 'payload vide'}")
            if st.button("Fermer", key=f"hx_close_err_{stable_key}"):
                _clear_history_modal_session()
                st.rerun()
            return

    merge_meta_from_disk_json(data, entry, cfg)

    kind = str(entry.get("kind") or (data.get("_meta") or {}).get("kind") or "")
    filename = str(entry.get("source_filename") or (data.get("_meta") or {}).get("source_filename") or "—")
    saved_at_disp = _format_saved_at(entry.get("saved_at"))
    is_error = bool(data.get("error"))

    verified = st.session_state.get(f"hist_verified_{stable_key}", False)

    badge_html = (
        '<span class="hx-badge-err">Erreur</span>'
        if is_error
        else '<span class="hx-badge-ok">Succès</span>'
    )
    ver_html = '<span class="hx-badge-ver">Vérifié</span>' if verified else ""

    st.markdown(
        f"""
        <div class="hx-modal-head">
            <p class="hx-modal-title">📄 {filename}</p>
            <div class="hx-modal-sub">
              {_kind_label_fr(kind)} · Traité le {saved_at_disp}
              <span style="margin-left:10px;">{badge_html}{ver_html}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    vp_left, vp_right = st.columns([1, 1.35], gap="small")
    with vp_left:
        _render_source_panel(entry, data, cfg, stable_key)
    with vp_right:
        _render_modal_tabs(
            data=data,
            kind=kind,
            saved_at_disp=saved_at_disp,
            is_error=is_error,
            stable_key=stable_key,
        )

    st.divider()
    popover_ok = hasattr(st, "popover")
    fc1, fc2, fc3, fc4 = st.columns([1.1, 1.1, 1, 0.9], gap="small")

    with fc1:
        if popover_ok:
            with st.popover("Exporter", use_container_width=True):
                try:
                    from src.services.extraction_report_pdf import build_extraction_report_pdf

                    if kind and not is_error:
                        pdf_bytes = build_extraction_report_pdf(data, kind)
                        stem = Path(filename).stem or "extraction"
                        st.download_button(
                            "PDF (rapport DOCEXTRACT)",
                            data=pdf_bytes,
                            file_name=f"DOCEXTRACT_{stem}.pdf",
                            mime="application/pdf",
                            key=f"hx_exp_pdf_{stable_key}",
                            use_container_width=True,
                        )
                except Exception:
                    st.caption("PDF indisponible.")
                raw_json = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
                st.download_button(
                    "JSON brut",
                    data=raw_json,
                    file_name=f"extraction_{stable_key}.json",
                    mime="application/json",
                    key=f"hx_exp_js_{stable_key}",
                    use_container_width=True,
                )
        else:
            try:
                from src.services.extraction_report_pdf import build_extraction_report_pdf

                if kind and not is_error:
                    pdf_bytes = build_extraction_report_pdf(data, kind)
                    stem = Path(filename).stem or "extraction"
                    st.download_button(
                        "Exporter PDF",
                        data=pdf_bytes,
                        file_name=f"DOCEXTRACT_{stem}.pdf",
                        mime="application/pdf",
                        key=f"hx_exp_pdf_{stable_key}",
                        use_container_width=True,
                    )
            except Exception:
                st.caption("PDF indisponible.")

    with fc2:
        raw_json_b = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        if not popover_ok:
            st.download_button(
                "Exporter JSON",
                data=raw_json_b,
                file_name=f"extraction_{stable_key}.json",
                mime="application/json",
                key=f"hx_exp_js2_{stable_key}",
                use_container_width=True,
            )

    with fc3:
        if st.button(
            "✓ Marquer comme vérifié",
            key=f"hx_verify_{stable_key}",
            disabled=is_error,
            use_container_width=True,
        ):
            st.session_state[f"hist_verified_{stable_key}"] = True
            _keep_modal_open_next_run()
            st.rerun()

    del_session_key = f"hx_modal_confirm_del_{stable_key}"
    with fc4:
        if st.session_state.get(del_session_key):
            st.caption("Confirmer ?")
            d1, d2 = st.columns(2)
            with d1:
                if st.button("Oui", key=f"hx_del_y_{stable_key}", type="primary"):
                    ok, msg = extraction_history_service.delete_history_entry(cfg, entry)
                    if ok:
                        st.session_state[del_session_key] = False
                        _clear_history_modal_session()
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
            with d2:
                if st.button("Non", key=f"hx_del_n_{stable_key}"):
                    st.session_state[del_session_key] = False
                    _keep_modal_open_next_run()
                    st.rerun()
        else:
            if st.button(
                "Supprimer",
                key=f"hx_del_{stable_key}",
                type="secondary",
                use_container_width=True,
            ):
                st.session_state[del_session_key] = True
                _keep_modal_open_next_run()
                st.rerun()

    if st.button("Fermer", key=f"hx_close_{stable_key}", use_container_width=True):
        _clear_history_modal_session()
        st.rerun()
