# AuditData AI — Analysis JSON Schema

This document freezes the contract of `analyze_dataset()` output. Any new field is **added**, never removed or renamed. This ensures the frontend never breaks from backend shape changes.

**Last updated:** July 2026

---

## Top-level `analysis` object

```json
{
  "filename": "string",
  "generated_at": "ISO 8601 string (America/Bogota UTC-5)",
  "row_count": "integer",
  "column_count": "integer",
  "headers": ["string array"],
  "duplicate_rows": "integer",
  "scores": { ... },
  "columns": [ ... ],
  "recommendations": [ ... ],
  "preview": [ { "header": "value" } array ]
}
```

### `scores` object

```json
{
  "completitud": "float 0-100",
  "consistencia": "float 0-100",
  "exactitud": "float 0-100",
  "unicidad": "float 0-100",
  "general": "float 0-100"
}
```

### `columns[]` — one per header, in order

```json
{
  "name": "string",
  "detected_type": "number | text | date | boolean",
  "total_rows": "integer",
  "missing": "integer",
  "unique_values": "integer",
  "examples": ["string array, max 8"],
  "format_issues": "integer",
  "format_groups": [
    { "canonical": "string", "variants": ["string array"] }
  ],
  "outliers": "integer",
  "outlier_examples": ["float array, max 8"],
  "min_value": "float | null",
  "max_value": "float | null",
  "mean": "float | null",
  "median": "float | null",
  "distribution_pct": "float 0-100",
  "value_distribution": [
    { "value": "string", "freq": "integer", "pct": "float" }
  ]
}
```

### `recommendations[]`

```json
[
  {
    "column": "string",
    "type": "string (category code)",
    "priority": "Alta | Media | Baja",
    "action": "string (human-readable)",
    "impact": "string (human-readable)"
  }
]
```

### `preview[]`

Array of `row_count` dicts (max 10) using header names as keys.

---

## Fields added after initial schema (backward-compatible)

| Field | Added in | Default if missing |
|-------|----------|--------------------|
| `invalid_type_count` | Fase 2 | `0` |
| `outlier_analysis_skipped` | Fase 3 | `false` |
| `key_columns` (param) | Fase 1 | `null` (full-row comparison) |

Frontend must read these with `?? 0` / `?? false` / `?? null` fallbacks.
