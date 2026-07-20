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

class CleanRequest(BaseModel):
    filename: str
    content_base64: str
    actions: list[ActionItem]

class ReportMarkdownRequest(BaseModel):
    cleaning: dict[str, Any] | None = None
    analysis: dict[str, Any] | None = None
    analyst: str = "-"
    version: str = "v1.0"

class ReportPdfRequest(BaseModel):
    cleaning: dict[str, Any] | None = None
    analysis: dict[str, Any] | None = None
    analyst: str = "-"
    version: str = "v1.0"

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
