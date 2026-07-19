"""Report builders for AuditData AI.

Markdown is used as the transparent source format. PDF is generated from the
same analysis object so future templates can preserve one source of truth.
"""

from __future__ import annotations

import io
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


BRAND = {
    "blue": "#0066FF",
    "blue_dark": "#0052CC",
    "cyan": "#00D4FF",
    "black": "#0A0A0F",
    "surface": "#12121A",
    "text": "#F0F0F5",
    "muted": "#9090A0",
}


def build_pdf_report(analysis: dict[str, Any], analyst: str = "-", version: str = "v1.0") -> bytes:
    """Generate a clean executive PDF report with the project palette."""

    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.4 * cm,
        leftMargin=1.4 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
    )
    styles = _styles()
    story = [
        Paragraph("DATA CLEANING REPORT", styles["TitleBar"]),
        Paragraph("Informe profesional de limpieza y validacion de calidad de datos", styles["SubtitleBar"]),
        Spacer(1, 0.5 * cm),
        Paragraph("INFORMACION GENERAL", styles["Section"]),
        _table(
            [
                ["Dataset", analysis["filename"]],
                ["Analista", analyst or "-"],
                ["Version", version or "v1.0"],
                ["Filas", str(analysis["row_count"])],
                ["Columnas", str(analysis["column_count"])],
                ["Fecha tecnica", analysis["generated_at"]],
            ]
        ),
        Spacer(1, 0.45 * cm),
        Paragraph("RESUMEN EJECUTIVO", styles["Section"]),
        Paragraph(_summary(analysis), styles["Body"]),
        Spacer(1, 0.45 * cm),
        Paragraph("INDICADORES CLAVE", styles["Section"]),
        _table(
            [
                ["Indicador", "Resultado"],
                ["Completitud", f"{analysis['scores']['completeness']}%"],
                ["Consistencia", f"{analysis['scores']['consistency']}%"],
                ["Exactitud estadistica", f"{analysis['scores']['accuracy']}%"],
                ["Unicidad", f"{analysis['scores']['uniqueness']}%"],
                ["Calidad general", f"{analysis['scores']['overall']}%"],
                ["Filas duplicadas", str(analysis["duplicate_rows"])],
            ],
            header=True,
        ),
        Spacer(1, 0.45 * cm),
        Paragraph("PROBLEMAS ENCONTRADOS", styles["Section"]),
        _table(
            [["Columna", "Tipo", "Faltantes", "Inconsist.", "Outliers"]]
            + [
                [
                    c["name"],
                    c["detected_type"],
                    str(c["missing"]),
                    str(c["format_issues"]),
                    str(c["outliers"]),
                ]
                for c in analysis["columns"]
            ],
            header=True,
        ),
        Spacer(1, 0.45 * cm),
        Paragraph("RECOMENDACIONES", styles["Section"]),
    ]

    for recommendation in analysis["recommendations"]:
        story.append(Paragraph(f"<b>{recommendation['priority']}:</b> {recommendation['message']}", styles["Body"]))

    document.build(story)
    return buffer.getvalue()


