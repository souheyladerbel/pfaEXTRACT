"""Design system global et themes visuels reutilisables."""

from __future__ import annotations

import streamlit as st

_BASE_CSS = """
<style>
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stSidebar"],
    button,
    input,
    textarea,
    select {
        font-family: "Aptos", "Segoe UI", sans-serif !important;
    }
    h1, h2, h3, h4, h5, h6 {
        font-family: "Bahnschrift", "Aptos", sans-serif !important;
        letter-spacing: -0.02em;
    }
    code, pre, .stCodeBlock {
        font-family: "JetBrains Mono", "Consolas", monospace !important;
    }
    .block-container {
        max-width: 1380px;
        padding-top: 1.05rem !important;
        padding-bottom: 2.4rem !important;
    }
    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(980px 420px at 7% -6%, rgba(34, 197, 94, 0.11), transparent 52%),
            radial-gradient(760px 340px at 100% 0%, rgba(16, 185, 129, 0.09), transparent 42%),
            var(--hx-bg) !important;
    }
    [data-testid="stHeader"] {
        background: transparent !important;
    }
    .main .block-container > div {
        animation: hxFadeIn 0.28s ease-out;
    }
    @keyframes hxFadeIn {
        from { opacity: 0; transform: translateY(6px); }
        to { opacity: 1; transform: translateY(0); }
    }
    h1 {
        color: var(--hx-text) !important;
        margin-bottom: 0.2rem !important;
    }
    h2, h3 {
        color: var(--hx-text) !important;
        border-bottom: 1px solid var(--hx-border-soft);
        padding-bottom: 0.28rem;
        margin-top: 1rem !important;
    }
    p, li, label, [data-testid="stWidgetLabel"], .stCaption {
        color: var(--hx-muted) !important;
    }
    a {
        color: var(--hx-link) !important;
    }
    hr {
        border: none;
        border-top: 1px solid var(--hx-border-soft) !important;
        margin-top: 1.2rem !important;
        margin-bottom: 1.2rem !important;
    }
    [data-testid="stSidebar"] {
        background:
            linear-gradient(180deg, var(--hx-side-top) 0%, var(--hx-side-mid) 62%, var(--hx-side-bot) 100%) !important;
        border-right: 1px solid var(--hx-side-border);
    }
    [data-testid="stSidebar"] * {
        color: var(--hx-side-text) !important;
    }
    .hx-side-brand {
        padding: 14px 14px 12px;
        margin-bottom: 0.75rem;
        border-radius: 18px;
        background: linear-gradient(145deg, rgba(34, 197, 94, 0.18), rgba(15, 23, 42, 0.05));
        border: 1px solid rgba(34, 197, 94, 0.22);
        box-shadow: 0 16px 34px rgba(2, 6, 23, 0.18);
    }
    .hx-side-brand-title {
        margin: 0;
        font-size: 1rem;
        font-weight: 800;
        color: #f8fafc;
    }
    .hx-side-brand-sub {
        margin-top: 4px;
        font-size: 0.8rem;
        color: rgba(226, 232, 240, 0.78);
        line-height: 1.45;
    }
    [data-testid="stSidebarNav"] {
        padding-top: 0.2rem;
    }
    [data-testid="stSidebarNav"] a {
        border-radius: 12px;
        margin: 4px 8px;
        padding-top: 4px !important;
        padding-bottom: 4px !important;
        border: 1px solid transparent;
        transition: transform 0.16s ease, background 0.16s ease, border-color 0.16s ease;
    }
    [data-testid="stSidebarNav"] a:hover {
        background: rgba(34, 197, 94, 0.11);
        border-color: rgba(34, 197, 94, 0.2);
        transform: translateX(1px);
    }
    [data-testid="stSidebarNav"] a[aria-current="page"] {
        background: linear-gradient(90deg, rgba(34, 197, 94, 0.18), rgba(16, 185, 129, 0.11));
        border-color: rgba(34, 197, 94, 0.34);
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
    }
    div[data-testid="stMetric"] {
        background: linear-gradient(180deg, var(--hx-card), var(--hx-card-2));
        border: 1px solid var(--hx-border);
        border-radius: 18px;
        padding: 12px 14px;
        box-shadow: var(--hx-shadow);
    }
    div[data-testid="stMetric"] label {
        color: var(--hx-muted) !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: var(--hx-text) !important;
    }
    [data-testid="stDataFrame"] {
        border: 1px solid var(--hx-border) !important;
        border-radius: 18px;
        overflow: hidden;
        box-shadow: var(--hx-shadow);
        background: var(--hx-card);
    }
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div,
    .stTextInput input,
    .stNumberInput input,
    textarea[data-testid="stTextArea"],
    div[data-testid="stFileUploader"] section {
        background: var(--hx-input-bg) !important;
        color: var(--hx-text) !important;
        border-color: var(--hx-border) !important;
        border-radius: 14px !important;
    }
    div[data-baseweb="select"] svg,
    div[data-baseweb="input"] svg,
    .stTextInput input::placeholder,
    textarea::placeholder {
        color: var(--hx-muted) !important;
    }
    [data-testid="stRadio"] > div,
    [data-testid="stCheckbox"] > label,
    [data-testid="stToggle"] > label {
        background: transparent;
    }
    div[data-testid="stExpander"] {
        border: 1px solid var(--hx-border) !important;
        border-radius: 16px !important;
        background: var(--hx-card) !important;
        box-shadow: var(--hx-shadow);
    }
    div[data-testid="stExpander"] details summary p {
        color: var(--hx-text) !important;
        font-weight: 700 !important;
    }
    .stButton button,
    .stDownloadButton button,
    button[kind="secondary"],
    button[kind="primary"] {
        border-radius: 14px !important;
        border: 1px solid rgba(34, 197, 94, 0.32) !important;
        background: linear-gradient(135deg, var(--hx-btn-a), var(--hx-btn-b)) !important;
        color: var(--hx-btn-text) !important;
        min-height: 2.7rem;
        font-weight: 700 !important;
        transition: transform 0.16s ease, box-shadow 0.16s ease, border-color 0.16s ease !important;
        box-shadow: 0 12px 22px rgba(22, 163, 74, 0.14);
    }
    .stButton button:hover,
    .stDownloadButton button:hover {
        transform: translateY(-1px);
        box-shadow: 0 16px 28px rgba(22, 163, 74, 0.2);
        border-color: rgba(34, 197, 94, 0.45) !important;
    }
    .stButton button[kind="secondary"] {
        background: linear-gradient(180deg, var(--hx-card), var(--hx-card-2)) !important;
        color: var(--hx-text) !important;
        box-shadow: var(--hx-shadow);
    }
    .stAlert, .stInfo, .stSuccess, .stWarning, .stError {
        border-radius: 16px !important;
        border-width: 1px !important;
    }
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #22c55e, #16a34a) !important;
    }
</style>
"""

