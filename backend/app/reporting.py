"""Report builders for AuditData AI.

PDF report follows the academic Data Cleaning Report standard:
Información General, Resumen Ejecutivo, Indicadores Clave,
Problemas por Dimensión, Outliers, Plan de Acciones,
Evaluación de Calidad, Checklist, Riesgos, Metodología y Conclusión.
"""

from __future__ import annotations

import io
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


BRAND = {
    "blue": "#0066FF",
    "blue_dark": "#0052CC",
    "cyan": "#00D4FF",
    "black": "#0A0A0F",
    "surface": "#12121A",
    "text": "#F0F0F5",
    "muted": "#9090A0",
}


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
            spaceBefore=8,
            spaceAfter=4,
        ),
        "SubSection": ParagraphStyle(
            "SubSection",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=colors.HexColor(BRAND["blue_dark"]),
            leading=14,
            spaceBefore=6,
            spaceAfter=3,
        ),
        "Body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontSize=9,
            leading=13,
            spaceAfter=3,
        ),
        "BodySmall": ParagraphStyle(
            "BodySmall",
            parent=base["BodyText"],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#555555"),
        ),
        "Bullet": ParagraphStyle(
            "Bullet",
            parent=base["BodyText"],
            fontSize=9,
            leading=12,
            leftIndent=12,
            bulletIndent=0,
            spaceBefore=1,
            spaceAfter=1,
        ),
    }


_CELL_STYLE = ParagraphStyle(
    "CellStyle",
    fontName="Helvetica",
    fontSize=8,
    leading=10,
    textColor=colors.HexColor("#333333"),
)

_CELL_STYLE_BOLD = ParagraphStyle(
    "CellStyleBold",
    parent=_CELL_STYLE,
    fontName="Helvetica-Bold",
)

_HEADER_CELL_STYLE = ParagraphStyle(
    "HeaderCellStyle",
    parent=_CELL_STYLE,
    fontName="Helvetica-Bold",
    fontSize=8,
    leading=10,
    textColor=colors.white,
)


def _cell(text: str, bold: bool = False) -> Paragraph:
    """Wrap text in a Paragraph so ReportLab can word-wrap inside table cells."""
    text = str(text).strip()
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    if bold:
        return Paragraph(text, _CELL_STYLE_BOLD)
    return Paragraph(text, _CELL_STYLE)


def _header_cell(text: str) -> Paragraph:
    text = str(text).strip()
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return Paragraph(text, _HEADER_CELL_STYLE)


def _table(rows: list[list[str]], header: bool = False) -> Table:
    """Build a table where all cells are Paragraphs for automatic word-wrapping."""
    wrapped: list[list[Paragraph]] = []
    for row_idx, row in enumerate(rows):
        if header and row_idx == 0:
            wrapped.append([_header_cell(cell) for cell in row])
        else:
            wrapped.append([_cell(cell, bold=(col_idx == 0)) for col_idx, cell in enumerate(row)])

    table = Table(wrapped, hAlign="LEFT", repeatRows=1 if header else 0)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B8B8C8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F5F7FB")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        style.extend([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(BRAND["blue_dark"])),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ])
    table.setStyle(TableStyle(style))
    return table


def build_pdf_report(analysis: dict[str, Any], analyst: str = "-", version: str = "v1.0") -> bytes:
    """Generate an analysis-only PDF report with full methodology sections."""

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
    ]

    _add_informacion_general(story, styles, analysis, analyst, version)
    _add_resumen_ejecutivo(story, styles, analysis)
    _add_indicadores_clave(story, styles, analysis)
    _add_problemas_encontrados(story, styles, analysis)
    _add_outliers_section(story, styles, analysis)
    _add_recomendaciones(story, styles, analysis)
    _add_metodologia(story, styles)

    document.build(story)
    return buffer.getvalue()


