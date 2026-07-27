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

class ReportMarkdownRequest(BaseModel):
    cleaning: dict[str, Any] | None = None
    analysis: dict[str, Any] | None = None
    analyst: str = "-"
    version: str = "v1.0"
    row_meaning: str = ""
    analysis_objective: str = ""

class ReportPdfRequest(BaseModel):
    cleaning: dict[str, Any] | None = None
    analysis: dict[str, Any] | None = None
    analyst: str = "-"
    version: str = "v1.0"
    row_meaning: str = ""
    analysis_objective: str = ""

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0", "service": "AuditData AI"}

@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    try:
        payload = base64.b64decode(req.content_base64)
        if len(payload) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="El archivo excede el límite de 10MB")
        analysis = analyze_dataset(req.filename, payload)
        return {"analysis": analysis}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/diagnose")
def diagnose(req: AnalyzeRequest):
    try:
        payload = base64.b64decode(req.content_base64)
        if len(payload) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="El archivo excede el limite de 10MB")
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
        payload = base64.b64decode(req.content_base64)
        if len(payload) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="El archivo excede el limite de 10MB")
        from data_engine.analyzer import detect_file_settings
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
    chat_history: list[dict[str, str]] | None = None


class ColumnRecommendRequest(BaseModel):
    filename: str
    content_base64: str
    column: str


@app.post("/api/ai/recommend")
async def ai_recommend(req: AnalyzeRequest):
    """
    Endpoint asíncrono para obtener recomendaciones de IA rápidas.
    """
    try:
        payload = base64.b64decode(req.content_base64)
        if len(payload) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="El archivo excede el límite de 10MB")

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
        payload = base64.b64decode(req.content_base64)
        if len(payload) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="El archivo excede el límite de 10MB")

        from data_engine.diagnostic import diagnose_dataset
        from data_engine.analyzer import load_dataset
        from data_engine.ai_advisor import chat_with_column_advisor

        headers, rows, header_row_index = load_dataset(req.filename, payload)
        diagnostic = diagnose_dataset(headers, rows, header_row_index)
        diag_dict = diagnostic.to_dict()

        col_diag = None
        for col in diag_dict.get("columns", []):
            if col.get("column") == req.column:
                col_diag = col
                break

        res = await chat_with_column_advisor(
            column_name=req.column,
            user_query=req.user_query,
            column_diagnostic=col_diag,
            sample_rows=rows[:20],
            chat_history=req.chat_history
        )
        return res

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/ai/column-recommendations")
async def ai_column_recommendations(req: ColumnRecommendRequest):
    """Genera recomendaciones de depuración para una columna específica."""
    try:
        payload = base64.b64decode(req.content_base64)
        if len(payload) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="El archivo excede el límite de 10MB")

        from data_engine.diagnostic import diagnose_dataset
        from data_engine.analyzer import load_dataset
        from data_engine.ai_advisor import get_column_depuration_recommendations

        headers, rows, header_row_index = load_dataset(req.filename, payload)
        diagnostic = diagnose_dataset(headers, rows, header_row_index)
        diag_dict = diagnostic.to_dict()

        col_diag = {"issues": [], "inferred_domain": None, "total_rows": len(rows)}
        for col in diag_dict.get("columns", []):
            if col.get("column") == req.column:
                col_diag = col
                break

        result = await get_column_depuration_recommendations(
            column_name=req.column,
            column_diagnostic=col_diag,
            sample_rows=rows[:20]
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error en column-recommendations: %s", e)
        return {"recommendations": [], "status": "error", "message": str(e)}


@app.post("/api/clean")
def clean(req: CleanRequest):
    try:
        payload = base64.b64decode(req.content_base64)
        if len(payload) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="El archivo excede el límite de 10MB")
        actions_dict = [action.model_dump() for action in req.actions]
        cleaning = apply_cleaning_actions(req.filename, payload, actions_dict)
        return {"cleaning": cleaning}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/report/markdown")
def report_markdown(req: ReportMarkdownRequest):
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
def report_pdf(req: ReportPdfRequest):
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
        payload = base64.b64decode(req.content_base64)
        if len(payload) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="El archivo excede el límite de 10MB")
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
