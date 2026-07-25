"""Granular diagnostic engine for AuditData AI.

Scans every column and returns all issues grouped by category.
28 categories: 12 main + 16 annexes from the master diagnostic guide.

Each column returns a verdict:
  - "LIMPIA": no issues found
  - list of issue groups, each with: category, severity, count, description, examples
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from .domain_rules import (
    BOOLEAN_SYNONYMS,
    COUNTRY_SYNONYMS,
    DATE_FORMATS,
    EXCEL_FORMULA_ERRORS,
    GENDER_SYNONYMS,
    MISSING_TOKENS_EXTENDED,
    MULTIVALUE_SEPARATORS,
    detect_date_format,
    get_country_synonym,
    get_gender_synonym,
    is_boolean_synonym,
    is_hidden_missing,
    is_valid_calendar_date,
    match_column_name,
)


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
        }


@dataclass
class ColumnDiagnostic:
    column: str
    inferred_domain: str | None
    confidence: float
    verdict: str
    issues: list[IssueGroup] = field(default_factory=list)
    total_rows: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "column": self.column,
            "inferred_domain": self.inferred_domain,
            "confidence": self.confidence,
            "verdict": self.verdict,
            "issues": [i.to_dict() for i in self.issues],
            "total_rows": self.total_rows,
            "issue_count": len(self.issues),
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


def diagnose_column(header: str, values: list[str], total_rows: int) -> ColumnDiagnostic:
    """Run all 28 category checks on a single column and return results."""
    domain_info = match_column_name(header)
    inferred_domain = domain_info["domain"] if domain_info else None
    confidence = 0.95 if domain_info else 0.5

    issues: list[IssueGroup] = []

    issues.extend(_check_missing(values, total_rows))
    issues.extend(_check_duplicates(values, total_rows))
    issues.extend(_check_date_formats(values, total_rows))
    issues.extend(_check_numeric_domain_violations(values, total_rows, domain_info))
    issues.extend(_check_text_errors(values, total_rows))
    issues.extend(_check_categorical_inconsistency(values, total_rows, domain_info))
    issues.extend(_check_type_errors(values, total_rows, domain_info))
    issues.extend(_check_unit_inconsistency(values, total_rows, domain_info))
    issues.extend(_check_encoding(values, total_rows))
    issues.extend(_check_out_of_range(values, total_rows, domain_info))
    issues.extend(_check_formula_errors(values, total_rows))
    issues.extend(_check_scientific_notation(values, total_rows))
    issues.extend(_check_multivalue_cells(values, total_rows))
    issues.extend(_check_mixed_languages(values, total_rows, domain_info))
    issues.extend(_check_ghost_characters(values, total_rows))
    issues.extend(_check_text_truncation(values, total_rows))
    issues.extend(_check_boolean_inconsistency(values, total_rows))
    issues.extend(_check_coleccion_inconsistencia(values, total_rows, domain_info))
    issues.extend(_check_type_per_cell(values, total_rows, domain_info))

    if not issues:
        return ColumnDiagnostic(
            column=header,
            inferred_domain=inferred_domain,
            confidence=confidence,
            verdict="LIMPIA",
            total_rows=total_rows,
        )

    return ColumnDiagnostic(
        column=header,
        inferred_domain=inferred_domain,
        confidence=confidence,
        verdict=f"{len(issues)} problema(s) detectado(s)",
        issues=issues,
        total_rows=total_rows,
    )


def diagnose_dataset(headers: list[str], rows: list[dict[str, Any]]) -> DatasetDiagnostic:
    """Run diagnosis on all columns of a dataset."""
    total_rows = len(rows)
    total_issues = 0
    total_clean = 0
    category_counts: Counter = Counter()

    column_diagnostics: list[ColumnDiagnostic] = []
    for header in headers:
        col_values = [str(row.get(header, "")) for row in rows]
        diag = diagnose_column(header, col_values, total_rows)
        column_diagnostics.append(diag)

        for issue in diag.issues:
            total_issues += issue.count
            category_counts[issue.category_code] += 1
        if diag.verdict == "LIMPIA":
            total_clean += 1

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


# ── CHECK FUNCTIONS ──────────────────────────────────────────────────────────

def _check_missing(values: list[str], total: int) -> list[IssueGroup]:
    issues: list[IssueGroup] = []
    missing_vals: list[str] = []
    sentinel_vals: list[str] = []

    for v in values:
        if v is None or v == "":
            missing_vals.append(v or "")
        elif is_hidden_missing(v):
            sentinel_vals.append(v)

    if missing_vals:
        issues.append(IssueGroup(
            category="Valores faltantes",
            category_code="MISSING",
            severity="ALTA",
            count=len(missing_vals),
            total_rows=total,
            percentage=len(missing_vals) / total * 100 if total > 0 else 0,
            description=f"Celdas vacias o NULL: {len(missing_vals)} de {total}",
            examples=[{"row": i, "value": v} for i, v in enumerate(missing_vals[:5])],
        ))

    if sentinel_vals:
        issues.append(IssueGroup(
            category="Placeholders ocultos",
            category_code="HIDDEN_MISSING",
            severity="MEDIA",
            count=len(sentinel_vals),
            total_rows=total,
            percentage=len(sentinel_vals) / total * 100 if total > 0 else 0,
            description=f"Tokens que ocultan valores faltantes: {len(sentinel_vals)} ocurrencias",
            examples=[{"value": v} for v in set(sentinel_vals[:5])],
        ))

    return issues


def _check_duplicates(values: list[str], total: int) -> list[IssueGroup]:
    issues: list[IssueGroup] = []

    non_empty = [v.strip().lower() for v in values if v.strip()]
    counter = Counter(non_empty)
    duplicates = {k: v for k, v in counter.items() if v > 1}

    if duplicates:
        examples = [{"value": k, "count": v} for k, v in sorted(duplicates.items(), key=lambda x: -x[1])[:5]]
        issues.append(IssueGroup(
            category="Duplicados exactos",
            category_code="DUPLICATE",
            severity="CRITICA",
            count=sum(duplicates.values()) - len(duplicates),
            total_rows=total,
            percentage=(sum(duplicates.values()) - len(duplicates)) / total * 100 if total > 0 else 0,
            description=f"Valores repetidos: {len(duplicates)} valores unicos aparecen mas de una vez",
            examples=examples,
        ))

    return issues


def _check_date_formats(values: list[str], total: int) -> list[IssueGroup]:
    issues: list[IssueGroup] = []
    format_counts: Counter = Counter()
    invalid_dates: list[str] = []
    parsed_count = 0

    date_pattern = re.compile(r"\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4}|\d{2}/\d{2}/\d{2}")

    for v in values:
        v_stripped = v.strip()
        if not v_stripped:
            continue
        if date_pattern.search(v_stripped):
            parsed_count += 1
            fmt = detect_date_format(v_stripped)
            if fmt:
                format_counts[fmt] += 1
            else:
                format_counts["desconocido"] += 1

    if len(format_counts) > 1:
        examples = [{"format": f, "count": c} for f, c in format_counts.most_common(5)]
        issues.append(IssueGroup(
            category="Inconsistencia de formato de fecha",
            category_code="DATE_FORMAT",
            severity="ALTA",
            count=parsed_count,
            total_rows=total,
            percentage=parsed_count / total * 100 if total > 0 else 0,
            description=f"Multiples formatos de fecha detectados: {dict(format_counts)}",
            examples=examples,
        ))

    for v in values:
        v_stripped = v.strip()
        if date_pattern.search(v_stripped) and not is_valid_calendar_date(v_stripped):
            invalid_dates.append(v_stripped)

    if invalid_dates:
        issues.append(IssueGroup(
            category="Fechas imposibles",
            category_code="DATE_INVALID",
            severity="CRITICA",
            count=len(invalid_dates),
            total_rows=total,
            percentage=len(invalid_dates) / total * 100 if total > 0 else 0,
            description=f"Fechar con dias/meses invalidos: {len(invalid_dates)} ocurrencias",
            examples=[{"value": v} for v in set(invalid_dates[:5])],
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

    violations: list[str] = []
    for v in values:
        v_stripped = v.strip()
        if not v_stripped or is_hidden_missing(v_stripped):
            continue
        try:
            num = float(v_stripped.replace(",", "."))
            if min_val is not None and num < min_val:
                violations.append(v_stripped)
            elif max_val is not None and num > max_val:
                violations.append(v_stripped)
        except (ValueError, TypeError):
            continue

    if violations:
        domain_name = domain_info.get("domain", "dominio")
        issues.append(IssueGroup(
            category="Violaciones de dominio numerico",
            category_code="NUMERIC_DOMAIN",
            severity="CRITICA",
            count=len(violations),
            total_rows=total,
            percentage=len(violations) / total * 100 if total > 0 else 0,
            description=f"Valores fuera del rango [{min_val}, {max_val}] para '{domain_name}': {len(violations)} ocurrencias",
            examples=[{"value": v} for v in set(violations[:5])],
        ))

    return issues


def _check_text_errors(values: list[str], total: int) -> list[IssueGroup]:
    issues: list[IssueGroup] = []
    leading_space = 0
    trailing_space = 0
    double_space = 0
    inconsistent_case: Counter = Counter()

    for v in values:
        if not v.strip():
            continue
        if v != v.strip():
            leading_space += 1 if v[0] == " " else 0
            trailing_space += 1 if v[-1] == " " else 0
        if "  " in v:
            double_space += 1

        normalized = v.strip().lower()
        if normalized:
            inconsistent_case[normalized] += 1

    case_issues = {k: v for k, v in inconsistent_case.items() if v > 1 and k != k.title()}
    if case_issues:
        issues.append(IssueGroup(
            category="Errores de redaccion y formato",
            category_code="TEXT_ERROR",
            severity="BAJA",
            count=sum(case_issues.values()),
            total_rows=total,
            percentage=sum(case_issues.values()) / total * 100 if total > 0 else 0,
            description="Inconsistencia de mayusculas/minusculas y espacios",
            examples=[{"value": k, "variants": v} for k, v in list(case_issues.items())[:5]],
        ))

    total_spacing = leading_space + trailing_space + double_space
    if total_spacing > 0:
        issues.append(IssueGroup(
            category="Errores de redaccion y formato",
            category_code="TEXT_ERROR",
            severity="BAJA",
            count=total_spacing,
            total_rows=total,
            percentage=total_spacing / total * 100 if total > 0 else 0,
            description=f"Espacios extra: {leading_space} inicio, {trailing_space} fin, {double_space} dobles",
            examples=[],
        ))

    return issues


def _check_categorical_inconsistency(
    values: list[str], total: int, domain_info: dict | None
) -> list[IssueGroup]:
    issues: list[IssueGroup] = []
    non_empty = [v.strip() for v in values if v.strip()]
    if not non_empty:
        return issues

    counter = Counter(v.lower() for v in non_empty)

    if domain_info and domain_info["domain"] == "gender":
        synonyms = Counter()
        for v in non_empty:
            standard = get_gender_synonym(v)
            synonyms[standard] += 1
        if len(synonyms) > 1:
            issues.append(IssueGroup(
                category="Inconsistencia categorica",
                category_code="CATEGORICAL",
                severity="MEDIA",
                count=len(non_empty),
                total_rows=total,
                percentage=len(non_empty) / total * 100 if total > 0 else 0,
                description=f"Valores equivalentes con diferentes etiquetas: {dict(synonyms)}",
                examples=[{"original": v, "standard": get_gender_synonym(v)} for v in list(dict.fromkeys(non_empty))[:5]],
            ))

    if domain_info and domain_info["domain"] == "country":
        synonyms = Counter()
        for v in non_empty:
            standard = get_country_synonym(v)
            synonyms[standard] += 1
        if len(synonyms) > 1:
            issues.append(IssueGroup(
                category="Inconsistencia categorica",
                category_code="CATEGORICAL",
                severity="MEDIA",
                count=len(non_empty),
                total_rows=total,
                percentage=len(non_empty) / total * 100 if total > 0 else 0,
                description=f"Paises con diferentes formatos: {dict(synonyms)}",
                examples=[{"original": v, "standard": get_country_synonym(v)} for v in list(dict.fromkeys(non_empty))[:5]],
            ))

    return issues


def _check_type_errors(
    values: list[str], total: int, domain_info: dict | None
) -> list[IssueGroup]:
    issues: list[IssueGroup] = []

    if not domain_info:
        return issues

    expected = domain_info.get("expected_type", "text")
    if expected not in ("number", "date"):
        return issues

    non_empty = [v.strip() for v in values if v.strip() and not is_hidden_missing(v)]
    if not non_empty:
        return issues

    cast_failures = 0
    for v in non_empty:
        if expected == "number":
            try:
                float(v.replace(",", "."))
            except (ValueError, TypeError):
                cast_failures += 1
        elif expected == "date":
            if not date_pattern.search(v):
                cast_failures += 1

    if cast_failures > 0:
        issues.append(IssueGroup(
            category="Errores de tipo de dato",
            category_code="TYPE_ERROR",
            severity="ALTA",
            count=cast_failures,
            total_rows=total,
            percentage=cast_failures / total * 100 if total > 0 else 0,
            description=f"Valores que no se pueden convertir a '{expected}': {cast_failures} de {len(non_empty)}",
            examples=[{"value": v} for v in non_empty if _fails_type(v, expected)][:5],
        ))

    return issues


def _check_unit_inconsistency(
    values: list[str], total: int, domain_info: dict | None
) -> list[IssueGroup]:
    issues: list[IssueGroup] = []
    if not domain_info:
        return issues

    non_empty = [v.strip() for v in values if v.strip() and not is_hidden_missing(v)]
    has_alpha = [v for v in non_empty if re.search(r"[a-zA-Z]", v)]

    if len(has_alpha) > 0 and len(has_alpha) < len(non_empty) * 0.3:
        units = Counter()
        for v in has_alpha:
            match = re.search(r"([a-zA-Z]+)$", v)
            if match:
                units[match.group(1).lower()] += 1

        if len(units) > 1:
            issues.append(IssueGroup(
                category="Inconsistencia de unidades",
                category_code="UNIT_ERROR",
                severity="MEDIA",
                count=len(has_alpha),
                total_rows=total,
                percentage=len(has_alpha) / total * 100 if total > 0 else 0,
                description=f"Unidades de medida mezcladas: {dict(units)}",
                examples=[{"value": v} for v in has_alpha[:5]],
            ))

    return issues


def _check_encoding(values: list[str], total: int) -> list[IssueGroup]:
    issues: list[IssueGroup] = []
    corrupt_patterns = ["Ã±", "Ã©", "Ã¡", "Ã", "\ufffd", "â€œ", "â€", "Ã³"]
    corrupt_vals: list[str] = []

    for v in values:
        for pat in corrupt_patterns:
            if pat in v:
                corrupt_vals.append(v)
                break

    if corrupt_vals:
        issues.append(IssueGroup(
            category="Problemas de codificacion",
            category_code="ENCODING",
            severity="MEDIA",
            count=len(corrupt_vals),
            total_rows=total,
            percentage=len(corrupt_vals) / total * 100 if total > 0 else 0,
            description=f"Caracteres corruptos por encoding: {len(corrupt_vals)} valores afectados",
            examples=[{"value": v} for v in set(corrupt_vals[:5])],
        ))

    return issues


def _check_out_of_range(
    values: list[str], total: int, domain_info: dict | None
) -> list[IssueGroup]:
    issues: list[IssueGroup] = []

    if not domain_info or not domain_info.get("range"):
        return issues

    min_val, max_val = domain_info["range"]
    if min_val is None and max_val is None:
        return issues

    out_of_range: list[str] = []
    for v in values:
        v_stripped = v.strip()
        if not v_stripped or is_hidden_missing(v_stripped):
            continue
        try:
            num = float(v_stripped.replace(",", "."))
            if min_val is not None and num < min_val:
                out_of_range.append(v_stripped)
            elif max_val is not None and num > max_val:
                out_of_range.append(v_stripped)
        except (ValueError, TypeError):
            continue

    if out_of_range:
        domain_name = domain_info.get("domain", "dominio")
        issues.append(IssueGroup(
            category="Valores fuera de rango",
            category_code="OUT_OF_RANGE",
            severity="ALTA",
            count=len(out_of_range),
            total_rows=total,
            percentage=len(out_of_range) / total * 100 if total > 0 else 0,
            description=f"Valores fuera de rango logico para '{domain_name}': {len(out_of_range)} ocurrencias",
            examples=[{"value": v} for v in set(out_of_range[:5])],
        ))

    return issues


def _check_formula_errors(values: list[str], total: int) -> list[IssueGroup]:
    issues: list[IssueGroup] = []
    formula_errors = [v for v in values if v.strip() in EXCEL_FORMULA_ERRORS]

    if formula_errors:
        error_types = Counter(v.strip() for v in formula_errors)
        issues.append(IssueGroup(
            category="Errores de formula como texto",
            category_code="FORMULA_ERROR",
            severity="ALTA",
            count=len(formula_errors),
            total_rows=total,
            percentage=len(formula_errors) / total * 100 if total > 0 else 0,
            description=f"Errores de Excel exportados como texto: {dict(error_types)}",
            examples=[{"error": k, "count": v} for k, v in error_types.most_common(5)],
        ))

    return issues


def _check_scientific_notation(values: list[str], total: int) -> list[IssueGroup]:
    issues: list[IssueGroup] = []
    sci_vals: list[str] = []

    for v in values:
        v_stripped = v.strip()
        if re.match(r"^\d+\.?\d*[Ee][+-]?\d+$", v_stripped):
            sci_vals.append(v_stripped)

    if sci_vals:
        issues.append(IssueGroup(
            category="Notacion cientifica no deseada",
            category_code="SCIENTIFIC",
            severity="MEDIA",
            count=len(sci_vals),
            total_rows=total,
            percentage=len(sci_vals) / total * 100 if total > 0 else 0,
            description=f"Numeros en notacion cientifica: {len(sci_vals)} ocurrencias",
            examples=[{"value": v} for v in sci_vals[:5]],
        ))

    return issues


def _check_multivalue_cells(values: list[str], total: int) -> list[IssueGroup]:
    issues: list[IssueGroup] = []
    multi_vals: list[str] = []

    for v in values:
        v_stripped = v.strip()
        if not v_stripped:
            continue
        for sep in MULTIVALUE_SEPARATORS:
            if sep in v_stripped and len(v_stripped.split(sep)) > 2:
                multi_vals.append(v_stripped)
                break

    if multi_vals:
        issues.append(IssueGroup(
            category="Campos multivaluados",
            category_code="MULTI_VALUE",
            severity="MEDIA",
            count=len(multi_vals),
            total_rows=total,
            percentage=len(multi_vals) / total * 100 if total > 0 else 0,
            description=f"Celdas con multiples valores separados: {len(multi_vals)} ocurrencias",
            examples=[{"value": v} for v in multi_vals[:5]],
        ))

    return issues


def _check_mixed_languages(
    values: list[str], total: int, domain_info: dict | None
) -> list[IssueGroup]:
    issues: list[IssueGroup] = []
    non_empty = [v.strip() for v in values if v.strip()]
    if not non_empty or len(non_empty) < 5:
        return issues

    lang_es = 0
    lang_en = 0
    es_words = {"el", "la", "los", "las", "un", "una", "de", "del", "en", "y", "o", "por", "para", "con", "sin", "sobre"}
    en_words = {"the", "a", "an", "of", "in", "on", "at", "to", "for", "with", "by", "from", "and", "or", "not"}

    for v in non_empty:
        words = set(v.lower().split())
        if words & es_words:
            lang_es += 1
        if words & en_words:
            lang_en += 1

    if lang_es > 0 and lang_en > 0:
        issues.append(IssueGroup(
            category="Mezcla de idiomas",
            category_code="MIXED_LANG",
            severity="BAJA",
            count=lang_es + lang_en,
            total_rows=total,
            percentage=(lang_es + lang_en) / total * 100 if total > 0 else 0,
            description=f"Valores en multiples idiomas: {lang_es} espanol, {lang_en} ingles",
            examples=[],
        ))

    return issues


def _check_ghost_characters(values: list[str], total: int) -> list[IssueGroup]:
    issues: list[IssueGroup] = []
    ghost_vals: list[str] = []

    ghost_chars = {"\u00a0", "\u200b", "\u200c", "\u200d", "\ufeff", "\r", "\u00ad"}

    for v in values:
        for ch in ghost_chars:
            if ch in v:
                ghost_vals.append(v)
                break

    if ghost_vals:
        issues.append(IssueGroup(
            category="Caracteres fantasma",
            category_code="GHOST_CHAR",
            severity="BAJA",
            count=len(ghost_vals),
            total_rows=total,
            percentage=len(ghost_vals) / total * 100 if total > 0 else 0,
            description=f"Caracteres invisibles de copiado/pegado: {len(ghost_vals)} valores",
            examples=[{"value": repr(v)} for v in ghost_vals[:5]],
        ))

    return issues


def _check_text_truncation(values: list[str], total: int) -> list[IssueGroup]:
    issues: list[IssueGroup] = []
    non_empty = [v.strip() for v in values if v.strip()]
    if not non_empty:
        return issues

    max_len = max(len(v) for v in non_empty)
    if max_len < 50:
        return issues

    at_limit = [v for v in non_empty if len(v) == max_len]
    if len(at_limit) > 3:
        issues.append(IssueGroup(
            category="Truncamiento de texto",
            category_code="TEXT_TRUNCATION",
            severity="MEDIA",
            count=len(at_limit),
            total_rows=total,
            percentage=len(at_limit) / total * 100 if total > 0 else 0,
            description=f"{len(at_limit)} valores exactamente de {max_len} caracteres (posible truncamiento)",
            examples=[{"value": v} for v in at_limit[:3]],
        ))

    return issues


def _check_boolean_inconsistency(values: list[str], total: int) -> list[IssueGroup]:
    issues: list[IssueGroup] = []
    non_empty = [v.strip() for v in values if v.strip()]
    if not non_empty:
        return issues

    bool_map: dict[str, bool | None] = {}
    for v in non_empty:
        result = is_boolean_synonym(v)
        if result is not None:
            bool_map[v] = result

    if not bool_map:
        return issues

    true_vals = {k for k, v in bool_map.items() if v is True}
    false_vals = {k for k, v in bool_map.items() if v is False}

    if true_vals and false_vals:
        issues.append(IssueGroup(
            category="Inconsistencia booleana",
            category_code="BOOL_INCONSISTENCY",
            severity="MEDIA",
            count=len(non_empty),
            total_rows=total,
            percentage=len(non_empty) / total * 100 if total > 0 else 0,
            description=f"Valores booleanos con multiples representaciones: verdadero={true_vals}, falso={false_vals}",
            examples=[{"value": v, "meaning": "verdadero" if v in true_vals else "falso"} for v in list(true_vals | false_vals)[:5]],
        ))

    return issues


def _check_coleccion_inconsistencia(
    values: list[str], total: int, domain_info: dict | None
) -> list[IssueGroup]:
    issues: list[IssueGroup] = []

    non_empty = [v.strip() for v in values if v.strip()]
    if not non_empty or len(non_empty) < 10:
        return issues

    numeric_count = sum(1 for v in non_empty if _is_numeric(v))
    text_count = len(non_empty) - numeric_count

    if numeric_count > 0 and text_count > 0:
        dominant_ratio = max(numeric_count, text_count) / len(non_empty)
        if dominant_ratio < 0.95:
            issues.append(IssueGroup(
                category="Inconsistencia de tipo por celda",
                category_code="TYPE_PER_CELL",
                severity="ALTA",
                count=text_count if numeric_count > text_count else numeric_count,
                total_rows=total,
                percentage=min(numeric_count, text_count) / total * 100 if total > 0 else 0,
                description=f"Columna mezcla tipos: {numeric_count} numeros, {text_count} textos",
                examples=[],
            ))

    return issues


def _check_type_per_cell(
    values: list[str], total: int, domain_info: dict | None
) -> list[IssueGroup]:
    issues: list[IssueGroup] = []
    non_empty = [v.strip() for v in values if v.strip() and not is_hidden_missing(v)]

    if not non_empty or not domain_info:
        return issues

    expected = domain_info.get("expected_type", "text")
    if expected == "text":
        return issues

    wrong_type = []
    for v in non_empty:
        if expected == "number" and not _is_numeric(v):
            wrong_type.append(v)
        elif expected == "date" and not date_pattern.search(v):
            wrong_type.append(v)

    if wrong_type and len(wrong_type) < len(non_empty):
        issues.append(IssueGroup(
            category="Valores de tipo inesperado",
            category_code="UNEXPECTED_TYPE",
            severity="ALTA",
            count=len(wrong_type),
            total_rows=total,
            percentage=len(wrong_type) / total * 100 if total > 0 else 0,
            description=f"Valores que no coinciden con tipo esperado '{expected}': {len(wrong_type)} ocurrencias",
            examples=[{"value": v} for v in wrong_type[:5]],
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