def build_cleaning_pdf_report(cleaning: dict[str, Any], analyst: str = "-", version: str = "v1.0") -> bytes:
    """Generate the full Data Cleaning Report with before/after evidence."""

    before = cleaning["before"]
    after = cleaning["after"]
    actions = cleaning.get("actions", [])

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
    ]

    _add_informacion_general_cleaning(story, styles, before, after, actions, analyst, version)
    _add_resumen_ejecutivo_cleaning(story, styles, before, after, actions)
    _add_indicadores_clave_cleaning(story, styles, before, after)
    _add_problemas_encontrados_cleaning(story, styles, before, after)
    _add_outliers_cleaning(story, styles, before)
    _add_plan_acciones(story, styles, actions)
    _add_evaluacion_calidad(story, styles, before, after)
    _add_checklist(story, styles, after, actions)
    _add_riesgos(story, styles, after)
    _add_metodologia(story, styles)
    _add_conclusion(story, styles, before, after)

    document.build(story)
    return buffer.getvalue()


def _add_informacion_general(story, styles, analysis, analyst, version):
    story.append(Paragraph("1. INFORMACION GENERAL", styles["Section"]))
    story.append(_table([
        ["Campo", "Detalle"],
        ["Dataset", analysis["filename"]],
        ["Analista", analyst or "-"],
        ["Version del informe", version or "v1.0"],
        ["Registros", str(analysis["row_count"])],
        ["Columnas", str(analysis["column_count"])],
        ["Fecha de generacion", analysis["generated_at"]],
        ["Herramienta utilizada", "AuditData AI - Motor Python"],
    ], header=True))
    story.append(Spacer(1, 0.3 * cm))


def _add_informacion_general_cleaning(story, styles, before, after, actions, analyst, version):
    story.append(Paragraph("1. INFORMACION GENERAL", styles["Section"]))
    story.append(_table([
        ["Campo", "Detalle"],
        ["Dataset original", before["filename"]],
        ["Dataset limpio", after["filename"]],
        ["Analista", analyst or "-"],
        ["Version del informe", version or "v1.0"],
        ["Registros antes", str(before["row_count"])],
        ["Registros despues", str(after["row_count"])],
        ["Columnas antes", str(before["column_count"])],
        ["Columnas despues", str(after["column_count"])],
        ["Acciones documentadas", str(len(actions))],
        ["Fecha de generacion", after["generated_at"]],
        ["Herramienta utilizada", "AuditData AI - Motor Python"],
    ], header=True))
    story.append(Spacer(1, 0.3 * cm))


def _add_resumen_ejecutivo(story, styles, analysis):
    story.append(Paragraph("2. RESUMEN EJECUTIVO", styles["Section"]))
    scores = analysis["scores"]
    total_issues = (
        sum(c.get("missing", 0) for c in analysis["columns"])
        + sum(c.get("format_issues", 0) for c in analysis["columns"])
        + analysis["duplicate_rows"]
    )
    text = (
        f"Se analizo el dataset '{analysis['filename']}' compuesto por "
        f"{analysis['row_count']} registros y {analysis['column_count']} columnas. "
        f"El diagnostico tecnico identifico un total de {total_issues} problemas: "
        f"{analysis['duplicate_rows']} filas duplicadas, "
        f"{sum(c.get('missing', 0) for c in analysis['columns'])} valores faltantes, "
        f"{sum(c.get('format_issues', 0) for c in analysis['columns'])} inconsistencias de formato, "
        f"y {sum(c.get('outliers', 0) for c in analysis['columns'])} valores atipicos. "
        f"La calidad general calculada es {scores['overall']}%. "
        "Los hallazgos sirven como diagnostico tecnico inicial y deben validarse "
        "con reglas de negocio antes de ejecutar cualquier cambio definitivo."
    )
    story.append(Paragraph(text, styles["Body"]))
    story.append(Spacer(1, 0.3 * cm))


