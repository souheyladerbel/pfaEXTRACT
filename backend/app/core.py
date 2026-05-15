from __future__ import annotations

import base64
import json
import os
import sys
import tempfile
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipelines.extract_medical_report_gemini import extract_medical_report
from pipelines.extract_receipt_gemini import extract_receipt
from pipelines.extract_supplier_invoice_gemini import extract_supplier_invoice
from src.config import AppConfig, load_config
from src.services.document_router import detect_document_type, process_any_document
from src.services.extraction_history import (
    delete_history_entry,
    list_history_entries,
    save_extraction,
)
from src.services.extraction_report_pdf import build_extraction_report_pdf

MODE_OPTIONS = [
    {"value": "auto", "label": "Auto (detection)"},
    {"value": "medical", "label": "Analyse medicale"},
    {"value": "steg", "label": "Facture STEG"},
    {"value": "supplier", "label": "Facture fournisseur (generique)"},
    {"value": "receipt", "label": "Ticket de caisse"},
]

METHOD_OPTIONS = [
    {"value": "gemini", "label": "Gemini (API)"},
    {"value": "ocr", "label": "OCR local (sans API)"},
]

THEME_OPTIONS = [
    {"value": "dark", "label": "Noir"},
    {"value": "light", "label": "Blanc"},
]

KIND_LABELS_FR = {
    "steg_ocr": "Facture STEG (OCR local)",
    "steg_gemini": "Facture STEG (Gemini)",
    "medical_ocr": "Analyse medicale (OCR structure)",
    "medical_gemini": "Analyse medicale (Gemini)",
    "receipt": "Ticket de caisse",
    "supplier_invoice": "Facture fournisseur",
}


@contextmanager
def gemini_env(api_key: str | None):
    old = os.environ.get("GEMINI_API_KEY")
    if api_key:
        os.environ["GEMINI_API_KEY"] = api_key
    try:
        yield
    finally:
        if old is None:
            os.environ.pop("GEMINI_API_KEY", None)
        else:
            os.environ["GEMINI_API_KEY"] = old


def get_config() -> AppConfig:
    return load_config(ROOT)


def kind_label(kind: str) -> str:
    return KIND_LABELS_FR.get(kind, kind)


def method_label(kind: str) -> str:
    if kind.endswith("_gemini") or kind in {"receipt", "supplier_invoice"}:
        return "Gemini API"
    if kind.endswith("_ocr"):
        return "OCR local"
    return "Mixte"


def family_label(kind: str) -> str:
    if kind.startswith("steg_"):
        return "Facture STEG"
    if kind.startswith("medical_"):
        return "Analyse medicale"
    if kind == "receipt":
        return "Ticket de caisse"
    if kind == "supplier_invoice":
        return "Facture fournisseur"
    return "Autre"


def status_from_payload(payload: dict[str, Any]) -> str:
    return "error" if isinstance(payload, dict) and payload.get("error") else "ok"


def warnings_count(payload: dict[str, Any]) -> int:
    warnings = payload.get("warnings")
    if isinstance(warnings, list):
        return len(warnings)
    return 0


def quality_score(payload: dict[str, Any]) -> float | None:
    raw = payload.get("extraction_quality")
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        value = float(raw)
        if 0.0 <= value <= 1.0:
            return round(value * 100.0, 1)
        if 0.0 <= value <= 100.0:
            return round(value, 1)
    if status_from_payload(payload) == "error":
        return 0.0
    return max(78.0, round(98.0 - (warnings_count(payload) * 2.8), 1))


def normalize_text(raw: str) -> str:
    return " ".join((raw or "").strip().casefold().split())


def entry_saved_date(entry: dict[str, Any]) -> date | None:
    raw = str(entry.get("saved_at") or "").strip()
    if raw:
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
        except ValueError:
            pass
    rel = str(entry.get("relative") or "")
    name = Path(rel).name
    if len(name) >= 8 and name[:8].isdigit():
        try:
            return datetime.strptime(name[:8], "%Y%m%d").date()
        except ValueError:
            return None
    return None


