import base64
import os
from typing import Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    filename: str
    content_base64: str
    duplicate_key_columns: list[str] | None = None

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
        analysis = analyze_dataset(req.filename, payload, duplicate_key_columns=req.duplicate_key_columns)
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
        headers, rows, header_row_index = load_dataset(req.filename, payload)
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

        headers, rows, header_row_index = load_dataset(req.filename, payload)
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
        payload = _decode_payload(req.content_base64)

        from data_engine.diagnostic import diagnose_dataset
        from data_engine.analyzer import load_dataset
        from data_engine.ai_advisor import chat_with_column_advisor, compute_column_context

        headers, rows, header_row_index = load_dataset(req.filename, payload)
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

        res = await chat_with_column_advisor(
            column_name=req.column,
            user_query=req.user_query,
            column_diagnostic=col_diag,
            chat_history=req.chat_history,
            context=context,
            total_rows=len(rows),
            total_columns=len(headers),
            headers=headers,
            detected_type=req.detected_type,
            inferred_domain=req.inferred_domain,
        )
        return res

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


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

        headers, rows, header_row_index = load_dataset(req.filename, payload)
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
        cleaning = apply_cleaning_actions(req.filename, payload, actions_dict, duplicate_key_columns=req.duplicate_key_columns)
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

frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend")

@app.get("/")
def read_root():
    return FileResponse(os.path.join(frontend_path, "index.html"))

app.mount("/frontend", StaticFiles(directory=frontend_path), name="frontend")