def _add_resumen_ejecutivo_cleaning(story, styles, before, after, actions):
    story.append(Paragraph("2. RESUMEN EJECUTIVO", styles["Section"]))
    total_actions = len(actions)
    improvements = []
    if before["scores"]["completeness"] != after["scores"]["completeness"]:
        improvements.append(f"completitud ({before['scores']['completeness']}% -> {after['scores']['completeness']}%)")
    if before["scores"]["consistency"] != after["scores"]["consistency"]:
        improvements.append(f"consistencia ({before['scores']['consistency']}% -> {after['scores']['consistency']}%)")
    if before["scores"]["accuracy"] != after["scores"]["accuracy"]:
        improvements.append(f"exactitud ({before['scores']['accuracy']}% -> {after['scores']['accuracy']}%)")
    if before["scores"]["uniqueness"] != after["scores"]["uniqueness"]:
        improvements.append(f"unicidad ({before['scores']['uniqueness']}% -> {after['scores']['uniqueness']}%)")

    improvement_text = ", ".join(improvements) if improvements else "sin cambios significativos"

    text = (
        f"Se ejecuto un proceso secuencial de limpieza sobre el dataset '{before['filename']}', "
        f"compuesto por {before['row_count']} registros y {before['column_count']} columnas. "
        f"Se documentaron {total_actions} acciones de limpieza. "
        f"La calidad general paso de {before['scores']['overall']}% a {after['scores']['overall']}%. "
        f"Las dimensiones con mejoras: {improvement_text}. "
        "Cada decision quedo registrada para facilitar auditoria, mantenimiento y reutilizacion."
    )
    story.append(Paragraph(text, styles["Body"]))
    story.append(Spacer(1, 0.3 * cm))


def _add_indicadores_clave(story, styles, analysis):
    story.append(Paragraph("3. INDICADORES CLAVE DEL DATASET", styles["Section"]))
    scores = analysis["scores"]
    story.append(_table([
        ["Indicador", "Resultado"],
        ["Completitud", f"{scores['completeness']}%"],
        ["Consistencia", f"{scores['consistency']}%"],
        ["Exactitud estadistica", f"{scores['accuracy']}%"],
        ["Unicidad", f"{scores['uniqueness']}%"],
        ["Calidad general", f"{scores['overall']}%"],
        ["Filas totales", str(analysis["row_count"])],
        ["Filas duplicadas", str(analysis["duplicate_rows"])],
    ], header=True))
    story.append(Spacer(1, 0.3 * cm))


def _add_indicadores_clave_cleaning(story, styles, before, after):
    story.append(Paragraph("3. INDICADORES CLAVE DEL DATASET", styles["Section"]))
    story.append(Paragraph(
        "Tabla comparativa de indicadores de calidad antes y despues del proceso de limpieza.",
        styles["Body"],
    ))
    story.append(_table([
        ["Indicador", "Antes", "Despues"],
        ["Registros", str(before["row_count"]), str(after["row_count"])],
        ["Columnas", str(before["column_count"]), str(after["column_count"])],
        ["Filas duplicadas", str(before["duplicate_rows"]), str(after["duplicate_rows"])],
        ["Completitud", f"{before['scores']['completeness']}%", f"{after['scores']['completeness']}%"],
        ["Consistencia", f"{before['scores']['consistency']}%", f"{after['scores']['consistency']}%"],
        ["Exactitud", f"{before['scores']['accuracy']}%", f"{after['scores']['accuracy']}%"],
        ["Unicidad", f"{before['scores']['uniqueness']}%", f"{after['scores']['uniqueness']}%"],
        ["Calidad general", f"{before['scores']['overall']}%", f"{after['scores']['overall']}%"],
    ], header=True))
    story.append(Spacer(1, 0.3 * cm))


