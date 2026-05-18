from __future__ import annotations

import json
import re
import shutil
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


def _trash_root(cfg: AppConfig) -> Path:
    return cfg.extraction_history_dir.parent / "trash"


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path

    counter = 2
    while True:
        candidate = path.with_name(f"{path.stem}_{counter}{path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


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
    """Entrees triees par date de fichier (plus recent en premier)."""
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
            for row in db_rows:
                payload: dict[str, Any] = {}
                try:
                    payload = json.loads(row["payload_json"]) if row["payload_json"] else {}
                except Exception:
                    payload = {}
                relative = row["relative_path"] or f"db://extraction_history/{row['id']}"
                rows.append(
                    {
                        "id": row["id"],
                        "path": None,
                        "relative": relative,
                        "kind": row["kind"],
                        "saved_at": row["saved_at"],
                        "source_filename": row["source_filename"],
                        "size_bytes": len((row["payload_json"] or "").encode("utf-8")),
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

    for path in sorted(root.rglob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        relative = path.relative_to(root)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            meta = data.get("_meta") or {}
            rows.append(
                {
                    "id": None,
                    "path": path,
                    "relative": str(relative),
                    "kind": meta.get("kind") or path.parent.name,
                    "saved_at": meta.get("saved_at") or "",
                    "source_filename": meta.get("source_filename") or "",
                    "size_bytes": path.stat().st_size,
                    "payload": data,
                    "storage": "file",
                }
            )
        except Exception:
            rows.append(
                {
                    "id": None,
                    "path": path,
                    "relative": str(relative),
                    "kind": path.parent.name,
                    "saved_at": "",
                    "source_filename": path.name,
                    "size_bytes": path.stat().st_size,
                    "payload": {},
                    "storage": "file",
                }
            )
    return rows


def delete_history_entry(cfg: AppConfig, entry: dict[str, Any]) -> tuple[bool, str]:
    """Deplace une extraction vers la corbeille puis la retire de la liste active."""
    root = cfg.extraction_history_dir
    trash_root = _trash_root(cfg)
    relative = str(entry.get("relative") or "")
    payload = entry.get("payload") if isinstance(entry.get("payload"), dict) else {}
    source_filename = str(entry.get("source_filename") or "document")
    kind = str(entry.get("kind") or "autre")

    try:
        trash_root.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        fallback_name = f"{timestamp}_{_safe_stem(source_filename)}.json"
        relative_candidate = (
            Path(relative)
            if relative and not relative.startswith("db://")
            else Path(kind) / fallback_name
        )
        trash_json_path = _unique_path(trash_root / relative_candidate)
        trash_json_path.parent.mkdir(parents=True, exist_ok=True)

        trashed_payload = dict(payload)
        meta = trashed_payload.get("_meta") if isinstance(trashed_payload.get("_meta"), dict) else {}
        trashed_meta = dict(meta)
        trashed_meta["trashed_at"] = datetime.now(timezone.utc).isoformat()
        if relative:
            trashed_meta["original_relative_path"] = relative

        source_relative = trashed_meta.get("source_file_relative")
        if source_relative:
            source_path = (root / Path(str(source_relative))).resolve()
            if root.resolve() in source_path.parents and source_path.is_file():
                target_source_path = _unique_path(trash_root / Path(str(source_relative)))
                target_source_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source_path), str(target_source_path))
                trashed_meta["source_file_relative"] = str(target_source_path.relative_to(trash_root))

        trashed_payload["_meta"] = trashed_meta
        trash_json_path.write_text(
            json.dumps(trashed_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        if relative and not relative.startswith("db://"):
            json_path = (root / Path(relative)).resolve()
            if root.resolve() in json_path.parents and json_path.is_file():
                json_path.unlink(missing_ok=True)
    except Exception as exc:
        return False, f"Mise en corbeille impossible: {exc}"

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
                elif relative and not relative.startswith("db://"):
                    conn.execute("DELETE FROM extraction_history WHERE relative_path = ?", (relative,))
    except Exception as exc:
        return False, f"Mise a jour DB impossible apres corbeille: {exc}"

    return True, "Document deplace vers la corbeille."