def build_cleaning_pdf_report(cleaning: dict[str, Any], analyst: str = "-", version: str = "v1.0") -> bytes:
    """Generate a Data Cleaning Report with before/after evidence."""

    before = cleaning["before"]
    after = cleaning["after"]
    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.4 * cm,
        leftMargin=1.4 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
    )
    styles = _styles()
    story = [
        Paragraph("DATA CLEANING REPORT", styles["TitleBar"]),
        Paragraph("Limpieza, validacion y trazabilidad de decisiones", styles["SubtitleBar"]),
        Spacer(1, 0.5 * cm),
        Paragraph("1. INFORMACION GENERAL", styles["Section"]),
        _table(
            [
                ["Dataset original", before["filename"]],
                ["Dataset limpio", after["filename"]],
                ["Analista", analyst or "-"],
                ["Version", version or "v1.0"],
                ["Fecha tecnica", after["generated_at"]],
                ["Acciones documentadas", str(len(cleaning["actions"]))],
            ]
        ),
        Spacer(1, 0.45 * cm),
        Paragraph("2. RESUMEN EJECUTIVO", styles["Section"]),
        Paragraph(
            f"Se ejecuto un proceso secuencial de limpieza sobre {before['filename']}. "
            f"La calidad general paso de {before['scores']['overall']}% a {after['scores']['overall']}%. "
            "Cada decision quedo registrada para facilitar auditoria, mantenimiento y reutilizacion.",
            styles["Body"],
        ),
        Spacer(1, 0.45 * cm),
        Paragraph("3. CALIDAD ANTES Y DESPUES", styles["Section"]),
        _table(
            [
                ["Indicador", "Antes", "Despues"],
                ["Filas", str(before["row_count"]), str(after["row_count"])],
                ["Columnas", str(before["column_count"]), str(after["column_count"])],
                ["Duplicados", str(before["duplicate_rows"]), str(after["duplicate_rows"])],
                ["Completitud", f"{before['scores']['completeness']}%", f"{after['scores']['completeness']}%"],
                ["Consistencia", f"{before['scores']['consistency']}%", f"{after['scores']['consistency']}%"],
                ["Exactitud", f"{before['scores']['accuracy']}%", f"{after['scores']['accuracy']}%"],
                ["Unicidad", f"{before['scores']['uniqueness']}%", f"{after['scores']['uniqueness']}%"],
                ["Calidad general", f"{before['scores']['overall']}%", f"{after['scores']['overall']}%"],
            ],
            header=True,
        ),
        Spacer(1, 0.45 * cm),
        Paragraph("4. ACCIONES REALIZADAS", styles["Section"]),
        _table(
            [["Columna", "Accion", "Justificacion", "Resultado"]]
            + [
                [item["column"], item["action"], item["reason"], item["result"]]
                for item in cleaning["actions"]
            ]
            if cleaning["actions"]
            else [["Columna", "Accion", "Justificacion", "Resultado"], ["Dataset", "Sin acciones", "-", "Sin cambios"]],
            header=True,
        ),
        Spacer(1, 0.45 * cm),
        Paragraph("5. RIESGOS Y CONCLUSION", styles["Section"]),
        Paragraph(_cleaning_conclusion(after), styles["Body"]),
    ]

    document.build(story)
    return buffer.getvalue()


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "TitleBar": ParagraphStyle(
            "TitleBar",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            textColor=colors.white,
            alignment=1,
            backColor=colors.HexColor(BRAND["blue_dark"]),
            leading=24,
            spaceAfter=0,
        ),
        "SubtitleBar": ParagraphStyle(
            "SubtitleBar",
            parent=base["Normal"],
            fontSize=11,
            textColor=colors.white,
            alignment=1,
            backColor=colors.HexColor(BRAND["blue"]),
            leading=18,
        ),
        "Section": ParagraphStyle(
            "Section",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=colors.white,
            alignment=1,
            backColor=colors.HexColor(BRAND["blue"]),
            leading=17,
            spaceBefore=6,
            spaceAfter=4,
        ),
        "Body": ParagraphStyle("Body", parent=base["BodyText"], fontSize=10, leading=13),
    }


def _table(rows: list[list[str]], header: bool = False) -> Table:
    table = Table(rows, hAlign="LEFT", repeatRows=1 if header else 0)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B8B8C8")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F5F7FB")),
    ]
    if header:
        style.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(BRAND["blue_dark"])),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        )
    else:
        style.extend([("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold")])
    table.setStyle(TableStyle(style))
    return table


def _summary(analysis: dict[str, Any]) -> str:
    return (
        f"Se analizo el dataset {analysis['filename']} con {analysis['row_count']} filas y "
        f"{analysis['column_count']} columnas. El diagnostico calcula una calidad general de "
        f"{analysis['scores']['overall']}%. Los resultados sirven como base documentada para "
        "tomar decisiones de limpieza sin inventar datos y con trazabilidad metodologica."
    )


def _cleaning_conclusion(after: dict[str, Any]) -> str:
    overall = after["scores"]["overall"]
    if overall >= 95:
        return f"El dataset limpio alcanza una calidad general de {overall}% y queda listo para analisis descriptivo, visualizacion y entrega ejecutiva."
    if overall >= 80:
        return f"El dataset limpio alcanza una calidad general de {overall}%. Puede utilizarse, aunque se recomienda revisar riesgos pendientes antes de decisiones criticas."
    return f"El dataset limpio alcanza una calidad general de {overall}%. El proceso debe continuar antes de declarar el dataset listo para analisis."
