from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import AppConfig


def _safe_stem(name: str) -> str:
    stem = Path(name).stem
    stem = re.sub(r"[^\w\-]+", "_", stem, flags=re.UNICODE)
    stem = stem.strip("._") or "document"
    return stem[:80]


def save_extraction(
    cfg: AppConfig,
    kind: str,
    source_filename: str,
    payload: dict[str, Any],
    source_bytes: bytes | None = None,
) -> Path:
    """
    Enregistre un JSON sous ``{extraction_history_dir}/{kind}/{timestamp}_{stem}.json``.
    ``kind`` : receipt, supplier_invoice, medical_gemini, medical_ocr, steg_ocr, steg_gemini.
    """
    root = cfg.extraction_history_dir
    root.mkdir(parents=True, exist_ok=True)
    sub = root / kind
    sub.mkdir(parents=True, exist_ok=True)
    db_path = cfg.extraction_history_db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    fname = f"{ts}_{_safe_stem(source_filename)}.json"
    path = sub / fname
    source_path: Path | None = None
    if source_bytes is not None:
        src_ext = Path(source_filename).suffix or ".bin"
        source_path = sub / f"{ts}_{_safe_stem(source_filename)}{src_ext}"
        source_path.write_bytes(source_bytes)

    doc = dict(payload)
    doc.pop("_meta", None)
    meta = {
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "source_filename": source_filename,
        "kind": kind,
    }
    if source_path is not None:
        meta["source_file_relative"] = str(source_path.relative_to(root))
    doc["_meta"] = meta
    payload_json = json.dumps(doc, ensure_ascii=False)

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS extraction_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                source_filename TEXT NOT NULL,
                saved_at TEXT NOT NULL,
                relative_path TEXT,
                payload_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO extraction_history (kind, source_filename, saved_at, relative_path, payload_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                kind,
                source_filename,
                doc["_meta"]["saved_at"],
                str(path.relative_to(root)),
                payload_json,
            ),
        )

    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def list_history_entries(cfg: AppConfig) -> list[dict[str, Any]]:
    """Entrées triées par date de fichier (plus récent en premier)."""
    rows: list[dict[str, Any]] = []
    db_path = cfg.extraction_history_db_path
    if db_path.is_file():
        try:
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS extraction_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        kind TEXT NOT NULL,
                        source_filename TEXT NOT NULL,
                        saved_at TEXT NOT NULL,
                        relative_path TEXT,
                        payload_json TEXT NOT NULL
                    )
                    """
                )
                db_rows = conn.execute(
                    """
                    SELECT id, kind, source_filename, saved_at, relative_path, payload_json
                    FROM extraction_history
                    ORDER BY datetime(saved_at) DESC, id DESC
                    """
                ).fetchall()
            for r in db_rows:
                payload: dict[str, Any] = {}
                try:
                    payload = json.loads(r["payload_json"]) if r["payload_json"] else {}
                except Exception:
                    payload = {}
                rel = r["relative_path"] or f"db://extraction_history/{r['id']}"
                rows.append(
                    {
                        "id": r["id"],
                        "path": None,
                        "relative": rel,
                        "kind": r["kind"],
                        "saved_at": r["saved_at"],
                        "source_filename": r["source_filename"],
                        "size_bytes": len((r["payload_json"] or "").encode("utf-8")),
                        "payload": payload,
                        "storage": "db",
                    }
                )
            if rows:
                return rows
        except Exception:
            pass

    root = cfg.extraction_history_dir
    if not root.is_dir():
        return []
    for p in sorted(root.rglob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        rel = p.relative_to(root)
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            meta = data.get("_meta") or {}
            rows.append(
                {
                    "id": None,
                    "path": p,
                    "relative": str(rel),
                    "kind": meta.get("kind") or p.parent.name,
                    "saved_at": meta.get("saved_at") or "",
                    "source_filename": meta.get("source_filename") or "",
                    "size_bytes": p.stat().st_size,
                    "payload": data,
                    "storage": "file",
                }
            )
        except Exception:
            rows.append(
                {
                    "id": None,
                    "path": p,
                    "relative": str(rel),
                    "kind": p.parent.name,
                    "saved_at": "",
                    "source_filename": p.name,
                    "size_bytes": p.stat().st_size,
                    "payload": {},
                    "storage": "file",
                }
            )
    return rows


def delete_history_entry(cfg: AppConfig, entry: dict[str, Any]) -> tuple[bool, str]:
    """Supprime une extraction (DB + JSON + source archivée si présente)."""
    root = cfg.extraction_history_dir
    rel = str(entry.get("relative") or "")
    payload = entry.get("payload") if isinstance(entry.get("payload"), dict) else {}

    try:
        db_path = cfg.extraction_history_db_path
        if db_path.is_file():
            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS extraction_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        kind TEXT NOT NULL,
                        source_filename TEXT NOT NULL,
                        saved_at TEXT NOT NULL,
                        relative_path TEXT,
                        payload_json TEXT NOT NULL
                    )
                    """
                )
                row_id = entry.get("id")
                if isinstance(row_id, int):
                    conn.execute("DELETE FROM extraction_history WHERE id = ?", (row_id,))
                elif rel and not rel.startswith("db://"):
                    conn.execute("DELETE FROM extraction_history WHERE relative_path = ?", (rel,))
    except Exception as exc:
        return False, f"Suppression DB impossible: {exc}"

    if rel and not rel.startswith("db://"):
        try:
            jp = (root / Path(rel)).resolve()
            if root.resolve() in jp.parents and jp.is_file():
                jp.unlink(missing_ok=True)
        except Exception as exc:
            return False, f"Suppression JSON impossible: {exc}"

    meta = payload.get("_meta") if isinstance(payload, dict) else {}
    src_rel = meta.get("source_file_relative") if isinstance(meta, dict) else None
    if src_rel:
        try:
            sp = (root / Path(str(src_rel))).resolve()
            if root.resolve() in sp.parents and sp.is_file():
                sp.unlink(missing_ok=True)
        except Exception:
            pass

    return True, "Extraction supprimée."