def _add_problemas_encontrados(story, styles, analysis):
    story.append(Paragraph("4. PROBLEMAS ENCONTRADOS", styles["Section"]))

    # 4.1 Faltantes
    cols_with_missing = [c for c in analysis["columns"] if c.get("missing", 0) > 0]
    story.append(Paragraph("4.1 Valores Faltantes por Columna", styles["SubSection"]))
    if cols_with_missing:
        total_missing = sum(c["missing"] for c in cols_with_missing)
        total_cells = analysis["row_count"] * analysis["column_count"]
        pct = round(total_missing / max(total_cells, 1) * 100, 1)
        story.append(Paragraph(
            f"El dataset presenta {total_missing} celdas vacias ({pct}% del total). "
            "Los valores faltantes afectan la completitud del dataset y deben decidirse: "
            "eliminar, imputar o mantener segun el contexto.",
            styles["Body"],
        ))
        story.append(_table(
            [["Columna", "Faltantes", "% Columna", "Tipo detectado"]]
            + [[
                c["name"],
                str(c["missing"]),
                f"{round(c['missing'] / max(analysis['row_count'], 1) * 100, 1)}%",
                c["detected_type"],
            ] for c in cols_with_missing],
            header=True,
        ))
    else:
        story.append(Paragraph("No se detectaron valores faltantes en el dataset.", styles["Body"]))
    story.append(Spacer(1, 0.2 * cm))

    # 4.2 Duplicados
    story.append(Paragraph("4.2 Filas Duplicadas", styles["SubSection"]))
    dup = analysis["duplicate_rows"]
    if dup > 0:
        dup_pct = round(dup / max(analysis["row_count"], 1) * 100, 1)
        story.append(Paragraph(
            f"Se detectaron {dup} filas duplicadas ({dup_pct}% del total). "
            "Las filas duplicadas afectan la unicidad y pueden sesgar indicadores si no se tratan. "
            "Se recomienda eliminar duplicados solo si cada fila representa una entidad unica.",
            styles["Body"],
        ))
        story.append(_table([
            ["Metrica", "Valor"],
            ["Filas totales", str(analysis["row_count"])],
            ["Filas duplicadas", str(dup)],
            ["Porcentaje duplicado", f"{dup_pct}%"],
        ], header=True))
    else:
        story.append(Paragraph("No se detectaron filas duplicadas en el dataset.", styles["Body"]))
    story.append(Spacer(1, 0.2 * cm))

    # 4.3 Errores de escritura
    cols_with_format = [c for c in analysis["columns"] if c.get("format_issues", 0) > 0]
    story.append(Paragraph("4.3 Errores de Escritura y Variantes de Texto", styles["SubSection"]))
    if cols_with_format:
        total_format = sum(c["format_issues"] for c in cols_with_format)
        story.append(Paragraph(
            f"Se encontraron {total_format} inconsistencias de formato en {len(cols_with_format)} columnas. "
            "Estas variantes fragmentan categorias y dificultan el analisis agregado.",
            styles["Body"],
        ))
        for col in cols_with_format:
            groups = col.get("format_groups", [])
            if groups:
                story.append(Paragraph(f"<b>{col['name']}</b>:", styles["BodySmall"]))
                for g in groups[:5]:
                    variants = g.get("variants", [])
                    story.append(Paragraph(
                        f"  Canonical: '{g.get('canonical', '')}' | Variantes: {', '.join(variants)}",
                        styles["BodySmall"],
                    ))
    else:
        story.append(Paragraph("No se detectaron errores de escritura significativos.", styles["Body"]))
    story.append(Spacer(1, 0.2 * cm))

    # 4.4 Formatos inconsistentes
    story.append(Paragraph("4.4 Formatos Inconsistentes", styles["SubSection"]))
    cols_with_format_issue = [c for c in analysis["columns"] if c.get("format_groups")]
    if cols_with_format_issue:
        story.append(Paragraph(
            f"{len(cols_with_format_issue)} columnas presentan formatos mixtos que deben estandarizarse.",
            styles["Body"],
        ))
    else:
        story.append(Paragraph("No se detectaron formatos inconsistentes.", styles["Body"]))
    story.append(Spacer(1, 0.2 * cm))

    # 4.5 Categorias inconsistentes
    story.append(Paragraph("4.5 Categorias Inconsistentes", styles["SubSection"]))
    if cols_with_format:
        story.append(Paragraph(
            f"{len(cols_with_format)} columnas presentan categorias fragmentadas por variantes de texto. "
            "Se recomienda estandarizar con capitalizacion, mayusculas o minusculas segun el caso.",
            styles["Body"],
        ))
    else:
        story.append(Paragraph("No se detectaron categorias inconsistentes.", styles["Body"]))
    story.append(Spacer(1, 0.2 * cm))

    # 4.6 Valores atipicos
    cols_with_outliers = [c for c in analysis["columns"] if c.get("outliers", 0) > 0]
    story.append(Paragraph("4.6 Valores Atipicos", styles["SubSection"]))
    if cols_with_outliers:
        total_outliers = sum(c["outliers"] for c in cols_with_outliers)
        story.append(Paragraph(
            f"Se detectaron {total_outliers} valores atipicos en {len(cols_with_outliers)} columnas. "
            "Los valores atipicos se calculan con el rango intercuartilico (IQR): "
            "valores menores a Q1 - 1.5*IQR o mayores a Q3 + 1.5*IQR.",
            styles["Body"],
        ))
        story.append(_table(
            [["Columna", "Outliers", "Ejemplos"]]
            + [[
                c["name"],
                str(c["outliers"]),
                ", ".join(str(v) for v in (c.get("outlier_examples") or [])[:5]),
            ] for c in cols_with_outliers],
            header=True,
        ))
    else:
        story.append(Paragraph("No se detectaron valores atipicos.", styles["Body"]))
    story.append(Spacer(1, 0.3 * cm))


