"""Utilitaires partagés : résolution des chemins JSON/source et aperçu PDF (historique)."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image
from pdf2image import convert_from_bytes

from src.config import AppConfig
from src.web.history_views import load_json_file


def history_json_path(entry: dict, cfg: AppConfig) -> Path | None:
    """Chemin du fichier JSON d'historique sur disque (depuis ``relative``)."""
    rel = entry.get("relative") or ""
    s = str(rel)
    if not s or s.startswith("db://"):
        return None
    p = cfg.extraction_history_dir / s
    return p if p.is_file() and p.suffix.lower() == ".json" else None


def merge_meta_from_disk_json(data: dict, entry: dict, cfg: AppConfig) -> None:
    """Complète ``data._meta`` depuis le JSON sur disque si la base est incomplète."""
    jp = history_json_path(entry, cfg)
    if jp is None or not isinstance(data, dict):
        return
    disk, _ = load_json_file(jp)
    if not isinstance(disk, dict):
        return
    dm = disk.get("_meta") or {}
    if not isinstance(dm, dict) or not dm.get("source_file_relative"):
        return
    em = data.get("_meta") or {}
    if isinstance(em, dict) and em.get("source_file_relative"):
        return
    data["_meta"] = {**(em if isinstance(em, dict) else {}), **dm}


def entry_payload_for_report(entry: dict, cfg: AppConfig) -> dict:
    """Payload fusionné (mémoire + JSON disque) pour rapport / modale."""
    data = entry.get("payload")
    if not isinstance(data, dict):
        data = {}
    else:
        data = dict(data)
    jp = history_json_path(entry, cfg)
    if not data and jp is not None:
        disk, _ = load_json_file(jp)
        if isinstance(disk, dict):
            data = dict(disk)
    elif jp is not None:
        merge_meta_from_disk_json(data, entry, cfg)
    return data


def resolve_archived_source_path(entry: dict, cfg: AppConfig, data: dict | None = None) -> Path | None:
    """
    Fichier source archivé : ``_meta.source_file_relative``, sinon fichier voisin du JSON
    (même nom de base que le JSON).
    """
    payloads: list[dict] = []
    if isinstance(data, dict):
        payloads.append(data)
    if isinstance(entry.get("payload"), dict):
        payloads.append(entry["payload"])
    root = cfg.extraction_history_dir
    for payload in payloads:
        meta = payload.get("_meta") or {}
        if isinstance(meta, dict) and meta.get("source_file_relative"):
            p = root / Path(str(meta["source_file_relative"]))
            if p.is_file():
                return p

    jp = history_json_path(entry, cfg)
    if jp is None:
        return None
    stem = jp.stem
    parent = jp.parent
    for ext in (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".bmp", ".pdf"):
        cand = parent / f"{stem}{ext}"
        if cand.is_file():
            return cand
    return None


def pdf_bytes_for_source_path(path: Path, download_stem: str) -> tuple[bytes | None, str]:
    """Retourne (octets PDF, nom de fichier .pdf). PDF d'origine ou image convertie."""
    stem = Path(download_stem).stem or path.stem or "document"
    out_name = f"{stem}.pdf"
    suf = path.suffix.lower()
    try:
        if suf == ".pdf":
            return path.read_bytes(), out_name
        if suf in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}:
            img = Image.open(path).convert("RGB")
            buf = BytesIO()
            img.save(buf, format="PDF", resolution=100.0)
            return buf.getvalue(), out_name
    except Exception:
        return None, out_name
    return None, out_name


def pdf_first_page_preview(pdf_bytes: bytes) -> Image.Image | None:
    """Première page d'un PDF en image pour aperçu."""
    if not pdf_bytes:
        return None
    try:
        pages = convert_from_bytes(pdf_bytes, dpi=140, first_page=1, last_page=1)
        if not pages:
            return None
        return pages[0]
    except Exception:
        return None
