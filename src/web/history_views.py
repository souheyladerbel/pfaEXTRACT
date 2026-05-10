"""Affichage structuré des enregistrements d'historique (même logique que la page principale)."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd
import streamlit as st

MEDICAL_RESULT_COLUMNS = ("Analyse", "Valeur", "Unité")


def render_quality_and_warnings_section(body: dict[str, Any]) -> None:
    """Affiche les avertissements issus de la validation / heuristiques (la qualité est dans le tableau)."""
    warns = body.get("warnings") or []
    if not warns:
        return
    for w in warns:
        if not isinstance(w, dict):
            continue
        code = (w.get("code") or "").strip()
        msg = (w.get("message") or "").strip()
        if not msg:
            continue
        label = f"{code}: {msg}" if code else msg
        st.warning(label)


def _show_kv(rows: list[dict[str, Any]]) -> None:
    st.dataframe(rows, width="stretch", hide_index=True)


def _valeur_test_dict(t: dict[str, Any]) -> str:
    if t.get("value") is not None:
        return str(t["value"])
    if t.get("value_text"):
        return str(t["value_text"])
    return ""


_GEMINI_SKIP_DISPLAY_KEYS = frozenset(
    {"reference_range", "previous_value", "previous_date"}
)


def gemini_analyses_for_display(analyses: list[Any]) -> list[dict[str, Any]]:
    """Lignes d'analyses Gemini sans colonnes retirées du produit (historique / app, y compris anciens JSON)."""
    out: list[dict[str, Any]] = []
    for a in analyses:
        if not isinstance(a, dict):
            continue
        out.append({k: v for k, v in a.items() if k not in _GEMINI_SKIP_DISPLAY_KEYS})
    return out


def medical_gemini_analyses_for_display(analyses: list[Any]) -> list[dict[str, Any]]:
    """Tableau lisible : Analyse / Valeur / Unité uniquement (pas normes ni statut pour ce flux)."""
    out: list[dict[str, Any]] = []
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
        out.append(
            {
                "Analyse": nm if nm not in (None, "") else "—",
                "Valeur": val if val not in (None, "") else "—",
                "Unité": unit if unit not in (None, "") else "—",
            }
        )
    return out


def medical_results_df(rows: list[dict[str, Any]]) -> pd.DataFrame:
    """Force exactement trois colonnes (ignore toute clé parasite du JSON / LLM)."""
    return pd.DataFrame(rows or [], columns=list(MEDICAL_RESULT_COLUMNS))