def _add_problemas_encontrados_cleaning(story, styles, before, after):
    story.append(Paragraph("4. PROBLEMAS ENCONTRADOS", styles["Section"]))

    # Same analysis as before
    cols_with_missing = [c for c in before["columns"] if c.get("missing", 0) > 0]
    cols_with_format = [c for c in before["columns"] if c.get("format_issues", 0) > 0]
    cols_with_outliers = [c for c in before["columns"] if c.get("outliers", 0) > 0]

    # 4.1 Faltantes
    story.append(Paragraph("4.1 Valores Faltantes por Columna", styles["SubSection"]))
    if cols_with_missing:
        total_missing = sum(c["missing"] for c in cols_with_missing)
        total_cells = before["row_count"] * before["column_count"]
        pct = round(total_missing / max(total_cells, 1) * 100, 1)
        story.append(Paragraph(
            f"El dataset presento {total_missing} celdas vacias ({pct}% del total). "
            "Los valores faltantes afectan la completitud del dataset.",
            styles["Body"],
        ))
        story.append(_table(
            [["Columna", "Faltantes", "% Columna", "Tipo detectado"]]
            + [[
                c["name"],
                str(c["missing"]),
                f"{round(c['missing'] / max(before['row_count'], 1) * 100, 1)}%",
                c["detected_type"],
            ] for c in cols_with_missing],
            header=True,
        ))
    else:
        story.append(Paragraph("No se detectaron valores faltantes.", styles["Body"]))
    story.append(Spacer(1, 0.2 * cm))

    # 4.2 Duplicados
    story.append(Paragraph("4.2 Filas Duplicadas", styles["SubSection"]))
    dup = before["duplicate_rows"]
    if dup > 0:
        dup_pct = round(dup / max(before["row_count"], 1) * 100, 1)
        story.append(Paragraph(
            f"Se detectaron {dup} filas duplicadas ({dup_pct}% del total). "
            "Las filas duplicadas afectan la unicidad y pueden sesgar indicadores.",
            styles["Body"],
        ))
    else:
        story.append(Paragraph("No se detectaron filas duplicadas.", styles["Body"]))
    story.append(Spacer(1, 0.2 * cm))

    # 4.3 Errores de escritura
    story.append(Paragraph("4.3 Errores de Escritura y Variantes de Texto", styles["SubSection"]))
    if cols_with_format:
        total_format = sum(c["format_issues"] for c in cols_with_format)
        story.append(Paragraph(
            f"Se encontraron {total_format} inconsistencias de formato en {len(cols_with_format)} columnas. "
            "Estas variantes fragmentan categorias y dificultan el analisis.",
            styles["Body"],
        ))
        for col in cols_with_format:
            groups = col.get("format_groups", [])
            if groups:
                story.append(Paragraph(f"<b>{col['name']}</b>:", styles["BodySmall"]))
                for g in groups[:5]:
                    variants = g.get("variants", [])
                    story.append(Paragraph(
                        f"  Canonical: '{g.get('canonical', '')}' | Variantes: {', '.join(variants)}",
                        styles["BodySmall"],
                    ))
    else:
        story.append(Paragraph("No se detectaron errores de escritura significativos.", styles["Body"]))
    story.append(Spacer(1, 0.2 * cm))

    # 4.4 Formatos inconsistentes
    story.append(Paragraph("4.4 Formatos Inconsistentes", styles["SubSection"]))
    cols_with_format_groups = [c for c in before["columns"] if c.get("format_groups")]
    if cols_with_format_groups:
        story.append(Paragraph(
            f"{len(cols_with_format_groups)} columnas presentan formatos mixtos que deben estandarizarse.",
            styles["Body"],
        ))
    else:
        story.append(Paragraph("No se detectaron formatos inconsistentes.", styles["Body"]))
    story.append(Spacer(1, 0.2 * cm))

    # 4.5 Categorias inconsistentes
    story.append(Paragraph("4.5 Categorias Inconsistentes", styles["SubSection"]))
    if cols_with_format:
        story.append(Paragraph(
            f"{len(cols_with_format)} columnas presentan categorias fragmentadas por variantes de texto.",
            styles["Body"],
        ))
    else:
        story.append(Paragraph("No se detectaron categorias inconsistentes.", styles["Body"]))
    story.append(Spacer(1, 0.2 * cm))

    # 4.6 Valores atipicos
    story.append(Paragraph("4.6 Valores Atipicos", styles["SubSection"]))
    if cols_with_outliers:
        total_outliers = sum(c["outliers"] for c in cols_with_outliers)
        story.append(Paragraph(
            f"Se detectaron {total_outliers} valores atipicos en {len(cols_with_outliers)} columnas. "
            "Se calculan con el rango intercuartilico (IQR).",
            styles["Body"],
        ))
        story.append(_table(
            [["Columna", "Outliers", "Ejemplos"]]
            + [[
                c["name"],
                str(c["outliers"]),
                ", ".join(str(v) for v in (c.get("outlier_examples") or [])[:5]),
            ] for c in cols_with_outliers],
            header=True,
        ))
    else:
        story.append(Paragraph("No se detectaron valores atipicos.", styles["Body"]))
    story.append(Spacer(1, 0.3 * cm))


