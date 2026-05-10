from __future__ import annotations

import hashlib
import json
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
try:
    import plotly.express as px
except Exception:  # pragma: no cover - fallback if plotly is not installed
    px = None

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import load_config
from src.services.extraction_history import list_history_entries
from src.web.history_views import load_json_file, render_extraction_detail
from src.web.ui_theme import inject_app_styles, inject_page_theme

_KIND_LABELS_FR = {
    "steg_ocr": "Facture STEG (OCR)",
    "steg_gemini": "Facture STEG",
    "medical_ocr": "Analyse medicale (OCR)",
    "medical_gemini": "Analyse medicale",
    "receipt": "Ticket de caisse",
    "supplier_invoice": "Facture fournisseur",
}


def _kind_label(slug: str) -> str:
    return _KIND_LABELS_FR.get(slug, slug)


def _parse_dt(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _normalize_text(raw: str) -> str:
    return unicodedata.normalize("NFC", (raw or "").strip()).casefold()


def _payload_reference(payload: dict) -> str:
    return _normalize_text(str(payload.get("reference") or ""))


def _payload_patient(payload: dict) -> str:
    raw = payload.get("patient_name")
    if not raw:
        patient_info = payload.get("patient_info") or {}
        if isinstance(patient_info, dict):
            raw = patient_info.get("patient_name")
    return _normalize_text(str(raw or ""))


def _payload_invoice_number(payload: dict) -> str:
    return _normalize_text(str(payload.get("invoice_number") or ""))


def _payload_extraction_quality(payload: dict) -> float | None:
    q = payload.get("extraction_quality")
    if isinstance(q, (int, float)) and not isinstance(q, bool):
        v = float(q)
        if 0.0 <= v <= 1.0:
            return v
    return None


def _payload_warnings_count(payload: dict) -> int:
    w = payload.get("warnings")
    if isinstance(w, list):
        return len(w)
    return 0


def _selected_dataframe_row_index(state: object, num_rows: int) -> int | None:
    if state is None or num_rows <= 0:
        return None
    sel = state["selection"] if isinstance(state, dict) else getattr(state, "selection", None)
    if sel is None:
        return None
    rows = sel["rows"] if isinstance(sel, dict) else getattr(sel, "rows", None)
    if not rows:
        return None
    i = int(rows[0])
    return max(0, min(i, num_rows - 1))


def _method_label(kind: str) -> str:
    if kind.endswith("_gemini") or kind in ("receipt", "supplier_invoice"):
        return "Gemini"
    if kind.endswith("_ocr"):
        return "OCR local"
    return "Mixte"


def _kind_family(kind: str) -> str:
    if kind.startswith("steg_"):
        return "Facture STEG"
    if kind.startswith("medical_"):
        return "Analyse médicale"
    if kind == "receipt":
        return "Ticket de caisse"
    if kind == "supplier_invoice":
        return "Facture fournisseur"
    return "Autre"


def _status_badge(status: str) -> str:
    return "🟢 Succès" if status == "ok" else "🔴 Erreur"


def _format_amount(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "—"
    cleaned = raw.replace(" ", "").replace(",", ".")
    try:
        num = float(cleaned)
    except ValueError:
        return raw
    return f"{num:.2f}"


def _render_dashboard_header() -> None:
    st.markdown(
        """
        <style>
        .dash-hero {
            border: 1px solid rgba(15, 23, 42, 0.10);
            border-left: 5px solid #2563eb;
            border-radius: 12px;
            padding: 14px 16px;
            background: #ffffff;
            box-shadow: 0 4px 12px rgba(15, 23, 42, 0.06);
            margin-bottom: 0.55rem;
        }
        .dash-title { font-size: 1.35rem; font-weight: 700; margin: 0; color: #0f172a; }
        .dash-sub { color: #475569; margin-top: 4px; font-size: 1rem; }
        .dash-badge {
            display: inline-block; padding: 3px 10px; border-radius: 999px;
            font-size: 0.78rem; font-weight: 600; margin-top: 10px;
            background: rgba(22, 163, 74, 0.12); color: #166534; border: 1px solid rgba(22, 163, 74, 0.25);
        }
        .kpi-card {
            border-radius: 12px; padding: 12px 14px; border: 1px solid rgba(120,120,120,0.22);
            min-height: 106px; background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        .kpi-top { font-size: 0.9rem; font-weight: 600; color: #2f2f2f; }
        .kpi-value { font-size: 1.55rem; font-weight: 700; margin-top: 4px; }
        .kpi-help { margin-top: 3px; font-size: 0.78rem; color: #6b7280; }
        .empty-state {
            border: 1px dashed rgba(120,120,120,0.35);
            border-radius: 12px; padding: 22px; text-align: center; color: #5f6368;
        }
        .result-card {
            border: 1px solid rgba(120,120,120,0.22);
            border-radius: 12px;
            padding: 14px;
            background: white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            margin-bottom: 10px;
        }
        .value-row {
            display: grid;
            grid-template-columns: 190px 1fr;
            gap: 10px;
            padding: 8px 0;
            border-bottom: 1px solid rgba(120,120,120,0.16);
        }
        .value-row:last-child { border-bottom: none; }
        .value-label { font-weight: 600; color: #1f2937; }
        .value-data { color: #111827; }
        .summary-card {
            border: 1px solid rgba(120,120,120,0.22);
            border-radius: 12px;
            padding: 10px 12px;
            background: #ffffff;
            min-height: 92px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }
        .summary-label {
            font-size: 0.86rem;
            color: #6b7280;
            margin-bottom: 4px;
            font-weight: 600;
        }
        .summary-value {
            font-size: 1.05rem;
            color: #111827;
            font-weight: 700;
            line-height: 1.2rem;
            white-space: normal;
            word-break: break-word;
        }
        .dash-tile {
            border-radius: 14px;
            border: 1px solid rgba(120,120,120,0.18);
            background: linear-gradient(135deg,#ffffff,#f8fbff);
            box-shadow: 0 10px 20px rgba(15,23,42,0.07);
            padding: 12px;
            min-height: 118px;
        }
        </style>
        <div class="dash-hero">
            <p class="dash-title">Dashboard d'extraction documentaire</p>
            <div class="dash-sub">Suivi des performances, historique et details des traitements (OCR / Gemini).</div>
            <span class="dash-badge">Statut: Operationnel</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _kpi_card(title: str, icon: str, value: str, description: str, color: str) -> None:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-top">{icon} {title}</div>
            <div class="kpi-value" style="color:{color};">{value}</div>
            <div class="kpi-help">{description}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _summary_card(label: str, value: str) -> None:
    st.markdown(
        f"""
        <div class="summary-card">
            <div class="summary-label">{label}</div>
            <div class="summary-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.set_page_config(page_title="Dashboard", layout="wide")
inject_app_styles()
inject_page_theme("dashboard")
_render_dashboard_header()
st.caption("Pour traiter des documents, utilisez la page `Extraction`.")

cfg = load_config()
entries = list_history_entries(cfg)

if not entries:
    st.info("Aucune extraction disponible pour afficher le dashboard.")
    st.stop()

rows = []
for e in entries:
    payload = e.get("payload") if isinstance(e.get("payload"), dict) else {}
    is_error = bool(payload.get("error"))
    dt = _parse_dt(str(e.get("saved_at") or ""))
    rows.append(
        {
            "saved_at": dt,
            "date": dt.date().isoformat() if dt else "inconnue",
            "kind": str(e.get("kind") or "inconnu"),
            "kind_label": _kind_label(str(e.get("kind") or "inconnu")),
            "source_filename": str(e.get("source_filename") or ""),
            "source_filename_norm": _normalize_text(str(e.get("source_filename") or "")),
            "status": "erreur" if is_error else "ok",
            "relative": str(e.get("relative") or ""),
            "reference_norm": _payload_reference(payload),
            "patient_norm": _payload_patient(payload),
            "invoice_norm": _payload_invoice_number(payload),
            "extraction_quality": _payload_extraction_quality(payload),
            "warnings_count": _payload_warnings_count(payload),
            "payload": payload,
            "path": e.get("path"),
        }
    )

df = pd.DataFrame(rows)
kind_options = ["(tous)"] + sorted(df["kind"].dropna().unique().tolist())

st.markdown("### Filtres")
with st.container():
    f1, f2, f3 = st.columns([1.05, 1.2, 0.45], vertical_alignment="bottom")
    with f1:
        selected_kind = st.selectbox(
            "Type de document",
            options=kind_options,
            format_func=lambda k: "Tous les types" if k == "(tous)" else _kind_label(k),
            key="dash_kind_filter",
        )
    with f2:
        name_query = st.text_input(
            "Recherche fichier source",
            value="",
            placeholder="ex. analyse, steg, ticket...",
            help="Filtre sur le nom du fichier source (contient).",
            key="dash_name_query",
        )
    with f3:
        if st.button("Reinitialiser", use_container_width=True):
            for key in ("dash_kind_filter", "dash_name_query", "dash_typed_query", "dash_table_search"):
                st.session_state.pop(key, None)
            st.rerun()

typed_query = ""
if selected_kind in {"steg_gemini", "steg_ocr"}:
    typed_query = st.text_input(
        "Filtrer STEG par reference",
        value="",
        placeholder="ex. 7472...",
        help="Recherche sur la reference extraite.",
        key="dash_typed_query",
    )
elif selected_kind in {"medical_gemini", "medical_ocr"}:
    typed_query = st.text_input(
        "Filtrer medical par patient",
        value="",
        placeholder="ex. nom patient",
        help="Recherche sur le nom du patient extrait.",
        key="dash_typed_query",
    )
elif selected_kind == "supplier_invoice":
    typed_query = st.text_input(
        "Filtrer par numero de facture",
        value="",
        placeholder="ex. INV-…",
        help="Recherche sur invoice_number extrait.",
        key="dash_typed_query",
    )

filtered_df = df.copy()
if selected_kind != "(tous)":
    filtered_df = filtered_df[filtered_df["kind"] == selected_kind]

name_query_norm = _normalize_text(name_query)
if name_query_norm:
    filtered_df = filtered_df[filtered_df["source_filename_norm"].str.contains(name_query_norm, na=False)]

typed_query_norm = _normalize_text(typed_query)
if typed_query_norm:
    if selected_kind in {"steg_gemini", "steg_ocr"}:
        filtered_df = filtered_df[filtered_df["reference_norm"].str.contains(typed_query_norm, na=False)]
    elif selected_kind in {"medical_gemini", "medical_ocr"}:
        filtered_df = filtered_df[filtered_df["patient_norm"].str.contains(typed_query_norm, na=False)]
    elif selected_kind == "supplier_invoice":
        filtered_df = filtered_df[filtered_df["invoice_norm"].str.contains(typed_query_norm, na=False)]

if filtered_df.empty:
    st.warning("Aucun resultat avec ces filtres.")
    st.stop()

total = len(filtered_df)
errors = int((filtered_df["status"] == "erreur").sum())
ok = total - errors
success_rate = (ok / total) * 100 if total else 0.0
type_count = int(filtered_df["kind"].map(_kind_family).nunique())

st.markdown("### Statistiques clés")
k1, k2, k3, k4, k5 = st.columns(5, gap="small")
with k1:
    _kpi_card("Documents traites", "📄", str(total), "Volume total avec filtres actifs", "#1d4ed8")
with k2:
    _kpi_card("Succes", "✅", str(ok), "Extractions sans erreur", "#15803d")
with k3:
    _kpi_card("Erreurs", "⚠️", str(errors), "Extractions en echec", "#c2410c")
with k4:
    _kpi_card("Taux de succes", "📈", f"{success_rate:.1f}%", "Part des extractions sans champ error", "#7c3aed")
with k5:
    _kpi_card("Types visibles", "🧩", str(type_count), "Familles de documents (filtre)", "#0f766e")

with_warnings = int((filtered_df["warnings_count"] > 0).sum())
rate_warn_pct = (with_warnings / total) * 100.0 if total else 0.0

st.markdown("### Statistiques d'extractions")
q1, q2 = st.columns(2, gap="small")
with q1:
    _kpi_card(
        "Avec avertissements",
        "🔔",
        str(with_warnings),
        f"{rate_warn_pct:.1f} % des documents filtres",
        "#b45309",
    )
with q2:
    gemini_n = int((filtered_df["kind"].map(_method_label) == "Gemini").sum())
    ocr_n = int((filtered_df["kind"].map(_method_label) == "OCR local").sum())
    _kpi_card(
        "Pipeline",
        "⚙️",
        f"{gemini_n} / {ocr_n}",
        "Gemini vs OCR local (volume filtre)",
        "#4f46e5",
    )

st.markdown("### Visualisations")
left, right = st.columns(2)
with left:
    st.markdown("**Evolution quotidienne des extractions**")
    by_day = (
        filtered_df[filtered_df["date"] != "inconnue"]
        .groupby("date", as_index=False)
        .size()
        .rename(columns={"size": "documents"})
        .sort_values("date")
    )
    if by_day.empty:
        st.info("Pas assez de dates disponibles.")
    else:
        if px is not None:
            fig_day = px.line(
                by_day,
                x="date",
                y="documents",
                markers=True,
                template="plotly_white",
                title="Activite par jour",
            )
            fig_day.update_traces(
                hovertemplate="Date: %{x}<br>Documents: %{y}<extra></extra>",
                line_color="#2563eb",
                line_shape="spline",
            )
            fig_day.update_layout(
                height=290,
                margin=dict(l=20, r=20, t=45, b=25),
                xaxis_title="Date",
                yaxis_title="Nombre de documents",
            )
            st.plotly_chart(fig_day, use_container_width=True)
        else:
            st.line_chart(by_day.set_index("date")["documents"], height=290)

with right:
    st.markdown("**Repartition des documents par type**")
    by_kind = (
        filtered_df.groupby("kind_label", as_index=False)
        .size()
        .rename(columns={"size": "documents"})
        .sort_values("documents", ascending=False)
    )
    if px is not None and not by_kind.empty:
        fig_kind = px.bar(
            by_kind,
            x="documents",
            y="kind_label",
            orientation="h",
            color="kind_label",
            template="plotly_white",
            title="Repartition par type de document",
            labels={"kind_label": "Type", "documents": "Nombre de documents"},
        )
        fig_kind.update_layout(
            height=290,
            showlegend=False,
            margin=dict(l=20, r=20, t=45, b=25),
            yaxis=dict(automargin=True),
        )
        fig_kind.update_traces(hovertemplate="Type: %{y}<br>Documents: %{x}<extra></extra>")
        st.plotly_chart(fig_kind, use_container_width=True)
    else:
        st.bar_chart(by_kind.set_index("kind_label")["documents"], height=290)

st.markdown("### Bloc analytique IA")
a1, a2 = st.columns([1.15, 1], gap="small")
with a1:
    heat = (
        filtered_df[filtered_df["date"] != "inconnue"]
        .groupby(["date", "status"], as_index=False)
        .size()
        .rename(columns={"size": "documents"})
    )
    if px is not None:
        if not heat.empty:
            fig_heat = px.density_heatmap(
                heat,
                x="date",
                y="status",
                z="documents",
                color_continuous_scale="Blues",
                title="Heatmap activité / statut",
                template="plotly_white",
            )
            fig_heat.update_layout(height=260, margin=dict(l=20, r=20, t=45, b=35))
            st.plotly_chart(fig_heat, use_container_width=True)
        else:
            st.info("Heatmap indisponible: données insuffisantes.")
    else:
        if heat.empty:
            st.info("Données insuffisantes pour le bloc analytique.")
        else:
            st.caption("Mode simplifié (Plotly non installé)")
            fallback = (
                heat.pivot_table(index="date", columns="status", values="documents", fill_value=0)
                .rename(columns={"ok": "Succès", "erreur": "Erreur"})
                .sort_index()
            )
            st.area_chart(fallback, height=260)
            st.dataframe(
                fallback.reset_index().rename(columns={"date": "Date"}),
                width="stretch",
                hide_index=True,
                height=180,
            )
with a2:
    warn_rate = (with_warnings / total * 100.0) if total else 0.0
    st.markdown(
        f"""
        <div class="dash-tile hx-fade-in">
            <div style="font-size:0.86rem;color:#64748b;font-weight:600;">AI HEALTH SCORE</div>
            <div style="font-size:1.9rem;font-weight:800;color:#2563eb;margin-top:4px;">{max(0.0, 100.0 - warn_rate):.1f}%</div>
            <div style="margin-top:5px;color:#475569;font-size:0.86rem;">Basé sur les avertissements, les erreurs et la stabilité du pipeline.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

timeline_df = (
    filtered_df[filtered_df["date"] != "inconnue"]
    .sort_values("saved_at", ascending=False)
    .head(8)[["date", "kind_label", "source_filename", "status"]]
)
st.markdown("### Activité récente & actions rapides")
t1, t2 = st.columns([1.65, 1], gap="small")
with t1:
    if timeline_df.empty:
        st.info("Pas encore d'activité récente exploitable.")
    else:
        tl_rows = []
        for _, r in timeline_df.iterrows():
            state = "Succès" if r["status"] == "ok" else "Erreur"
            tl_rows.append(
                {
                    "Date": r["date"],
                    "Type": r["kind_label"],
                    "Fichier": r["source_filename"],
                    "Statut": state,
                }
            )
        st.dataframe(tl_rows, width="stretch", hide_index=True, height=290)
with t2:
    st.markdown(
        """
        <div class="kpi-card hx-fade-in">
            <div class="kpi-top">⚡ Actions rapides</div>
            <div class="kpi-help" style="margin-top:6px;">Naviguez rapidement dans la plateforme.</div>
            <div style="display:grid; gap:8px; margin-top:10px;">
                <div style="padding:8px 10px; border-radius:10px; background:#eff6ff; border:1px solid #bfdbfe;">1. Ouvrir <b>Extraction</b> pour traiter de nouveaux documents</div>
                <div style="padding:8px 10px; border-radius:10px; background:#f8fafc; border:1px solid #e2e8f0;">2. Vérifier les erreurs dans <b>Historiques</b></div>
                <div style="padding:8px 10px; border-radius:10px; background:#f0fdf4; border:1px solid #bbf7d0;">3. Exporter les rapports PDF depuis le détail</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("### Visualisations (complément)")
viz2a, viz2b = st.columns(2)
with viz2a:
    st.markdown("**Répartition succès / erreur**")
    status_fr = filtered_df["status"].map({"ok": "Succès", "erreur": "Erreur"})
    by_status = status_fr.value_counts().reset_index()
    by_status.columns = ["statut", "documents"]
    if by_status.empty:
        st.info("Aucune donnée.")
    elif px is not None:
        fig_status = px.pie(
            by_status,
            names="statut",
            values="documents",
            hole=0.42,
            template="plotly_white",
            title="Statut des extractions",
            color="statut",
            color_discrete_map={"Succès": "#22c55e", "Erreur": "#f87171"},
        )
        fig_status.update_traces(textposition="inside", textinfo="percent+label+value")
        fig_status.update_layout(height=300, margin=dict(l=20, r=20, t=48, b=20), showlegend=True)
        st.plotly_chart(fig_status, use_container_width=True)
    else:
        st.bar_chart(by_status.set_index("statut")["documents"], height=300)

with viz2b:
    st.markdown("**Volume par moteur (Gemini vs OCR)**")
    _meth_vc = filtered_df["kind"].map(_method_label).value_counts()
    by_method = pd.DataFrame(
        {"methode": _meth_vc.index.astype(str), "documents": _meth_vc.to_numpy(dtype="int64")}
    )
    if by_method.empty:
        st.info("Aucune donnée.")
    elif px is not None:
        fig_m = px.bar(
            by_method,
            x="methode",
            y="documents",
            color="methode",
            template="plotly_white",
            title="Méthode d'extraction",
            labels={"methode": "Méthode", "documents": "Documents"},
            color_discrete_map={"Gemini": "#6366f1", "OCR local": "#0d9488", "Mixte": "#a855f7"},
        )
        fig_m.update_layout(height=300, showlegend=False, margin=dict(l=20, r=20, t=48, b=20))
        fig_m.update_traces(hovertemplate="%{x}<br>Documents: %{y}<extra></extra>")
        st.plotly_chart(fig_m, use_container_width=True)
    else:
        st.bar_chart(by_method.set_index("methode")["documents"], height=300)

st.markdown("### Visualisations (complément)")
st.markdown("**Activité par jour et par type (empilé)**")
with st.container():
    day_kind = filtered_df[filtered_df["date"] != "inconnue"].copy()
    if day_kind.empty:
        st.info("Pas assez de dates pour un empilement par type.")
    else:
        pivot = (
            day_kind.groupby(["date", "kind_label"], as_index=False)
            .size()
            .rename(columns={"size": "documents"})
            .sort_values("date")
        )
        if px is not None and not pivot.empty:
            fig_stack = px.bar(
                pivot,
                x="date",
                y="documents",
                color="kind_label",
                template="plotly_white",
                title="Documents par jour",
                labels={"date": "Date", "documents": "Nombre", "kind_label": "Type"},
            )
            fig_stack.update_layout(
                height=320,
                barmode="stack",
                margin=dict(l=20, r=20, t=48, b=60),
                legend_title_text="Type",
                xaxis_tickangle=-25,
            )
            st.plotly_chart(fig_stack, use_container_width=True)
        elif not pivot.empty:
            wide = pivot.pivot_table(index="date", columns="kind_label", values="documents", fill_value=0)
            st.bar_chart(wide, height=320)
        else:
            st.info("Pas de données agrégées.")

st.markdown("### Documents traités récemment")
table_query = st.text_input(
    "Recherche rapide dans l'historique",
    value="",
    placeholder="Rechercher par type, nom de fichier ou méthode...",
    key="dash_table_search",
)
table_df = filtered_df.head(30).copy()


display_df = pd.DataFrame(
    {
        "Statut": table_df["status"].map(_status_badge),
        "Type": table_df["kind_label"],
        "Fichier source": table_df["source_filename"],
        "Date": table_df["date"],
        "Méthode": table_df["kind"].map(_method_label),
        "Alertes": table_df["warnings_count"].astype(int),
    }
)
if table_query.strip():
    q = _normalize_text(table_query)
    mask = (
        display_df["Type"].map(_normalize_text).str.contains(q, na=False)
        | display_df["Fichier source"].map(_normalize_text).str.contains(q, na=False)
        | display_df["Méthode"].map(_normalize_text).str.contains(q, na=False)
        | display_df["Statut"].map(_normalize_text).str.contains(q, na=False)
        | display_df["Alertes"].astype(str).str.contains(q, na=False)
    )
    display_df = display_df[mask]
    table_df = table_df.loc[display_df.index]

if display_df.empty:
    st.info("Aucune extraction ne correspond aux filtres et a la recherche.")
    st.stop()

st.dataframe(
    display_df,
    width="stretch",
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
    key="dash_sel",
    column_config={
        "Statut": st.column_config.TextColumn("Statut", width="small"),
        "Type": st.column_config.TextColumn("Type", width="medium"),
        "Fichier source": st.column_config.TextColumn("Fichier source", width="large"),
        "Date": st.column_config.TextColumn("Date", width="small"),
        "Méthode": st.column_config.TextColumn("Méthode", width="small"),
        "Alertes": st.column_config.NumberColumn("Alertes", width="small", help="Nombre d'avertissements enregistrés"),
    },
)

idx = _selected_dataframe_row_index(st.session_state.get("dash_sel"), len(display_df))
st.divider()
st.markdown("### Résultat du document")
if idx is None:
    st.markdown(
        """
        <div class="empty-state">
            <div style="font-size:2rem;">🗂️</div>
            <div style="font-weight:600; margin-top:4px;">Aucune extraction selectionnee</div>
            <div style="margin-top:4px;">Selectionnez une ligne du tableau pour afficher les details complets et les exports.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    rec = table_df.iloc[idx]
    if rec is None:
        st.warning("Impossible de retrouver le détail de cette ligne.")
    else:
        data = rec.get("payload")
        if not isinstance(data, dict) or not data:
            p = rec.get("path")
            if isinstance(p, Path):
                data, err = load_json_file(p)
                if data is None:
                    st.error(f"Lecture impossible: {err}")
                    st.stop()
            else:
                st.error("Aucune donnee detaillee disponible pour cette ligne.")
                st.stop()

        kind_dash = str(rec.get("kind") or "")
        st.success(f"Document sélectionné : {rec.get('source_filename') or 'fichier inconnu'}")
        meta1, meta2, meta3, meta4 = st.columns([1, 1.4, 1.15, 1], gap="small")
        with meta1:
            _summary_card("Statut", "Erreur" if rec.get("status") == "erreur" else "Succès")
        with meta2:
            _summary_card("Type", _kind_label(kind_dash))
        with meta3:
            _summary_card("Méthode", _method_label(kind_dash))
        with meta4:
            _summary_card("Date", str(rec.get("date") or "inconnue"))

        body = {k: v for k, v in data.items() if k != "_meta"} if isinstance(data, dict) else {}

        if kind_dash == "receipt":
            st.markdown("#### Ticket de caisse")
            st.markdown('<div class="result-card">', unsafe_allow_html=True)
            receipt_rows = [
                ("Magasin", body.get("store_name") or "—"),
                ("Date", body.get("date") or "—"),
                ("Heure", body.get("time") or "—"),
                ("Numéro ticket", body.get("ticket_number") or "—"),
                ("Devise", body.get("currency") or "—"),
                ("Total", _format_amount(body.get("total"))),
                ("Mode de paiement", body.get("payment_method") or "—"),
            ]
            st.markdown(
                "".join(
                    f'<div class="value-row"><div class="value-label">{label}</div><div class="value-data">{value}</div></div>'
                    for label, value in receipt_rows
                ),
                unsafe_allow_html=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("#### Articles")
            items = body.get("items") or []
            if items:
                rows = []
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    rows.append(
                        {
                            "Description": item.get("description") or "—",
                            "Quantité": item.get("quantity") or "—",
                            "Prix unitaire": _format_amount(item.get("unit_price")),
                            "Total ligne": _format_amount(item.get("line_total")),
                        }
                    )
                if rows:
                    st.dataframe(rows, width="stretch", hide_index=True)
                else:
                    st.info("Aucun article exploitable n'a été détecté.")
            else:
                st.info("Aucun article trouvé pour ce ticket.")
        else:
            render_extraction_detail(data, kind_dash)

        try:
            from src.services.extraction_report_pdf import build_extraction_report_pdf

            kind_pdf = kind_dash or str((data.get("_meta") or {}).get("kind") or "")
            if kind_pdf:
                rep_pdf = build_extraction_report_pdf(data, kind_pdf)
                base = str((data.get("_meta") or {}).get("source_filename") or rec.get("source_filename") or "export")
                stem = Path(base).stem
                st.download_button(
                    "Télécharger PDF",
                    data=rep_pdf,
                    file_name=f"DOCEXTRACT_{stem}.pdf",
                    mime="application/pdf",
                    key=f"dash_docextract_{hashlib.md5(str(rec.get('relative')).encode('utf-8')).hexdigest()[:16]}",
                    use_container_width=True,
                )
        except Exception as exc:
            st.error("Le rapport PDF est temporairement indisponible. Veuillez réessayer.")
