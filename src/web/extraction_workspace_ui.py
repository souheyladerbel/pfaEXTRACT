"""
UI premium pour la page Extraction — HTML/CSS + helpers Streamlit (sans logique métier).
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from streamlit.column_config import TextColumn

_EXTRACTION_CSS_STRUCTURE = """
<style>
/* Hero glass */
.hx-xp-hero{
    position:relative;
    overflow:hidden;
    border-radius:20px;
    padding:28px 28px 22px;
    margin-bottom:20px;
    background:linear-gradient(135deg,
        rgba(99,102,241,0.14) 0%,
        rgba(139,92,246,0.10) 45%,
        rgba(255,255,255,0.06) 100%);
    border:1px solid var(--hx-w-border);
    box-shadow:0 20px 50px rgba(15,23,42,0.12), inset 0 1px 0 rgba(255,255,255,0.45);
    backdrop-filter:blur(14px);
    -webkit-backdrop-filter:blur(14px);
}
.hx-xp-hero::before{
    content:"";
    position:absolute; inset:-40% 40% auto -20%;
    height:120%;
    background:radial-gradient(ellipse at center, var(--hx-w-glow), transparent 55%);
    opacity:0.5;
    pointer-events:none;
}
.hx-xp-hero-inner{ position:relative; z-index:1; }
.hx-xp-title{
    font-size:clamp(1.35rem, 2.2vw, 1.85rem);
    font-weight:800;
    letter-spacing:-0.03em;
    color:var(--hx-w-text);
    margin:0 0 6px;
    display:flex;
    align-items:center;
    gap:12px;
}
.hx-xp-title-icon{
    width:44px;height:44px;border-radius:14px;
    display:inline-flex;align-items:center;justify-content:center;
    background:linear-gradient(135deg,var(--hx-w-accent),var(--hx-w-accent2));
    color:#fff;font-size:20px;
    box-shadow:0 10px 28px rgba(99,102,241,0.35);
}
.hx-xp-sub{ color:var(--hx-w-muted); font-size:0.98rem; max-width:720px; line-height:1.55; margin:0; }
.hx-xp-badges{ margin-top:18px; display:flex; flex-wrap:wrap; gap:8px; }
.hx-xp-badge{
    font-size:11px; font-weight:700; letter-spacing:0.06em; text-transform:uppercase;
    padding:7px 12px; border-radius:999px;
    background:var(--hx-w-card2);
    border:1px solid var(--hx-w-border);
    color:var(--hx-w-muted);
    transition:transform .2s ease, box-shadow .2s ease;
}
.hx-xp-badge--on{
    background:linear-gradient(90deg,rgba(99,102,241,0.15),rgba(139,92,246,0.12));
    border-color:rgba(99,102,241,0.35);
    color:var(--hx-w-text);
    box-shadow:0 0 20px rgba(99,102,241,0.15);
}

/* Upload zone */
.hx-xp-upload-shell{
    border-radius:20px;
    padding:4px;
    background:linear-gradient(135deg,rgba(99,102,241,0.25),rgba(139,92,246,0.15),rgba(59,130,246,0.12));
    margin-bottom:16px;
}
.hx-xp-upload-shell-inner{
    border-radius:17px;
    background:var(--hx-w-card);
    padding:8px 10px 14px;
}
div[data-testid="stFileUploader"]{
    border:none !important;
    background:transparent !important;
    box-shadow:none !important;
    padding:4px 4px 8px !important;
}
div[data-testid="stFileUploader"] section{
    border:2px dashed rgba(99,102,241,0.35) !important;
    border-radius:16px !important;
    background:var(--hx-w-card2) !important;
    min-height:168px !important;
    transition:border-color .25s ease, box-shadow .25s ease, transform .2s ease !important;
}
div[data-testid="stFileUploader"] section:hover{
    border-color:var(--hx-w-accent) !important;
    box-shadow:0 0 0 4px rgba(99,102,241,0.12), 0 18px 40px rgba(99,102,241,0.12) !important;
}
div[data-testid="stFileUploaderDropzoneInstructions"] > div:first-child{
    visibility:hidden !important; height:0 !important; position:relative !important;
}
div[data-testid="stFileUploaderDropzoneInstructions"] > div:first-child::after{
    content:"☁️\a Glissez vos documents ici";
    white-space:pre-wrap;
    font-size:1.05rem;
    font-weight:700;
    color:var(--hx-w-text);
    display:block;
    text-align:center;
    margin:12px 0 8px;
    line-height:1.45;
    animation:hxCloud 2.8s ease-in-out infinite;
    visibility:visible !important;
    height:auto !important;
}
@keyframes hxCloud{
    0%,100%{ transform:translateY(0); opacity:.85; }
    50%{ transform:translateY(-6px); opacity:1; }
}
div[data-testid="stFileUploaderDropzoneInstructions"] small{
    visibility:hidden !important;
}
div[data-testid="stFileUploaderDropzoneInstructions"] small::after{
    content:"PDF · PNG · JPG · TIFF · jusqu'à 200 Mo";
    visibility:visible !important;
    display:block;
    text-align:center;
    color:var(--hx-w-muted);
    font-size:13px;
    margin-top:4px;
}

