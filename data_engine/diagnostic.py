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


EXCEL_ROW_OFFSET = 2


def _to_excel_row(index: int) -> int:
    """Convert 0-based data index to Excel row number (header=row 1, data starts row 2)."""
    return index + EXCEL_ROW_OFFSET


def _shift_issue_rows(issue: IssueGroup) -> IssueGroup:
    """Shift all row indices in affected_rows and examples by the Excel offset."""
    issue.affected_rows = [_to_excel_row(r) for r in issue.affected_rows]
    new_examples: list[dict[str, Any]] = []
    for ex in issue.examples:
        ex = dict(ex)
        if "row" in ex:
            ex["row"] = _to_excel_row(ex["row"])
        if "rows" in ex:
            ex["rows"] = [_to_excel_row(r) for r in ex["rows"]]
        new_examples.append(ex)
    issue.examples = new_examples
    return issue


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

    for issue in issues:
        _shift_issue_rows(issue)

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

    row_dup_issues = _check_row_duplicates(headers, rows)
    if row_dup_issues:
        for issue in row_dup_issues:
            _shift_issue_rows(issue)
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
        return tuple(str(row.get(c, "")).strip().lower() for c in cols)

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


def _check_duplicates(values: list[str], total: int) -> list[IssueGroup]:
    return []


