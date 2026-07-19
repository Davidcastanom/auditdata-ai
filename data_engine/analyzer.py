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
from datetime import datetime, timezone
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
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z",
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
    """

    headers, rows = load_dataset(filename, payload)
    before = analyze_dataset(filename, payload)
    log: list[dict[str, str]] = []

    for action in actions:
        kind = action.get("kind")
        column = action.get("column", "")
        reason = action.get("reason", "").strip() or "Decision registrada sin detalle adicional."

        # Generate professional justification using Gemini if key is provided
        ai_reason = generate_ai_justification(column or "Dataset", kind, reason)

        if kind == "delete_column" and column in headers:
            headers.remove(column)
            for row in rows:
                row.pop(column, None)
            log.append(_log_entry(column, "Eliminar columna", ai_reason, "Columna eliminada del dataset limpio."))

        elif kind == "drop_missing_rows" and column in headers:
            before_count = len(rows)
            rows = [row for row in rows if _normalize_missing(row.get(column, "")) != ""]
            log.append(
                _log_entry(
                    column,
                    "Eliminar filas con faltantes",
                    ai_reason,
                    f"{before_count - len(rows)} filas eliminadas.",
                )
            )

        elif kind == "impute_missing" and column in headers:
            method = action.get("method", "mode")
            value = _imputation_value(rows, column, method, action.get("value"))
            changed = 0
            for row in rows:
                if _normalize_missing(row.get(column, "")) == "":
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
                    row[column] = updated
                    changed += 1
            log.append(_log_entry(column, f"Estandarizar texto ({mode})", ai_reason, f"{changed} celdas normalizadas."))

        elif kind == "remove_duplicate_rows":
            before_count = len(rows)
            rows = _dedupe_rows(headers, rows)
            log.append(
                _log_entry(
                    "Dataset",
                    "Eliminar filas duplicadas",
                    ai_reason,
                    f"{before_count - len(rows)} filas duplicadas eliminadas.",
                )
            )

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
                log.append(_log_entry(column, f"Renombrar a '{new_name}'", ai_reason, f"Columna renombrada a '{new_name}'."))

        elif kind == "replace_value" and column in headers:
            target_val = action.get("method", "")
            repl_val = action.get("value", "")
            changed = 0
            for row in rows:
                if str(row.get(column, "")) == target_val:
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
                        row[column] = casted
                        changed += 1
                elif target_type == "text":
                    row[column] = str(val)
                    changed += 1
                elif target_type == "boolean":
                    lower_val = str(val).strip().lower()
                    row[column] = "si" if lower_val in {"si", "sí", "true", "1"} else "no"
                    changed += 1
            log.append(_log_entry(column, f"Cambiar tipo de dato a {target_type}", ai_reason, f"{changed} valores convertidos."))

    clean_csv = rows_to_csv(headers, rows)
    after = analyze_dataset(_clean_filename(filename), clean_csv.encode("utf-8"))
    return {"before": before, "after": after, "actions": log, "clean_csv": clean_csv}



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


def build_cleaning_markdown_report(cleaning: dict[str, Any], analyst: str = "-", version: str = "v1.0") -> str:
    """Create a before/after report for a completed cleaning workflow."""

    before = cleaning["before"]
    after = cleaning["after"]
    lines = [
        f"# Data Cleaning Report - {before['filename']}",
        "",
        "## 1. Informacion general",
        f"- Dataset original: {before['filename']}",
        f"- Dataset limpio: {after['filename']}",
        f"- Analista: {analyst or '-'}",
        f"- Version del informe: {version or 'v1.0'}",
        f"- Fecha tecnica: {after['generated_at']}",
        f"- Registros antes: {before['row_count']}",
        f"- Registros despues: {after['row_count']}",
        f"- Columnas antes: {before['column_count']}",
        f"- Columnas despues: {after['column_count']}",
        "",
        "## 2. Resumen ejecutivo",
        (
            f"Se ejecuto un proceso secuencial de limpieza sobre el dataset '{before['filename']}'. "
            f"La calidad general paso de {before['scores']['overall']}% a {after['scores']['overall']}%. "
            "Las decisiones aplicadas quedaron documentadas para garantizar trazabilidad, auditoria y reutilizacion."
        ),
        "",
        "## 3. Problemas encontrados",
        "| Indicador | Antes | Despues |",
        "|---|---:|---:|",
        f"| Filas | {before['row_count']} | {after['row_count']} |",
        f"| Columnas | {before['column_count']} | {after['column_count']} |",
        f"| Filas duplicadas | {before['duplicate_rows']} | {after['duplicate_rows']} |",
        f"| Completitud | {before['scores']['completeness']}% | {after['scores']['completeness']}% |",
        f"| Consistencia | {before['scores']['consistency']}% | {after['scores']['consistency']}% |",
        f"| Exactitud | {before['scores']['accuracy']}% | {after['scores']['accuracy']}% |",
        f"| Unicidad | {before['scores']['uniqueness']}% | {after['scores']['uniqueness']}% |",
        "",
        "## 4. Acciones realizadas",
        "| Columna | Accion | Justificacion | Resultado |",
        "|---|---|---|---|",
    ]

    if cleaning["actions"]:
        for item in cleaning["actions"]:
            lines.append(f"| {item['column']} | {item['action']} | {item['reason']} | {item['result']} |")
    else:
        lines.append("| Dataset | Sin acciones aplicadas | No se registraron decisiones de limpieza | Sin cambios |")

    lines.extend(
        [
            "",
            "## 5. Riesgos identificados",
            _risk_summary(after),
            "",
            "## 6. Conclusion",
            _conclusion(after),
            "",
            "## 7. Criterio metodologico",
            "El proceso siguio la metodologia de comprension, perfilado, reglas de calidad, clasificacion de problemas, tratamiento documentado y validacion final.",
        ]
    )
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
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z",
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