/* Section titles */
.hx-xp-section-title{
    font-size:0.78rem;
    font-weight:700;
    letter-spacing:0.14em;
    text-transform:uppercase;
    color:var(--hx-w-muted);
    margin:24px 0 12px;
}

/* File queue cards */
.hx-xp-queue{
    display:grid;
    grid-template-columns:repeat(auto-fill,minmax(260px,1fr));
    gap:12px;
    margin-bottom:16px;
}
.hx-xp-fcard{
    border-radius:14px;
    border:1px solid var(--hx-w-border);
    background:var(--hx-w-surface);
    padding:12px 14px;
    display:flex;
    gap:12px;
    align-items:flex-start;
    box-shadow:0 8px 24px rgba(15,23,42,0.06);
    animation:hxFadeIn .4s ease-out;
}
.hx-xp-ficon{
    width:40px;height:40px;border-radius:12px;
    background:linear-gradient(135deg,rgba(99,102,241,0.2),rgba(139,92,246,0.15));
    display:flex;align-items:center;justify-content:center;font-size:18px;
    flex-shrink:0;
}
.hx-xp-fname{ font-weight:700; color:var(--hx-w-text); font-size:14px; word-break:break-all; }
.hx-xp-fmeta{ font-size:12px; color:var(--hx-w-muted); margin-top:4px; }
.hx-xp-fpill{
    display:inline-block;margin-top:8px;font-size:11px;font-weight:700;
    padding:3px 8px;border-radius:999px;
    background:rgba(16,185,129,0.15);color:var(--hx-w-success);border:1px solid rgba(16,185,129,0.35);
}

/* Pipeline timeline */
.hx-xp-pipeline{
    display:flex;
    flex-wrap:wrap;
    align-items:center;
    gap:8px 6px;
    padding:14px 16px;
    border-radius:16px;
    border:1px solid var(--hx-w-border);
    background:var(--hx-w-card2);
    margin-bottom:14px;
}
.hx-xp-pstep{
    display:flex;align-items:center;gap:8px;
    padding:8px 12px;
    border-radius:12px;
    font-size:12px;font-weight:700;
    border:1px solid transparent;
    transition:all .25s ease;
}
.hx-xp-pstep--pending{ opacity:.45; color:var(--hx-w-muted); background:rgba(148,163,184,0.08); }
.hx-xp-pstep--processing{
    color:var(--hx-w-accent);
    border-color:rgba(99,102,241,0.35);
    box-shadow:0 0 24px rgba(99,102,241,0.2);
    animation:hxPulse 1.4s ease-in-out infinite;
}
.hx-xp-pstep--success{
    color:var(--hx-w-success);
    border-color:rgba(16,185,129,0.35);
    background:rgba(16,185,129,0.08);
}
.hx-xp-pstep--error{ color:var(--hx-w-danger); border-color:rgba(239,68,68,0.35); background:rgba(239,68,68,0.06); }
.hx-xp-pstep--skipped{
    opacity:.42;
    color:var(--hx-w-muted);
    border-color:rgba(148,163,184,0.28);
    background:rgba(148,163,184,0.06);
    font-style:italic;
}
@keyframes hxPulse{
    0%,100%{ box-shadow:0 0 12px rgba(99,102,241,0.15); }
    50%{ box-shadow:0 0 28px rgba(99,102,241,0.35); }
}
.hx-xp-parrow{ color:var(--hx-w-muted); font-size:14px; opacity:.5; }

/* Cards */
.hx-xp-card{
    border-radius:16px;
    border:1px solid var(--hx-w-border);
    background:var(--hx-w-card);
    padding:18px 20px;
    margin-bottom:14px;
    box-shadow:0 12px 32px rgba(15,23,42,0.06);
}
.hx-xp-card-head{
    display:flex;align-items:center;gap:10px;margin-bottom:14px;
    font-size:15px;font-weight:800;color:var(--hx-w-text);
}
.hx-xp-card-head span.ico{ font-size:1.15rem; }

/* KPI grid */
.hx-xp-kpi-grid{
    display:grid;
    grid-template-columns:repeat(auto-fill,minmax(140px,1fr));
    gap:10px;
}
.hx-xp-kpi{
    border-radius:14px;
    padding:12px 14px;
    border:1px solid var(--hx-w-border);
    background:linear-gradient(180deg,var(--hx-w-card2),var(--hx-w-card));
}
.hx-xp-kpi label{
    display:block;font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
    color:var(--hx-w-muted);margin-bottom:6px;
}
.hx-xp-kpi .val{
    font-size:1.05rem;font-weight:800;color:var(--hx-w-text);line-height:1.2;word-break:break-word;
}
.hx-xp-kpi .badge{
    margin-top:8px;display:inline-block;font-size:10px;font-weight:700;padding:2px 8px;border-radius:999px;
    background:rgba(99,102,241,0.12);color:var(--hx-w-accent);border:1px solid rgba(99,102,241,0.25);
}