def render_extraction_detail(data: dict[str, Any], kind: str) -> None:
    """Affiche le détail lisible selon ``kind`` (champ _meta.kind ou dossier parent)."""
    meta = data.get("_meta") or {}
    body = {k: v for k, v in data.items() if k != "_meta"}

    st.markdown("##### Informations du document")
    _show_kv(
        [
            {"Champ": "Fichier source", "Valeur": meta.get("source_filename") or "—"},
            {"Champ": "Type", "Valeur": kind or meta.get("kind") or "—"},
            {"Champ": "Enregistré le", "Valeur": meta.get("saved_at") or "—"},
        ]
    )

    if kind in ("steg_ocr", "steg_gemini"):
        st.subheader("Facture STEG")
        render_quality_and_warnings_section(body)
        _show_kv(
            [
                {"Champ": "Référence", "Valeur": body.get("reference") or "—"},
                {"Champ": "Montant à payer", "Valeur": body.get("montant_a_payer") or "—"},
                {"Champ": "Date limite paiement", "Valeur": body.get("date_limite_paiement") or "—"},
                {"Champ": "Période Du", "Valeur": body.get("periode_du") or "—"},
                {"Champ": "Période Au", "Valeur": body.get("periode_au") or "—"},
                {"Champ": "Montant coupon (bas)", "Valeur": body.get("coupon_montant") or "—"},
                {"Champ": "Confiance", "Valeur": body.get("confidence_note") or "—"},
            ]
        )
        return

    if kind == "receipt":
        st.subheader("Ticket de caisse")
        render_quality_and_warnings_section(body)
        _show_kv(
            [
                {"Champ": "Magasin", "Valeur": body.get("store_name") or "—"},
                {"Champ": "Date", "Valeur": body.get("date") or "—"},
                {"Champ": "Heure", "Valeur": body.get("time") or "—"},
                {"Champ": "N° ticket", "Valeur": body.get("ticket_number") or "—"},
                {"Champ": "Devise", "Valeur": body.get("currency") or "—"},
                {"Champ": "Total", "Valeur": body.get("total") or "—"},
                {"Champ": "Paiement", "Valeur": body.get("payment_method") or "—"},
            ]
        )
        items = body.get("items") or []
        st.subheader("Articles")
        if items:
            st.dataframe(items, width="stretch", hide_index=True)
        else:
            st.caption("Aucune ligne article.")
        return

    if kind == "supplier_invoice":
        st.subheader("Facture fournisseur")
        render_quality_and_warnings_section(body)
        rtl = body.get("ocr_rtl_text_ratio")
        gen = [
            {"Champ": "N° facture", "Valeur": body.get("invoice_number") or "—"},
            {"Champ": "Date facture", "Valeur": body.get("invoice_date") or "—"},
            {"Champ": "Échéance", "Valeur": body.get("due_date") or "—"},
            {"Champ": "Devise", "Valeur": body.get("currency") or "—"},
            {"Champ": "Confiance", "Valeur": body.get("confidence") or "—"},
        ]
        if rtl is not None:
            gen.append({"Champ": "Indice RTL (OCR)", "Valeur": str(rtl)})
        st.markdown("##### Informations générales")
        _show_kv(gen)
        seller = body.get("seller") if isinstance(body.get("seller"), dict) else {}
        client = body.get("client") if isinstance(body.get("client"), dict) else {}
        st.markdown("##### Fournisseur")
        _show_kv(
            [
                {"Champ": "Nom", "Valeur": seller.get("name") or "—"},
                {"Champ": "Adresse", "Valeur": seller.get("address") or "—"},
                {"Champ": "Identifiant fiscal", "Valeur": seller.get("tax_id") or "—"},
                {"Champ": "IBAN", "Valeur": seller.get("iban") or "—"},
                {"Champ": "Email", "Valeur": seller.get("email") or "—"},
                {"Champ": "Téléphone", "Valeur": seller.get("phone") or "—"},
            ]
        )
        st.markdown("##### Client")
        _show_kv(
            [
                {"Champ": "Nom", "Valeur": client.get("name") or "—"},
                {"Champ": "Adresse", "Valeur": client.get("address") or "—"},
                {"Champ": "Identifiant fiscal", "Valeur": client.get("tax_id") or "—"},
                {"Champ": "Email", "Valeur": client.get("email") or "—"},
                {"Champ": "Téléphone", "Valeur": client.get("phone") or "—"},
            ]
        )
        st.markdown("##### Articles")
        items_sup = body.get("items") or []
        if items_sup:
            st.dataframe(items_sup, width="stretch", hide_index=True)
        else:
            st.caption("Aucune ligne article.")
        summary = body.get("summary") if isinstance(body.get("summary"), dict) else {}
        st.markdown("##### Résumé")
        _show_kv(
            [
                {"Champ": "Sous-total", "Valeur": summary.get("subtotal") or "—"},
                {"Champ": "Total TVA", "Valeur": summary.get("tax_total") or "—"},
                {"Champ": "Remise", "Valeur": summary.get("discount") or "—"},
                {"Champ": "Livraison", "Valeur": summary.get("shipping") or "—"},
                {"Champ": "Total", "Valeur": summary.get("total_amount") or "—"},
                {"Champ": "Montant dû", "Valeur": summary.get("amount_due") or "—"},
            ]
        )
        return

    if kind == "medical_gemini":
        st.subheader("Analyse médicale")
        render_quality_and_warnings_section(body)
        _show_kv(
            [
                {"Champ": "Patient", "Valeur": body.get("patient_name") or "—"},
                {"Champ": "Médecin", "Valeur": body.get("doctor_name") or "—"},
                {"Champ": "Date", "Valeur": body.get("date") or "—"},
            ]
        )
        analyses = body.get("analyses") or []
        st.subheader("Résultats d'analyses")
        if analyses:
            st.dataframe(
                medical_results_df(medical_gemini_analyses_for_display(analyses)),
                width="stretch",
                hide_index=True,
            )
        else:
            st.caption("Aucune analyse.")
        return

    if kind == "medical_ocr":
        st.subheader("Analyse médicale (OCR structuré)")
        lab = body.get("lab_info") or {}
        patient = body.get("patient_info") or {}
        docmeta = body.get("document_metadata") or {}
        _show_kv(
            [
                {"Champ": "Laboratoire", "Valeur": lab.get("lab_name") or "—"},
                {"Champ": "Médecin", "Valeur": lab.get("doctor_name") or "—"},
                {"Champ": "Patient", "Valeur": patient.get("patient_name") or "—"},
                {"Champ": "N° dossier", "Valeur": docmeta.get("dossier_number") or "—"},
                {"Champ": "Date prélèvement", "Valeur": docmeta.get("sample_date") or "—"},
                {"Champ": "Date compte-rendu", "Valeur": docmeta.get("report_date") or "—"},
                {"Champ": "Source extraction", "Valeur": body.get("extraction_source") or "—"},
            ]
        )
        warnings = body.get("warnings") or []
        for w in warnings:
            if isinstance(w, dict):
                st.warning(f"{w.get('code', '')}: {w.get('message', '')}")
        tests = body.get("tests") or []
        st.subheader("Résultats d'analyses")
        if tests:
            rows = []
            for t in tests:
                if not isinstance(t, dict):
                    continue
                rows.append(
                    {
                        "Analyse": t.get("raw_test_name") or "—",
                        "Valeur": _valeur_test_dict(t) or "—",
                        "Unité": t.get("unit") or "—",
                    }
                )
            st.dataframe(medical_results_df(rows), width="stretch", hide_index=True)
        else:
            st.caption("Aucune ligne d'analyse.")
        return

    st.subheader("Données extraites")
    st.json(body if body else data)


def load_json_file(path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        raw = path.read_text(encoding="utf-8")
        return json.loads(raw), raw
    except Exception as exc:
        return None, str(exc)