def _add_outliers_section(story, styles, analysis):
    story.append(Paragraph("5. VALORES ATIPICOS Y FUERA DE RANGO", styles["Section"]))
    cols_with_outliers = [c for c in analysis["columns"] if c.get("outliers", 0) > 0]
    if cols_with_outliers:
        story.append(Paragraph(
            "La siguiente tabla detalla los valores atipicos detectados por columna. "
            "Los valores se marcan como atipicos si estan fuera del rango "
            "[Q1 - 1.5*IQR, Q3 + 1.5*IQR].",
            styles["Body"],
        ))
        story.append(_table(
            [["Columna", "Outliers", "Min", "Max", "Media", "Mediana", "Ejemplos"]]
            + [[
                c["name"],
                str(c["outliers"]),
                str(c.get("min_value", "-")),
                str(c.get("max_value", "-")),
                str(c.get("mean", "-")),
                str(c.get("median", "-")),
                ", ".join(str(v) for v in (c.get("outlier_examples") or [])[:4]),
            ] for c in cols_with_outliers],
            header=True,
        ))
    else:
        story.append(Paragraph("No se detectaron valores atipicos en el dataset.", styles["Body"]))
    story.append(Spacer(1, 0.3 * cm))


def _add_outliers_cleaning(story, styles, before):
    story.append(Paragraph("5. VALORES ATIPICOS Y FUERA DE RANGO", styles["Section"]))
    cols_with_outliers = [c for c in before["columns"] if c.get("outliers", 0) > 0]
    if cols_with_outliers:
        story.append(Paragraph(
            "Valores atipicos detectados antes del proceso de limpieza:",
            styles["Body"],
        ))
        story.append(_table(
            [["Columna", "Outliers", "Min", "Max", "Media", "Mediana", "Ejemplos"]]
            + [[
                c["name"],
                str(c["outliers"]),
                str(c.get("min_value", "-")),
                str(c.get("max_value", "-")),
                str(c.get("mean", "-")),
                str(c.get("median", "-")),
                ", ".join(str(v) for v in (c.get("outlier_examples") or [])[:4]),
            ] for c in cols_with_outliers],
            header=True,
        ))
    else:
        story.append(Paragraph("No se detectaron valores atipicos.", styles["Body"]))
    story.append(Spacer(1, 0.3 * cm))