def _check_date_formats(values: list[str], total: int) -> list[IssueGroup]:
    issues: list[IssueGroup] = []
    format_counts: Counter = Counter()
    format_rows: dict[str, list[int]] = {}
    invalid_dates: list[str] = []
    invalid_rows: list[int] = []
    parsed_count = 0

    date_pattern = re.compile(r"\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4}|\d{2}/\d{2}/\d{2}")

    for i, v in enumerate(values):
        v_stripped = v.strip()
        if not v_stripped:
            continue
        if date_pattern.search(v_stripped):
            parsed_count += 1
            fmt = detect_date_format(v_stripped)
            if fmt:
                format_counts[fmt] += 1
                format_rows.setdefault(fmt, []).append(i)
            else:
                format_counts["desconocido"] += 1
                format_rows.setdefault("desconocido", []).append(i)

    if len(format_counts) > 1:
        all_rows: list[int] = []
        examples: list[dict[str, Any]] = []
        for f, c in format_counts.most_common(5):
            rows_for_fmt = format_rows.get(f, [])
            all_rows.extend(rows_for_fmt)
            examples.append({"row": rows_for_fmt[0] if rows_for_fmt else 0, "format": f, "count": c})
        issues.append(IssueGroup(
            category="Inconsistencia de formato de fecha",
            category_code="DATE_FORMAT",
            severity="ALTA",
            count=parsed_count,
            total_rows=total,
            percentage=parsed_count / total * 100 if total > 0 else 0,
            description=f"Multiples formatos de fecha detectados: {dict(format_counts)}",
            examples=examples,
            affected_rows=all_rows,
        ))

    for i, v in enumerate(values):
        v_stripped = v.strip()
        if date_pattern.search(v_stripped) and not is_valid_calendar_date(v_stripped):
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
            description=f"Fechar con dias/meses invalidos: {len(invalid_dates)} ocurrencias",
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
    inconsistent_case: Counter = Counter()
    case_rows: dict[str, list[int]] = {}

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

        normalized = v.strip().lower()
        if normalized:
            inconsistent_case[normalized] += 1
            case_rows.setdefault(normalized, []).append(i)

    case_issues = {k: v for k, v in inconsistent_case.items() if v > 1 and k != k.title()}
    if case_issues:
        all_rows: list[int] = []
        examples: list[dict[str, Any]] = []
        for k, v in list(case_issues.items())[:5]:
            rows_for_val = case_rows.get(k, [])
            all_rows.extend(rows_for_val)
            examples.append({"row": rows_for_val[0] if rows_for_val else 0, "value": k, "variants": v})
        issues.append(IssueGroup(
            category="Errores de redaccion y formato",
            category_code="TEXT_ERROR",
            severity="BAJA",
            count=sum(case_issues.values()),
            total_rows=total,
            percentage=sum(case_issues.values()) / total * 100 if total > 0 else 0,
            description="Inconsistencia de mayusculas/minusculas y espacios",
            examples=examples,
            affected_rows=all_rows,
        ))

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
            category="Errores de redaccion y formato",
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
            all_rows_c: list[int] = []
            examples_c: list[dict[str, Any]] = []
            seen_c: list[str] = []
            for i, v in non_empty_indices:
                standard = get_country_synonym(v)
                if v not in seen_c:
                    seen_c.append(v)
                    all_rows_c.append(i)
                    examples_c.append({"row": i, "original": v, "standard": standard})
                if len(examples_c) >= 5:
                    break
            issues.append(IssueGroup(
                category="Inconsistencia categorica",
                category_code="CATEGORICAL",
                severity="MEDIA",
                count=len(non_empty_indices),
                total_rows=total,
                percentage=len(non_empty_indices) / total * 100 if total > 0 else 0,
                description=f"Paises con diferentes formatos: {dict(synonyms_c)}",
                examples=examples_c,
                affected_rows=all_rows_c,
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

    non_empty_indices = [(i, v.strip()) for i, v in enumerate(values) if v.strip() and not is_hidden_missing(v)]
    if not non_empty_indices:
        return issues

    wrong_rows: list[int] = []
    wrong_vals: list[str] = []
    for i, v in non_empty_indices:
        if _fails_type(v, expected):
            wrong_rows.append(i)
            wrong_vals.append(v)

    if wrong_rows:
        examples = [{"row": wrong_rows[j], "value": wrong_vals[j]} for j in range(min(5, len(wrong_rows)))]
        issues.append(IssueGroup(
            category="Errores de tipo de dato",
            category_code="TYPE_ERROR",
            severity="ALTA",
            count=len(wrong_rows),
            total_rows=total,
            percentage=len(wrong_rows) / total * 100 if total > 0 else 0,
            description=f"Valores que no se pueden convertir a '{expected}': {len(wrong_rows)} de {len(non_empty_indices)}",
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
    has_alpha = [(i, v) for i, v in non_empty_indices if re.search(r"[a-zA-Z]", v)]

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
            category="Problemas de codificacion",
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
            category="Notacion cientifica no deseada",
            category_code="SCIENTIFIC",
            severity="MEDIA",
            count=len(sci_rows),
            total_rows=total,
            percentage=len(sci_rows) / total * 100 if total > 0 else 0,
            description=f"Numeros en notacion cientifica: {len(sci_rows)} ocurrencias",
            examples=examples,
            affected_rows=sci_rows,
        ))

    return issues


def _check_multivalue_cells(values: list[str], total: int) -> list[IssueGroup]:
    issues: list[IssueGroup] = []
    multi_rows: list[int] = []
    multi_vals: list[str] = []

    for i, v in enumerate(values):
        v_stripped = v.strip()
        if not v_stripped:
            continue
        for sep in MULTIVALUE_SEPARATORS:
            if sep in v_stripped and len(v_stripped.split(sep)) > 2:
                multi_rows.append(i)
                multi_vals.append(v_stripped)
                break

    if multi_rows:
        examples = [{"row": multi_rows[j], "value": multi_vals[j]} for j in range(min(5, len(multi_rows)))]
        issues.append(IssueGroup(
            category="Campos multivaluados",
            category_code="MULTI_VALUE",
            severity="MEDIA",
            count=len(multi_rows),
            total_rows=total,
            percentage=len(multi_rows) / total * 100 if total > 0 else 0,
            description=f"Celdas con multiples valores separados: {len(multi_rows)} ocurrencias",
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

    bool_map: dict[str, bool | None] = {}
    bool_rows: dict[str, int] = {}
    for i, v in non_empty_indices:
        result = is_boolean_synonym(v)
        if result is not None:
            bool_map[v] = result
            bool_rows.setdefault(v, i)

    if not bool_map:
        return issues

    true_vals = {k for k, v in bool_map.items() if v is True}
    false_vals = {k for k, v in bool_map.items() if v is False}

    if true_vals and false_vals:
        all_rows: list[int] = []
        examples: list[dict[str, Any]] = []
        for v in list(true_vals | false_vals)[:5]:
            all_rows.append(bool_rows.get(v, 0))
            examples.append({"row": bool_rows.get(v, 0), "value": v, "meaning": "verdadero" if v in true_vals else "falso"})
        issues.append(IssueGroup(
            category="Inconsistencia booleana",
            category_code="BOOL_INCONSISTENCY",
            severity="MEDIA",
            count=len(non_empty_indices),
            total_rows=total,
            percentage=len(non_empty_indices) / total * 100 if total > 0 else 0,
            description=f"Valores booleanos con multiples representaciones: verdadero={true_vals}, falso={false_vals}",
            examples=examples,
            affected_rows=all_rows,
        ))

    return issues


def _check_coleccion_inconsistencia(
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


def _check_type_per_cell(
    values: list[str], total: int, domain_info: dict | None
) -> list[IssueGroup]:
    issues: list[IssueGroup] = []
    non_empty_indices = [(i, v.strip()) for i, v in enumerate(values) if v.strip() and not is_hidden_missing(v)]

    if not non_empty_indices or not domain_info:
        return issues

    expected = domain_info.get("expected_type", "text")
    if expected == "text":
        return issues

    wrong_rows: list[int] = []
    wrong_vals: list[str] = []
    for i, v in non_empty_indices:
        if expected == "number" and not _is_numeric(v) or expected == "date" and not date_pattern.search(v):
            wrong_rows.append(i)
            wrong_vals.append(v)

    if wrong_rows and len(wrong_rows) < len(non_empty_indices):
        examples = [{"row": wrong_rows[j], "value": wrong_vals[j]} for j in range(min(5, len(wrong_rows)))]
        issues.append(IssueGroup(
            category="Valores de tipo inesperado",
            category_code="UNEXPECTED_TYPE",
            severity="ALTA",
            count=len(wrong_rows),
            total_rows=total,
            percentage=len(wrong_rows) / total * 100 if total > 0 else 0,
            description=f"Valores que no coinciden con tipo esperado '{expected}': {len(wrong_rows)} ocurrencias",
            examples=examples,
            affected_rows=wrong_rows,
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