_LIGHT_THEME_CSS = """
<style>
    :root {
        --hx-bg: #f4f7f6;
        --hx-card: #ffffff;
        --hx-card-2: #f7fbf8;
        --hx-text: #101827;
        --hx-muted: #556476;
        --hx-link: #14734c;
        --hx-border: rgba(15, 23, 42, 0.08);
        --hx-border-soft: rgba(15, 23, 42, 0.06);
        --hx-input-bg: #ffffff;
        --hx-side-top: #f7fbf8;
        --hx-side-mid: #eef6f0;
        --hx-side-bot: #e9f4ec;
        --hx-side-border: rgba(21, 128, 61, 0.1);
        --hx-side-text: #0f172a;
        --hx-btn-a: #1bb45d;
        --hx-btn-b: #169c52;
        --hx-btn-text: #f8fffb;
        --hx-shadow: 0 14px 32px rgba(15, 23, 42, 0.06);
    }
    .hx-side-brand-title {
        color: #0f172a;
    }
    .hx-side-brand-sub {
        color: #35524a;
    }
    .hx-side-brand {
        background: linear-gradient(145deg, rgba(34, 197, 94, 0.14), rgba(255, 255, 255, 0.92));
        border-color: rgba(21, 128, 61, 0.14);
        box-shadow: 0 16px 34px rgba(15, 23, 42, 0.08);
    }
</style>
"""