def _add_recomendaciones(story, styles, analysis):
    story.append(Paragraph("6. RECOMENDACIONES", styles["Section"]))
    for recommendation in analysis.get("recommendations", []):
        story.append(Paragraph(
            f"<b>{recommendation['priority']}:</b> {recommendation['message']}",
            styles["Body"],
        ))
    story.append(Spacer(1, 0.3 * cm))


def _add_plan_acciones(story, styles, actions):
    story.append(Paragraph("6. PLAN Y ACCIONES DE LIMPIEZA", styles["Section"]))
    if actions:
        story.append(Paragraph(
            f"Se documentaron {len(actions)} acciones de limpieza. "
            "Cada accion incluye la columna afectada, la accion aplicada, "
            "la justificacion tecnica y el resultado obtenido.",
            styles["Body"],
        ))
        story.append(_table(
            [["N.", "Columna", "Accion", "Justificacion", "Resultado"]]
            + [[
                str(i + 1),
                item.get("column", ""),
                item.get("action", ""),
                item.get("reason", ""),
                item.get("result", ""),
            ] for i, item in enumerate(actions)],
            header=True,
        ))
    else:
        story.append(Paragraph(
            "No se aplicaron acciones de limpieza. El dataset se mantiene en su estado original.",
            styles["Body"],
        ))
    story.append(Spacer(1, 0.3 * cm))


def _add_evaluacion_calidad(story, styles, before, after):
    story.append(Paragraph("7. EVALUACION DE CALIDAD - ANTES vs DESPUES", styles["Section"]))
    story.append(Paragraph(
        "Comparacion de indicadores de calidad entre el dataset original y el dataset limpio.",
        styles["Body"],
    ))
    dims = [
        ("Completitud", "completeness"),
        ("Consistencia", "consistency"),
        ("Exactitud", "accuracy"),
        ("Unicidad", "uniqueness"),
    ]
    rows = [["Dimension", "Antes", "Despues", "Cambio"]]
    for label, key in dims:
        b = before["scores"][key]
        a = after["scores"][key]
        diff = round(a - b, 2)
        sign = "+" if diff > 0 else ""
        rows.append([label, f"{b}%", f"{a}%", f"{sign}{diff}%"])
    rows.append([
        "Calidad general",
        f"{before['scores']['overall']}%",
        f"{after['scores']['overall']}%",
        f"{'+' if after['scores']['overall'] - before['scores']['overall'] > 0 else ''}"
        f"{round(after['scores']['overall'] - before['scores']['overall'], 2)}%",
    ])
    story.append(_table(rows, header=True))
    story.append(Spacer(1, 0.3 * cm))