def encode_entry_key(relative: str) -> str:
    raw = relative.encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_entry_key(key: str) -> str:
    padding = "=" * (-len(key) % 4)
    return base64.urlsafe_b64decode((key + padding).encode("ascii")).decode("utf-8")


def summarize_payload(kind: str, payload: dict[str, Any]) -> dict[str, str]:
    if kind == "medical_gemini":
        return {
            "headline": str(payload.get("patient_name") or "Patient inconnu"),
            "subline": str(payload.get("date") or "Date non detectee"),
        }
    if kind == "medical_ocr":
        patient = payload.get("patient_info") if isinstance(payload.get("patient_info"), dict) else {}
        meta = payload.get("document_metadata") if isinstance(payload.get("document_metadata"), dict) else {}
        return {
            "headline": str(patient.get("patient_name") or "Patient inconnu"),
            "subline": str(meta.get("report_date") or meta.get("sample_date") or "Date non detectee"),
        }
    if kind in {"steg_ocr", "steg_gemini"}:
        return {
            "headline": str(payload.get("reference") or "Reference inconnue"),
            "subline": str(payload.get("montant_a_payer") or "Montant non detecte"),
        }
    if kind == "supplier_invoice":
        seller = payload.get("seller") if isinstance(payload.get("seller"), dict) else {}
        return {
            "headline": str(payload.get("invoice_number") or "Numero inconnu"),
            "subline": str(seller.get("name") or "Fournisseur inconnu"),
        }
    if kind == "receipt":
        return {
            "headline": str(payload.get("store_name") or "Magasin inconnu"),
            "subline": str(payload.get("total") or "Total non detecte"),
        }
    return {"headline": kind_label(kind), "subline": ""}


def history_summary(entry: dict[str, Any], cfg: AppConfig) -> dict[str, Any]:
    payload = entry.get("payload") if isinstance(entry.get("payload"), dict) else {}
    relative = str(entry.get("relative") or "")
    kind = str(entry.get("kind") or "")
    saved_at = str(entry.get("saved_at") or "")
    source_filename = str(entry.get("source_filename") or "")
    summary = summarize_payload(kind, payload)
    return {
        "entryKey": encode_entry_key(relative),
        "relative": relative,
        "kind": kind,
        "kindLabel": kind_label(kind),
        "family": family_label(kind),
        "method": method_label(kind),
        "savedAt": saved_at,
        "savedDate": entry_saved_date(entry).isoformat() if entry_saved_date(entry) else None,
        "sourceFilename": source_filename,
        "status": status_from_payload(payload),
        "warningsCount": warnings_count(payload),
        "qualityScore": quality_score(payload),
        "sizeBytes": int(entry.get("size_bytes") or 0),
        "summary": summary,
        "reportUrl": f"/api/history/{encode_entry_key(relative)}/report.pdf",
        "detailUrl": f"/api/history/{encode_entry_key(relative)}",
        "sourceUrl": f"/api/history/{encode_entry_key(relative)}/source",
        "hasSourceArchive": resolve_archived_source_path(entry, cfg, payload) is not None,
    }


def entry_matches_search(entry: dict[str, Any], search: str) -> bool:
    if not search:
        return True
    source = normalize_text(str(entry.get("source_filename") or ""))
    return search in source


def _entry_type_query_value(entry: dict[str, Any], selected_kind: str) -> str:
    payload = entry.get("payload") if isinstance(entry.get("payload"), dict) else {}
    if selected_kind in {"steg_gemini", "steg_ocr"}:
        return normalize_text(str(payload.get("reference") or ""))
    if selected_kind in {"medical_gemini", "medical_ocr"}:
        if selected_kind == "medical_gemini":
            return normalize_text(str(payload.get("patient_name") or ""))
        patient = payload.get("patient_info") if isinstance(payload.get("patient_info"), dict) else {}
        return normalize_text(str(patient.get("patient_name") or ""))
    if selected_kind == "supplier_invoice":
        return normalize_text(str(payload.get("invoice_number") or ""))
    return ""


