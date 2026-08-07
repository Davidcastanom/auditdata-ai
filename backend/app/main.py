import base64
import hashlib
import os
import time
from typing import Any
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.app.reporting import build_cleaning_pdf_report, build_pdf_report
from data_engine.analyzer import (
    analyze_dataset,
    apply_cleaning_actions,
    build_cleaning_markdown_report,
    build_markdown_report,
    csv_to_xlsx,
    detect_file_settings,
    generate_audit_log,
)

app = FastAPI(title="AuditData AI API", version="1.0.0")

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://127.0.0.1:8000").split(",")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAINTENANCE_MODE = os.getenv("MAINTENANCE_MODE", "0").lower() in ("1", "true", "yes")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def maintenance_middleware(request, call_next):
    """Si MAINTENANCE_MODE está activo, redirige todo excepto rutas esenciales."""
    if MAINTENANCE_MODE:
        path = request.url.path
        # Rutas que siguen funcionando durante mantenimiento
        allowed = (
            path == "/maintenance"
            or path.startswith("/frontend/")
            or path == "/api/health"
            or path.startswith("/admin")
        )
        if not allowed:
            from starlette.responses import RedirectResponse
            return RedirectResponse(url="/maintenance", status_code=307)
    return await call_next(request)


@app.middleware("http")
async def metrics_middleware(request, call_next):
    """Mide duración y status de cada request /api/* para métricas anónimas.
    NUNCA captura contenido del cuerpo: solo endpoint, status y tiempo."""
    start = time.perf_counter()
    status_code = 500
    error_type = None
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception as e:
        error_type = type(e).__name__
        raise
    finally:
        if request.url.path.startswith("/api/"):
            duration_ms = (time.perf_counter() - start) * 1000
            client_id = request.headers.get("x-client-id", "anon")
            session_id = request.headers.get("x-session-id", "")
            try:
                from backend.app.metrics import record_error, record_usage_event

                record_usage_event(
                    client_id=client_id,
                    session_id=session_id,
                    endpoint=request.url.path,
                    method=request.method,
                    status_code=status_code,
                    duration_ms=duration_ms,
                )
                if status_code >= 400:
                    record_error(
                        client_id=client_id,
                        endpoint=request.url.path,
                        status_code=status_code,
                        error_type=error_type,
                    )
            except Exception as e:
                # Las métricas jamás deben romper la aplicación
                import logging

                logging.getLogger(__name__).warning("Métricas ignoradas: %s", e)

class AnalyzeRequest(BaseModel):
    filename: str
    content_base64: str
    duplicate_key_columns: list[str] | None = None
    delimiter: str | None = None
    encoding: str | None = None
    header_row: int | None = None


def _dataset_settings(req: BaseModel) -> dict[str, Any]:
    """Extract the CSV parse settings detected in the file preview (if any)."""
    return {
        "delimiter": getattr(req, "delimiter", None),
        "encoding": getattr(req, "encoding", None),
        "header_row": getattr(req, "header_row", None),
    }

class ActionItem(BaseModel):
    kind: str
    column: str = ""
    reason: str = ""
    method: str = ""
    value: Any = ""
    rows: list[int] | None = None
    _rowsKey: str = ""

class CleanRequest(BaseModel):
    filename: str
    content_base64: str
    actions: list[ActionItem]
    duplicate_key_columns: list[str] | None = None
    delimiter: str | None = None
    encoding: str | None = None
    header_row: int | None = None

class ReportRequest(BaseModel):
    cleaning: dict[str, Any] | None = None
    analysis: dict[str, Any] | None = None
    analyst: str = "-"
    version: str = "v1.0"
    row_meaning: str = ""
    analysis_objective: str = ""


def _decode_payload(content_base64: str) -> bytes:
    """Decode base64 payload and enforce MAX_FILE_SIZE."""
    payload = base64.b64decode(content_base64)
    if len(payload) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="El archivo excede el limite de 10MB")
    return payload

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0", "service": "AuditData AI"}

@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    try:
        payload = _decode_payload(req.content_base64)
        analysis = analyze_dataset(req.filename, payload, duplicate_key_columns=req.duplicate_key_columns, **_dataset_settings(req))
        return {"analysis": analysis}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/diagnose")
