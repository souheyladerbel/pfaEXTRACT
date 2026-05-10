from __future__ import annotations

import hashlib
import json
import sys
import unicodedata
from datetime import date, datetime, timedelta
from math import ceil
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import load_config
from src.services import extraction_history as extraction_history_service
from src.web.history_detail_modal import (
    HIST_MODAL_ENTRY_KEY,
    HIST_MODAL_SHOULD_OPEN,
    history_modal_entry_key,
    open_history_detail_modal,
)
from src.web.history_entry_utils import entry_payload_for_report
from src.web.ui_theme import inject_app_styles, inject_page_theme

_KIND_LABELS_FR: dict[str, str] = {
    "steg_ocr": "Facture STEG (OCR Tesseract)",
    "steg_gemini": "Facture STEG",
    "medical_ocr": "Analyse médicale (OCR structuré)",
    "medical_gemini": "Analyse médicale",
    "receipt": "Ticket de caisse",
    "supplier_invoice": "Facture fournisseur (générique)",
}

# Types OCR retirés du filtre (l’app n’utilise plus ces flux) ; les JSON restent visibles sous « Tous les types ».
_FILTER_EXCLUDED_KINDS = frozenset({"steg_ocr", "medical_ocr"})


def _kind_label_fr(slug: str) -> str:
    if slug == "(tous)":
        return "Tous les types"
    return _KIND_LABELS_FR.get(slug, slug)


def _entry_saved_date(entry: dict) -> date | None:
    """Date locale (jour) d’après ``saved_at`` ou le préfixe horodaté du nom de fichier."""
    raw = (entry.get("saved_at") or "").strip()
    if raw:
        try:
            iso = raw.replace("Z", "+00:00")
            return datetime.fromisoformat(iso).date()
        except ValueError:
            pass
    name = entry.get("path")
    if isinstance(name, Path):
        name = name.name
    else:
        name = str(name or "")
    if len(name) >= 8 and name[:8].isdigit():
        try:
            return datetime.strptime(name[:8], "%Y%m%d").date()
        except ValueError:
            pass
    return None


def _date_bounds(entries: list[dict]) -> tuple[date, date]:
    ds = [d for e in entries if (d := _entry_saved_date(e)) is not None]
    if not ds:
        t = date.today()
        return t, t
    return min(ds), max(ds)


def _normalize_search_q(raw: str) -> str:
    """Texte de recherche normalisé (trim, Unicode NFC, casse)."""
    s = unicodedata.normalize("NFC", (raw or "").strip())
    return s.casefold()


def _entry_source_filename_normalized(entry: dict) -> str:
    """Nom du fichier source seul (NFC + casefold) — pas la date ni le chemin JSON."""
    raw = entry.get("source_filename") or ""
    return unicodedata.normalize("NFC", raw).casefold()


def _entry_matches_search(entry: dict, needle: str) -> bool:
    """True si le nom du fichier source contient ``needle`` (déjà normalisé), insensible à la casse."""
    if not needle:
        return True
    name = _entry_source_filename_normalized(entry)
    return needle in name


def _entry_reference_normalized(entry: dict) -> str:
    """Reference STEG normalisee depuis le payload."""
    payload = entry.get("payload")
    if not isinstance(payload, dict):
        return ""
    raw = payload.get("reference") or ""
    return unicodedata.normalize("NFC", str(raw)).casefold()


def _entry_invoice_number_normalized(entry: dict) -> str:
    """Numero de facture fournisseur normalise depuis le payload."""
    payload = entry.get("payload")
    if not isinstance(payload, dict):
        return ""
    raw = payload.get("invoice_number") or ""
    return unicodedata.normalize("NFC", str(raw)).casefold()


def _entry_patient_normalized(entry: dict) -> str:
    """Patient normalise depuis payload medical Gemini/OCR."""
    payload = entry.get("payload")
    if not isinstance(payload, dict):
        return ""
    raw = payload.get("patient_name")
    if not raw:
        patient_info = payload.get("patient_info") or {}
        if isinstance(patient_info, dict):
            raw = patient_info.get("patient_name")
    return unicodedata.normalize("NFC", str(raw or "")).casefold()


