"""F7: validacion E2E local - 3 datasets reales (CSV ',', CSV ';', XLSX) por el flujo completo.
Valida: file/preview -> analyze -> diagnose -> clean -> report/markdown -> report/pdf.
Contract R3: claves que usa el FRONTEND conservadas; nuevas claves (signal/confidence) presentes.
"""
import base64, os, io
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from openpyxl import Workbook

client = TestClient(app)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES = os.path.join(ROOT, "samples")


def load_b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def _make_semi():
    sem_csv = "\n".join([
        "id;nombre;ciudad;monto;fecha",
        "1;Ana;Bogota;1250,75;2024-01-15",
        "2;Juan;bogota;800,50;2024-02-20",
        "3;Ana;Bogota;1250,75;2024-01-15",
        "4;Maria;Medellin;ABC;2024-03-01",
    ])
    return base64.b64encode(sem_csv.encode()).decode()


def _make_xlsx():
    wb = Workbook()
    ws = wb.active
    ws.title = "Datos"
    ws.append(["id", "cliente", "email", "edad", "registro"])
    ws.append([1, "Ana", "ana@x.com", 28, "2024-01-15"])
    ws.append([2, "Juan", "juan@x.com", 31, "2024-01-16"])
    ws.append([3, "Ana", "ana@x.com", 28, "2024-01-15"])
    ws.append([4, "Maria", "maria@x.com", 450, "2024-01-17"])
    buf = io.BytesIO()
    wb.save(buf)
    return base64.b64encode(buf.getvalue()).decode()


def _preview_settings(filename, b64):
    r = client.post("/api/file/preview", json={"filename": filename, "content_base64": b64})
    assert r.status_code == 200, f"preview {r.status_code}: {r.text}"
    pv = r.json()
    assert "delimiter" in pv and "encoding" in pv and "detected_header_row" in pv and "headers" in pv
    settings = {"delimiter": pv.get("delimiter"), "encoding": pv.get("encoding"), "header_row_index": pv.get("detected_header_row")}
    return {k: v for k, v in settings.items() if v is not None}


def _flow_asserts(filename, b64):
    settings = _preview_settings(filename, b64)

    # analyze: contrato frontend
    r = client.post("/api/analyze", json={"filename": filename, "content_base64": b64, **settings})
    assert r.status_code == 200, f"analyze {r.status_code}: {r.text}"
    an = r.json()["analysis"]
    for key in ["row_count", "column_count", "headers", "scores", "columns", "duplicate_rows", "preview"]:
        assert key in an, f"analyze sin '{key}'"
    assert isinstance(an["scores"].get("overall"), (int, float))
    col0 = an["columns"][0]
    for key in ["name", "detected_type", "missing", "unique_values", "format_issues", "invalid_type_count"]:
        assert key in col0, f"analyze col sin '{key}'"

    # diagnose: motor 28 categorias + R3
    r = client.post("/api/diagnose", json={"filename": filename, "content_base64": b64, **settings})
    assert r.status_code == 200, f"diagnose {r.status_code}: {r.text}"
    diag = r.json()["diagnostic"]
    assert "columns" in diag and "summary" in diag
    all_issues = [i for c in diag["columns"] for i in c.get("issues", [])]
    for iss in all_issues:
        for k in ["category_code", "category", "severity", "description", "count", "affected_rows", "percentage", "examples"]:
            assert k in iss, f"issue sin '{k}': {iss.get('category_code','?')}"
        assert "signal" in iss and "confidence" in iss, f"issue sin signal/confidence: {iss.get('category_code','?')}"
    sum_total = diag["summary"].get("total_issues", 0)
    dist_total = sum(diag["summary"].get("category_distribution", {}).values())
    assert sum_total >= len(all_issues)
    assert dist_total == len(all_issues)

    # clean: review_issue (CL-04) sin mutar datos
    actions = []
    for col in diag["columns"]:
        for iss in col.get("issues", [])[:2]:
            actions.append({"kind": "review_issue", "column": col["column"], "reason": f"Revision manual de {iss.get('category_code','')} (F7)"})
    r = client.post("/api/clean", json={"filename": filename, "content_base64": b64, "actions": actions, **settings})
    assert r.status_code == 200, f"clean {r.status_code}: {r.text}"
    clean = r.json()["cleaning"]
    for key in ["before", "after", "actions", "changelog", "clean_csv", "xlsx_base64"]:
        assert key in clean, f"clean sin '{key}'"
    cl = clean["changelog"]
    review = [e for e in cl if e.get("action") == "Revision manual"]
    assert len(review) == len(actions), f"revisiones {len(review)} != acciones {len(actions)}"
    for e in review:
        assert e.get("changes") == []
    if clean.get("clean_csv"):
        assert clean.get("xlsx_base64"), "clean no genero xlsx_base64"

    # report: markdown + pdf
    r = client.post("/api/report/markdown", json={"cleaning": clean})
    assert r.status_code == 200, f"report/markdown {r.status_code}: {r.text}"
    assert "Revision manual" in r.json()["content"]
    r = client.post("/api/report/pdf", json={"cleaning": clean})
    assert r.status_code == 200, f"report/pdf {r.status_code}: {r.text}"
    pdf = base64.b64decode(r.json()["content_base64"])
    assert pdf[:5] == b"%PDF-", "report/pdf no es PDF valido"

    return len(all_issues)


@pytest.mark.parametrize("name,filename,b64", [
    ("CSV ',' (real sucio)", "dataset_sucio.csv", load_b64(os.path.join(SAMPLES, "dataset_sucio.csv"))),
    ("CSV ';' (numeros con coma)", "reporte_semicolon.csv", _make_semi()),
    ("XLSX (multihilo)", "datos_ventas.xlsx", _make_xlsx()),
])
def test_f7_flujo_completo(name, filename, b64):
    """F7: cada tipo de dataset recorre preview->analyze->diagnose->clean->report sin romper contrato."""
    n = _flow_asserts(filename, b64)
    assert n >= 0


def test_f7_dataset_sucio_detecta_problemas():
    """F7: el dataset sucio real debe detectar multiples hallazgos con signal/confidence."""
    b64 = load_b64(os.path.join(SAMPLES, "dataset_sucio.csv"))
    settings = _preview_settings("dataset_sucio.csv", b64)
    r = client.post("/api/diagnose", json={"filename": "dataset_sucio.csv", "content_base64": b64, **settings})
    diag = r.json()["diagnostic"]
    all_issues = [i for c in diag["columns"] for i in c.get("issues", [])]
    assert len(all_issues) >= 10, f"solo {len(all_issues)} issues detectados"
    assert all(i.get("signal") in ("CONFIRMADO", "A_REVISAR") for i in all_issues)
    codes = {i["category_code"] for i in all_issues}
    assert {"MISSING", "HIDDEN_MISSING", "CATEGORICAL", "TYPE_PER_CELL"} <= codes