def diagnose(req: AnalyzeRequest):
    try:
        payload = _decode_payload(req.content_base64)
        from data_engine.diagnostic import diagnose_dataset
        from data_engine.analyzer import load_dataset
        headers, rows, header_row_index = load_dataset(req.filename, payload, **_dataset_settings(req))
        diagnostic = diagnose_dataset(headers, rows, header_row_index)
        return {"diagnostic": diagnostic.to_dict()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/file/preview")
def file_preview(req: AnalyzeRequest):
    """Detect encoding, delimiter, header row and return preview of the file."""
    try:
        payload = _decode_payload(req.content_base64)
        settings = detect_file_settings(req.filename, payload)
        return settings
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class AIChatRequest(BaseModel):
    filename: str
    content_base64: str
    column: str
    user_query: str
    detected_type: str = "unknown"
    inferred_domain: str = ""
    chat_history: list[dict[str, str]] | None = None


@app.post("/api/ai/recommend")
async def ai_recommend(req: AnalyzeRequest):
    """
    Endpoint asíncrono para obtener recomendaciones de IA rápidas.
    """
    try:
        payload = _decode_payload(req.content_base64)

        from data_engine.diagnostic import diagnose_dataset
        from data_engine.analyzer import load_dataset
        from data_engine.ai_advisor import get_ai_recommendations_async

        headers, rows, header_row_index = load_dataset(req.filename, payload, **_dataset_settings(req))
        diagnostic = diagnose_dataset(headers, rows, header_row_index)

        recommendations = await get_ai_recommendations_async(
            diagnostic=diagnostic.to_dict(),
            sample_rows=rows[:20]
        )

        return {"recommendations": recommendations}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/ai/chat-column")
async def ai_chat_column(req: AIChatRequest):
    """
    Endpoint para chatear interactivamente con el Copiloto de IA sobre una columna o el dataset.
    """
    try:
        from data_engine.ai_advisor import chat_with_column_advisor

        session = _get_chat_session(req)

        res = await chat_with_column_advisor(
            column_name=req.column,
            user_query=req.user_query,
            column_diagnostic=session["col_diag"],
            chat_history=req.chat_history,
            context=session["context"],
            total_rows=session["total_rows"],
            total_columns=session["total_columns"],
            headers=session["headers"],
            detected_type=req.detected_type,
            inferred_domain=req.inferred_domain,
            other_columns=session["other_columns"],
        )
        return res

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# CHAT-04: cache en memoria del trabajo pesado del chat (decode + load + diagnose
# + contexto de columna), por hash del archivo. El 2º mensaje del mismo archivo no
# recalcula nada. Adecuado para 1 instancia Render; se pierde al reiniciar.
_chat_session_cache: dict[str, dict[str, Any]] = {}
CHAT_SESSION_CACHE_MAX = 8


def _get_chat_session(req: AIChatRequest) -> dict[str, Any]:
    """Recupera o construye el contexto de chat cacheado para un archivo+columna."""
    key = f"{req.column}:{req.detected_type}:{hashlib.sha256(req.content_base64.encode('utf-8')).hexdigest()}"
    cached = _chat_session_cache.get(key)
    if cached is not None:
        return cached

    payload = _decode_payload(req.content_base64)

    from data_engine.diagnostic import diagnose_dataset
    from data_engine.analyzer import load_dataset
    from data_engine.ai_advisor import compute_column_context

    headers, rows, header_row_index = load_dataset(req.filename, payload, **_dataset_settings(req))
    file_row_start = header_row_index + 2
    column_data = [(file_row_start + i, row.get(req.column, "")) for i, row in enumerate(rows)]

    diagnostic = diagnose_dataset(headers, rows, header_row_index)
    diag_dict = diagnostic.to_dict()

    col_diag = None
    for col in diag_dict.get("columns", []):
        if col.get("column") == req.column:
            col_diag = col
            break

    context = compute_column_context(column_data, req.detected_type)

    other_columns = [
        {
            "name": col.get("column"),
            "detected_type": (col.get("profiler") or {}).get("type"),
            "total_categories": (col.get("profiler") or {}).get("total_categories"),
            "issue_count": col.get("issue_count"),
        }
        for col in diag_dict.get("columns", [])
        if col.get("column") != req.column
    ]

    session = {
        "col_diag": col_diag,
        "context": context,
        "total_rows": len(rows),
        "total_columns": len(headers),
        "headers": headers,
        "other_columns": other_columns,
    }
    _chat_session_cache[key] = session
    if len(_chat_session_cache) > CHAT_SESSION_CACHE_MAX:
        _chat_session_cache.pop(next(iter(_chat_session_cache)))
    return session


class ColumnDeepAnalysisRequest(BaseModel):
    filename: str
    content_base64: str
    column: str
    detected_type: str = "unknown"
    inferred_domain: str = ""


@app.post("/api/ai/column-deep-analysis")
async def ai_column_deep_analysis(req: ColumnDeepAnalysisRequest):
    """
    Analiza una columna como experto senior: hallazgos + recomendaciones estructuradas.
    Incluye contexto completo: indicadores, frecuencias, estadisticas y datos ordenados.
    """
    try:
        payload = _decode_payload(req.content_base64)

        from data_engine.ai_advisor import analyze_column_deep, compute_column_context
        from data_engine.analyzer import load_dataset

        headers, rows, header_row_index = load_dataset(req.filename, payload, **_dataset_settings(req))
        file_row_start = header_row_index + 2
        column_data = [(file_row_start + i, row.get(req.column, "")) for i, row in enumerate(rows)]

        context = compute_column_context(column_data, req.detected_type)

        result = await analyze_column_deep(
            column_name=req.column,
            column_data=context["sorted_data"],
            total_rows=len(rows),
            total_columns=len(headers),
            headers=headers,
            detected_type=req.detected_type,
            inferred_domain=req.inferred_domain,
            unique_count=context["unique_count"],
            missing_count=context["missing_count"],
            value_distribution=context["value_distribution"],
            stats_summary=context["stats_summary"],
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        return {"analysis": f"Error: {e}", "status": "error"}


@app.post("/api/clean")
def clean(req: CleanRequest):
    try:
        payload = _decode_payload(req.content_base64)
        actions_dict = [action.model_dump() for action in req.actions]
        cleaning = apply_cleaning_actions(req.filename, payload, actions_dict, duplicate_key_columns=req.duplicate_key_columns, **_dataset_settings(req))
        clean_csv = cleaning.get("clean_csv", "")
        xlsx_b64 = ""
        if clean_csv:
            try:
                xlsx_bytes = csv_to_xlsx(clean_csv)
                xlsx_b64 = base64.b64encode(xlsx_bytes).decode("ascii")
            except Exception:
                xlsx_b64 = ""
        cleaning["xlsx_base64"] = xlsx_b64
        return {"cleaning": cleaning}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/report/markdown")
def report_markdown(req: ReportRequest):
    try:
        if req.cleaning:
            markdown = build_cleaning_markdown_report(
                req.cleaning,
                analyst=req.analyst,
                version=req.version,
                row_meaning=req.row_meaning,
                analysis_objective=req.analysis_objective,
            )
        elif req.analysis:
            markdown = build_markdown_report(
                req.analysis,
                analyst=req.analyst,
                version=req.version,
            )
        else:
            raise HTTPException(status_code=400, detail="Faltan datos de limpieza o análisis")
        return {"filename": "data_cleaning_report.md", "content": markdown}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/report/pdf")
def report_pdf(req: ReportRequest):
    try:
        if req.cleaning:
            pdf = build_cleaning_pdf_report(
                req.cleaning,
                analyst=req.analyst,
                version=req.version,
                row_meaning=req.row_meaning,
                analysis_objective=req.analysis_objective,
            )
        elif req.analysis:
            pdf = build_pdf_report(
                req.analysis,
                analyst=req.analyst,
                version=req.version,
            )
        else:
            raise HTTPException(status_code=400, detail="Faltan datos de limpieza o análisis")
        pdf_b64 = base64.b64encode(pdf).decode("ascii")
        return {"filename": "data_cleaning_report.pdf", "content_base64": pdf_b64}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/report/audit-log")
def report_audit_log(req: CleanRequest):
    try:
        payload = _decode_payload(req.content_base64)
        actions_dict = [action.model_dump() for action in req.actions]
        cleaning = apply_cleaning_actions(req.filename, payload, actions_dict)
        changelog = cleaning.get("changelog", [])
        markdown = generate_audit_log(changelog, filename=req.filename)
        return {"filename": "bitacora_cambios.md", "content": markdown}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# ADMIN: métricas anónimas de uso (ver backend/app/metrics.py)
# ---------------------------------------------------------------------------

def _admin_emails() -> list[str]:
    return [
        e.strip().lower()
        for e in os.getenv("ADMIN_EMAILS", "").split(",")
        if e.strip()
    ]


def _require_admin(authorization: str | None):
    """Valida el acceso de administrador. Acepta:
    1. JWT de Supabase (login con Google o email/password) cuyo usuario tenga
       user_metadata.role == "admin" o esté en ADMIN_EMAILS.
    2. ADMIN_TOKEN (fallback para scripts / make send-errors).
    Nunca expone datos de usuarios: solo devuelve rol y email del admin."""
    from backend.app.auth import verify_token
    from backend.app.metrics import ADMIN_TOKEN as _token

    if not authorization:
        raise HTTPException(status_code=401, detail="Token requerido")

    token = authorization.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    # 1) Token interno (make / scripts)
    if _token and token == _token:
        return {"role": "admin", "source": "token"}

    # 2) JWT de Supabase
    user = verify_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

    email = (user.get("email") or "").lower()
    # Solo el server puede escribir app_metadata (los usuarios no pueden
    # auto-promoverse modificando user_metadata, que es editable por el cliente).
    role = (user.get("app_metadata") or {}).get("role", "")
    if role == "admin" or email in _admin_emails():
        return {"role": "admin", "email": email, "source": "supabase"}

    raise HTTPException(status_code=403, detail="No tienes permisos de administrador")


@app.get("/api/admin/metrics")
def admin_metrics(authorization: str | None = Header(default=None)):
    """Métricas agregadas para el panel admin: actividad diaria y duración de sesiones."""
    _require_admin(authorization)
    from backend.app.metrics import get_admin_metrics

    return {"metrics": get_admin_metrics()}


@app.get("/api/admin/errors")
def admin_errors(
    authorization: str | None = Header(default=None),
    limit: int = 50,
    resolved: str = "false",
):
    """Lista de errores recientes (solo tipo + endpoint, sin datos de usuario).

    resolved: "false" (pendientes, por defecto) | "true" (resueltos) | "all".
    """
    _require_admin(authorization)
    from backend.app.metrics import get_admin_errors

    filter_map = {"false": False, "true": True, "all": None}
    resolved_filter = filter_map.get((resolved or "false").lower(), False)
    return {"errors": get_admin_errors(limit=limit, resolved=resolved_filter)}


class ResolveErrorsRequest(BaseModel):
    ids: list[str] | None = None


@app.post("/api/admin/errors/resolve")
def admin_errors_resolve(
    req: ResolveErrorsRequest | None = None,
    authorization: str | None = Header(default=None),
):
    """Marca errores como resueltos. ids vacío/ausente resuelve todos los pendientes."""
    _require_admin(authorization)
    from backend.app.metrics import resolve_errors

    ids = list(req.ids) if req and req.ids else None
    resolved = resolve_errors(ids)
    return {"resolved": resolved}


@app.post("/api/admin/errors/send")
async def admin_errors_send(authorization: str | None = Header(default=None)):
    """Envía el resumen de errores al webhook de Make.com (email automatizado)."""
    _require_admin(authorization)
    from backend.app.metrics import build_errors_report, notify_make_webhook

    payload = build_errors_report()
    result = await notify_make_webhook(payload)
    return {"result": result, "report": payload}

frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend")

@app.get("/")
def read_root():
    return FileResponse(os.path.join(frontend_path, "index.html"))


@app.get("/admin")
def read_admin():
    """Ventana de administrador: métricas anónimas de uso."""
    return FileResponse(os.path.join(frontend_path, "admin.html"))


@app.get("/maintenance")
def read_maintenance():
    """Página de mantenimiento programado."""
    return FileResponse(os.path.join(frontend_path, "maintenance.html"))

app.mount("/frontend", StaticFiles(directory=frontend_path), name="frontend")