def _entry_matches_type_filter(entry: dict, selected_kind: str, needle: str) -> bool:
    """Filtre metier selon type: STEG par reference, medical par patient."""
    if not needle:
        return True
    if selected_kind in {"steg_gemini", "steg_ocr"}:
        return needle in _entry_reference_normalized(entry)
    if selected_kind in {"medical_gemini", "medical_ocr"}:
        return needle in _entry_patient_normalized(entry)
    if selected_kind == "supplier_invoice":
        return needle in _entry_invoice_number_normalized(entry)
    return True


def _kind_select_index(options: list[str], current: str) -> int:
    try:
        return options.index(current)
    except ValueError:
        return 0


st.set_page_config(page_title="Historique extractions", layout="wide")
inject_app_styles()
inject_page_theme("history")
st.markdown(
    """
    <style>
    .hist-hero{
        border:1px solid rgba(15,23,42,0.10);
        border-left:5px solid #2563eb;
        border-radius:12px;
        padding:14px 16px;
        background:#ffffff;
        box-shadow:0 4px 12px rgba(15,23,42,0.06);
        margin-bottom:0.75rem;
    }
    .hist-title{font-size:1.35rem;font-weight:700;color:#0f172a;margin:0;}
    .hist-sub{color:#475569;margin-top:4px;}
    .hist-badge{
        display:inline-block;padding:3px 10px;border-radius:999px;margin-top:10px;
        background:rgba(22,163,74,0.12);color:#166534;border:1px solid rgba(22,163,74,0.25);
        font-size:0.78rem;font-weight:600;
    }
    .panel-card{
        border:1px solid rgba(120,120,120,0.22);
        border-radius:12px;
        padding:12px;
        background:#ffffff;
        box-shadow:0 2px 8px rgba(0,0,0,0.04);
        margin-bottom:10px;
    }
    .kpi-card{min-height:98px;}
    .kpi-title{font-size:0.88rem;font-weight:600;color:#374151;}
    .kpi-value{font-size:1.55rem;font-weight:700;margin-top:5px;}
    .kpi-sub{font-size:0.78rem;color:#6b7280;margin-top:3px;}
    .doc-card{
        border:1px solid rgba(120,120,120,0.22);
        border-radius:12px;
        padding:10px 12px;
        background:#ffffff;
        box-shadow:0 2px 8px rgba(0,0,0,0.04);
        margin-bottom:8px;
        transition: all .18s ease;
    }
    .doc-card:hover{
        transform: translateY(-1px);
        box-shadow:0 10px 18px rgba(15,23,42,0.10);
    }
    .doc-card.selected{
        border-color:#93c5fd;
        box-shadow:0 0 0 2px rgba(37,99,235,0.15);
        background:#f8fbff;
    }
    .status-badge{
        display:inline-block;padding:3px 10px;border-radius:999px;font-size:12px;font-weight:700;
    }
    .status-ok{background:#dcfce7;color:#166534;border:1px solid #86efac;}
    .status-err{background:#fee2e2;color:#991b1b;border:1px solid #fca5a5;}
    .empty-state{
        border:1px dashed rgba(120,120,120,0.35);
        border-radius:12px;padding:22px;text-align:center;color:#5f6368;
    }
    </style>
    <div class="hx-archive-hero hx-fade-in">
        <p class="hist-title">Document Management Center</p>
        <div class="hist-sub">Archive intelligente des traitements avec filtres avancés, statut qualité et accès rapide aux détails.</div>
        <span class="hx-archive-chip">Enterprise archive view</span>
    </div>
    """,
    unsafe_allow_html=True,
)

cfg = load_config()

with st.spinner("Chargement de l'historique..."):
    entries = extraction_history_service.list_history_entries(cfg)
