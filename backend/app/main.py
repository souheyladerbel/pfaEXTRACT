from __future__ import annotations

import json
import mimetypes
from datetime import date
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response

from backend.app.core import (
    build_dashboard_payload,
    build_history_detail,
    build_history_list_payload,
    build_meta_payload,
    build_models_payload,
    build_report_for_entry,
    delete_entry_by_key,
    find_history_entry,
    get_config,
    process_batch,
    resolve_archived_source_path,
)

app = FastAPI(
    title="DocuAI API",
    version="2.0.0",
    summary="Backend FastAPI pour la nouvelle interface DocuAI",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Date invalide: {raw}") from exc


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/meta")
def meta() -> dict:
    return build_meta_payload(get_config())


@app.get("/api/dashboard")
def dashboard() -> dict:
    return build_dashboard_payload(get_config())


@app.get("/api/analyses")
def analyses() -> dict:
    return build_dashboard_payload(get_config())


@app.get("/api/models")
def models() -> dict:
    return build_models_payload(get_config())


@app.get("/api/history")
def history(
    kind: str = "",
    search: str = "",
    typeQuery: str = "",
    dateFrom: str | None = None,
    dateTo: str | None = None,
    page: int = 1,
    pageSize: int = 12,
) -> dict:
    return build_history_list_payload(
        get_config(),
        kind=kind,
        search=search,
        type_query=typeQuery,
        date_from=_parse_date(dateFrom),
        date_to=_parse_date(dateTo),
        page=page,
        page_size=pageSize,
    )


@app.get("/api/history/{entry_key}")
def history_detail(entry_key: str) -> dict:
    cfg = get_config()
    entry = find_history_entry(cfg, entry_key)
    if entry is None:
        raise HTTPException(status_code=404, detail="Entree introuvable.")
    return build_history_detail(cfg, entry)


@app.delete("/api/history/{entry_key}")
def history_delete(entry_key: str) -> dict[str, str]:
    ok, message = delete_entry_by_key(get_config(), entry_key)
    if not ok:
        raise HTTPException(status_code=404, detail=message)
    return {"status": "ok", "message": message}


@app.get("/api/history/{entry_key}/report.pdf")
def history_report(entry_key: str) -> Response:
    cfg = get_config()
    entry = find_history_entry(cfg, entry_key)
    if entry is None:
        raise HTTPException(status_code=404, detail="Entree introuvable.")
    pdf_bytes = build_report_for_entry(cfg, entry)
    return Response(content=pdf_bytes, media_type="application/pdf")


@app.get("/api/history/{entry_key}/source")
def history_source(entry_key: str):
    cfg = get_config()
    entry = find_history_entry(cfg, entry_key)
    if entry is None:
        raise HTTPException(status_code=404, detail="Entree introuvable.")
    payload = build_history_detail(cfg, entry).get("payload")
    source_path = resolve_archived_source_path(entry, cfg, payload if isinstance(payload, dict) else None)
    if source_path is None:
        raise HTTPException(status_code=404, detail="Source archivee indisponible.")
    media_type, _ = mimetypes.guess_type(str(source_path))
    return FileResponse(path=source_path, media_type=media_type or "application/octet-stream")


@app.get("/api/results/latest")
def latest_result():
    cfg = get_config()
    history = build_history_list_payload(cfg, page=1, page_size=1)
    items = history.get("items") if isinstance(history.get("items"), list) else []
    if not items:
        return JSONResponse({"item": None})
    entry = find_history_entry(cfg, items[0]["entryKey"])
    if entry is None:
        return JSONResponse({"item": None})
    return {"item": build_history_detail(cfg, entry)}


@app.post("/api/extractions")
async def extractions(
    files: Annotated[list[UploadFile], File(...)],
    mode: Annotated[str, Form()] = "auto",
    method: Annotated[str, Form()] = "gemini",
    geminiApiKey: Annotated[str | None, Form()] = None,
    geminiModel: Annotated[str | None, Form()] = None,
    retries: Annotated[int, Form()] = 5,
    retryDelay: Annotated[float, Form()] = 2.0,
    originsJson: Annotated[str | None, Form()] = None,
) -> dict:
    if not files:
        raise HTTPException(status_code=400, detail="Aucun fichier envoye.")

    origins: list[str] = []
    if originsJson:
        try:
            parsed = json.loads(originsJson)
            if isinstance(parsed, list):
                origins = [str(item or "upload") for item in parsed]
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="originsJson invalide.") from exc

    payload_files: list[dict] = []
    for index, upload in enumerate(files):
        file_bytes = await upload.read()
        payload_files.append(
            {
                "name": upload.filename or f"document_{index + 1}",
                "bytes": file_bytes,
                "origin": origins[index] if index < len(origins) else "upload",
            }
        )

    return process_batch(
        get_config(),
        files=payload_files,
        mode=mode,
        extraction_method=method,
        gemini_api_key=geminiApiKey,
        gemini_model=geminiModel,
        retries=retries,
        retry_delay=retryDelay,
    )