def _add_checklist(story, styles, after, actions):
    story.append(Paragraph("8. CHECKLIST DE VALIDACION FINAL", styles["Section"]))
    checks = [
        ("Completitud >= 95%", after["scores"]["completeness"] >= 95),
        ("Consistencia >= 95%", after["scores"]["consistency"] >= 95),
        ("Exactitud >= 95%", after["scores"]["accuracy"] >= 95),
        ("Sin duplicados pendientes", after["duplicate_rows"] == 0),
        ("Acciones documentadas", len(actions) > 0),
        ("Calidad general >= 90%", after["scores"]["overall"] >= 90),
    ]
    story.append(_table(
        [["Criterio", "Estado"]]
        + [[criterion, "Cumple" if passed else "Requiere revision"] for criterion, passed in checks]
    ))
    story.append(Spacer(1, 0.3 * cm))


def _add_riesgos(story, styles, after):
    story.append(Paragraph("9. RIESGOS IDENTIFICADOS", styles["Section"]))
    risks = []
    if after["scores"]["completeness"] < 95:
        risks.append("Persisten valores faltantes que pueden sesgar indicadores.")
    if after["scores"]["consistency"] < 95:
        risks.append("Persisten inconsistencias de formato que pueden fragmentar categorias.")
    if after["scores"]["accuracy"] < 95:
        risks.append("Persisten outliers que requieren validacion con la fuente original.")
    if after["duplicate_rows"]:
        risks.append("Persisten duplicados que deben evaluarse segun la unidad de analisis.")
    if not risks:
        risks.append("No se identifican riesgos criticos en el diagnostico posterior a la limpieza.")
    for risk in risks:
        story.append(Paragraph(f"- {risk}", styles["Bullet"]))
    story.append(Spacer(1, 0.3 * cm))


def _add_conclusion(story, styles, before, after):
    story.append(Paragraph("10. CONCLUSION FINAL", styles["Section"]))
    overall = after["scores"]["overall"]
    if overall >= 95:
        text = (
            f"El dataset limpio alcanza una calidad general de {overall}%. "
            "Los datos son confiables para analisis descriptivo, toma de decisiones "
            "y entrega a las areas interesadas. Se recomienda mantener la trazabilidad "
            "de decisiones aplicadas."
        )
    elif overall >= 80:
        text = (
            f"El dataset limpio alcanza una calidad general de {overall}%. "
            "Es utilizable para analisis, pero se recomienda revisar los riesgos "
            "pendientes antes de decisiones criticas."
        )
    else:
        text = (
            f"El dataset limpio alcanza una calidad general de {overall}%. "
            "Se recomienda continuar la depuracion antes de declarar el dataset "
            "listo para analisis."
        )
    story.append(Paragraph(text, styles["Body"]))


def _add_metodologia(story, styles):
    story.append(Paragraph("METODOLOGIA DE CALCULO", styles["Section"]))
    story.append(Paragraph(
        "<b>Completitud:</b> Se calcula como 100% - (celdas vacias / total de celdas) * 100. "
        "Una celda se considera vacia si contiene valores como '', 'na', 'n/a', 'null', 'none', 'nan' o '-'.",
        styles["Body"],
    ))
    story.append(Paragraph(
        "<b>Consistencia:</b> Se calcula como 100% - (inconsistencias de formato / total de celdas) * 100. "
        "Se detectan variantes de texto que representan lo mismo pero estan escritas diferente.",
        styles["Body"],
    ))
    story.append(Paragraph(
        "<b>Exactitud:</b> Se calcula como 100% - (valores atipicos / total de celdas) * 100. "
        "Los valores atipicos se detectan con el rango intercuartilico (IQR): "
        "valores fuera de [Q1 - 1.5*IQR, Q3 + 1.5*IQR].",
        styles["Body"],
    ))
    story.append(Paragraph(
        "<b>Unicidad:</b> Se calcula como 100% - (filas duplicadas / total de filas) * 100. "
        "Una fila se considera duplicada si es identica en todas las columnas.",
        styles["Body"],
    ))
    story.append(Paragraph(
        "<b>Calidad general:</b> Promedio aritmetico de las cuatro dimensiones: "
        "completitud, consistencia, exactitud y unicidad.",
        styles["Body"],
    ))
    story.append(Spacer(1, 0.3 * cm))