/* Party grid */
.hx-xp-party-grid{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(280px,1fr));
    gap:14px;
}
.hx-xp-party{
    border-radius:16px;
    border:1px solid var(--hx-w-border);
    background:var(--hx-w-card);
    padding:16px 18px;
}
.hx-xp-party-top{
    display:flex;gap:12px;align-items:center;margin-bottom:14px;
}
.hx-xp-avatar{
    width:48px;height:48px;border-radius:14px;
    background:linear-gradient(135deg,var(--hx-w-accent),var(--hx-w-accent2));
    display:flex;align-items:center;justify-content:center;color:#fff;font-size:20px;font-weight:800;
}
.hx-xp-party h4{ margin:0;font-size:15px;font-weight:800;color:var(--hx-w-text); }
.hx-xp-party small{ color:var(--hx-w-muted);font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase; }
.hx-xp-field{ margin-bottom:10px; }
.hx-xp-field label{ font-size:11px;color:var(--hx-w-muted);font-weight:700;display:block;margin-bottom:3px; }
.hx-xp-field div{ font-size:13px;color:var(--hx-w-text); font-weight:600; }

/* Financial hero */
.hx-xp-fin{
    border-radius:18px;
    border:1px solid var(--hx-w-border);
    background:linear-gradient(135deg,rgba(99,102,241,0.08),rgba(139,92,246,0.06));
    padding:20px 22px;
    display:grid;
    grid-template-columns:1fr auto;
    gap:20px;
    align-items:center;
}
@media(max-width:720px){ .hx-xp-fin{ grid-template-columns:1fr; } }
.hx-xp-fin-row{
    display:flex;justify-content:space-between;align-items:center;padding:8px 0;
    border-bottom:1px solid var(--hx-w-border);font-size:14px;
}
.hx-xp-fin-row:last-child{ border-bottom:none; }
.hx-xp-fin-total{
    font-size:clamp(1.5rem,3vw,2.1rem);
    font-weight:900;
    letter-spacing:-0.03em;
    background:linear-gradient(90deg,var(--hx-w-accent),var(--hx-w-accent2));
    -webkit-background-clip:text;
    -webkit-text-fill-color:transparent;
    background-clip:text;
}
.hx-xp-donut{ width:120px!important; height:120px!important; }

/* Success / error strip */
.hx-xp-alert{
    border-radius:14px;padding:14px 18px;margin-bottom:14px;display:flex;align-items:center;gap:12px;
    font-weight:700;font-size:14px;
}
.hx-xp-alert--ok{
    background:rgba(16,185,129,0.12);border:1px solid rgba(16,185,129,0.35);color:var(--hx-w-success);
}
.hx-xp-alert--err{
    background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.35);color:var(--hx-w-danger);
}

/* Doc shell */
.hx-xp-docbar{
    border-radius:16px;
    border:1px solid var(--hx-w-border);
    padding:14px 18px;
    margin:18px 0 14px;
    background:var(--hx-w-card2);
    display:flex;flex-wrap:wrap;justify-content:space-between;gap:10px;align-items:center;
}
.hx-xp-docbar h3{ margin:0;font-size:16px;font-weight:800;color:var(--hx-w-text); }

/* Table zebra parent */
.hx-xp-table-wrap .glide-data-grid-container,
div[data-testid="stDataFrame"]{
    border-radius:14px!important;
    border:1px solid var(--hx-w-border)!important;
}
/* Batch summary */
.hx-xp-metrics{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
    gap:12px;
    margin-bottom:14px;
}
.hx-xp-metric{
    border-radius:14px;border:1px solid var(--hx-w-border);
    padding:16px;background:var(--hx-w-card);
}
.hx-xp-metric .v{ font-size:1.65rem;font-weight:900;color:var(--hx-w-text); }
.hx-xp-metric .l{ font-size:11px;color:var(--hx-w-muted);font-weight:700;text-transform:uppercase;letter-spacing:.08em; }

/* Expanders terminal style */
.hx-xp-expander.dark-exp summary{
    font-weight:700!important;
}
div[data-testid="stExpander"] details summary{
    border-radius:12px!important;
}
/* Sidebar shortcuts */
.hx-xp-side-short button{
    border-radius:10px!important;
}

@keyframes hxFadeIn{
    from{opacity:0;transform:translateY(8px);}
    to{opacity:1;transform:translateY(0);}
}
.hx-fade-in{ animation:hxFadeIn .45s ease-out; }
</style>
"""

_EXTRACTION_CSS_LIGHT_VARS = """
<style>
:root{
    --hx-w-bg:#f4f7fd;
    --hx-w-surface:rgba(255,255,255,0.72);
    --hx-w-card:#ffffff;
    --hx-w-card2:#f8fafc;
    --hx-w-border:rgba(99,102,241,0.18);
    --hx-w-text:#0f172a;
    --hx-w-muted:#64748b;
    --hx-w-accent:#6366f1;
    --hx-w-accent2:#8b5cf6;
    --hx-w-glow:rgba(99,102,241,0.35);
    --hx-w-success:#10b981;
    --hx-w-danger:#ef4444;
}
</style>
"""

_EXTRACTION_CSS_DARK_VARS = """
<style>
:root{
    --hx-w-bg:#0b1020;
    --hx-w-surface:rgba(17,24,39,0.88);
    --hx-w-card:#111827;
    --hx-w-card2:#0f172a;
    --hx-w-border:rgba(99,102,241,0.28);
    --hx-w-text:#f1f5f9;
    --hx-w-muted:#94a3b8;
    --hx-w-accent:#818cf8;
    --hx-w-accent2:#a78bfa;
    --hx-w-glow:rgba(129,140,248,0.45);
    --hx-w-success:#34d399;
    --hx-w-danger:#f87171;
}
.hx-xp-hero{
    background:linear-gradient(135deg,
        rgba(99,102,241,0.22) 0%,
        rgba(139,92,246,0.12) 40%,
        rgba(15,23,42,0.4) 100%) !important;
    box-shadow:0 24px 60px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.06) !important;
}
.hx-xp-fcard{ box-shadow:0 12px 32px rgba(0,0,0,0.35) !important; }
.hx-xp-card{ box-shadow:0 16px 40px rgba(0,0,0,0.35) !important; }
div[data-testid="stExpander"]{
    background:var(--hx-w-card)!important;
    border-color:var(--hx-w-border)!important;
}
</style>
"""


def inject_extraction_workspace_styles(*, dark: bool) -> None:
    """Feuilles de style pour la page Extraction (palette sombre optionnelle)."""
    st.markdown(_EXTRACTION_CSS_STRUCTURE, unsafe_allow_html=True)
    st.markdown(_EXTRACTION_CSS_DARK_VARS if dark else _EXTRACTION_CSS_LIGHT_VARS, unsafe_allow_html=True)


def render_workspace_hero() -> None:
    st.markdown(
        """