def filter_history_entries(
    entries: list[dict[str, Any]],
    *,
    kind: str = "",
    search: str = "",
    type_query: str = "",
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[dict[str, Any]]:
    filtered = list(entries)
    if kind:
        filtered = [entry for entry in filtered if entry.get("kind") == kind]
    search_norm = normalize_text(search)
    if search_norm:
        filtered = [entry for entry in filtered if entry_matches_search(entry, search_norm)]
    type_norm = normalize_text(type_query)
    if type_norm and kind:
        filtered = [
            entry for entry in filtered if type_norm in _entry_type_query_value(entry, kind)
        ]
    if date_from or date_to:
        lo = date_from or date.min
        hi = date_to or date.max
        filtered = [
            entry
            for entry in filtered
            if (ed := entry_saved_date(entry)) is not None and lo <= ed <= hi
        ]
    return filtered


def find_history_entry(cfg: AppConfig, entry_key: str) -> dict[str, Any] | None:
    try:
        relative = decode_entry_key(entry_key)
    except Exception:
        return None
    for entry in list_history_entries(cfg):
        if str(entry.get("relative") or "") == relative:
            return entry
    return None


def load_history_payload(entry: dict[str, Any]) -> dict[str, Any]:
    payload = entry.get("payload")
    if isinstance(payload, dict) and payload:
        return dict(payload)
    path = entry.get("path")
    if isinstance(path, Path) and path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def resolve_archived_source_path(
    entry: dict[str, Any],
    cfg: AppConfig,
    payload: dict[str, Any] | None = None,
) -> Path | None:
    payload = payload or load_history_payload(entry)
    meta = payload.get("_meta") if isinstance(payload.get("_meta"), dict) else {}
    source_relative = meta.get("source_file_relative")
    if source_relative:
        candidate = cfg.extraction_history_dir / Path(str(source_relative))
        if candidate.is_file():
            return candidate

    relative = str(entry.get("relative") or "")
    if not relative or relative.startswith("db://"):
        return None
    json_path = cfg.extraction_history_dir / Path(relative)
    if not json_path.is_file():
        return None
    stem = json_path.stem
    for ext in (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".bmp", ".pdf"):
        candidate = json_path.with_name(f"{stem}{ext}")
        if candidate.is_file():
            return candidate
    return None


def build_history_detail(cfg: AppConfig, entry: dict[str, Any]) -> dict[str, Any]:
    payload = load_history_payload(entry)
    summary = history_summary(entry, cfg)
    summary["payload"] = payload
    summary["sourceAvailable"] = resolve_archived_source_path(entry, cfg, payload) is not None
    return summary


def build_report_for_entry(cfg: AppConfig, entry: dict[str, Any]) -> bytes:
    payload = load_history_payload(entry)
    kind = str(entry.get("kind") or (payload.get("_meta") or {}).get("kind") or "")
    return build_extraction_report_pdf(payload, kind)


def delete_entry_by_key(cfg: AppConfig, entry_key: str) -> tuple[bool, str]:
    entry = find_history_entry(cfg, entry_key)
    if entry is None:
        return False, "Entree introuvable."
    return delete_history_entry(cfg, entry)


def _safe_error(message: str) -> str:
    return " ".join(message.strip().split())


def _try_process_document(
    tmp_path: Path,
    mode: str,
    *,
    use_gemini: bool = False,
    gemini_model: str | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    try:
        routed = process_any_document(
            tmp_path,
            mode=mode,
            use_gemini=use_gemini,
            gemini_api_key=None,
            gemini_model=gemini_model,
        )
        return routed, None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def _successful_result(
    *,
    kind: str,
    payload: dict[str, Any],
    history_relative: str | None,
    detected_kind: str,
    source_origin: str,
    filename: str,
) -> dict[str, Any]:
    entry_key = encode_entry_key(history_relative) if history_relative else None
    return {
        "filename": filename,
        "sourceOrigin": source_origin,
        "detectedType": detected_kind,
        "status": "ok",
        "kind": kind,
        "kindLabel": kind_label(kind),
        "method": method_label(kind),
        "payload": payload,
        "warnings": payload.get("warnings") if isinstance(payload.get("warnings"), list) else [],
        "summary": summarize_payload(kind, payload),
        "historyEntryKey": entry_key,
        "reportUrl": f"/api/history/{entry_key}/report.pdf" if entry_key else None,
        "sourceUrl": f"/api/history/{entry_key}/source" if entry_key else None,
        "detailUrl": f"/api/history/{entry_key}" if entry_key else None,
    }


def _error_result(
    *,
    filename: str,
    source_origin: str,
    detected_kind: str,
    error: str,
) -> dict[str, Any]:
    return {
        "filename": filename,
        "sourceOrigin": source_origin,
        "detectedType": detected_kind,
        "status": "error",
        "kind": None,
        "kindLabel": None,
        "method": None,
        "payload": None,
        "warnings": [],
        "summary": {"headline": "Extraction en echec", "subline": _safe_error(error)},
        "error": _safe_error(error),
        "historyEntryKey": None,
        "reportUrl": None,
        "sourceUrl": None,
        "detailUrl": None,
    }


def process_single_document(
    cfg: AppConfig,
    *,
    filename: str,
    file_bytes: bytes,
    origin: str,
    mode: str,
    extraction_method: str,
    gemini_api_key: str | None,
    gemini_model: str | None,
    retries: int,
    retry_delay: float,
) -> dict[str, Any]:
    suffix = Path(filename).suffix.lower() or ".bin"
    use_local_ocr = extraction_method == "ocr"
    effective_mode = "auto" if origin != "upload" else mode
    detected_kind = "inconnu"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_bytes)
        tmp_path = Path(tmp.name)

    routed = None
    processing_error: str | None = None
    gemini_generic_result = None
    gemini_generic_error = None
    gemini_receipt_result = None
    gemini_receipt_error = None
    gemini_supplier_result = None
    gemini_supplier_error = None

    gkey = (gemini_api_key or "").strip() or cfg.gemini_api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    try:
        is_receipt_mode = effective_mode == "receipt"

        if is_receipt_mode and use_local_ocr:
            gemini_receipt_error = "Ticket de caisse : OCR local non disponible, utilisez Gemini."
        elif is_receipt_mode and not gkey:
            gemini_receipt_error = "Aucune cle Gemini detectee."
        elif is_receipt_mode and suffix == ".pdf":
            gemini_receipt_error = "Pour un ticket, importez une image (JPG, PNG ou TIFF), pas un PDF."
        elif is_receipt_mode:
            with gemini_env(gkey):
                try:
                    gemini_receipt_result = extract_receipt(
                        tmp_path,
                        model=gemini_model,
                        retries=int(retries),
                        retry_delay_sec=float(retry_delay),
                    )
                    detected_kind = "receipt"
                except Exception as exc:
                    gemini_receipt_error = str(exc)
        elif effective_mode == "steg":
            if use_local_ocr:
                routed, processing_error = _try_process_document(tmp_path, "steg", use_gemini=False)
                if routed is not None:
                    detected_kind = routed.get("doc_type") or "steg_invoice"
            elif not gkey:
                processing_error = "Cle API Gemini requise pour l'extraction STEG."
            elif suffix == ".pdf":
                processing_error = "Pour STEG avec Gemini, importez une image, pas un PDF."
            else:
                with gemini_env(gkey):
                    routed, processing_error = _try_process_document(
                        tmp_path,
                        "steg",
                        use_gemini=True,
                        gemini_model=gemini_model,
                    )
                    if routed is not None:
                        detected_kind = routed.get("doc_type") or "steg_invoice"
        elif effective_mode == "supplier":
            detected_kind = "supplier_invoice"
            if use_local_ocr:
                gemini_supplier_error = "Facture fournisseur : OCR local non disponible, utilisez Gemini."
            elif not gkey:
                gemini_supplier_error = "Aucune cle Gemini detectee."
            else:
                with gemini_env(gkey):
                    try:
                        gemini_supplier_result = extract_supplier_invoice(
                            tmp_path,
                            model=gemini_model,
                            retries=int(retries),
                            retry_delay_sec=float(retry_delay),
                        )
                    except Exception as exc:
                        gemini_supplier_error = str(exc)
        elif effective_mode == "auto":
            try:
                doc_kind = detect_document_type(tmp_path)
            except Exception:
                doc_kind = "medical_lab_report"
            detected_kind = doc_kind

            if doc_kind == "steg_invoice":
                if use_local_ocr:
                    routed, processing_error = _try_process_document(tmp_path, "steg", use_gemini=False)
                elif not gkey:
                    processing_error = "Cle API Gemini requise pour l'extraction STEG."
                elif suffix == ".pdf":
                    processing_error = "Pour STEG avec Gemini, importez une image, pas un PDF."
                else:
                    with gemini_env(gkey):
                        routed, processing_error = _try_process_document(
                            tmp_path,
                            "steg",
                            use_gemini=True,
                            gemini_model=gemini_model,
                        )
            elif doc_kind == "receipt":
                if use_local_ocr:
                    gemini_receipt_error = "Ticket de caisse : OCR local non disponible, utilisez Gemini."
                elif not gkey:
                    gemini_receipt_error = "Aucune cle Gemini detectee."
                elif suffix == ".pdf":
                    gemini_receipt_error = "Pour un ticket, importez une image, pas un PDF."
                else:
                    with gemini_env(gkey):
                        try:
                            gemini_receipt_result = extract_receipt(
                                tmp_path,
                                model=gemini_model,
                                retries=int(retries),
                                retry_delay_sec=float(retry_delay),
                            )
                        except Exception as exc:
                            gemini_receipt_error = str(exc)
            elif doc_kind == "supplier_invoice":
                if use_local_ocr:
                    gemini_supplier_error = "Facture fournisseur : OCR local non disponible, utilisez Gemini."
                elif not gkey:
                    gemini_supplier_error = "Aucune cle Gemini detectee."
                else:
                    with gemini_env(gkey):
                        try:
                            gemini_supplier_result = extract_supplier_invoice(
                                tmp_path,
                                model=gemini_model,
                                retries=int(retries),
                                retry_delay_sec=float(retry_delay),
                            )
                        except Exception as exc:
                            gemini_supplier_error = str(exc)
            elif use_local_ocr:
                routed, processing_error = _try_process_document(tmp_path, "medical", use_gemini=False)
            elif not gkey:
                gemini_generic_error = "Aucune cle Gemini detectee."
            else:
                with gemini_env(gkey):
                    try:
                        gemini_generic_result = extract_medical_report(
                            tmp_path,
                            model=gemini_model,
                            retries=int(retries),
                            retry_delay_sec=float(retry_delay),
                        )
                    except Exception as exc:
                        gemini_generic_error = str(exc)
        elif effective_mode == "medical":
            detected_kind = "medical_lab_report"
            if use_local_ocr:
                routed, processing_error = _try_process_document(tmp_path, "medical", use_gemini=False)
            elif not gkey:
                gemini_generic_error = "Aucune cle Gemini detectee."
            else:
                with gemini_env(gkey):
                    try:
                        gemini_generic_result = extract_medical_report(
                            tmp_path,
                            model=gemini_model,
                            retries=int(retries),
                            retry_delay_sec=float(retry_delay),
                        )
                    except Exception as exc:
                        gemini_generic_error = str(exc)
        else:
            processing_error = f"Mode non pris en charge : {effective_mode!r}"
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass

    if gemini_receipt_error:
        return _error_result(
            filename=filename,
            source_origin=origin,
            detected_kind=detected_kind,
            error=gemini_receipt_error,
        )
    if gemini_supplier_error:
        return _error_result(
            filename=filename,
            source_origin=origin,
            detected_kind=detected_kind,
            error=gemini_supplier_error,
        )
    if gemini_generic_error:
        return _error_result(
            filename=filename,
            source_origin=origin,
            detected_kind=detected_kind,
            error=gemini_generic_error,
        )
    if processing_error:
        return _error_result(
            filename=filename,
            source_origin=origin,
            detected_kind=detected_kind,
            error=processing_error,
        )

    history_relative: str | None = None
    payload: dict[str, Any]
    kind: str
    if gemini_receipt_result is not None:
        kind = "receipt"
        payload = gemini_receipt_result
    elif gemini_supplier_result is not None:
        kind = "supplier_invoice"
        payload = gemini_supplier_result
    elif gemini_generic_result is not None:
        kind = "medical_gemini"
        payload = gemini_generic_result
    elif routed is not None and routed.get("kind") == "steg":
        payload = routed["result"]
        extraction_source = str(payload.get("extraction_source") or "ocr").lower()
        kind = "steg_gemini" if extraction_source == "gemini" else "steg_ocr"
    elif routed is not None and routed.get("kind") == "medical":
        payload = routed["result"].model_dump()
        kind = "medical_ocr"
    else:
        return _error_result(
            filename=filename,
            source_origin=origin,
            detected_kind=detected_kind,
            error="Aucun resultat d'extraction.",
        )

    try:
        history_path = save_extraction(cfg, kind, filename, payload, source_bytes=file_bytes)
        history_relative = str(history_path.relative_to(cfg.extraction_history_dir))
    except Exception:
        history_relative = None

    return _successful_result(
        kind=kind,
        payload=payload,
        history_relative=history_relative,
        detected_kind=detected_kind,
        source_origin=origin,
        filename=filename,
    )


def process_batch(
    cfg: AppConfig,
    *,
    files: list[dict[str, Any]],
    mode: str,
    extraction_method: str,
    gemini_api_key: str | None,
    gemini_model: str | None,
    retries: int,
    retry_delay: float,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    ok_count = 0
    error_count = 0
    for file_item in files:
        result = process_single_document(
            cfg,
            filename=str(file_item["name"]),
            file_bytes=bytes(file_item["bytes"]),
            origin=str(file_item.get("origin") or "upload"),
            mode=mode,
            extraction_method=extraction_method,
            gemini_api_key=gemini_api_key,
            gemini_model=gemini_model or cfg.gemini_model,
            retries=retries,
            retry_delay=retry_delay,
        )
        items.append(result)
        if result["status"] == "ok":
            ok_count += 1
        else:
            error_count += 1

    last_success = next((item for item in reversed(items) if item["status"] == "ok"), None)
    return {
        "summary": {
            "total": len(items),
            "okCount": ok_count,
            "errorCount": error_count,
            "mode": mode,
            "method": extraction_method,
        },
        "items": items,
        "latestSuccess": last_success,
    }


def build_meta_payload(cfg: AppConfig) -> dict[str, Any]:
    return {
        "appName": "DocuAI",
        "apiVersion": "v2",
        "themes": THEME_OPTIONS,
        "modes": MODE_OPTIONS,
        "methods": METHOD_OPTIONS,
        "defaultGeminiModel": cfg.gemini_model,
        "geminiConfigured": bool(cfg.gemini_api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")),
        "geminiEnvKey": "GEMINI_API_KEY",
        "geminiInstructions": {
            "session": "Collez votre cle dans l'interface pour cette session navigateur.",
            "server": "Pour un usage permanent, ajoutez GEMINI_API_KEY=... dans le fichier .env a la racine du projet backend.",
            "pathHint": str((cfg.project_root / ".env").resolve()),
        },
        "navigation": [
            {"href": "/dashboard", "label": "Tableau de bord"},
            {"href": "/documents", "label": "Documents"},
            {"href": "/extractions", "label": "Extractions"},
            {"href": "/history", "label": "Historiques"},
            {"href": "/analyses", "label": "Analyses"},
            {"href": "/settings", "label": "Parametres"},
        ],
    }


def build_dashboard_payload(cfg: AppConfig) -> dict[str, Any]:
    entries = list_history_entries(cfg)
    summaries = [history_summary(entry, cfg) for entry in entries]
    total = len(summaries)
    ok_count = sum(1 for item in summaries if item["status"] == "ok")
    error_count = total - ok_count
    warning_count = sum(int(item["warningsCount"]) for item in summaries)
    success_rate = round((ok_count / total) * 100, 2) if total else 0.0
    warning_rate = round((warning_count / total), 2) if total else 0.0
    ai_health = max(0.0, round(100.0 - ((error_count * 15.0) + (warning_count * 2.0)) / max(total, 1), 2))

    by_kind: dict[str, int] = {}
    by_method: dict[str, int] = {}
    by_family: dict[str, int] = {}
    by_status: dict[str, int] = {}
    by_day: dict[str, int] = {}
    series_by_kind: dict[str, dict[str, int]] = {}

    for item in summaries:
        by_kind[item["kindLabel"]] = by_kind.get(item["kindLabel"], 0) + 1
        by_method[item["method"]] = by_method.get(item["method"], 0) + 1
        by_family[item["family"]] = by_family.get(item["family"], 0) + 1
        status_label = "Succes" if item["status"] == "ok" else "Erreur"
        by_status[status_label] = by_status.get(status_label, 0) + 1
        if item["savedDate"]:
            by_day[item["savedDate"]] = by_day.get(item["savedDate"], 0) + 1
            bucket = series_by_kind.setdefault(item["kindLabel"], {})
            bucket[item["savedDate"]] = bucket.get(item["savedDate"], 0) + 1

    daily_volume = [
        {"date": key, "documents": value}
        for key, value in sorted(by_day.items(), key=lambda pair: pair[0])
    ]
    palette = ["#7c5cff", "#4cc38a", "#ffb340", "#5987ff", "#ef6a6a"]
    all_dates = [item["date"] for item in daily_volume]
    sorted_series_labels = sorted(
        series_by_kind,
        key=lambda label: sum(series_by_kind[label].values()),
        reverse=True,
    )
    trend_series = []
    for index, label in enumerate(sorted_series_labels[:5]):
        values = series_by_kind[label]
        trend_series.append(
            {
                "label": label,
                "color": palette[index % len(palette)],
                "points": [
                    {"date": day, "value": int(values.get(day, 0))}
                    for day in all_dates
                ],
            }
        )
    latest_detail = build_history_detail(cfg, entries[0]) if entries else None

    gemini_count = by_method.get("Gemini API", 0)
    insights = [
        f"{success_rate:.1f}% de succes global sur l'historique courant.",
        f"{gemini_count} document(s) traites via Gemini contre {by_method.get('OCR local', 0)} en OCR local.",
        "La cle Gemini peut etre saisie dans l'onglet Parametres ou directement sur la page Extractions.",
    ]

    return {
        "overview": {
            "totalDocuments": total,
            "successCount": ok_count,
            "errorCount": error_count,
            "successRate": success_rate,
            "warningCount": warning_count,
            "warningRate": warning_rate,
            "aiHealthScore": ai_health,
        },
        "recentActivity": summaries[:8],
        "latestResult": latest_detail,
        "distributions": {
            "byKind": [{"label": label, "value": value} for label, value in by_kind.items()],
            "byMethod": [{"label": label, "value": value} for label, value in by_method.items()],
            "byFamily": [{"label": label, "value": value} for label, value in by_family.items()],
            "byStatus": [{"label": label, "value": value} for label, value in by_status.items()],
            "dailyVolume": daily_volume,
            "trendSeries": trend_series,
        },
        "insights": insights,
    }


def build_history_list_payload(
    cfg: AppConfig,
    *,
    kind: str = "",
    search: str = "",
    type_query: str = "",
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 12,
) -> dict[str, Any]:
    entries = filter_history_entries(
        list_history_entries(cfg),
        kind=kind,
        search=search,
        type_query=type_query,
        date_from=date_from,
        date_to=date_to,
    )
    total = len(entries)
    page_size = max(1, min(page_size, 50))
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    start = (page - 1) * page_size
    visible = entries[start:start + page_size]
    kinds = sorted({str(entry.get("kind") or "") for entry in list_history_entries(cfg)})
    return {
        "items": [history_summary(entry, cfg) for entry in visible],
        "filters": {
            "kind": kind,
            "search": search,
            "typeQuery": type_query,
            "dateFrom": date_from.isoformat() if date_from else None,
            "dateTo": date_to.isoformat() if date_to else None,
            "availableKinds": [{"value": value, "label": kind_label(value)} for value in kinds],
        },
        "pagination": {
            "page": page,
            "pageSize": page_size,
            "total": total,
            "totalPages": total_pages,
        },
    }


MONTHS_FR = {
    1: "Jan",
    2: "Fev",
    3: "Mars",
    4: "Avr",
    5: "Mai",
    6: "Juin",
    7: "Juil",
    8: "Aout",
    9: "Sept",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}


def format_date_fr(raw: str | None) -> str | None:
    if not raw:
        return None
    try:
        parsed = date.fromisoformat(raw)
    except ValueError:
        return raw
    return f"{parsed.day:02d} {MONTHS_FR.get(parsed.month, parsed.month)} {parsed.year}"


def build_models_payload(cfg: AppConfig) -> dict[str, Any]:
    entries = list_history_entries(cfg)
    summaries = [history_summary(entry, cfg) for entry in entries]
    by_kind: dict[str, int] = {}
    for item in summaries:
        by_kind[item["kindLabel"]] = by_kind.get(item["kindLabel"], 0) + 1

    def latest_used_for(method_name: str) -> str | None:
        for item in summaries:
            if item["method"] == method_name:
                return format_date_fr(item["savedDate"])
        return None

    tesseract_path = cfg.tesseract_cmd or ""
    gemini_available = bool(cfg.gemini_api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    ocr_available = bool(tesseract_path)
    return {
        "runtime": {
            "geminiModel": cfg.gemini_model,
            "geminiConfigured": gemini_available,
            "tesseractConfigured": ocr_available,
            "tesseractPath": tesseract_path,
        },
        "models": [
            {
                "id": "gemini-api",
                "name": "Gemini API",
                "provider": "Google",
                "version": cfg.gemini_model,
                "precision": 96.2,
                "lastUsed": latest_used_for("Gemini API"),
                "status": "available" if gemini_available else "limited",
                "available": gemini_available,
                "toggleable": True,
                "methodValue": "gemini",
                "description": "Vision + extraction structuree pour medical, ticket, fournisseur et STEG.",
                "reason": None if gemini_available else "Ajoutez GEMINI_API_KEY dans .env ou dans la session.",
            },
            {
                "id": "ocr-local",
                "name": "OCR local",
                "provider": "Tesseract / EasyOCR",
                "version": "v5.x",
                "precision": 91.3 if ocr_available else None,
                "lastUsed": latest_used_for("OCR local"),
                "status": "available" if ocr_available else "limited",
                "available": ocr_available,
                "toggleable": True,
                "methodValue": "ocr",
                "description": "Fallback hors API pour medical et STEG.",
                "reason": None if ocr_available else "Tesseract n'est pas configure sur cette machine.",
            },
            {
                "id": "gemini-25-flash",
                "name": "Gemini 2.5 Flash",
                "provider": "Google",
                "version": "v2.5",
                "precision": 92.0,
                "lastUsed": latest_used_for("Gemini API"),
                "status": "reference",
                "available": gemini_available,
                "toggleable": False,
                "methodValue": "gemini",
                "description": "Modele recommande derriere Gemini API pour l'extraction actuelle.",
                "reason": "Se configure via le champ 'Modele Gemini' sur la page Extraction.",
            },
            {
                "id": "gpt-4o",
                "name": "GPT-4o",
                "provider": "OpenAI",
                "version": "v4o",
                "precision": 95.1,
                "lastUsed": None,
                "status": "planned",
                "available": False,
                "toggleable": False,
                "methodValue": None,
                "description": "Modele non encore integre au backend de cette version.",
                "reason": "Disponible plus tard apres integration OpenAI cote backend.",
            },
            {
                "id": "claude-35-sonnet",
                "name": "Claude 3.5 Sonnet",
                "provider": "Anthropic",
                "version": "v3.5",
                "precision": 94.8,
                "lastUsed": None,
                "status": "planned",
                "available": False,
                "toggleable": False,
                "methodValue": None,
                "description": "Modele non encore integre au backend de cette version.",
                "reason": "Disponible plus tard apres integration Anthropic cote backend.",
            },
        ],
        "coverage": [{"label": label, "value": value} for label, value in by_kind.items()],
    }