_DARK_THEME_CSS = """
<style>
    :root {
        --hx-bg: #080c12;
        --hx-card: #11161f;
        --hx-card-2: #0d121a;
        --hx-text: #f4f7fb;
        --hx-muted: #93a1b5;
        --hx-link: #62d58b;
        --hx-border: rgba(148, 163, 184, 0.14);
        --hx-border-soft: rgba(148, 163, 184, 0.11);
        --hx-input-bg: #0b1118;
        --hx-side-top: #0d1218;
        --hx-side-mid: #0b1117;
        --hx-side-bot: #080d13;
        --hx-side-border: rgba(148, 163, 184, 0.1);
        --hx-side-text: #ecf3fb;
        --hx-btn-a: #1cc465;
        --hx-btn-b: #14914c;
        --hx-btn-text: #06110a;
        --hx-shadow: 0 18px 38px rgba(0, 0, 0, 0.34);
    }
    [data-testid="stTextInput"] label,
    [data-testid="stNumberInput"] label,
    [data-testid="stSelectbox"] label,
    [data-testid="stRadio"] label,
    [data-testid="stFileUploader"] label,
    [data-testid="stToggle"] label,
    [data-testid="stCheckbox"] label {
        color: #dbe5f1 !important;
    }
    .stAlert p, .stAlert span, .stAlert div {
        color: inherit !important;
    }
</style>
"""


def inject_app_styles(*, show_theme_toggle: bool = True) -> None:
    if "hx_dark_mode" not in st.session_state:
        st.session_state["hx_dark_mode"] = False

    if show_theme_toggle:
        with st.sidebar:
            st.markdown(
                """
                <div class="hx-side-brand">
                    <p class="hx-side-brand-title">DocuAI Workspace</p>
                    <div class="hx-side-brand-sub">
                        Interface de pilotage pour extraction OCR, Gemini et historique.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.toggle(
                "Theme noir",
                key="hx_dark_mode",
                help="Bascule l'interface complete entre un rendu noir et blanc.",
            )
            st.caption("Le theme s'applique a toutes les pages.")

    st.markdown(_BASE_CSS, unsafe_allow_html=True)
    st.markdown(
        _DARK_THEME_CSS if st.session_state.get("hx_dark_mode") else _LIGHT_THEME_CSS,
        unsafe_allow_html=True,
    )


def get_plotly_template() -> str:
    return "plotly_dark" if st.session_state.get("hx_dark_mode") else "plotly_white"


def inject_page_theme(page: str) -> None:
    styles = {
        "dashboard": """
        <style>
        .hx-page-shell {
            padding: 4px 0 0;
        }
        .hx-page-hero {
            border-radius: 26px;
            padding: 22px 24px;
            background:
                linear-gradient(145deg, rgba(16, 185, 129, 0.18), rgba(15, 23, 42, 0.02)),
                var(--hx-card);
            border: 1px solid var(--hx-border);
            box-shadow: var(--hx-shadow);
        }
        .hx-page-hero .sub {
            color: var(--hx-muted);
            font-size: 0.94rem;
            line-height: 1.55;
        }
        </style>
        """,
        "extraction": """
        <style>
        .hx-guided-note {
            padding: 12px 14px;
            border-radius: 16px;
            border: 1px solid var(--hx-border);
            background: linear-gradient(180deg, var(--hx-card), var(--hx-card-2));
            box-shadow: var(--hx-shadow);
        }
        .hx-guided-note b {
            color: var(--hx-text);
        }
        </style>
        """,
        "history": """
        <style>
        .hx-archive-hero {
            border-radius: 24px;
            padding: 18px 20px;
            background:
                linear-gradient(145deg, rgba(22, 163, 74, 0.12), rgba(15, 23, 42, 0.02)),
                var(--hx-card);
            border: 1px solid var(--hx-border);
            box-shadow: var(--hx-shadow);
        }
        .hx-archive-chip {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
            background: rgba(34, 197, 94, 0.12);
            color: var(--hx-text);
            border: 1px solid rgba(34, 197, 94, 0.24);
        }
        </style>
        """,
    }
    if page in styles:
        st.markdown(styles[page], unsafe_allow_html=True)