if not entries:
    st.markdown(
        """
        <div class="empty-state">
            <div style="font-size:2rem;">📄</div>
            <div style="font-weight:600; margin-top:4px;">Aucun document disponible</div>
            <div style="margin-top:4px;">Lancez une extraction depuis la page Extraction pour alimenter l'historique.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

kinds_all = sorted({e["kind"] for e in entries})
kinds_filtered = sorted(k for k in kinds_all if k not in _FILTER_EXCLUDED_KINDS)
kind_options = ["(tous)"] + kinds_filtered

d_lo, d_hi = _date_bounds(entries)
if "hist_applied" not in st.session_state:
    st.session_state.hist_applied = {
        "filter_kind": "(tous)",
        "search": "",
        "type_query": "",
        "use_period": False,
        "d_start": d_lo,
        "d_end": d_hi,
    }

applied = st.session_state.hist_applied
if applied.get("filter_kind") not in kind_options:
    st.session_state.hist_applied = {**applied, "filter_kind": "(tous)"}
    applied = st.session_state.hist_applied
if "type_query" not in applied:
    st.session_state.hist_applied = {**applied, "type_query": ""}
    applied = st.session_state.hist_applied

# Éviter value= sur le texte dans le form : il se réinitialisait à chaque rerun (ex. clic tableau).
if "hist_search_field" not in st.session_state:
    st.session_state.hist_search_field = applied.get("search") or ""
if "hist_type_filter_field" not in st.session_state:
    st.session_state.hist_type_filter_field = applied.get("type_query") or ""

with st.form("historique_filtres", clear_on_submit=False):
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)
    l1c1, l1c2 = st.columns([1, 1.2], gap="small")
    with l1c1:
        filter_kind = st.selectbox(
            "📁 Type de document",
            options=kind_options,
            index=_kind_select_index(kind_options, applied["filter_kind"]),
            format_func=_kind_label_fr,
        )
    with l1c2:
        st.text_input(
            "🔎 Recherche fichier",
            key="hist_search_field",
            placeholder="Rechercher par nom de fichier...",
        )
    l2c1, l2c2, l2c3, l2c4 = st.columns([1, 1, 0.7, 0.6], gap="small")
    with l2c1:
        d_start = st.date_input(
            "📅 Date début",
            value=applied.get("d_start") or d_lo,
            min_value=date(2000, 1, 1),
            max_value=date.today() + timedelta(days=1),
        )
    with l2c2:
        d_end = st.date_input(
            "📅 Date fin",
            value=applied.get("d_end") or d_hi,
            min_value=date(2000, 1, 1),
            max_value=date.today() + timedelta(days=1),
        )
    with l2c3:
        use_period = st.checkbox("Activer période", value=applied["use_period"])
    with l2c4:
        submitted = st.form_submit_button("Appliquer", type="primary", use_container_width=True)
    reset = st.form_submit_button("Réinitialiser", use_container_width=False)
    st.markdown("</div>", unsafe_allow_html=True)

    with st.container():
        if filter_kind in {"steg_gemini", "steg_ocr"}:
            st.text_input(
                "Filtrer par référence STEG",
                key="hist_type_filter_field",
                placeholder="ex. 7472...",
                help="Recherche dans le champ `reference` extrait.",
            )
        elif filter_kind in {"medical_gemini", "medical_ocr"}:
            st.text_input(
                "Filtrer par patient (analyse médicale)",
                key="hist_type_filter_field",
                placeholder="ex. nom patient",
                help="Recherche dans le champ patient extrait.",
            )
        elif filter_kind == "supplier_invoice":
            st.text_input(
                "Filtrer par numéro de facture",
                key="hist_type_filter_field",
                placeholder="ex. INV-2024…",
                help="Recherche dans invoice_number extrait.",
            )
        else:
            st.caption(
                "Filtre métier : STEG / médical / facture fournisseur pour référence, patient ou N° facture."
            )

if reset:
    st.session_state.hist_applied = {
        "filter_kind": "(tous)",
        "search": "",
        "type_query": "",
        "use_period": False,
        "d_start": d_lo,
        "d_end": d_hi,
    }
    st.session_state.hist_search_field = ""
    st.session_state.hist_type_filter_field = ""
    applied = st.session_state.hist_applied
    st.rerun()

if submitted:
    lo, hi = (d_start, d_end) if d_start <= d_end else (d_end, d_start)
    st.session_state.hist_applied = {
        "filter_kind": filter_kind,
        "search": _normalize_search_q(st.session_state.get("hist_search_field", "")),
        "type_query": _normalize_search_q(st.session_state.get("hist_type_filter_field", "")),
        "use_period": use_period,
        "d_start": lo,
        "d_end": hi,
    }
    applied = st.session_state.hist_applied

filtered = entries
if applied["filter_kind"] != "(tous)":
    filtered = [e for e in filtered if e["kind"] == applied["filter_kind"]]
if applied["search"]:
    q = applied["search"]
    filtered = [e for e in filtered if _entry_matches_search(e, q)]
if applied.get("type_query"):
    q_type = applied.get("type_query") or ""
    filtered = [e for e in filtered if _entry_matches_type_filter(e, applied["filter_kind"], q_type)]
if applied["use_period"]:
    lo, hi = applied["d_start"], applied["d_end"]
    filtered = [
        e for e in filtered if (ed := _entry_saved_date(e)) is not None and lo <= ed <= hi
    ]

ok_count = sum(
    1
    for e in filtered
    if not (isinstance(e.get("payload"), dict) and e.get("payload", {}).get("error"))
)
err_count = max(0, len(filtered) - ok_count)
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(
        f'<div class="panel-card kpi-card"><div class="kpi-title">📄 Entrées affichées</div><div class="kpi-value" style="color:#1d4ed8;">{len(filtered)}</div><div class="kpi-sub">Documents après filtres</div></div>',
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        f'<div class="panel-card kpi-card"><div class="kpi-title">✅ Succès</div><div class="kpi-value" style="color:#15803d;">{ok_count}</div><div class="kpi-sub">Traitements sans erreur</div></div>',
        unsafe_allow_html=True,
    )
with c3:
    st.markdown(
        f'<div class="panel-card kpi-card"><div class="kpi-title">⚠️ Erreurs</div><div class="kpi-value" style="color:#b91c1c;">{err_count}</div><div class="kpi-sub">Documents à vérifier</div></div>',
        unsafe_allow_html=True,
    )

if not filtered:
    st.markdown(
        """
        <div class="empty-state">
            <div style="font-size:2rem;">🔎</div>
            <div style="font-weight:600; margin-top:4px;">Aucun document trouvé</div>
            <div style="margin-top:4px;">Ajustez les filtres puis cliquez sur Appliquer.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

# Nouvelle clé quand les filtres appliqués changent → sélection du tableau remise à zéro.
_period_part = ""
if applied["use_period"] and applied.get("d_start") and applied.get("d_end"):
    _period_part = f"|{applied['d_start'].isoformat()}|{applied['d_end'].isoformat()}"
_df_key = hashlib.md5(
    f"{applied['filter_kind']}|{applied['search']}|{applied.get('type_query', '')}|{applied['use_period']}{_period_part}".encode("utf-8")
).hexdigest()[:16]

sel_key = f"hist_detail_idx_{_df_key}"
if sel_key not in st.session_state:
    st.session_state[sel_key] = None
pending_delete_key = f"hist_pending_delete_{_df_key}"
if pending_delete_key not in st.session_state:
    st.session_state[pending_delete_key] = None

st.markdown("### Documents traités récemment")
page_size = 8
total_pages = max(1, ceil(len(filtered) / page_size))
page_state_key = f"hist_page_{_df_key}"
if page_state_key not in st.session_state:
    st.session_state[page_state_key] = 1
page_num = int(st.session_state[page_state_key])
page_num = max(1, min(page_num, total_pages))
st.session_state[page_state_key] = page_num

pg1, pg2, pg3 = st.columns([0.25, 0.5, 0.25])
with pg1:
    if st.button("⬅ Précédent", disabled=page_num <= 1, use_container_width=True):
        st.session_state[page_state_key] = max(1, page_num - 1)
        st.rerun()
with pg2:
    st.markdown(f"<div style='text-align:center; padding-top:8px;'>Page <b>{page_num}</b> / {total_pages}</div>", unsafe_allow_html=True)
with pg3:
    if st.button("Suivant ➡", disabled=page_num >= total_pages, use_container_width=True):
        st.session_state[page_state_key] = min(total_pages, page_num + 1)
        st.rerun()

start = (int(page_num) - 1) * page_size
end = start + page_size
visible = filtered[start:end]

for local_i, e in enumerate(visible):
    i = start + local_i
    is_selected_row = st.session_state.get(sel_key) == i
    stat_is_error = isinstance(e.get("payload"), dict) and e["payload"].get("error")
    stat_txt = "Erreur" if stat_is_error else "OK"
    typ = _kind_label_fr(e["kind"])
    fn = e.get("source_filename") or "—"
    dt = (e.get("saved_at") or "—")[:19] if e.get("saved_at") else "—"

    st.markdown(f'<div class="doc-card {"selected" if is_selected_row else ""}">', unsafe_allow_html=True)
    top = st.columns([1, 1.4, 1.8, 1.2], gap="small")
    with top[0]:
        st.markdown(
            '<span class="status-badge status-ok">Succès</span>' if stat_txt == "OK"
            else '<span class="status-badge status-err">Erreur</span>',
            unsafe_allow_html=True,
        )
    with top[1]:
        st.caption("Type")
        st.markdown(f"**{typ}**")
    with top[2]:
        st.caption("Fichier")
        st.markdown(f"`{fn[:44]}{'…' if len(fn) > 44 else ''}`")
    with top[3]:
        st.caption("Date")
        st.markdown(f"**{dt}**")

    act = st.columns([0.9, 1.2, 1.1, 1], gap="small")
    with act[0]:
        if st.button("👁️ Voir détail", key=f"hist_pick_{_df_key}_{i}", use_container_width=True):
            st.session_state[sel_key] = i
            st.session_state[HIST_MODAL_ENTRY_KEY] = history_modal_entry_key(e)
            st.session_state[HIST_MODAL_SHOULD_OPEN] = True
    with act[1]:
        data_row = entry_payload_for_report(e, cfg)
        if stat_txt == "OK" and isinstance(data_row, dict) and not data_row.get("error"):
            try:
                from src.services.extraction_report_pdf import build_extraction_report_pdf

                kind_row = str(e.get("kind") or (data_row.get("_meta") or {}).get("kind") or "")
                if kind_row:
                    rep_b = build_extraction_report_pdf(data_row, kind_row)
                    stem = Path(fn).stem if fn and fn != "—" else f"ligne_{i}"
                    st.download_button(
                        "⬇ Télécharger",
                        data=rep_b,
                        file_name=f"DOCEXTRACT_{stem}.pdf",
                        mime="application/pdf",
                        key=f"hist_rep_{_df_key}_{i}",
                        use_container_width=True,
                    )
                else:
                    st.button("⬇ Télécharger", disabled=True, use_container_width=True, key=f"hist_rep_dis_{_df_key}_{i}")
            except Exception:
                st.button("⬇ Télécharger", disabled=True, use_container_width=True, key=f"hist_rep_exc_{_df_key}_{i}")
        else:
            st.button("⬇ Télécharger", disabled=True, use_container_width=True, key=f"hist_rep_na_{_df_key}_{i}")
    with act[2]:
        if st.session_state.get(pending_delete_key) == i:
            cdel1, cdel2 = st.columns(2)
            with cdel1:
                if st.button("✅", key=f"hist_del_ok_{_df_key}_{i}", help="Confirmer suppression", use_container_width=True):
                    delete_fn = getattr(extraction_history_service, "delete_history_entry", None)
                    if delete_fn is None:
                        st.error("La suppression est indisponible pour le moment.")
                        st.stop()
                    ok, msg = delete_fn(cfg, e)
                    if ok:
                        st.session_state[sel_key] = None
                        st.session_state[pending_delete_key] = None
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
            with cdel2:
                if st.button("✖", key=f"hist_del_no_{_df_key}_{i}", help="Annuler", use_container_width=True):
                    st.session_state[pending_delete_key] = None
                    st.rerun()
        elif st.button("🗑️ Supprimer", key=f"hist_del_{_df_key}_{i}", use_container_width=True):
            st.session_state[pending_delete_key] = i
            st.rerun()
    with act[3]:
        if is_selected_row:
            st.success("Sélectionné")
    st.markdown("</div>", unsafe_allow_html=True)

idx = st.session_state.get(sel_key)
if idx is not None and (not isinstance(idx, int) or idx < 0 or idx >= len(filtered)):
    st.session_state[sel_key] = None

st.divider()
st.markdown("### Consulter le détail")
st.markdown(
    """
    <div class="empty-state">
        <div style="font-size:2rem;">📋</div>
        <div style="font-weight:600; margin-top:4px;">Fenêtre de consultation</div>
        <div style="margin-top:4px;">Cliquez sur <strong>Voir détail</strong> sur une ligne pour ouvrir la modale : résumé, données extraites, JSON, document source et exports.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

_modal_k = st.session_state.get(HIST_MODAL_ENTRY_KEY)
if _modal_k and st.session_state.pop(HIST_MODAL_SHOULD_OPEN, False):
    _modal_entry = next((e for e in filtered if history_modal_entry_key(e) == _modal_k), None)
    if _modal_entry is not None:
        open_history_detail_modal(_modal_entry, cfg)
    else:
        st.session_state.pop(HIST_MODAL_ENTRY_KEY, None)