<div class="hx-xp-hero hx-fade-in">
  <div class="hx-xp-hero-inner">
    <h1 class="hx-xp-title">
      <span class="hx-xp-title-icon">⚡</span>
      AI Document Extraction Workspace
    </h1>
    <p class="hx-xp-sub">
      Analyse intelligente de documents avec OCR, IA et structuration automatique.
    </p>
    <div class="hx-xp-badges">
      <span class="hx-xp-badge hx-xp-badge--on">Upload</span>
      <span class="hx-xp-badge hx-xp-badge--on">OCR</span>
      <span class="hx-xp-badge hx-xp-badge--on">AI Extraction</span>
      <span class="hx-xp-badge hx-xp-badge--on">Structuring</span>
      <span class="hx-xp-badge hx-xp-badge--on">Validation</span>
    </div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_upload_section_title() -> None:
    st.markdown('<p class="hx-xp-section-title">Importer des documents</p>', unsafe_allow_html=True)


def render_file_queue_cards(docs: list[dict[str, Any]]) -> None:
    if not docs:
        return
    parts = ['<div class="hx-xp-queue">']
    for d in docs:
        name = html.escape(str(d.get("name") or ""))
        raw_b = d.get("bytes")
        n_bytes = len(raw_b) if isinstance(raw_b, (bytes, bytearray)) else 0
        if n_bytes >= 1024 * 1024:
            sz = f"{n_bytes / (1024*1024):.2f} Mo"
        elif n_bytes >= 1024:
            sz = f"{n_bytes / 1024:.1f} Ko"
        else:
            sz = f"{n_bytes} o"
        ext = Path(str(d.get("name") or "")).suffix.lower() or "—"
        icon = "📄"
        if ext == ".pdf":
            icon = "📕"
        elif ext in (".png", ".jpg", ".jpeg", ".webp"):
            icon = "🖼️"
        parts.append(
            f'<div class="hx-xp-fcard"><div class="hx-xp-ficon">{icon}</div>'
            f'<div><div class="hx-xp-fname">{name}</div>'
            f'<div class="hx-xp-fmeta">{html.escape(sz)} · {html.escape(ext)}</div>'
            f'<span class="hx-xp-fpill">Prêt</span></div></div>'
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def render_pipeline_timeline(
    *,
    step_status: dict[str, str],
) -> None:
    """
    step_status keys: upload, ocr, ai, structure, validate
    values: pending | processing | success | error | skipped
    """
    order = [
        ("upload", "📤", "Upload"),
        ("ocr", "🔍", "OCR"),
        ("ai", "🧠", "IA"),
        ("structure", "📐", "Structure"),
        ("validate", "✓", "Validation"),
    ]
    chunks = ['<div class="hx-xp-pipeline hx-fade-in">']
    for i, (key, emoji, label) in enumerate(order):
        st_v = step_status.get(key, "pending")
        cls = f"hx-xp-pstep hx-xp-pstep--{st_v}"
        title = ""
        if st_v == "skipped":
            title = ' title="Non exécutée — méthode ou type de document incompatible"'
        chunks.append(
            f'<div class="{cls}"{title}><span>{emoji}</span><span>{html.escape(label)}</span></div>'
        )
        if i < len(order) - 1:
            chunks.append('<span class="hx-xp-parrow">→</span>')
    chunks.append("</div>")
    st.markdown("".join(chunks), unsafe_allow_html=True)


def timeline_from_batch_status(status: str, *, processing: bool) -> dict[str, str]:
    if processing:
        return {
            "upload": "success",
            "ocr": "processing",
            "ai": "pending",
            "structure": "pending",
            "validate": "pending",
        }
    if status == "ok":
        return {k: "success" for k in ("upload", "ocr", "ai", "structure", "validate")}
    if status == "erreur":
        return {
            "upload": "success",
            "ocr": "pending",
            "ai": "error",
            "structure": "pending",
            "validate": "pending",
        }
    return {
        "upload": "success",
        "ocr": "pending",
        "ai": "pending",
        "structure": "pending",
        "validate": "pending",
    }


def resolve_pipeline_steps(
    *,
    batch_status: str,
    gemini_receipt_error: str | None,
    gemini_supplier_error: str | None,
    gemini_generic_error: str | None,
    processing_error: str | None,
) -> dict[str, str]:
    """Construit l'état visuel du pipeline selon le résultat réel (évite OCR ✓ alors que rien n'a été joué)."""
    keys = ("upload", "ocr", "ai", "structure", "validate")
    if batch_status == "ok":
        return dict.fromkeys(keys, "success")

    def _blocked_local(msg: str | None) -> bool:
        if not msg:
            return False
        m = msg.lower()
        return "ocr local" in m or "sans api" in m

    if _blocked_local(gemini_receipt_error) or _blocked_local(gemini_supplier_error):
        return {
            "upload": "success",
            "ocr": "skipped",
            "ai": "error",
            "structure": "pending",
            "validate": "pending",
        }
    if gemini_receipt_error or gemini_supplier_error or gemini_generic_error or processing_error:
        return {
            "upload": "success",
            "ocr": "pending",
            "ai": "error",
            "structure": "pending",
            "validate": "pending",
        }
    return timeline_from_batch_status(batch_status, processing=False)


def render_document_header(*, index: int, filename: str, source_origin: str) -> None:
    fn = html.escape(filename)
    so = html.escape(str(source_origin))
    st.markdown(
        f"""
<div class="hx-xp-docbar hx-fade-in">
  <h3>#{index} · {fn}</h3>
  <span style="font-size:12px;font-weight:700;color:var(--hx-w-muted);">Source · {so}</span>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_alert_ok(message: str) -> None:
    msg = html.escape(message)
    st.markdown(f'<div class="hx-xp-alert hx-xp-alert--ok hx-fade-in"><span>✓</span><span>{msg}</span></div>', unsafe_allow_html=True)


def render_alert_error(message: str) -> None:
    msg = html.escape(message)
    st.markdown(f'<div class="hx-xp-alert hx-xp-alert--err hx-fade-in"><span>✕</span><span>{msg}</span></div>', unsafe_allow_html=True)


def _fmt_money(s: Any) -> str:
    t = str(s or "").strip()
    return t if t else "—"


def render_supplier_results(
    sup: dict[str, Any],
    *,
    uploaded_name: str,
    json_download_key: str,
    effective_mode_auto: bool,
) -> None:
    subtitle = " — détection automatique" if effective_mode_auto else ""
    render_alert_ok(f"Extraction facture fournisseur réussie (Gemini){subtitle}")

    rtl_note = sup.get("ocr_rtl_text_ratio")
    lang_guess = "—"
    if rtl_note is not None:
        try:
            r = float(rtl_note)
            lang_guess = "Arabe / mixte (RTL élevé)" if r >= 0.35 else "Latin / mixte"
        except (TypeError, ValueError):
            lang_guess = str(rtl_note)

    q = sup.get("extraction_quality")
    conf_label = str(sup.get("confidence") or "").strip() or "—"
    engine = str(sup.get("extraction_source") or "gemini")

    kpi_items: list[tuple[str, str, str]] = [
        ("N° facture", _fmt_money(sup.get("invoice_number")), ""),
        ("Date facture", _fmt_money(sup.get("invoice_date")), ""),
        ("Échéance", _fmt_money(sup.get("due_date")), ""),
        ("Devise", _fmt_money(sup.get("currency")), ""),
        ("Confiance IA", conf_label, ""),
        ("Langue (hint)", lang_guess, ""),
        ("Moteur", engine.upper(), "PIPELINE"),
    ]
    if q is not None:
        try:
            qf = float(q)
            pct = min(100.0, max(0.0, qf * 100.0))
            kpi_items.insert(
                5,
                ("Score extraction", f"{pct:.0f}%", "SCORE"),
            )
        except (TypeError, ValueError):
            pass

    gen_chunks = [
        '<div class="hx-xp-card hx-fade-in"><div class="hx-xp-card-head">'
        '<span class="ico">📋</span> Informations générales</div>',
        '<div class="hx-xp-kpi-grid">',
    ]
    for label, val, kind in kpi_items:
        badge = ""
        if kind == "PIPELINE":
            badge = '<span class="badge">Gemini Vision</span>'
        elif kind == "SCORE":
            badge = '<span class="badge">Qualité</span>'
        gen_chunks.append(
            f'<div class="hx-xp-kpi"><label>{html.escape(label)}</label>'
            f'<div class="val">{html.escape(val)}</div>{badge}</div>'
        )
    gen_chunks.extend(["</div>", "</div>"])
    st.markdown("".join(gen_chunks), unsafe_allow_html=True)
    q2 = sup.get("extraction_quality")
    if isinstance(q2, (int, float)):
        st.progress(min(1.0, max(0.0, float(q2))), text="Qualité d'extraction estimée")

    mf = sup.get("missing_fields") or []
    if mf:
        st.caption("Champs absents : " + ", ".join(str(x) for x in mf))
    rn = sup.get("raw_notes") or ""
    if rn:
        st.caption(f"Notes : {rn}")

    seller = sup.get("seller") if isinstance(sup.get("seller"), dict) else {}
    client = sup.get("client") if isinstance(sup.get("client"), dict) else {}

    st.markdown(
        '<div class="hx-xp-card-head hx-fade-in" style="margin-top:8px;"><span class="ico">🏢</span> Parties</div>',
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    with c1:
        _render_party_card_html("Fournisseur", "FV", seller, show_iban=True)
    with c2:
        _render_party_card_html("Client", "CL", client, show_iban=False)

    items_sup = sup.get("items") or []
    art_open = (
        '<div class="hx-xp-card hx-fade-in"><div class="hx-xp-card-head">'
        '<span class="ico">📦</span> Articles</div>'
    )
    st.markdown(art_open, unsafe_allow_html=True)
    if items_sup:
        rows = []
        for item in items_sup:
            if not isinstance(item, dict):
                continue
            tr = item.get("tax_rate") or "—"
            rows.append(
                {
                    "Description": item.get("description") or "—",
                    "Qté": item.get("quantity") or "—",
                    "Unité": item.get("unit") or "—",
                    "Prix unit.": item.get("unit_price") or "—",
                    "Net": item.get("net_amount") or "—",
                    "TVA %": tr,
                    "TVA": item.get("tax_amount") or "—",
                    "Brut": item.get("gross_amount") or "—",
                }
            )
        if rows:
            df = pd.DataFrame(rows)
            st.dataframe(
                df,
                width="stretch",
                hide_index=True,
                height=min(420, 56 + len(rows) * 36),
                column_config={
                    "Description": TextColumn(width="large"),
                    "TVA %": TextColumn(help="Taux ou libellé TVA"),
                },
            )
        else:
            st.caption("Aucune ligne article.")
    else:
        st.caption("Aucune ligne article.")
    st.markdown("</div>", unsafe_allow_html=True)

    summary = sup.get("summary") if isinstance(sup.get("summary"), dict) else {}
    st.markdown(
        '<div class="hx-xp-card hx-fade-in"><div class="hx-xp-card-head"><span class="ico">💰</span> Résumé financier</div>',
        unsafe_allow_html=True,
    )
    col_a, col_b = st.columns([1.4, 1])
    with col_a:
        sub = _fmt_money(summary.get("subtotal"))
        tax = _fmt_money(summary.get("tax_total"))
        tot = _fmt_money(summary.get("total_amount"))
        due = _fmt_money(summary.get("amount_due"))
        disc = _fmt_money(summary.get("discount"))
        ship = _fmt_money(summary.get("shipping"))
        fin_html = f"""
<div class="hx-xp-fin hx-fade-in">
  <div>
    <div class="hx-xp-fin-row"><span>Sous-total HT</span><strong>{html.escape(sub)}</strong></div>
    <div class="hx-xp-fin-row"><span>TVA</span><strong>{html.escape(tax)}</strong></div>
    <div class="hx-xp-fin-row"><span>Remise</span><strong>{html.escape(disc)}</strong></div>
    <div class="hx-xp-fin-row"><span>Livraison / frais</span><strong>{html.escape(ship)}</strong></div>
    <div class="hx-xp-fin-row"><span>Montant dû</span><strong>{html.escape(due)}</strong></div>
    <div style="margin-top:14px;"><span style="font-size:12px;font-weight:700;color:var(--hx-w-muted);text-transform:uppercase;">Total TTC</span>
    <div class="hx-xp-fin-total">{html.escape(tot)}</div></div>
  </div>
</div>
        """
        st.markdown(fin_html, unsafe_allow_html=True)
    with col_b:
        _try_donut_ht_tva(sub, tax)
    st.markdown("</div>", unsafe_allow_html=True)

    st.download_button(
        "⬇️ Télécharger JSON extraction",
        data=json.dumps(sup, ensure_ascii=False, indent=2).encode("utf-8"),
        file_name=f"{Path(uploaded_name).stem}_supplier_invoice.json",
        mime="application/json",
        key=json_download_key,
        use_container_width=True,
    )

    _render_debug_expanders(sup, title_prefix="Facture fournisseur")


def _render_party_card_html(title: str, letter: str, d: dict[str, Any], *, show_iban: bool) -> None:
    iban_row = ""
    if show_iban:
        iban_row = f'<div class="hx-xp-field"><label>IBAN</label><div>{html.escape(_fmt_money(d.get("iban")))}</div></div>'
    body = f"""
<div class="hx-xp-party hx-fade-in">
  <div class="hx-xp-party-top">
    <div class="hx-xp-avatar">{html.escape(letter[:2])}</div>
    <div><h4>{html.escape(title)}</h4><small>Coordonnées</small></div>
  </div>
  <div class="hx-xp-field"><label>Nom</label><div>{html.escape(_fmt_money(d.get("name")))}</div></div>
  <div class="hx-xp-field"><label>Adresse</label><div>{html.escape(_fmt_money(d.get("address")))}</div></div>
  <div class="hx-xp-field"><label>Fiscal</label><div>{html.escape(_fmt_money(d.get("tax_id")))}</div></div>
  {iban_row}
  <div class="hx-xp-field"><label>Contact</label><div>{html.escape(_fmt_money(d.get("email")))} · {html.escape(_fmt_money(d.get("phone")))}</div></div>
</div>
    """
    st.markdown(body, unsafe_allow_html=True)


def _parse_amount_loose(s: str) -> float | None:
    raw = re.sub(r"[^\d,.\-]", "", str(s).strip())
    if not raw or raw in "-":
        return None
    raw = raw.replace(",", ".")
    if raw.count(".") > 1:
        parts = raw.split(".")
        raw = "".join(parts[:-1]) + "." + parts[-1]
    try:
        return float(raw)
    except ValueError:
        return None


def _try_donut_ht_tva(sub_s: str, tax_s: str) -> None:
    hs = _parse_amount_loose(sub_s)
    tv = _parse_amount_loose(tax_s)
    if hs is None and tv is None:
        st.caption("Répartition TVA : valeurs non numériques — graphique indisponible.")
        return
    hs = hs or 0.0
    tv = tv or 0.0
    if hs <= 0 and tv <= 0:
        st.caption("Répartition TVA : montants non détectés.")
        return
    try:
        import plotly.graph_objects as go
    except Exception:
        st.caption("Installez plotly pour le graphique donut.")
        return
    fig = go.Figure(
        data=[
            go.Pie(
                labels=["Hors TVA (approx.)", "TVA"],
                values=[max(hs, 0.01), max(tv, 0.01)],
                hole=0.68,
                marker=dict(colors=["rgba(99,102,241,0.85)", "rgba(139,92,246,0.85)"]),
            )
        ]
    )
    fig.update_layout(
        showlegend=False,
        margin=dict(l=0, r=0, t=0, b=0),
        height=200,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=11),
    )
    fig.update_traces(textinfo="none")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _render_debug_expanders(payload: dict[str, Any], *, title_prefix: str) -> None:
    with st.expander("📟 JSON brut · extraction", expanded=False):
        st.code(json.dumps(payload, ensure_ascii=False, indent=2), language="json")
    with st.expander("📝 Texte OCR brut / hints", expanded=False):
        st.caption(
            "Le texte OCR complet n'est pas stocké dans ce flux ; utilisez les indices RTL ou les warnings."
        )
        if isinstance(payload, dict) and payload.get("ocr_rtl_text_ratio") is not None:
            st.code(f"ocr_rtl_text_ratio: {payload.get('ocr_rtl_text_ratio')}", language="text")
    warns = payload.get("warnings") or []
    if warns:
        with st.expander("⚠️ Avertissements pipeline", expanded=False):
            st.code(json.dumps(warns, ensure_ascii=False, indent=2), language="json")


def render_receipt_results(
    rec: dict[str, Any],
    *,
    uploaded_name: str,
    effective_mode_auto: bool,
) -> None:
    subtitle = " — détection automatique" if effective_mode_auto else ""
    render_alert_ok(f"Extraction ticket réussie (Gemini){subtitle}")
    st.markdown(
        '<div class="hx-xp-card hx-fade-in"><div class="hx-xp-card-head"><span class="ico">🧾</span> Ticket de caisse</div>',
        unsafe_allow_html=True,
    )
    grid = ['<div class="hx-xp-kpi-grid">']
    for label, val in [
        ("Magasin", rec.get("store_name")),
        ("Date", rec.get("date")),
        ("Heure", rec.get("time")),
        ("N° ticket", rec.get("ticket_number")),
        ("Devise", rec.get("currency")),
        ("Total", rec.get("total")),
        ("Paiement", rec.get("payment_method")),
    ]:
        grid.append(
            f'<div class="hx-xp-kpi"><label>{html.escape(label)}</label>'
            f'<div class="val">{html.escape(_fmt_money(val))}</div></div>'
        )
    grid.append("</div>")
    st.markdown("".join(grid), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    items = rec.get("items") or []
    st.markdown(
        '<div class="hx-xp-card hx-fade-in"><div class="hx-xp-card-head"><span class="ico">📦</span> Articles</div>',
        unsafe_allow_html=True,
    )
    if items:
        rows = []
        for item in items:
            if not isinstance(item, dict):
                continue
            rows.append(
                {
                    "Description": item.get("description") or "—",
                    "Qté": item.get("quantity") or "—",
                    "Prix unit.": item.get("unit_price") or "—",
                    "Total ligne": item.get("line_total") or "—",
                }
            )
        if rows:
            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True, height=min(400, 56 + len(rows) * 36))
    else:
        st.caption("Aucune ligne article.")
    st.markdown("</div>", unsafe_allow_html=True)
    _render_debug_expanders(rec, title_prefix="Ticket")


def render_medical_gemini_results(res: dict[str, Any]) -> None:
    render_alert_ok("Extraction médicale réussie (Gemini)")
    st.markdown(
        '<div class="hx-xp-card hx-fade-in"><div class="hx-xp-card-head"><span class="ico">🩺</span> En-tête document</div>',
        unsafe_allow_html=True,
    )
    grid = ['<div class="hx-xp-kpi-grid">']
    for label, val in [
        ("Patient", res.get("patient_name")),
        ("Médecin", res.get("doctor_name")),
        ("Date", res.get("date")),
    ]:
        grid.append(
            f'<div class="hx-xp-kpi"><label>{html.escape(label)}</label>'
            f'<div class="val">{html.escape(_fmt_money(val))}</div></div>'
        )
    grid.append("</div>")
    st.markdown("".join(grid), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    analyses = res.get("analyses") or []
    if analyses:
        st.markdown(
            '<div class="hx-xp-card hx-fade-in"><div class="hx-xp-card-head"><span class="ico">🔬</span> Analyses</div>',
            unsafe_allow_html=True,
        )
        from src.web.history_views import medical_gemini_analyses_for_display, medical_results_df

        st.dataframe(
            medical_results_df(medical_gemini_analyses_for_display(analyses)),
            width="stretch",
            hide_index=True,
            height=min(480, 56 + len(analyses) * 32),
        )
        st.markdown("</div>", unsafe_allow_html=True)
    _render_debug_expanders(res, title_prefix="Médical")


def render_steg_results(s: dict[str, Any]) -> None:
    render_alert_ok("Extraction STEG réussie")
    st.markdown(
        '<div class="hx-xp-card hx-fade-in"><div class="hx-xp-card-head"><span class="ico">⚡</span> Facture STEG</div>',
        unsafe_allow_html=True,
    )
    grid = ['<div class="hx-xp-kpi-grid">']
    for label, val in [
        ("Référence", s.get("reference")),
        ("Montant à payer", s.get("montant_a_payer")),
        ("Date limite", s.get("date_limite_paiement")),
        ("Période Du", s.get("periode_du")),
        ("Période Au", s.get("periode_au")),
        ("Coupon (bas)", s.get("coupon_montant")),
        ("Confiance", s.get("confidence_note")),
    ]:
        grid.append(
            f'<div class="hx-xp-kpi"><label>{html.escape(label)}</label>'
            f'<div class="val">{html.escape(_fmt_money(val))}</div></div>'
        )
    grid.append("</div>")
    st.markdown("".join(grid), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    _render_debug_expanders(s, title_prefix="STEG")


def render_medical_ocr_results(result: Any) -> None:
    render_alert_ok("Analyse médicale extraite (OCR)")
    dump = result.model_dump()
    lab = dump.get("lab_info") or {}
    patient = dump.get("patient_info") or {}
    docmeta = dump.get("document_metadata") or {}
    st.markdown(
        '<div class="hx-xp-card hx-fade-in"><div class="hx-xp-card-head"><span class="ico">🩺</span> Laboratoire & patient</div>',
        unsafe_allow_html=True,
    )
    grid = ['<div class="hx-xp-kpi-grid">']
    rows_kv = [
        ("Laboratoire", lab.get("lab_name")),
        ("Médecin", lab.get("doctor_name")),
        ("Patient", patient.get("patient_name")),
        ("N° dossier", docmeta.get("dossier_number")),
        ("Date prélèvement", docmeta.get("sample_date")),
        ("Date compte-rendu", docmeta.get("report_date")),
    ]
    for label, val in rows_kv:
        grid.append(
            f'<div class="hx-xp-kpi"><label>{html.escape(label)}</label>'
            f'<div class="val">{html.escape(_fmt_money(val))}</div></div>'
        )
    grid.append("</div>")
    st.markdown("".join(grid), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    tests = list(dump.get("tests") or [])
    if tests:
        st.markdown(
            '<div class="hx-xp-card hx-fade-in"><div class="hx-xp-card-head"><span class="ico">🔬</span> Résultats</div>',
            unsafe_allow_html=True,
        )
        body_rows = []
        for t in tests:
            td: dict[str, Any]
            if isinstance(t, dict):
                td = t
            elif hasattr(t, "model_dump"):
                td = t.model_dump()
            else:
                continue
            body_rows.append(
                {
                    "Analyse": td.get("raw_test_name") or "—",
                    "Valeur": (
                        str(td.get("value"))
                        if td.get("value") is not None
                        else str(td.get("value_text") or "—")
                    ),
                    "Unité": td.get("unit") or "—",
                }
            )
        from src.web.history_views import medical_results_df

        st.dataframe(
            medical_results_df(body_rows),
            width="stretch",
            hide_index=True,
            height=min(480, 56 + len(body_rows) * 32),
        )
        st.markdown("</div>", unsafe_allow_html=True)
    _render_debug_expanders(dump, title_prefix="Médical OCR")


def render_batch_summary(batch_rows: list[dict[str, Any]], *, ok_count: int, err_count: int) -> None:
    st.markdown('<p class="hx-xp-section-title">Synthèse du lot</p>', unsafe_allow_html=True)
    n = len(batch_rows)
    st.markdown(
        f"""
<div class="hx-xp-metrics hx-fade-in">
  <div class="hx-xp-metric"><div class="l">Fichiers</div><div class="v">{n}</div></div>
  <div class="hx-xp-metric"><div class="l">Succès</div><div class="v" style="color:var(--hx-w-success)!important;">{ok_count}</div></div>
  <div class="hx-xp-metric"><div class="l">Erreurs</div><div class="v" style="color:var(--hx-w-danger)!important;">{err_count}</div></div>
</div>
        """,
        unsafe_allow_html=True,
    )
    st.dataframe(pd.DataFrame(batch_rows), width="stretch", hide_index=True)


__all__ = [
    "inject_extraction_workspace_styles",
    "render_workspace_hero",
    "render_upload_section_title",
    "render_file_queue_cards",
    "render_pipeline_timeline",
    "render_document_header",
    "render_alert_ok",
    "render_alert_error",
    "render_supplier_results",
    "render_receipt_results",
    "render_medical_gemini_results",
    "render_steg_results",
    "render_medical_ocr_results",
    "render_batch_summary",
    "timeline_from_batch_status",
    "resolve_pipeline_steps",
]
