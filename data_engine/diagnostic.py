"""Granular diagnostic engine for AuditData AI.

Scans every column and returns all issues grouped by category.
28 categories: 12 main + 16 annexes from the master diagnostic guide.

Each column returns a verdict:
  - "LIMPIA": no issues found
  - list of issue groups, each with: category, severity, count, description, examples
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from .domain_rules import (
    EXCEL_FORMULA_ERRORS,
    MULTIVALUE_SEPARATORS,
    confirm_domain,
    detect_date_day_order,
    detect_date_format,
    get_country_synonym,
    get_gender_synonym,
    is_boolean_synonym,
    is_hidden_missing,
    is_valid_calendar_date,
    match_column_name,
    normalize_for_comparison,
)

ID_NAME_PATTERNS = re.compile(
    r"(^|[_\s])id($|[_\s])|^cod[_\s]|^codigo[_\s]|^identifica|^documento|^cedula|^nit$|^uuid|^key$|^ref[_\s]|^referencia|^registro$|^consecutivo|^num[_\s]",
    re.IGNORECASE,
)

ID_CARDINALITY_THRESHOLD = 0.95

# DG-01 (B1/B3): patron de valor que delata un identificador (UUID, codigos
# con prefijo/sufijo alfanumerico, hashes hex). Los numeros planos (ej. codigos
# postales "110111") NO cuentan como patron de ID.
ID_VALUE_PATTERN = re.compile(
    r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})"
    r"|([A-Za-z]{1,6}-?\d{3,})"
    r"|(\d{3,}-[A-Za-z]{1,6})"
    r"|([0-9a-fA-F]{32,64})",
)

# Dominios que nunca son identificadores, aunque el nombre matchee patrones ID.
NON_ID_DOMAINS = {"city", "gender", "country"}


def _is_id_column(header: str, values: list[str]) -> bool:
    """Detect if a column is an ID/unique identifier based on name + cardinality.

    DG-01 (B1/B3): nunca por nombre solo. Requiere nombre match AND
    (cardinalidad >= 95% O patron de valor de ID). Excluye dominios conocidos
    (ciudad, genero, pais) de ser "ID".
    """
    non_empty = [v.strip() for v in values if v.strip() and not is_hidden_missing(v.strip())]
    if not non_empty:
        return False
    domain = match_column_name(header)
    if domain and domain["domain"] in NON_ID_DOMAINS:
        return False
    name_match = bool(ID_NAME_PATTERNS.search(header.strip()))
    if not name_match:
        return False
    unique_ratio = len(set(non_empty)) / len(non_empty)
    if unique_ratio >= ID_CARDINALITY_THRESHOLD and len(non_empty) >= 10:
        return True
    pattern_matches = sum(1 for v in non_empty if ID_VALUE_PATTERN.fullmatch(v))
    return pattern_matches / len(non_empty) >= 0.9


@dataclass
class IssueGroup:
    category: str
    category_code: str
    severity: str
    count: int
    total_rows: int
    percentage: float
    description: str
    examples: list[dict[str, Any]] = field(default_factory=list)
    affected_rows: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "category_code": self.category_code,
            "severity": self.severity,
            "count": self.count,
            "total_rows": self.total_rows,
            "percentage": round(self.percentage, 2),
            "description": self.description,
            "examples": self.examples[:10],
            "affected_rows": self.affected_rows[:50],
        }


@dataclass
class ColumnDiagnostic:
    column: str
    inferred_domain: str | None
    confidence: float
    verdict: str
    issues: list[IssueGroup] = field(default_factory=list)
    total_rows: int = 0
    profiler: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "column": self.column,
            "inferred_domain": self.inferred_domain,
            "confidence": self.confidence,
            "verdict": self.verdict,
            "issues": [i.to_dict() for i in self.issues],
            "total_rows": self.total_rows,
            "issue_count": len(self.issues),
            "profiler": self.profiler,
        }


@dataclass
class DatasetDiagnostic:
    columns: list[ColumnDiagnostic]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "columns": [c.to_dict() for c in self.columns],
            "summary": self.summary,
        }


def _is_numeric_value(value: str) -> bool:
    try:
        float(value.strip().replace(",", "."))
        return True
    except (ValueError, TypeError):
        return False


def _classify_column_by_frequency(values: list[str]) -> dict[str, Any]:
    """FastTextProfiler v3.0 — Classify a text column by frequency distribution.

    Returns dict with: type, coverage, dominant_values, suspicious_values, confidence, risk.
    """
    non_empty = [v.strip() for v in values if v.strip()]
    n = len(non_empty)
    if n == 0:
        return {"type": "VACIA", "coverage": 0, "confidence": 1.0, "risk": "BAJO",
                "dominant_values": [], "suspicious_values": [], "total_categories": 0}

    freq: Counter = Counter(non_empty)
    unique_count = len(freq)
    p_unique = unique_count / n * 100

    sorted_vals = freq.most_common()
    top_counts = [count for _, count in sorted_vals]

    def coverage(top_k: int) -> float:
        return sum(top_counts[:top_k]) / n * 100

    top1 = coverage(1)
    top2 = coverage(2)
    top3 = coverage(3)
    top5 = coverage(5)
    top10 = coverage(10)

    column_type = "TEXTO_LIBRE"
    dominant_k = 0

    if p_unique >= 95:
        column_type = "IDENTIFICADOR"
    elif top1 >= 95:
        column_type = "CONSTANTE"
        dominant_k = 1
    elif top2 >= 95:
        column_type = "BOOLEANA"
        dominant_k = 2
    elif top3 >= 90:
        column_type = "CATEGORICA"
        dominant_k = 3
    elif top5 >= 90:
        column_type = "CATEGORICA"
        dominant_k = 5
    elif top10 >= 90:
        column_type = "CATEGORICA"
        dominant_k = 10

    guard_pct = p_unique
    guard_moda_pct = top1
    if guard_pct > 50 and guard_moda_pct < 5:
        column_type = "TEXTO_LIBRE"
        dominant_k = 0

    # DG-02 (B2): columnas que hoy se saltan los 16 chequeos
    # (IDENTIFICADOR/CONSTANTE/TEXTO_LIBRE) pero que son claramente fechas o
    # numeros (>=90% parseable) deben correr los chequeos DATE/NUMERIC (spec 4.3).
    if column_type in ("IDENTIFICADOR", "CONSTANTE", "TEXTO_LIBRE"):
        date_ratio = sum(1 for v in non_empty if is_valid_calendar_date(v)) / n
        if date_ratio >= 0.9:
            column_type = "FECHA"
        elif sum(1 for v in non_empty if _is_numeric_value(v)) / n >= 0.9:
            column_type = "NUMERICA"

    dominant_values = [{"value": val, "freq": count, "pct": round(count / n * 100, 2)}
                       for val, count in sorted_vals[:dominant_k]]

    suspicious_values = []
    if dominant_k > 0:
        for val, count in sorted_vals[dominant_k:]:
            pct = count / n * 100
            row_indices = [i for i, v in enumerate(values) if v.strip() == val]
            suspicious_values.append({
                "value": val, "freq": count,
                "pct": round(pct, 2),
                "rows": row_indices[:20],
            })

    if dominant_k > 0:
        coverage_val = sum(top_counts[:dominant_k]) / n * 100
    else:
        coverage_val = 0

    if coverage_val >= 95:
        risk = "BAJO"
    elif coverage_val >= 90:
        risk = "MEDIO"
    elif coverage_val >= 50:
        risk = "ALTO"
    else:
        risk = "MANUAL"

    if risk == "BAJO":
        confidence = 95
    elif risk == "MEDIO":
        confidence = 85
    elif risk == "ALTO":
        confidence = 70
    else:
        confidence = 50

    return {
        "type": column_type,
        "coverage": round(coverage_val, 2),
        "dominant_values": dominant_values,
        "suspicious_values": suspicious_values,
        "confidence": confidence,
        "risk": risk,
        "total_categories": unique_count,
        "top1": round(top1, 2),
        "top2": round(top2, 2),
        "top3": round(top3, 2),
        "top5": round(top5, 2),
        "top10": round(top10, 2),
    }


def _check_categorical_suspicious(
    profiler: dict[str, Any], values: list[str], total_rows: int
) -> list[IssueGroup]:
    """Build issue groups from profiler suspicious categories for CATEGORICA/BOOLEANA columns."""
    issues: list[IssueGroup] = []
    suspicious = profiler.get("suspicious_values", [])
    if not suspicious:
        return issues

    # DG-08 (C1): affected_rows = union de filas de TODOS los valores
    # sospechosos; count = nº de filas distintas (una fila tiene un solo valor,
    # asi que coincide con la suma de frecuencias).
    all_rows: list[int] = []
    for sv in suspicious:
        all_rows.extend(sv.get("rows", []))
    all_rows = sorted(set(all_rows))

    examples: list[dict[str, Any]] = []
    for sv in suspicious[:10]:
        examples.append({
            "value": sv["value"],
            "freq": sv["freq"],
            "pct": sv["pct"],
            "row": sv["rows"][0] if sv.get("rows") else 0,
        })

    risk = profiler.get("risk", "MEDIO")
    severity_map = {"BAJO": "BAJA", "MEDIO": "MEDIA", "ALTO": "ALTA", "MANUAL": "ALTA"}
    severity = severity_map.get(risk, "MEDIA")

    issues.append(IssueGroup(
        category="Categorías sospechosas (FastProfiler)",
        category_code="CATEGORICAL",
        severity=severity,
        count=len(all_rows),
        total_rows=total_rows,
        percentage=len(all_rows) / total_rows * 100 if total_rows > 0 else 0,
        description=f"{len(suspicious)} categoría(s) fuera del conjunto dominante (cobertura: {profiler.get('coverage', 0)}%)",
        examples=examples,
        affected_rows=all_rows,
    ))

    return issues


EXCEL_ROW_OFFSET = 2

_TEXT_LIKE_TYPES = {"TEXTO_LIBRE", "CATEGORICA", "BOOLEANA"}
_NON_TEXT_DOMAINS = {
    "number", "date", "quantity", "currency", "percentage", "phone",
    "latitude", "longitude", "score", "duration", "weight", "distance",
    "email", "id",
}


def _is_text_like(column_type: str, domain_info: dict | None) -> bool:
    """DG-07 (B8/B10): columnas de texto libre/categoricas. Las numericas,
    fechas, codigos y dominios numericos NO son texto libre."""
    if column_type not in _TEXT_LIKE_TYPES:
        return False
    if domain_info and domain_info["domain"] in _NON_TEXT_DOMAINS:
        return False
    return True


def _to_excel_row(index: int) -> int:
    """Convert 0-based data index to Excel row number (header=row 1, data starts row 2)."""
    return index + EXCEL_ROW_OFFSET


def _shift_issue_rows(issue: IssueGroup, row_offset: int = EXCEL_ROW_OFFSET) -> IssueGroup:
    """Shift all row indices in affected_rows and examples by the Excel offset."""
    issue.affected_rows = [r + row_offset for r in issue.affected_rows]
    new_examples: list[dict[str, Any]] = []
    for ex in issue.examples:
        ex = dict(ex)
        if "row" in ex:
            ex["row"] = ex["row"] + row_offset
        if "rows" in ex:
            ex["rows"] = [r + row_offset for r in ex["rows"]]
        new_examples.append(ex)
    issue.examples = new_examples
    return issue


def diagnose_column(header: str, values: list[str], total_rows: int, row_offset: int = EXCEL_ROW_OFFSET) -> ColumnDiagnostic:
    """Run all 28 category checks on a single column and return results."""
    domain_info = match_column_name(header)
    if domain_info and not confirm_domain(domain_info, values):
        # DM-01: el candidato por nombre no se confirma con los valores reales
        # (spec 4.2 paso 3) → sin dominio → se omiten los chequeos dependientes.
        domain_info = None
    inferred_domain = domain_info["domain"] if domain_info else None
    confidence = 0.95 if domain_info else 0.5

    profiler = _classify_column_by_frequency(values)

    issues: list[IssueGroup] = []

    issues.extend(_check_missing(values, total_rows))
    issues.extend(_check_duplicates(header, values, total_rows))

    column_type = profiler["type"]
    is_free_text = column_type == "TEXTO_LIBRE"
    is_identifier = column_type == "IDENTIFICADOR"
    is_constant = column_type == "CONSTANTE"

    if not is_free_text and not is_identifier and not is_constant:
        issues.extend(_check_date_formats(values, total_rows))
        issues.extend(_check_numeric_domain_violations(values, total_rows, domain_info))
        issues.extend(_check_text_errors(values, total_rows))
        issues.extend(_check_categorical_inconsistency(values, total_rows, domain_info))
        issues.extend(_check_type_validation(values, total_rows, domain_info))
        issues.extend(_check_unit_inconsistency(values, total_rows, domain_info))
        issues.extend(_check_encoding(values, total_rows))
        issues.extend(_check_formula_errors(values, total_rows))
        issues.extend(_check_multivalue_cells(values, total_rows))
        issues.extend(_check_ghost_characters(values, total_rows))
        issues.extend(_check_text_truncation(values, total_rows))
        issues.extend(_check_boolean_inconsistency(values, total_rows))
        issues.extend(_check_colección_inconsistencia(values, total_rows, domain_info))
        # DG-03 (B4): activar la deteccion de categorias sospechosas por
        # frecuencia. Analogia: un booleano tiene 2 valores predominantes y el
        # resto son errores potenciales; una categorica tiene 3+ valores
        # distinguidos por frecuencia. Los chequeos de contenido (16) y el de
        # distribucion (suspicious) son ortogonales y conviven.
        if column_type in ("CATEGORICA", "BOOLEANA"):
            issues.extend(_check_categorical_suspicious(profiler, values, total_rows))
        # DG-07 (B8/B10): SCIENTIFIC y MIXED_LANG solo aplican a columnas de
        # texto libre/categoricas; en numericas/fechas/codigos son falsos
        # positivos. UNIT_ERROR queda con su guard de dominio numerico interno.
        if _is_text_like(column_type, domain_info):
            issues.extend(_check_scientific_notation(values, total_rows))
            issues.extend(_check_mixed_languages(values, total_rows, domain_info))

    if not issues:
        return ColumnDiagnostic(
            column=header,
            inferred_domain=inferred_domain,
            confidence=confidence,
            verdict="LIMPIA",
            total_rows=total_rows,
            profiler=profiler,
        )

    for issue in issues:
        _shift_issue_rows(issue, row_offset=row_offset)

    return ColumnDiagnostic(
        column=header,
        inferred_domain=inferred_domain,
        confidence=confidence,
        verdict=f"{len(issues)} problema(s) detectado(s)",
        issues=issues,
        total_rows=total_rows,
        profiler=profiler,
    )


def diagnose_dataset(headers: list[str], rows: list[dict[str, Any]], header_row_index: int = 0) -> DatasetDiagnostic:
    """Run diagnosis on all columns of a dataset.

    header_row_index: 0-based position of the header row in the original file.
                      The Excel row offset is header_row_index + 2 (header row + 1 for 1-based).
    """
    total_rows = len(rows)
    total_issues = 0
    total_clean = 0
    category_counts: Counter = Counter()

    row_offset = header_row_index + 2

    column_diagnostics: list[ColumnDiagnostic] = []
    for header in headers:
        col_values = [str(row.get(header, "")) for row in rows]
        diag = diagnose_column(header, col_values, total_rows, row_offset=row_offset)
        column_diagnostics.append(diag)

        for issue in diag.issues:
            total_issues += issue.count
            category_counts[issue.category_code] += 1
        if diag.verdict == "LIMPIA":
            total_clean += 1

    row_dup_issues = _check_row_duplicates(headers, rows)
    if row_dup_issues:
        for issue in row_dup_issues:
            _shift_issue_rows(issue, row_offset=row_offset)
        total_issues += row_dup_issues[0].count
        category_counts["DUPLICATE"] += 1
        column_diagnostics.insert(0, ColumnDiagnostic(
            column="__dataset__",
            inferred_domain=None,
            confidence=1.0,
            verdict=f"{len(row_dup_issues)} problema(s) de duplicados por fila",
            issues=row_dup_issues,
            total_rows=total_rows,
        ))

    summary = {
        "total_rows": total_rows,
        "total_columns": len(headers),
        "total_issues": total_issues,
        "clean_columns": total_clean,
        "dirty_columns": len(headers) - total_clean,
        "category_distribution": dict(category_counts.most_common()),
        "verdict": "LIMPIO" if total_issues == 0 else f"REQUIERE LIMPIEZA ({total_issues} problemas en {len(headers) - total_clean} columnas)",
    }

    return DatasetDiagnostic(columns=column_diagnostics, summary=summary)


def _check_row_duplicates(headers: list[str], rows: list[dict[str, Any]]) -> list[IssueGroup]:
    """Detect full-row or near-full-row duplicates across the dataset."""
    issues: list[IssueGroup] = []
    if len(rows) < 2 or not headers:
        return issues

    def _row_signature(row: dict[str, Any], cols: list[str]) -> tuple[str, ...]:
        # DU-01: misma firma normalizada (NFKD + lower) que analyzer/removal.
        return tuple(normalize_for_comparison(row.get(c, "")) for c in cols)

    sig_to_rows: dict[tuple[str, ...], list[int]] = {}
    for i, row in enumerate(rows):
        sig = _row_signature(row, headers)
        sig_to_rows.setdefault(sig, []).append(i)

    exact_groups = {sig: row_indices for sig, row_indices in sig_to_rows.items() if len(row_indices) > 1}

    if exact_groups:
        all_dup_rows: list[int] = []
        examples: list[dict[str, Any]] = []
        for sig, row_indices in sorted(exact_groups.items(), key=lambda x: -len(x[1]))[:5]:
            all_dup_rows.extend(row_indices[1:])
            examples.append({
                "rows": row_indices,
                "match": "100%",
                "count": len(row_indices),
                "sample_value": sig[0][:50] if sig else "",
            })
        count = len(all_dup_rows)
        issues.append(IssueGroup(
            category="Filas duplicadas exactas",
            category_code="DUPLICATE",
            severity="CRITICA",
            count=count,
            total_rows=len(rows),
            percentage=count / len(rows) * 100 if rows else 0,
            description=f"{len(exact_groups)} grupo(s) de filas duplicadas: {count} filas a eliminar",
            examples=examples,
            affected_rows=all_dup_rows,
        ))

    return issues


# ── CHECK FUNCTIONS ──────────────────────────────────────────────────────────

def _check_missing(values: list[str], total: int) -> list[IssueGroup]:
    issues: list[IssueGroup] = []
    missing_rows: list[int] = []
    missing_vals: list[str] = []
    sentinel_rows: list[int] = []
    sentinel_vals: list[str] = []

    for i, v in enumerate(values):
        if v is None or v == "":
            missing_rows.append(i)
            missing_vals.append(v or "")
        elif is_hidden_missing(v):
            sentinel_rows.append(i)
            sentinel_vals.append(v)

    if missing_rows:
        examples = [{"row": missing_rows[j], "value": missing_vals[j]} for j in range(min(5, len(missing_rows)))]
        issues.append(IssueGroup(
            category="Valores faltantes",
            category_code="MISSING",
            severity="ALTA",
            count=len(missing_rows),
            total_rows=total,
            percentage=len(missing_rows) / total * 100 if total > 0 else 0,
            description=f"Celdas vacias o NULL: {len(missing_rows)} de {total}",
            examples=examples,
            affected_rows=missing_rows,
        ))

    if sentinel_rows:
        examples = [{"row": sentinel_rows[j], "value": sentinel_vals[j]} for j in range(min(5, len(sentinel_rows)))]
        issues.append(IssueGroup(
            category="Placeholders ocultos",
            category_code="HIDDEN_MISSING",
            severity="MEDIA",
            count=len(sentinel_rows),
            total_rows=total,
            percentage=len(sentinel_rows) / total * 100 if total > 0 else 0,
            description=f"Tokens que ocultan valores faltantes: {len(sentinel_rows)} ocurrencias",
            examples=examples,
            affected_rows=sentinel_rows,
        ))

    return issues


def _check_duplicates(header: str, values: list[str], total: int) -> list[IssueGroup]:
    """Detect duplicate values ONLY in ID/unique identifier columns.

    Repeated values in non-ID columns (e.g. "Bogotá" in a city column) are
    normal frequency, not quality issues.
    """
    issues: list[IssueGroup] = []

    if not _is_id_column(header, values):
        return issues

    val_to_rows: dict[str, list[int]] = {}
    for i, v in enumerate(values):
        v_stripped = v.strip()
        if not v_stripped or is_hidden_missing(v_stripped):
            continue
        val_to_rows.setdefault(v_stripped, []).append(i)

    dup_groups = {v: rows for v, rows in val_to_rows.items() if len(rows) > 1}

    if not dup_groups:
        return issues

    dup_rows: list[int] = []
    examples: list[dict[str, Any]] = []
    for val, rows in sorted(dup_groups.items(), key=lambda x: -len(x[1]))[:10]:
        dup_rows.extend(rows[1:])
        examples.append({
            "row": rows[0],
            "value": val,
            "count": len(rows),
            "detail": f"'{val}' aparece {len(rows)} veces",
        })

    total_dup = len(dup_rows)
    issues.append(IssueGroup(
        category="Valores duplicados en columna ID",
        category_code="DUPLICATE",
        severity="ALTA",
        count=total_dup,
        total_rows=total,
        percentage=total_dup / total * 100 if total > 0 else 0,
        description=f"Columna '{header}' es un identificador con {len(dup_groups)} valor(es) repetido(s). Se esperan valores únicos.",
        examples=examples,
        affected_rows=dup_rows,
    ))

    return issues


def _check_date_formats(values: list[str], total: int) -> list[IssueGroup]:
    issues: list[IssueGroup] = []
    format_counts: Counter = Counter()
    format_rows: dict[str, list[int]] = {}
    invalid_dates: list[str] = []
    invalid_rows: list[int] = []
    parsed_rows: list[int] = []

    date_pattern = re.compile(r"\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4}|\d{2}/\d{2}/\d{2}")

    day_order = detect_date_day_order(values)

    for i, v in enumerate(values):
        v_stripped = v.strip()
        if not v_stripped:
            continue
        if date_pattern.search(v_stripped):
            parsed_rows.append(i)
            fmt = detect_date_format(v_stripped)
            if fmt:
                format_counts[fmt] += 1
                format_rows.setdefault(fmt, []).append(i)
            else:
                format_counts["desconocido"] += 1
                format_rows.setdefault("desconocido", []).append(i)

    if len(format_counts) > 1:
        # DG-08 (C1): affected_rows = todas las filas con formato detectado;
        # los ejemplos se limitan a los 5 formatos principales.
        all_rows = parsed_rows
        examples: list[dict[str, Any]] = []
        for f, c in format_counts.most_common(5):
            rows_for_fmt = format_rows.get(f, [])
            examples.append({"row": rows_for_fmt[0] if rows_for_fmt else 0, "format": f, "count": c})
        issues.append(IssueGroup(
            category="Inconsistencia de formato de fecha",
            category_code="DATE_FORMAT",
            severity="ALTA",
            count=len(all_rows),
            total_rows=total,
            percentage=len(all_rows) / total * 100 if total > 0 else 0,
            description=f"Múltiples formatos de fecha detectados: {dict(format_counts)}",
            examples=examples,
            affected_rows=all_rows,
        ))

    for i, v in enumerate(values):
        v_stripped = v.strip()
        if date_pattern.search(v_stripped) and not is_valid_calendar_date(v_stripped, day_order):
            invalid_dates.append(v_stripped)
            invalid_rows.append(i)

    if invalid_dates:
        examples = [{"row": invalid_rows[j], "value": invalid_dates[j]} for j in range(min(5, len(invalid_dates)))]
        issues.append(IssueGroup(
            category="Fechas imposibles",
            category_code="DATE_INVALID",
            severity="CRITICA",
            count=len(invalid_dates),
            total_rows=total,
            percentage=len(invalid_dates) / total * 100 if total > 0 else 0,
            description=f"Fechar con días/meses invalidos: {len(invalid_dates)} ocurrencias",
            examples=examples,
            affected_rows=invalid_rows,
        ))

    return issues


def _check_numeric_domain_violations(
    values: list[str], total: int, domain_info: dict | None
) -> list[IssueGroup]:
    issues: list[IssueGroup] = []

    if not domain_info or not domain_info.get("range"):
        return issues

    min_val, max_val = domain_info["range"]
    if min_val is None and max_val is None:
        return issues

    violations_rows: list[int] = []
    violations_vals: list[str] = []
    for i, v in enumerate(values):
        v_stripped = v.strip()
        if not v_stripped or is_hidden_missing(v_stripped):
            continue
        try:
            num = float(v_stripped.replace(",", "."))
            if min_val is not None and num < min_val or max_val is not None and num > max_val:
                violations_rows.append(i)
                violations_vals.append(v_stripped)
        except (ValueError, TypeError):
            continue

    if violations_rows:
        domain_name = domain_info.get("domain", "dominio")
        examples = [{"row": violations_rows[j], "value": violations_vals[j]} for j in range(min(5, len(violations_rows)))]
        issues.append(IssueGroup(
            category="Violaciones de dominio numerico",
            category_code="NUMERIC_DOMAIN",
            severity="CRITICA",
            count=len(violations_rows),
            total_rows=total,
            percentage=len(violations_rows) / total * 100 if total > 0 else 0,
            description=f"Valores fuera del rango [{min_val}, {max_val}] para '{domain_name}': {len(violations_rows)} ocurrencias",
            examples=examples,
            affected_rows=violations_rows,
        ))

    return issues


def _check_text_errors(values: list[str], total: int) -> list[IssueGroup]:
    issues: list[IssueGroup] = []
    leading_rows: list[int] = []
    trailing_rows: list[int] = []
    double_space_rows: list[int] = []

    for i, v in enumerate(values):
        if not v.strip():
            continue
        if v != v.strip():
            if v[0] == " ":
                leading_rows.append(i)
            if v[-1] == " ":
                trailing_rows.append(i)
        if "  " in v:
            double_space_rows.append(i)

    total_spacing_rows = list(set(leading_rows + trailing_rows + double_space_rows))
    total_spacing = len(total_spacing_rows)
    if total_spacing > 0:
        examples_spacing = []
        if leading_rows:
            examples_spacing.append({"row": leading_rows[0], "detail": "espacio al inicio"})
        if trailing_rows:
            examples_spacing.append({"row": trailing_rows[0], "detail": "espacio al final"})
        if double_space_rows:
            examples_spacing.append({"row": double_space_rows[0], "detail": "espacio doble"})
        issues.append(IssueGroup(
            category="Errores de redacción y formato",
            category_code="TEXT_ERROR",
            severity="BAJA",
            count=total_spacing,
            total_rows=total,
            percentage=total_spacing / total * 100 if total > 0 else 0,
            description=f"Espacios extra: {len(leading_rows)} inicio, {len(trailing_rows)} fin, {len(double_space_rows)} dobles",
            examples=examples_spacing,
            affected_rows=total_spacing_rows,
        ))

    return issues


def _check_categorical_inconsistency(
    values: list[str], total: int, domain_info: dict | None
) -> list[IssueGroup]:
    issues: list[IssueGroup] = []
    non_empty_indices = [(i, v.strip()) for i, v in enumerate(values) if v.strip()]
    if not non_empty_indices:
        return issues

    if domain_info and domain_info["domain"] == "gender":
        synonyms: Counter = Counter()
        synonym_rows: dict[str, list[int]] = {}
        for i, v in non_empty_indices:
            standard = get_gender_synonym(v)
            synonyms[standard] += 1
            synonym_rows.setdefault(standard, []).append(i)
        if len(synonyms) > 1:
            all_rows: list[int] = []
            examples: list[dict[str, Any]] = []
            seen: list[str] = []
            for i, v in non_empty_indices:
                standard = get_gender_synonym(v)
                if v not in seen:
                    seen.append(v)
                    all_rows.extend(synonym_rows.get(v, [])[:1])
                    examples.append({"row": i, "original": v, "standard": standard})
                if len(examples) >= 5:
                    break
            issues.append(IssueGroup(
                category="Inconsistencia categorica",
                category_code="CATEGORICAL",
                severity="MEDIA",
                count=len(non_empty_indices),
                total_rows=total,
                percentage=len(non_empty_indices) / total * 100 if total > 0 else 0,
                description=f"Valores equivalentes con diferentes etiquetas: {dict(synonyms)}",
                examples=examples,
                affected_rows=[i for i, _ in non_empty_indices],
            ))

    if domain_info and domain_info["domain"] == "country":
        synonyms_c: Counter = Counter()
        for i, v in non_empty_indices:
            standard = get_country_synonym(v)
            synonyms_c[standard] += 1
        if len(synonyms_c) > 1:
            examples_c: list[dict[str, Any]] = []
            seen_c: list[str] = []
            for i, v in non_empty_indices:
                standard = get_country_synonym(v)
                if v not in seen_c:
                    seen_c.append(v)
                    examples_c.append({"row": i, "original": v, "standard": standard})
                if len(examples_c) >= 5:
                    break
            # DG-08 (C1): todas las filas con valor usan una variante inconsistente.
            all_rows_c: list[int] = [i for i, _ in non_empty_indices]
            issues.append(IssueGroup(
                category="Inconsistencia categorica",
                category_code="CATEGORICAL",
                severity="MEDIA",
                count=len(all_rows_c),
                total_rows=total,
                percentage=len(all_rows_c) / total * 100 if total > 0 else 0,
                description=f"Paises con diferentes formatos: {dict(synonyms_c)}",
                examples=examples_c,
                affected_rows=all_rows_c,
            ))

    # DG-05 (B6): variantes de mayusculas/acento del mismo valor son
    # CATEGORICAL (A_REVISAR), no TEXT_ERROR. Se salta gender/country, que ya
    # manejan sinonimos equivalentes en las ramas anteriores.
    if not (domain_info and domain_info["domain"] in ("gender", "country")):
        variant_groups: dict[str, set[str]] = {}
        variant_rows: dict[str, list[int]] = {}
        for i, v in non_empty_indices:
            key = normalize_for_comparison(v)
            variant_groups.setdefault(key, set()).add(v)
            variant_rows.setdefault(key, []).append(i)
        variants = {k: sorted(vs) for k, vs in variant_groups.items() if len(vs) > 1}
        if variants:
            all_rows_v = sorted({i for k in variants for i in variant_rows[k]})
            examples_v = [
                {"row": variant_rows[k][0], "value": " / ".join(vs), "variants": len(vs)}
                for k, vs in list(variants.items())[:5]
            ]
            issues.append(IssueGroup(
                category="Inconsistencia categorica",
                category_code="CATEGORICAL",
                severity="MEDIA",
                count=len(all_rows_v),
                total_rows=total,
                percentage=len(all_rows_v) / total * 100 if total > 0 else 0,
                description=f"Variantes de mayusculas/acento del mismo valor: {len(variants)} grupo(s)",
                examples=examples_v,
                affected_rows=all_rows_v,
            ))

    return issues


def _check_type_validation(
    values: list[str], total: int, domain_info: dict | None
) -> list[IssueGroup]:
    """Unified type validation: merges TYPE_ERROR + TYPE_PER_CELL."""
    issues: list[IssueGroup] = []
    if not domain_info:
        return issues

    expected = domain_info.get("expected_type", "text")
    if expected not in ("number", "date"):
        return issues

    non_empty_indices = [(i, v.strip()) for i, v in enumerate(values) if v.strip() and not is_hidden_missing(v)]
    if not non_empty_indices:
        return issues

    wrong_rows: list[int] = []
    wrong_vals: list[str] = []
    for i, v in non_empty_indices:
        if _fails_type(v, expected):
            wrong_rows.append(i)
            wrong_vals.append(v)

    if wrong_rows and len(wrong_rows) < len(non_empty_indices):
        examples = [{"row": wrong_rows[j], "value": wrong_vals[j]} for j in range(min(5, len(wrong_rows)))]
        issues.append(IssueGroup(
            category="Errores de tipo de dato",
            category_code="TYPE_VALIDATION",
            severity="ALTA",
            count=len(wrong_rows),
            total_rows=total,
            percentage=len(wrong_rows) / total * 100 if total > 0 else 0,
            description=f"Valores que no coinciden con tipo esperado '{expected}': {len(wrong_rows)} de {len(non_empty_indices)}",
            examples=examples,
            affected_rows=wrong_rows,
        ))

    return issues


def _check_unit_inconsistency(
    values: list[str], total: int, domain_info: dict | None
) -> list[IssueGroup]:
    issues: list[IssueGroup] = []
    if not domain_info:
        return issues

    non_empty_indices = [(i, v.strip()) for i, v in enumerate(values) if v.strip() and not is_hidden_missing(v)]
    # DG-07 (B10): una "unidad" es un sufijo corto pegado a un numero
    # ("10 kg", "1.5cm", "20lb"). "treinta" es un numero en palabras, no una
    # unidad; no debe contarse.
    has_alpha = [(i, v) for i, v in non_empty_indices if re.match(r"^\d+(?:[.,]\d+)?\s*[a-zA-Z]{1,4}$", v)]

    if len(has_alpha) > 0 and len(has_alpha) < len(non_empty_indices) * 0.3:
        units: Counter = Counter()
        for _, v in has_alpha:
            match = re.search(r"([a-zA-Z]+)$", v)
            if match:
                units[match.group(1).lower()] += 1

        if len(units) > 1:
            examples = [{"row": has_alpha[j][0], "value": has_alpha[j][1]} for j in range(min(5, len(has_alpha)))]
            issues.append(IssueGroup(
                category="Inconsistencia de unidades",
                category_code="UNIT_ERROR",
                severity="MEDIA",
                count=len(has_alpha),
                total_rows=total,
                percentage=len(has_alpha) / total * 100 if total > 0 else 0,
                description=f"Unidades de medida mezcladas: {dict(units)}",
                examples=examples,
                affected_rows=[i for i, _ in has_alpha],
            ))

    return issues


def _check_encoding(values: list[str], total: int) -> list[IssueGroup]:
    issues: list[IssueGroup] = []
    corrupt_patterns = ["Ã±", "Ã©", "Ã¡", "Ã", "\ufffd", "â€œ", "â€", "Ã³"]
    corrupt_rows: list[int] = []
    corrupt_vals: list[str] = []

    for i, v in enumerate(values):
        for pat in corrupt_patterns:
            if pat in v:
                corrupt_rows.append(i)
                corrupt_vals.append(v)
                break

    if corrupt_rows:
        examples = [{"row": corrupt_rows[j], "value": corrupt_vals[j]} for j in range(min(5, len(corrupt_rows)))]
        issues.append(IssueGroup(
            category="Problemas de codificación",
            category_code="ENCODING",
            severity="MEDIA",
            count=len(corrupt_rows),
            total_rows=total,
            percentage=len(corrupt_rows) / total * 100 if total > 0 else 0,
            description=f"Caracteres corruptos por encoding: {len(corrupt_rows)} valores afectados",
            examples=examples,
            affected_rows=corrupt_rows,
        ))

    return issues


def _check_formula_errors(values: list[str], total: int) -> list[IssueGroup]:
    issues: list[IssueGroup] = []
    formula_rows: list[int] = []
    formula_vals: list[str] = []

    for i, v in enumerate(values):
        if v.strip() in EXCEL_FORMULA_ERRORS:
            formula_rows.append(i)
            formula_vals.append(v.strip())

    if formula_rows:
        error_types = Counter(formula_vals)
        examples = [{"row": formula_rows[j], "error": formula_vals[j], "count": c} for j, (err, c) in enumerate(error_types.most_common(5)) if j < 5]
        issues.append(IssueGroup(
            category="Errores de formula como texto",
            category_code="FORMULA_ERROR",
            severity="ALTA",
            count=len(formula_rows),
            total_rows=total,
            percentage=len(formula_rows) / total * 100 if total > 0 else 0,
            description=f"Errores de Excel exportados como texto: {dict(error_types)}",
            examples=examples,
            affected_rows=formula_rows,
        ))

    return issues


def _check_scientific_notation(values: list[str], total: int) -> list[IssueGroup]:
    issues: list[IssueGroup] = []
    sci_rows: list[int] = []
    sci_vals: list[str] = []

    for i, v in enumerate(values):
        v_stripped = v.strip()
        if re.match(r"^\d+\.?\d*[Ee][+-]?\d+$", v_stripped):
            sci_rows.append(i)
            sci_vals.append(v_stripped)

    if sci_rows:
        examples = [{"row": sci_rows[j], "value": sci_vals[j]} for j in range(min(5, len(sci_rows)))]
        issues.append(IssueGroup(
            category="Notacion científica no deseada",
            category_code="SCIENTIFIC",
            severity="MEDIA",
            count=len(sci_rows),
            total_rows=total,
            percentage=len(sci_rows) / total * 100 if total > 0 else 0,
            description=f"Numeros en notacion científica: {len(sci_rows)} ocurrencias",
            examples=examples,
            affected_rows=sci_rows,
        ))

    return issues


def _is_multivalue_cell(value: str) -> bool:
    """DG-06 (B7): una celda es multivaluada solo si tiene separadores y
    NO es una fecha ni un número con separadores de miles. Con un solo
    separador exige al menos un token no numérico."""
    v = value.strip()
    if not v:
        return False
    if is_valid_calendar_date(v):
        return False
    sep_hits = [sep for sep in MULTIVALUE_SEPARATORS if sep in v]
    if not sep_hits:
        return False
    compact = v.replace(",", "").replace(".", "").replace(" ", "")
    try:
        float(compact)
        return False
    except (ValueError, TypeError):
        pass
    tokens = [t.strip() for t in re.split(r"[,;/|]+", v) if t.strip()]
    if len(tokens) <= 2:
        return False
    if len(set(sep_hits)) >= 2:
        return True
    return any(not _is_numeric_value(t) for t in tokens)


def _check_multivalue_cells(values: list[str], total: int) -> list[IssueGroup]:
    issues: list[IssueGroup] = []
    multi_rows: list[int] = []
    multi_vals: list[str] = []

    for i, v in enumerate(values):
        if _is_multivalue_cell(v):
            multi_rows.append(i)
            multi_vals.append(v.strip())

    if multi_rows:
        examples = [{"row": multi_rows[j], "value": multi_vals[j]} for j in range(min(5, len(multi_rows)))]
        issues.append(IssueGroup(
            category="Campos multivaluados",
            category_code="MULTI_VALUE",
            severity="MEDIA",
            count=len(multi_rows),
            total_rows=total,
            percentage=len(multi_rows) / total * 100 if total > 0 else 0,
            description=f"Celdas con múltiples valores separados: {len(multi_rows)} ocurrencias",
            examples=examples,
            affected_rows=multi_rows,
        ))

    return issues


def _check_mixed_languages(
    values: list[str], total: int, domain_info: dict | None
) -> list[IssueGroup]:
    issues: list[IssueGroup] = []
    non_empty = [v.strip() for v in values if v.strip()]
    if not non_empty or len(non_empty) < 5:
        return issues

    es_rows: list[int] = []
    en_rows: list[int] = []
    es_words = {"el", "la", "los", "las", "un", "una", "de", "del", "en", "y", "o", "por", "para", "con", "sin", "sobre"}
    en_words = {"the", "a", "an", "of", "in", "on", "at", "to", "for", "with", "by", "from", "and", "or", "not"}

    for i, v in enumerate(values):
        v = v.strip()
        if not v:
            continue
        words = set(v.lower().split())
        if words & es_words:
            es_rows.append(i)
        if words & en_words:
            en_rows.append(i)

    if es_rows and en_rows:
        # DG-08 (C1): count = nº de filas distintas afectadas, no ocurrencias sumadas.
        affected_rows = sorted(set(es_rows + en_rows))
        issues.append(IssueGroup(
            category="Mezcla de idiomas",
            category_code="MIXED_LANG",
            severity="BAJA",
            count=len(affected_rows),
            total_rows=total,
            percentage=len(affected_rows) / total * 100 if total > 0 else 0,
            description=f"Valores en múltiples idiomas: {len(es_rows)} español, {len(en_rows)} ingles",
            examples=[],
            affected_rows=affected_rows,
        ))

    return issues


def _check_ghost_characters(values: list[str], total: int) -> list[IssueGroup]:
    issues: list[IssueGroup] = []
    ghost_rows: list[int] = []
    ghost_vals: list[str] = []

    ghost_chars = {"\u00a0", "\u200b", "\u200c", "\u200d", "\ufeff", "\r", "\u00ad"}

    for i, v in enumerate(values):
        for ch in ghost_chars:
            if ch in v:
                ghost_rows.append(i)
                ghost_vals.append(v)
                break

    if ghost_rows:
        examples = [{"row": ghost_rows[j], "value": repr(ghost_vals[j])} for j in range(min(5, len(ghost_rows)))]
        issues.append(IssueGroup(
            category="Caracteres fantasma",
            category_code="GHOST_CHAR",
            severity="BAJA",
            count=len(ghost_rows),
            total_rows=total,
            percentage=len(ghost_rows) / total * 100 if total > 0 else 0,
            description=f"Caracteres invisibles de copiado/pegado: {len(ghost_rows)} valores",
            examples=examples,
            affected_rows=ghost_rows,
        ))

    return issues


def _check_text_truncation(values: list[str], total: int) -> list[IssueGroup]:
    issues: list[IssueGroup] = []
    non_empty_indices = [(i, v.strip()) for i, v in enumerate(values) if v.strip()]
    if not non_empty_indices:
        return issues

    max_len = max(len(v) for _, v in non_empty_indices)
    if max_len < 50:
        return issues

    at_limit = [(i, v) for i, v in non_empty_indices if len(v) == max_len]
    if len(at_limit) > 3:
        examples = [{"row": at_limit[j][0], "value": at_limit[j][1]} for j in range(min(3, len(at_limit)))]
        issues.append(IssueGroup(
            category="Truncamiento de texto",
            category_code="TEXT_TRUNCATION",
            severity="MEDIA",
            count=len(at_limit),
            total_rows=total,
            percentage=len(at_limit) / total * 100 if total > 0 else 0,
            description=f"{len(at_limit)} valores exactamente de {max_len} caracteres (posible truncamiento)",
            examples=examples,
            affected_rows=[i for i, _ in at_limit],
        ))

    return issues


def _check_boolean_inconsistency(values: list[str], total: int) -> list[IssueGroup]:
    issues: list[IssueGroup] = []
    non_empty_indices = [(i, v.strip()) for i, v in enumerate(values) if v.strip()]
    if not non_empty_indices:
        return issues

    norm_map: dict[str, bool] = {}
    display: dict[str, bool] = {}
    bool_rows: dict[str, int] = {}
    ambiguous = False
    for i, v in non_empty_indices:
        result = is_boolean_synonym(v)
        if result is not None:
            key = normalize_for_comparison(v)
            if key in norm_map and norm_map[key] != result:
                ambiguous = True
            norm_map[key] = result
            display.setdefault(v, result)
            bool_rows.setdefault(v, i)

    if not norm_map:
        return issues

    # DG-04 (B5): una columna con solo 2 representaciones canonicas
    # (verdadero/falso) esta bien formada. Solo hay inconsistencia si hay
    # >2 etiquetas distintas o la misma etiqueta mapea a ambos significados.
    if len(norm_map) <= 2 and not ambiguous:
        return issues

    true_vals = {k for k, m in display.items() if m is True}
    false_vals = {k for k, m in display.items() if m is False}

    if true_vals and false_vals:
        # DG-08 (C1): afectan todas las filas con valor (todas usan una
        # representación del conjunto inconsistente); count coincide con
        # len(affected_rows).
        all_rows: list[int] = [i for i, _ in non_empty_indices]
        examples: list[dict[str, Any]] = []
        for v in list(true_vals | false_vals)[:5]:
            examples.append({"row": bool_rows.get(v, 0), "value": v, "meaning": "verdadero" if v in true_vals else "falso"})
        issues.append(IssueGroup(
            category="Inconsistencia booleana",
            category_code="BOOL_INCONSISTENCY",
            severity="MEDIA",
            count=len(all_rows),
            total_rows=total,
            percentage=len(all_rows) / total * 100 if total > 0 else 0,
            description=f"Valores booleanos con múltiples representaciones: verdadero={true_vals}, falso={false_vals}",
            examples=examples,
            affected_rows=all_rows,
        ))

    return issues


def _check_colección_inconsistencia(
    values: list[str], total: int, domain_info: dict | None
) -> list[IssueGroup]:
    issues: list[IssueGroup] = []

    non_empty_indices = [(i, v.strip()) for i, v in enumerate(values) if v.strip()]
    if not non_empty_indices or len(non_empty_indices) < 10:
        return issues

    numeric_indices = [(i, v) for i, v in non_empty_indices if _is_numeric(v)]
    text_indices = [(i, v) for i, v in non_empty_indices if not _is_numeric(v)]

    if len(numeric_indices) > 0 and len(text_indices) > 0:
        dominant_ratio = max(len(numeric_indices), len(text_indices)) / len(non_empty_indices)
        if dominant_ratio < 0.95:
            minority = text_indices if len(text_indices) < len(numeric_indices) else numeric_indices
            examples = [{"row": minority[j][0], "value": minority[j][1]} for j in range(min(5, len(minority)))]
            issues.append(IssueGroup(
                category="Inconsistencia de tipo por celda",
                category_code="TYPE_PER_CELL",
                severity="ALTA",
                count=min(len(numeric_indices), len(text_indices)),
                total_rows=total,
                percentage=min(len(numeric_indices), len(text_indices)) / total * 100 if total > 0 else 0,
                description=f"Columna mezcla tipos: {len(numeric_indices)} numeros, {len(text_indices)} textos",
                examples=examples,
                affected_rows=[i for i, _ in minority],
            ))

    return issues


# ── HELPERS ──────────────────────────────────────────────────────────────────

date_pattern = re.compile(r"\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4}|\d{2}/\d{2}/\d{2}")


def _is_numeric(value: str) -> bool:
    try:
        float(value.replace(",", "."))
        return True
    except (ValueError, TypeError):
        return False


def _fails_type(value: str, expected_type: str) -> bool:
    if expected_type == "number":
        return not _is_numeric(value)
    if expected_type == "date":
        return not date_pattern.search(value)
    return False
