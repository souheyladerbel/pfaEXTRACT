"""Design system global + thèmes visuels par page."""

from __future__ import annotations

import streamlit as st

_APP_CSS = """
<style>
    :root{
        --hx-primary:#2563EB;
        --hx-secondary:#0F172A;
        --hx-success:#22C55E;
        --hx-warning:#F59E0B;
        --hx-danger:#EF4444;
        --hx-bg:#F8FAFC;
        --hx-card:#FFFFFF;
        --hx-border:#dbe5f1;
    }
    .block-container {
        padding-top: 1.1rem !important;
        padding-bottom: 2rem !important;
        max-width: 1240px;
    }
    [data-testid="stAppViewContainer"]{
        background: radial-gradient(1200px 500px at 6% -10%, rgba(37, 99, 235, 0.08), transparent 50%),
                    radial-gradient(1200px 500px at 100% 0%, rgba(15, 23, 42, 0.06), transparent 40%),
                    var(--hx-bg);
    }
    h1 {
        color: var(--hx-secondary) !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em;
        margin-bottom: 0.25rem !important;
    }
    h2, h3 {
        color: #1e3a5f !important;
        font-weight: 600 !important;
        margin-top: 0.85rem !important;
        padding-bottom: 0.25rem;
        border-bottom: 1px solid #e8f0fa;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 62%, #111827 100%);
        border-right: 1px solid rgba(148, 163, 184, 0.24);
    }
    [data-testid="stSidebar"] * {
        color: #e2e8f0 !important;
    }
    [data-testid="stSidebarNav"] a {
        border-radius: 10px;
        margin: 2px 6px;
        transition: all 0.18s ease;
    }
    [data-testid="stSidebarNav"] a:hover {
        background: rgba(37, 99, 235, 0.24);
        transform: translateX(1px);
    }
    [data-testid="stSidebarNav"] a[aria-current="page"] {
        background: linear-gradient(90deg, rgba(37,99,235,0.35), rgba(37,99,235,0.2));
        border: 1px solid rgba(96,165,250,0.45);
    }
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #ffffff 0%, #f8fbff 100%);
        border: 1px solid var(--hx-border);
        border-radius: 14px;
        padding: 10px 14px;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.06);
    }
    div[data-testid="stMetric"] label {
        color: #64748b !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #1a3a5c !important;
    }
    [data-testid="stDataFrame"] {
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.05);
    }
    .stDownloadButton button,
    .stButton button,
    div[data-testid="column"] button[kind="secondary"],
    div[data-testid="column"] button[kind="primary"] {
        border-radius: 10px !important;
        transition: all 0.2s ease !important;
    }
    .stButton button:hover,
    .stDownloadButton button:hover {
        transform: translateY(-1px);
        box-shadow: 0 7px 16px rgba(37, 99, 235, 0.18);
    }
    div[data-testid="stExpander"] {
        border: 1px solid #e5edf7;
        border-radius: 12px;
        background: #fafbfd;
    }
    @keyframes hxFadeIn {
        from { opacity: 0; transform: translateY(6px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .hx-fade-in { animation: hxFadeIn 0.35s ease-out; }
    hr {
        margin-top: 1.25rem !important;
        margin-bottom: 1.25rem !important;
        border: none;
        border-top: 1px solid #e8f0fa;
    }
</style>
"""

_DARK_OVERRIDES_CSS = """
<style>
    :root{
        --hx-bg:#0b1020;
        --hx-card:#111827;
        --hx-border:#1f2937;
    }
    [data-testid="stAppViewContainer"]{
        background: radial-gradient(1200px 500px at 6% -10%, rgba(99, 102, 241, 0.14), transparent 50%),
                    radial-gradient(900px 480px at 100% 8%, rgba(139, 92, 246, 0.12), transparent 42%),
                    #0b1020 !important;
    }
    .main .block-container{
        background: transparent !important;
    }
    section.main > div{
        background: transparent !important;
    }
    .block-container h1, .block-container h2, .block-container h3 {
        color: #f1f5f9 !important;
        border-bottom-color: rgba(51,65,85,0.65) !important;
    }
    .block-container p, .block-container span:not(.hx-xp-*), .block-container label,
    [data-testid="stWidgetLabel"]{
        color: #cbd5e1 !important;
    }
    div[data-testid="stMetric"],
    div[data-testid="stExpander"],
    [data-testid="stDataFrame"],
    div[data-testid="element-container"] [data-baseweb="select"]{
        background: #111827 !important;
        border-color: #1f2937 !important;
        box-shadow: 0 12px 28px rgba(0,0,0,0.35);
    }
    div[data-testid="stMarkdownContainer"] p:not(.hx-xp-sub){
        color: #94a3b8 !important;
    }
    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div,
    textarea[data-testid="stTextArea"], div[data-baseweb="input"] input{
        background: #0f172a !important;
        color: #e2e8f0 !important;
        border-color: #334155 !important;
    }
    .stButton button, .stDownloadButton button {
        background: linear-gradient(135deg,#1e1b4b,#312e81);
        border: 1px solid rgba(99,102,241,0.45);
        color: #f8fafc;
    }
    hr{
        border-top-color: rgba(51,65,85,0.65) !important;
    }
</style>
"""


def inject_app_styles() -> None:
    if "hx_dark_mode" not in st.session_state:
        st.session_state["hx_dark_mode"] = False
    with st.sidebar:
        st.session_state["hx_dark_mode"] = st.toggle(
            "Mode sombre",
            value=bool(st.session_state.get("hx_dark_mode", False)),
            help="Basculer entre thème clair et sombre.",
        )
    st.markdown(_APP_CSS, unsafe_allow_html=True)
    if st.session_state.get("hx_dark_mode"):
        st.markdown(_DARK_OVERRIDES_CSS, unsafe_allow_html=True)


def inject_page_theme(page: str) -> None:
    """Injecte un style additionnel spécifique à la page."""
    styles = {
        "dashboard": """
        <style>
        .hx-page-hero{
            background: linear-gradient(120deg, #0f172a 0%, #1e3a8a 48%, #2563eb 100%);
            border-radius: 16px;
            padding: 18px 18px;
            color: white;
            box-shadow: 0 16px 30px rgba(30, 58, 138, 0.28);
        }
        .hx-page-hero .sub{ color: rgba(226,232,240,0.94); font-size: 0.94rem; }
        </style>
        """,
        "extraction": """
        <style>
        /* Ancien hero remplacé par extraction_workspace_ui — styles légers résiduels si besoin */
        </style>
        """,
        "history": """
        <style>
        .hx-archive-hero{
            border: 1px solid #dbe5f1;
            border-left: 6px solid #2563EB;
            border-radius: 14px;
            background: linear-gradient(180deg, #ffffff, #f8fafc);
            padding: 14px 16px;
            box-shadow: 0 12px 24px rgba(15,23,42,0.07);
        }
        .hx-archive-chip{
            display:inline-block; padding:4px 10px; border-radius:999px; font-size:12px; font-weight:600;
            background:#e2e8f0; color:#334155;
        }
        </style>
        """,
    }
    if page in styles:
        st.markdown(styles[page], unsafe_allow_html=True)
