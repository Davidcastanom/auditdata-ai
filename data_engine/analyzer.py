"""Core data-quality analysis for AuditData AI.

This module is intentionally independent from the web server and the UI.
That makes the "brain" reusable from a CLI, API, notebook, automation, or
future SaaS backend without rewriting the quality logic.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import statistics
import zipfile
import os
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any

logger = logging.getLogger(__name__)

try:
    import openpyxl
except ImportError:
    openpyxl = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None


MISSING_TOKENS = {"", "na", "n/a", "null", "none", "nan", "-"}


def generate_ai_justification(column: str, action: str, current_reason: str) -> str:
    """Generate a professional justification for a cleaning action using Gemini API."""
    if not genai:
        return current_reason or "Tratamiento aplicado para mejorar la calidad del dataset."
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return current_reason or "Tratamiento aplicado para mejorar la calidad del dataset."

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = (
            f"Actúa como un Auditor Senior de Calidad de Datos.\n"
            f"El analista ha tomado la siguiente decisión:\n"
            f"- Columna afectada: '{column}'\n"
            f"- Acción: '{action}'\n"
            f"- Justificación inicial del analista: '{current_reason}'\n\n"
            f"Redacta una justificación técnica formal y profesional de una sola oración para el informe final de limpieza de datos, justificando por qué es correcto aplicar este tratamiento a nivel metodológico."
        )

        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]
        return text
    except Exception as e:
        logger.warning("Error calling Gemini: %s", e)
        return current_reason or "Tratamiento aplicado para mejorar la calidad del dataset."



@dataclass
class ColumnProfile:
    """Analysis result for one dataset column."""

    name: str
    detected_type: str
    total_rows: int
    missing: int
    unique_values: int
    examples: list[str] = field(default_factory=list)
    format_issues: int = 0
    format_groups: list[dict[str, Any]] = field(default_factory=list)
    outliers: int = 0
    outlier_examples: list[Any] = field(default_factory=list)
    min_value: float | None = None
    max_value: float | None = None
    mean: float | None = None
    median: float | None = None


def load_dataset(filename: str, payload: bytes) -> tuple[list[str], list[dict[str, Any]]]:
    """Load CSV or XLSX bytes into headers and row dictionaries.

    The function keeps parsing rules explicit so every dataset ingestion step
    can be documented later in the generated report.
    """

    lowered = filename.lower()
    if lowered.endswith(".csv"):
        return _load_csv(payload)
    if lowered.endswith((".xlsx", ".xlsm")):
        return _load_xlsx(payload)
    raise ValueError("Formato no soportado. Usa CSV o XLSX.")


def analyze_dataset(filename: str, payload: bytes) -> dict[str, Any]:
    """Run the complete reusable quality diagnosis for a dataset."""

    headers, rows = load_dataset(filename, payload)
    duplicate_rows = _count_duplicate_rows(headers, rows)
    columns = [_profile_column(header, rows) for header in headers]
    scores = _quality_scores(columns, duplicate_rows, len(rows), max(len(headers), 1))

    return {
        "filename": filename,
        "generated_at": datetime.now(timezone(timedelta(hours=-5))).isoformat(timespec="seconds"),
        "row_count": len(rows),
        "column_count": len(headers),
        "headers": headers,
        "duplicate_rows": duplicate_rows,
        "scores": scores,
        "columns": [profile.__dict__ for profile in columns],
        "recommendations": _recommendations(columns, duplicate_rows),
        "preview": rows[:10],
    }


def apply_cleaning_actions(filename: str, payload: bytes, actions: list[dict[str, Any]]) -> dict[str, Any]:
    """Apply documented cleaning actions and return before/after evidence.

    Every action creates a log entry. This follows the professional rule from
    the source lessons: cleaning is not complete until the decision is traceable.
    Now also tracks cell-level changes for the audit log.
    """

    headers, rows = load_dataset(filename, payload)
    before = analyze_dataset(filename, payload)
    log: list[dict[str, str]] = []
    changelog: list[dict[str, Any]] = []

    for action in actions:
        kind = action.get("kind")
        column = action.get("column", "")
        reason = action.get("reason", "").strip() or "Decision registrada sin detalle adicional."

        # Generate professional justification using Gemini if key is provided
        ai_reason = generate_ai_justification(column or "Dataset", kind, reason)

        if kind == "delete_column" and column in headers:
            changelog.append({
                "action": "Eliminar columna",
                "column": column,
                "reason": ai_reason,
                "changes": [{"row": "TODAS", "column": column, "old": "(valor presente)", "new": "(columna eliminada)"}],
            })
            headers.remove(column)
            for row in rows:
                row.pop(column, None)
            log.append(_log_entry(column, "Eliminar columna", ai_reason, "Columna eliminada del dataset limpio."))

        elif kind == "drop_missing_rows" and column in headers:
            before_count = len(rows)
            dropped_rows = []
            kept_rows = []
            for row in rows:
                if _normalize_missing(row.get(column, "")) == "":
                    dropped_rows.append(dict(row))
                else:
                    kept_rows.append(row)
            rows = kept_rows
            for dr in dropped_rows:
                row_id = dr.get("id", dr.get("ID", dr.get(headers[0], "?")))
                changelog.append({
                    "action": "Eliminar fila",
                    "column": column,
                    "reason": ai_reason,
                    "changes": [{"row": str(row_id), "column": column, "old": "(vacio)", "new": "(fila eliminada)"}],
                })
            log.append(_log_entry(column, "Eliminar filas con faltantes", ai_reason, f"{before_count - len(rows)} filas eliminadas."))

        elif kind == "impute_missing" and column in headers:
            method = action.get("method", "mode")
            value = _imputation_value(rows, column, method, action.get("value"))
            changed = 0
            for row in rows:
                if _normalize_missing(row.get(column, "")) == "":
                    old_val = row.get(column, "")
                    row_id = row.get("id", row.get("ID", row.get(headers[0], "?")))
                    changelog.append({
                        "action": f"Imputar con {method}",
                        "column": column,
                        "reason": ai_reason,
                        "changes": [{"row": str(row_id), "column": column, "old": str(old_val) or "(vacio)", "new": str(value)}],
                    })
                    row[column] = value
                    changed += 1
            log.append(_log_entry(column, f"Imputar faltantes con {method}", ai_reason, f"{changed} valores reemplazados."))

        elif kind == "standardize_text" and column in headers:
            mode = action.get("method", "title")
            changed = 0
            for row in rows:
                original = str(row.get(column, ""))
                updated = _standardize_text(original, mode)
                if original != updated:
                    row_id = row.get("id", row.get("ID", row.get(headers[0], "?")))
                    changelog.append({
                        "action": f"Estandarizar ({mode})",
                        "column": column,
                        "reason": ai_reason,
                        "changes": [{"row": str(row_id), "column": column, "old": original, "new": updated}],
                    })
                    row[column] = updated
                    changed += 1
            log.append(_log_entry(column, f"Estandarizar texto ({mode})", ai_reason, f"{changed} celdas normalizadas."))

        elif kind == "remove_duplicate_rows":
            before_count = len(rows)
            seen: set[tuple[str, ...]] = set()
            clean_rows = []
            for row in rows:
                key = tuple(str(row.get(h, "")).strip() for h in headers)
                if key not in seen:
                    seen.add(key)
                    clean_rows.append(row)
                else:
                    row_id = row.get("id", row.get("ID", row.get(headers[0], "?")))
                    changelog.append({
                        "action": "Eliminar duplicado",
                        "column": "Dataset",
                        "reason": ai_reason,
                        "changes": [{"row": str(row_id), "column": "*", "old": "(fila duplicada)", "new": "(fila eliminada)"}],
                    })
            rows = clean_rows
            log.append(_log_entry("Dataset", "Eliminar filas duplicadas", ai_reason, f"{before_count - len(rows)} filas duplicadas eliminadas."))

        elif kind == "flag_outliers" and column in headers:
            log.append(_log_entry(column, "Marcar outliers para revision", ai_reason, "Sin cambios destructivos en el dataset."))

        elif kind == "rename_column" and column in headers:
            new_name = action.get("value", "").strip()
            if new_name and new_name not in headers:
                idx = headers.index(column)
                headers[idx] = new_name
                for row in rows:
                    if column in row:
                        row[new_name] = row.pop(column)
                changelog.append({
                    "action": f"Renombrar a '{new_name}'",
                    "column": column,
                    "reason": ai_reason,
                    "changes": [{"row": "TODAS", "column": column, "old": column, "new": new_name}],
                })
                log.append(_log_entry(column, f"Renombrar a '{new_name}'", ai_reason, f"Columna renombrada a '{new_name}'."))

        elif kind == "replace_value" and column in headers:
            target_val = action.get("method", "")
            repl_val = action.get("value", "")
            changed = 0
            for row in rows:
                if str(row.get(column, "")) == target_val:
                    row_id = row.get("id", row.get("ID", row.get(headers[0], "?")))
                    changelog.append({
                        "action": f"Reemplazar '{target_val}' -> '{repl_val}'",
                        "column": column,
                        "reason": ai_reason,
                        "changes": [{"row": str(row_id), "column": column, "old": target_val, "new": repl_val}],
                    })
                    row[column] = repl_val
                    changed += 1
            log.append(_log_entry(column, f"Reemplazar '{target_val}' con '{repl_val}'", ai_reason, f"{changed} valores reemplazados."))

        elif kind == "change_type" and column in headers:
            target_type = action.get("value", "text")
            changed = 0
            for row in rows:
                val = row.get(column, "")
                if target_type == "number":
                    casted = _to_float(val)
                    if casted is not None:
                        row_id = row.get("id", row.get("ID", row.get(headers[0], "?")))
                        changelog.append({
                            "action": f"Tipo: {target_type}",
                            "column": column,
                            "reason": ai_reason,
                            "changes": [{"row": str(row_id), "column": column, "old": str(val), "new": str(casted)}],
                        })
                        row[column] = casted
                        changed += 1
                elif target_type == "text":
                    row_id = row.get("id", row.get("ID", row.get(headers[0], "?")))
                    changelog.append({
                        "action": f"Tipo: {target_type}",
                        "column": column,
                        "reason": ai_reason,
                        "changes": [{"row": str(row_id), "column": column, "old": str(val), "new": str(val)}],
                    })
                    row[column] = str(val)
                    changed += 1
                elif target_type == "boolean":
                    lower_val = str(val).strip().lower()
                    new_val = "si" if lower_val in {"si", "sí", "true", "1"} else "no"
                    row_id = row.get("id", row.get("ID", row.get(headers[0], "?")))
                    changelog.append({
                        "action": f"Tipo: {target_type}",
                        "column": column,
                        "reason": ai_reason,
                        "changes": [{"row": str(row_id), "column": column, "old": str(val), "new": new_val}],
                    })
                    row[column] = new_val
                    changed += 1
            log.append(_log_entry(column, f"Cambiar tipo de dato a {target_type}", ai_reason, f"{changed} valores convertidos."))

    clean_csv = rows_to_csv(headers, rows)
    after = analyze_dataset(_clean_filename(filename), clean_csv.encode("utf-8"))
    return {"before": before, "after": after, "actions": log, "clean_csv": clean_csv, "changelog": changelog}



def build_markdown_report(analysis: dict[str, Any], analyst: str = "-", version: str = "v1.0") -> str:
    """Create a professional Markdown report from an analysis object."""

    scores = analysis["scores"]
    lines = [
        f"# Data Cleaning Report - {analysis['filename']}",
        "",
        "## Informacion general",
        f"- Dataset: {analysis['filename']}",
        f"- Analista: {analyst or '-'}",
        f"- Version del informe: {version or 'v1.0'}",
        f"- Fecha tecnica: {analysis['generated_at']}",
        f"- Filas: {analysis['row_count']}",
        f"- Columnas: {analysis['column_count']}",
        "",
        "## Resumen ejecutivo",
        _executive_summary(analysis),
        "",
        "## Indicadores clave",
        "| Indicador | Resultado |",
        "|---|---:|",
        f"| Completitud | {scores['completeness']}% |",
        f"| Consistencia | {scores['consistency']}% |",
        f"| Exactitud estadistica | {scores['accuracy']}% |",
        f"| Unicidad | {scores['uniqueness']}% |",
        f"| Calidad general | {scores['overall']}% |",
        f"| Filas duplicadas | {analysis['duplicate_rows']} |",
        "",
        "## Problemas encontrados",
        "| Columna | Tipo | Faltantes | Inconsistencias | Outliers |",
        "|---|---|---:|---:|---:|",
    ]

    for column in analysis["columns"]:
        lines.append(
            f"| {column['name']} | {column['detected_type']} | {column['missing']} | "
            f"{column['format_issues']} | {column['outliers']} |"
        )

    lines.extend(["", "## Recomendaciones"])
    for item in analysis["recommendations"]:
        lines.append(f"- **{item['priority']}** - {item['message']}")

    lines.extend(
        [
            "",
            "## Criterio metodologico",
            "La herramienta no inventa datos. Los hallazgos se calculan sobre el dataset recibido y las acciones de limpieza deben validarse con criterio de negocio antes de reemplazar, eliminar o imputar valores.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_cleaning_markdown_report(cleaning: dict[str, Any], analyst: str = "-", version: str = "v1.0", row_meaning: str = "", analysis_objective: str = "") -> str:
    """Create a comprehensive before/after report matching the academic Data Cleaning Report standard."""

    before = cleaning["before"]
    after = cleaning["after"]
    actions = cleaning.get("actions", [])

    context_lines = []
    if row_meaning:
        context_lines.append(f"- Que representa cada fila: {row_meaning}")
    if analysis_objective:
        context_lines.append(f"- Objetivo del analisis: {analysis_objective}")

    lines = [
        f"# Data Cleaning Report - {before['filename']}",
        "",
        "## 1. Informacion General",
        f"- Dataset original: {before['filename']}",
        f"- Dataset limpio: {after['filename']}",
        f"- Analista: {analyst or '-'}",
        f"- Version del informe: {version or 'v1.0'}",
    ] + context_lines + [
        f"- Registros antes: {before['row_count']}",
        f"- Registros despues: {after['row_count']}",
        f"- Columnas antes: {before['column_count']}",
        f"- Columnas despues: {after['column_count']}",
        f"- Acciones documentadas: {len(actions)}",
        f"- Fecha de generacion: {after['generated_at']}",
        "- Herramienta utilizada: AuditData AI - Motor Python",
        "",
        "## 2. Resumen Ejecutivo",
        _cleaning_resumen(before, after, actions),
        "",
        "## 3. Indicadores Clave del Dataset",
        "| Indicador | Antes | Despues |",
        "|---|---:|---:|",
        f"| Registros | {before['row_count']} | {after['row_count']} |",
        f"| Columnas | {before['column_count']} | {after['column_count']} |",
        f"| Filas duplicadas | {before['duplicate_rows']} | {after['duplicate_rows']} |",
        f"| Completitud | {before['scores']['completeness']}% | {after['scores']['completeness']}% |",
        f"| Consistencia | {before['scores']['consistency']}% | {after['scores']['consistency']}% |",
        f"| Exactitud | {before['scores']['accuracy']}% | {after['scores']['accuracy']}% |",
        f"| Unicidad | {before['scores']['uniqueness']}% | {after['scores']['uniqueness']}% |",
        f"| Calidad general | {before['scores']['overall']}% | {after['scores']['overall']}% |",
        "",
        "## 4. Problemas Encontrados",
    ]

    missing_before = [c for c in before["columns"] if c.get("missing", 0) > 0]
    format_before = [c for c in before["columns"] if c.get("format_issues", 0) > 0]
    outliers_before = [c for c in before["columns"] if c.get("outliers", 0) > 0]

    lines.append("")
    lines.append("### 4.1 Valores Faltantes por Columna")
    if missing_before:
        total_missing = sum(c["missing"] for c in missing_before)
        lines.append(f"El dataset presento {total_missing} celdas vacias:")
        lines.append("| Columna | Faltantes | % Columna | Tipo detectado |")
        lines.append("|---|---:|---:|---|")
        for c in missing_before:
            pct = round(c["missing"] / max(before["row_count"], 1) * 100, 1)
            lines.append(f"| {c['name']} | {c['missing']} | {pct}% | {c['detected_type']} |")
    else:
        lines.append("No se detectaron valores faltantes.")

    lines.append("")
    lines.append("### 4.2 Filas Duplicadas")
    if before["duplicate_rows"] > 0:
        dup_pct = round(before["duplicate_rows"] / max(before["row_count"], 1) * 100, 1)
        lines.append(f"Se detectaron {before['duplicate_rows']} filas duplicadas ({dup_pct}% del total).")
    else:
        lines.append("No se detectaron filas duplicadas.")

    lines.append("")
    lines.append("### 4.3 Errores de Escritura y Variantes de Texto")
    if format_before:
        total_format = sum(c["format_issues"] for c in format_before)
        lines.append(f"Se encontraron {total_format} inconsistencias de formato en {len(format_before)} columnas.")
        for col in format_before:
            groups = col.get("format_groups", [])
            if groups:
                lines.append(f"**{col['name']}:**")
                for g in groups[:5]:
                    variants = g.get("variants", [])
                    lines.append(f"  - Canonical: '{g.get('canonical', '')}' | Variantes: {', '.join(variants)}")
    else:
        lines.append("No se detectaron errores de escritura significativos.")

    lines.append("")
    lines.append("### 4.4 Formatos Inconsistentes")
    cols_with_groups = [c for c in before["columns"] if c.get("format_groups")]
    if cols_with_groups:
        lines.append(f"{len(cols_with_groups)} columnas presentan formatos mixtos.")
    else:
        lines.append("No se detectaron formatos inconsistentes.")

    lines.append("")
    lines.append("### 4.5 Categorias Inconsistentes")
    if format_before:
        lines.append(f"{len(format_before)} columnas presentan categorias fragmentadas.")
    else:
        lines.append("No se detectaron categorias inconsistentes.")

    lines.append("")
    lines.append("### 4.6 Valores Atipicos")
    if outliers_before:
        total_outliers = sum(c["outliers"] for c in outliers_before)
        lines.append(f"Se detectaron {total_outliers} valores atipicos en {len(outliers_before)} columnas.")
        lines.append("| Columna | Outliers | Ejemplos |")
        lines.append("|---|---:|---|")
        for c in outliers_before:
            examples = ", ".join(str(v) for v in (c.get("outlier_examples") or [])[:5])
            lines.append(f"| {c['name']} | {c['outliers']} | {examples} |")
    else:
        lines.append("No se detectaron valores atipicos.")

    lines.extend(["", "## 5. Valores Atipicos y Fuera de Rango"])
    if outliers_before:
        lines.append("| Columna | Outliers | Min | Max | Media | Mediana |")
        lines.append("|---|---:|---|---|---|---|")
        for c in outliers_before:
            lines.append(f"| {c['name']} | {c['outliers']} | {c.get('min_value', '-')} | {c.get('max_value', '-')} | {c.get('mean', '-')} | {c.get('median', '-')} |")
    else:
        lines.append("No se detectaron valores atipicos.")

    lines.extend(["", "## 6. Plan y Acciones de Limpieza"])
    if actions:
        lines.append(f"Se documentaron {len(actions)} acciones de limpieza.")
        lines.append("| N. | Columna | Accion | Justificacion | Resultado |")
        lines.append("|---|---|---|---|---|")
        for i, item in enumerate(actions):
            lines.append(f"| {i+1} | {item.get('column', '')} | {item.get('action', '')} | {item.get('reason', '')} | {item.get('result', '')} |")
    else:
        lines.append("No se aplicaron acciones de limpieza.")

    lines.extend(["", "## 7. Evaluacion de Calidad - Antes vs Despues"])
    dims = [("Completitud", "completeness"), ("Consistencia", "consistency"), ("Exactitud", "accuracy"), ("Unicidad", "uniqueness")]
    lines.append("| Dimension | Antes | Despues | Cambio |")
    lines.append("|---|---|---|---|")
    for label, key in dims:
        diff = round(after["scores"][key] - before["scores"][key], 2)
        sign = "+" if diff > 0 else ""
        lines.append(f"| {label} | {before['scores'][key]}% | {after['scores'][key]}% | {sign}{diff}% |")
    overall_diff = round(after["scores"]["overall"] - before["scores"]["overall"], 2)
    overall_sign = "+" if overall_diff > 0 else ""
    lines.append(f"| Calidad general | {before['scores']['overall']}% | {after['scores']['overall']}% | {overall_sign}{overall_diff}% |")

    lines.extend(["", "## 8. Checklist de Validacion Final"])
    checks = [
        ("Completitud >= 95%", after["scores"]["completeness"] >= 95),
        ("Consistencia >= 95%", after["scores"]["consistency"] >= 95),
        ("Exactitud >= 95%", after["scores"]["accuracy"] >= 95),
        ("Sin duplicados pendientes", after["duplicate_rows"] == 0),
        ("Acciones documentadas", len(actions) > 0),
        ("Calidad general >= 90%", after["scores"]["overall"] >= 90),
    ]
    lines.append("| Criterio | Estado |")
    lines.append("|---|---|")
    for criterion, passed in checks:
        lines.append(f"| {criterion} | {'Cumple' if passed else 'Requiere revision'} |")

    lines.extend(["", "## 9. Riesgos Identificados"])
    risks = _risk_list(after)
    for risk in risks:
        lines.append(f"- {risk}")

    lines.extend(["", "## 10. Metodologia de Calculo"])
    lines.append("**Completitud:** 100% - (celdas vacias / total de celdas) * 100.")
    lines.append("**Consistencia:** 100% - (inconsistencias de formato / total de celdas) * 100.")
    lines.append("**Exactitud:** 100% - (valores atipicos / total de celdas) * 100. Calculados con IQR.")
    lines.append("**Unicidad:** 100% - (filas duplicadas / total de filas) * 100.")
    lines.append("**Calidad general:** Promedio aritmetico de las cuatro dimensiones.")

    lines.extend(["", "## 11. Conclusion Final"])
    lines.append(_conclusion(after))

    return "\n".join(lines) + "\n"


def rows_to_csv(headers: list[str], rows: list[dict[str, Any]]) -> str:
    """Serialize current dataset rows into CSV for download or re-analysis."""

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({header: row.get(header, "") for header in headers})
    return output.getvalue()


def analysis_to_json(analysis: dict[str, Any]) -> str:
    """Stable JSON serialization for API responses and future automation."""

    return json.dumps(analysis, ensure_ascii=False, indent=2)


def _load_csv(payload: bytes) -> tuple[list[str], list[dict[str, Any]]]:
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = payload.decode("latin-1")
    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    rows = [{header: row.get(header, "") for header in headers} for row in reader]
    return headers, rows


def _load_xlsx(payload: bytes) -> tuple[list[str], list[dict[str, Any]]]:
    if openpyxl is None:
        raise ValueError("openpyxl no esta disponible para leer XLSX.")
    if not zipfile.is_zipfile(io.BytesIO(payload)):
        raise ValueError("El archivo XLSX no parece valido.")

    workbook = openpyxl.load_workbook(io.BytesIO(payload), read_only=True, data_only=True)
    sheet = workbook[workbook.sheetnames[0]]
    raw_rows = list(sheet.iter_rows(values_only=True))
    if not raw_rows:
        return [], []

    headers = [str(value).strip() if value is not None else f"columna_{i+1}" for i, value in enumerate(raw_rows[0])]
    rows = []
    for raw in raw_rows[1:]:
        row = {}
        for index, header in enumerate(headers):
            row[header] = raw[index] if index < len(raw) and raw[index] is not None else ""
        rows.append(row)
    return headers, rows


def _profile_column(header: str, rows: list[dict[str, Any]]) -> ColumnProfile:
    values = [row.get(header, "") for row in rows]
    normalized = [_normalize_missing(value) for value in values]
    present = [value for value in normalized if value != ""]
    detected_type = _detect_type(present)
    unique_values = len(set(map(str, present)))
    profile = ColumnProfile(
        name=header,
        detected_type=detected_type,
        total_rows=len(rows),
        missing=len(values) - len(present),
        unique_values=unique_values,
        examples=list(dict.fromkeys(map(str, present)))[:8],
    )

    if detected_type == "number":
        numeric_values = [_to_float(value) for value in present]
        numeric_values = [value for value in numeric_values if value is not None]
        _add_numeric_stats(profile, numeric_values)
    else:
        _add_format_groups(profile, present)

    return profile


def _normalize_missing(value: Any) -> str:
    text = str(value).strip() if value is not None else ""
    return "" if text.lower() in MISSING_TOKENS else text


def _detect_type(values: list[str]) -> str:
    if not values:
        return "text"
    numbers = sum(_to_float(value) is not None for value in values)
    booleans = sum(str(value).strip().lower() in {"si", "sí", "no", "true", "false", "0", "1"} for value in values)
    dates = sum(_looks_like_date(str(value)) for value in values)

    total = len(values)
    if numbers / total >= 0.75:
        return "number"
    if dates / total >= 0.75:
        return "date"
    if booleans / total >= 0.75:
        return "boolean"
    return "text"


def _to_float(value: Any) -> float | None:
    try:
        return float(str(value).replace(",", ".").strip())
    except ValueError:
        return None


def _looks_like_date(value: str) -> bool:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            datetime.strptime(value.strip(), fmt)
            return True
        except ValueError:
            continue
    return False


def _add_numeric_stats(profile: ColumnProfile, values: list[float]) -> None:
    if not values:
        return
    profile.min_value = round(min(values), 4)
    profile.max_value = round(max(values), 4)
    profile.mean = round(statistics.fmean(values), 4)
    profile.median = round(statistics.median(values), 4)

    if len(values) < 4:
        return
    sorted_values = sorted(values)
    q1 = statistics.median(sorted_values[: len(sorted_values) // 2])
    q3 = statistics.median(sorted_values[(len(sorted_values) + 1) // 2 :])
    iqr = q3 - q1
    if iqr == 0:
        return
    low = q1 - 1.5 * iqr
    high = q3 + 1.5 * iqr
    outliers = [value for value in values if value < low or value > high]
    profile.outliers = len(outliers)
    profile.outlier_examples = outliers[:8]


def _add_format_groups(profile: ColumnProfile, values: list[str]) -> None:
    groups: dict[str, set[str]] = {}
    for value in values:
        key = " ".join(str(value).strip().lower().split())
        groups.setdefault(key, set()).add(str(value))

    for variants in groups.values():
        if len(variants) > 1:
            sorted_variants = sorted(variants)
            profile.format_groups.append({"canonical": sorted_variants[0], "variants": sorted_variants})
            profile.format_issues += len(variants)


def _count_duplicate_rows(headers: list[str], rows: list[dict[str, Any]]) -> int:
    seen: set[tuple[str, ...]] = set()
    duplicates = 0
    for row in rows:
        key = tuple(str(row.get(header, "")).strip() for header in headers)
        if key in seen:
            duplicates += 1
        else:
            seen.add(key)
    return duplicates


def _quality_scores(columns: list[ColumnProfile], duplicate_rows: int, row_count: int, column_count: int) -> dict[str, float]:
    total_cells = max(row_count * column_count, 1)
    missing = sum(column.missing for column in columns)
    format_issues = sum(column.format_issues for column in columns)
    outliers = sum(column.outliers for column in columns)

    completeness = _score_from_ratio(missing, total_cells)
    consistency = _score_from_ratio(format_issues, total_cells)
    accuracy = _score_from_ratio(outliers, total_cells)
    uniqueness = _score_from_ratio(duplicate_rows, max(row_count, 1))
    overall = round(statistics.fmean([completeness, consistency, accuracy, uniqueness]), 2)

    return {
        "completeness": completeness,
        "consistency": consistency,
        "accuracy": accuracy,
        "uniqueness": uniqueness,
        "overall": overall,
    }


def _score_from_ratio(problem_count: int, total: int) -> float:
    return round(max(0, 100 - (problem_count / max(total, 1) * 100)), 2)


def _recommendations(columns: list[ColumnProfile], duplicate_rows: int) -> list[dict[str, str]]:
    recommendations: list[dict[str, str]] = []
    for column in columns:
        if column.missing:
            recommendations.append(
                {
                    "priority": "Alta",
                    "message": f"Validar {column.missing} valores faltantes en '{column.name}' antes de tomar decisiones.",
                }
            )
        if column.format_issues:
            recommendations.append(
                {
                    "priority": "Media",
                    "message": f"Estandarizar variantes de escritura en '{column.name}' para evitar categorias fragmentadas.",
                }
            )
        if column.outliers:
            recommendations.append(
                {
                    "priority": "Media",
                    "message": f"Revisar {column.outliers} valores atipicos en '{column.name}' con la fuente original.",
                }
            )
    if duplicate_rows:
        recommendations.append(
            {
                "priority": "Alta",
                "message": f"Evaluar {duplicate_rows} filas duplicadas; eliminarlas solo si no representan eventos reales.",
            }
        )
    if not recommendations:
        recommendations.append({"priority": "Baja", "message": "No se detectaron problemas criticos en el diagnostico automatico."})
    return recommendations


def _log_entry(column: str, action: str, reason: str, result: str) -> dict[str, str]:
    return {
        "timestamp": datetime.now(timezone(timedelta(hours=-5))).isoformat(timespec="seconds"),
        "column": column,
        "action": action,
        "reason": reason,
        "result": result,
    }


def _imputation_value(rows: list[dict[str, Any]], column: str, method: str, custom_value: Any = None) -> Any:
    present = [_normalize_missing(row.get(column, "")) for row in rows]
    present = [value for value in present if value != ""]
    if method == "custom":
        return "" if custom_value is None else custom_value
    if not present:
        return ""
    numeric = [_to_float(value) for value in present]
    numeric = [value for value in numeric if value is not None]
    if method == "mean" and numeric:
        return round(statistics.fmean(numeric), 4)
    if method == "median" and numeric:
        return round(statistics.median(numeric), 4)
    counts = Counter(map(str, present))
    return counts.most_common(1)[0][0]


def _standardize_text(value: str, mode: str) -> str:
    normalized = " ".join(str(value).strip().split())
    if mode == "upper":
        return normalized.upper()
    if mode == "lower":
        return normalized.lower()
    return normalized.title()


def _dedupe_rows(headers: list[str], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, ...]] = set()
    clean_rows = []
    for row in rows:
        key = tuple(str(row.get(header, "")).strip() for header in headers)
        if key not in seen:
            seen.add(key)
            clean_rows.append(row)
    return clean_rows


def _clean_filename(filename: str) -> str:
    if "." in filename:
        stem, ext = filename.rsplit(".", 1)
        return f"{stem}_limpio.{ext}"
    return f"{filename}_limpio.csv"


def _risk_summary(analysis: dict[str, Any]) -> str:
    risks = []
    if analysis["scores"]["completeness"] < 95:
        risks.append("persisten valores faltantes que pueden sesgar indicadores.")
    if analysis["scores"]["consistency"] < 95:
        risks.append("persisten inconsistencias de formato que pueden fragmentar categorias.")
    if analysis["scores"]["accuracy"] < 95:
        risks.append("persisten outliers que requieren validacion con la fuente original.")
    if analysis["duplicate_rows"]:
        risks.append("persisten duplicados que deben evaluarse segun la unidad de analisis.")
    if not risks:
        return "No se identifican riesgos criticos en el diagnostico automatico posterior a la limpieza."
    return "Riesgos pendientes: " + " ".join(risks)


def _conclusion(analysis: dict[str, Any]) -> str:
    overall = analysis["scores"]["overall"]
    if overall >= 95:
        return f"El dataset alcanza una calidad general de {overall}% y esta listo para analisis descriptivo, manteniendo la documentacion de decisiones aplicada."
    if overall >= 80:
        return f"El dataset alcanza una calidad general de {overall}%. Es utilizable, pero conviene revisar los riesgos pendientes antes de decisiones finales."
    return f"El dataset alcanza una calidad general de {overall}%. Se recomienda continuar la depuracion antes de usarlo para toma de decisiones."


def _executive_summary(analysis: dict[str, Any]) -> str:
    scores = analysis["scores"]
    return (
        f"Se analizo el dataset '{analysis['filename']}' con {analysis['row_count']} filas y "
        f"{analysis['column_count']} columnas. La calidad general calculada fue de "
        f"{scores['overall']}%, considerando completitud, consistencia, exactitud estadistica "
        "y unicidad. Los hallazgos deben interpretarse como diagnostico tecnico inicial y "
        "validarse con reglas de negocio antes de ejecutar cambios definitivos."
    )


def _cleaning_resumen(before: dict[str, Any], after: dict[str, Any], actions: list[dict[str, Any]]) -> str:
    total_actions = len(actions)
    improvements = []
    dims = [("completitud", "completeness"), ("consistencia", "consistency"), ("exactitud", "accuracy"), ("unicidad", "uniqueness")]
    for label, key in dims:
        b = before["scores"][key]
        a = after["scores"][key]
        if b != a:
            diff = round(a - b, 2)
            sign = "+" if diff > 0 else ""
            improvements.append(f"{label} ({b}% -> {a}%, {sign}{diff}%)")
    improvement_text = ", ".join(improvements) if improvements else "sin cambios significativos"
    return (
        f"Se ejecuto un proceso secuencial de limpieza sobre el dataset '{before['filename']}', "
        f"compuesto por {before['row_count']} registros y {before['column_count']} columnas. "
        f"Se documentaron {total_actions} acciones de limpieza. "
        f"La calidad general paso de {before['scores']['overall']}% a {after['scores']['overall']}%. "
        f"Las dimensiones con mejoras: {improvement_text}. "
        "Cada decision quedo registrada para facilitar auditoria, mantenimiento y reutilizacion."
    )


def _risk_list(analysis: dict[str, Any]) -> list[str]:
    risks = []
    if analysis["scores"]["completeness"] < 95:
        risks.append("Persisten valores faltantes que pueden sesgar indicadores.")
    if analysis["scores"]["consistency"] < 95:
        risks.append("Persisten inconsistencias de formato que pueden fragmentar categorias.")
    if analysis["scores"]["accuracy"] < 95:
        risks.append("Persisten outliers que requieren validacion con la fuente original.")
    if analysis["duplicate_rows"]:
        risks.append("Persisten duplicados que deben evaluarse segun la unidad de analisis.")
    if not risks:
        risks.append("No se identifican riesgos criticos en el diagnostico posterior a la limpieza.")
    return risks


def generate_audit_log(changelog: list[dict[str, Any]], filename: str = "dataset") -> str:
    """Generate a Markdown changelog documenting every cell-level change made during cleaning.

    Returns a structured document suitable for auditing, regulatory compliance,
    or reproducibility purposes.
    """
    lines: list[str] = []
    lines.append(f"# Bitácora de Cambios - {filename}")
    lines.append("")
    lines.append("Documento de auditoría que registra cada modificación realizada sobre el dataset durante el proceso de limpieza.")
    lines.append("")
    lines.append(f"**Total de acciones registradas:** {len(changelog)}")
    lines.append("")

    if not changelog:
        lines.append("_No se realizaron cambios en el dataset._")
        lines.append("")
        return "\n".join(lines)

    lines.append("---")
    lines.append("")

    for idx, entry in enumerate(changelog, 1):
        action = entry.get("action", "Acción desconocida")
        column = entry.get("column", "?")
        reason = entry.get("reason", "Sin justificación registrada.")
        changes = entry.get("changes", [])

        lines.append(f"## {idx}. {action}")
        lines.append("")
        lines.append(f"- **Columna afectada:** {column}")
        lines.append(f"- **Justificación:** {reason}")
        lines.append(f"- **Filas modificadas:** {len(changes)}")
        lines.append("")

        if changes:
            lines.append("| Fila | Columna | Valor anterior | Valor nuevo |")
            lines.append("|------|---------|---------------|-------------|")
            for ch in changes:
                row_id = str(ch.get("row", "?"))
                col = str(ch.get("column", "?"))
                old_val = str(ch.get("old", ""))
                new_val = str(ch.get("new", ""))
                lines.append(f"| {row_id} | {col} | {old_val} | {new_val} |")
            lines.append("")

        lines.append("---")
        lines.append("")

    lines.append("## Resumen")
    lines.append("")
    lines.append("Documento generado automáticamente por AuditData AI.")
    lines.append(f"- **Archivo original:** {filename}")
    lines.append(f"- **Total de acciones:** {len(changelog)}")
    total_changes = sum(len(e.get("changes", [])) for e in changelog)
    lines.append(f"- **Total de celdas modificadas:** {total_changes}")
    lines.append("")
    lines.append("_Este documento debe conservarse como evidencia del proceso de limpieza de datos._")
    lines.append("")

    return "\n".join(lines)
