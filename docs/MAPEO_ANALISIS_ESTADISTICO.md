# Mapeo del Análisis Estadístico — AuditData AI

Este documento responde a la pregunta: **¿dónde se implementa cada algoritmo estadístico y en qué punto del flujo (frontend/PDF/API) se refleja?**

Todos los cálculos viven en el backend Python (`data_engine/`). El frontend **no calcula**; solo renderiza lo que devuelve la API y hace conteos aritméticos simples (sumas de `missing`, `outliers`, etc.) para las comparaciones antes/después.

---

## 1. Perfilado técnico por columna (`data_engine/analyzer.py`)

Orquestado por `analyze_dataset` (L110-129). Endpoint: `POST /api/analyze` (`main.py:119`). Reflejo UI: **Paso 1 "Perfilar"** → `renderProfile` (`frontend/src/app.js:440`).

| Estadística | Función | Línea | Cálculo |
|---|---|---|---|
| Detección de tipo | `_detect_type` | 943 | Clasifica `number / date / boolean / text` con umbral de **≥75%** de valores que parsean. Si no hay valores → `text`. |
| Parseo numérico | `_to_float` | 960 | `float(str(value).replace(",", "."))` — acepta coma decimal. |
| Fecha | `_looks_like_date` | 967 | `%Y-%m-%d`, `%d/%m/%Y`, `%m/%d/%Y`. |
| Missing | `_normalize_missing` | 938 | Normaliza con `MISSING_TOKENS` (vacíos, `"", "null", "na", "n/a", ...`). |
| Distribución de completitud | `_profile_column` | 905 | `distribution_pct = (total - missing) / total * 100`. |
| Valores únicos | `_profile_column` | 910 | `len(set(map(str, present)))`. |
| Ejemplos | `_profile_column` | 921 | Primeros 8 valores únicos. |
| Media / Mediana / Min / Max | `_add_numeric_stats` | 989-995 | `statistics.fmean`, `statistics.median` (redondeo a 4 decimales). |
| **Outliers (IQR)** | `_add_numeric_stats` | 997-1010 | Q1/Q3 por mediana de mitades; rango `[Q1-1.5·IQR, Q3+1.5·IQR]`; cuenta y ejemplos (top 8). Salta si `<4` valores (`outlier_analysis_skipped`) o si `IQR == 0` (se omite sin aviso). |
| Frecuencias | `_add_value_distribution` | 977 | `Counter` ordenado, con `freq` y `pct`. Solo para columnas no numéricas. |
| Inconsistencias de formato | `_add_format_groups` | 1013 | Agrupa variantes (case/espacios) con key normalizada; `format_groups` + `format_issues`. |
| `invalid_type_count` | `_profile_column` | 927 | Solo se calcula cuando el tipo detectado es `number`. |
| Duplicados | `_count_duplicate_rows` | 1026 | Compara fila completa por defecto; con `duplicate_key_columns` usa solo esas columnas normalizando (strip + lowercase + NFKD para acentos). |
| Duplicados normalización | `normalize_for_comparison` (en `domain_rules.py`) | — | NFKD + quita diacríticos; firma única compartida por analyzer, diagnostic y removal (DU-01/DU-02). |

### Scores de calidad — 4 dimensiones (`_quality_scores`, L1055)

```
total_cells = row_count * column_count
completeness = 100 - (missing / total_cells) * 100
consistency  = 100 - (format_issues / total_cells) * 100
accuracy     = 100 - (outliers / total_cells) * 100
uniqueness   = 100 - (duplicate_rows / row_count) * 100
overall      = mean(completeness, consistency, accuracy, uniqueness)
```

Helper: `_score_from_ratio` (L1076). Reflejo: `renderValidation` (`app.js:1188`) compara antes/después con umbrales duros (Completitud/Consistencia/Exactitud ≥95, Unicidad = 0, Calidad ≥90) y en el PDF sección "Evaluación de Calidad".

### Recomendaciones automáticas (`_recommendations`, L1080)

- **Alta**: columnas con `missing`; filas `duplicate_rows`.
- **Media**: `format_issues`; `outliers`.
- **Baja**: mensaje por defecto si no hay problemas.

### Resumen / conclusión

- `_executive_summary` (L1173), `_conclusión` (L1164), `_cleaning_resumen` (L1184) → secciones del informe PDF/Markdown.

---

## 2. Diagnóstico granular — 28 categorías (`data_engine/diagnostic.py`)

Endpoints: `POST /api/diagnose` (`main.py:130`, usado por `nube.js:92`) y `POST /api/ai/recommend` (`main.py:168`). Reflejo UI: **Paso 3 "Diagnóstico"** → `nube.js` (diagnóstico manual por columna con drawer) y tarjetas de columna.

- Clasificación de columnas **FastTextProfiler v3.0** (README): `IDENTIFICADOR` ≥95% únicos · `CONSTANTE` un valor ≥95% · `BOOLEANA` 2-3 valores ≥95% · `CATEGORICA` top ≥90% · `TEXTO_LIBRE` sin match.
- `_is_id_column`: nombre (patrones `ID_NAME_PATTERNS`) + cardinalidad `ID_CARDINALITY_THRESHOLD = 0.95`.
- `IssueGroup` (dataclass): `category / category_code / severity / count`.

### Códigos de categoría encontrados en el código (L247-1139)

| Código | Línea(s) | | Código | Línea(s) |
|---|---|---|---|---|
| `CATEGORICAL` | 247, 751, 780 | | `UNIT_ERROR` | 854 |
| `DUPLICATE` | 427, 525 | | `ENCODING` | 884 |
| `MISSING` | 461 | | `FORMULA_ERROR` | 912 |
| `HIDDEN_MISSING` | 475 | | `SCIENTIFIC` | 940 |
| `DATE_FORMAT` | 571 | | `MULTI_VALUE` | 972 |
| `DATE_INVALID` | 591 | | `MIXED_LANG` | 1008 |
| `NUMERIC_DOMAIN` | 635 | | `GHOST_CHAR` | 1038 |
| `TEXT_ERROR` | 687, 709 | | `TEXT_TRUNCATION` | 1066 |
| `TYPE_VALIDATION` | 820 | | `BOOL_INCONSISTENCY` | 1107 |
| | | | `TYPE_PER_CELL` | 1139 |

El README documenta **28 categorías (12 principales + 16 anexos)** con nombres como `EMPTY`, `FORMAT_INCONSISTENCY`, `CASE_INCONSISTENCY`, `NUMERIC_OUTLIER`, `NUMERIC_RANGE`, etc. Los códigos reales usados por `diagnostic.py` difieren en nomenclatura (ver §4 del documento de arquitectura — posible inconsistencia de documentación a validar).

- Reglas de dominio: `data_engine/domain_rules.py` (~20 reglas): fórmulas Excel, separadores multivalor, formatos de fecha, sinónimos país/género, booleanos no estándar, missing oculto, fechas calendario, `match_column_name`.

---

## 3. Gráficas para PDF (`data_engine/charts.py`)

- `missing_values_chart`, `generate_all_charts(profile, total_rows, actions_log)` — matplotlib en modo `Agg`.
- Usadas por `backend/app/reporting.py` (`build_pdf_report` / `build_cleaning_pdf_report`) e incrustadas en el PDF (paleta clara `PDF_COLORS`).
- `charts.py:119`: `t = action.get("action_type", action.get("kind", "other"))`.

---

## 4. Capa IA (`data_engine/ai_advisor.py`)

| Función | Uso | Endpoint |
|---|---|---|
| `get_ai_recommendations_async` | Recomendaciones batch (primer mensaje detallado) | `POST /api/ai/recommend` (main.py:168) |
| `chat_with_column_advisor` | Chat interactivo por columna (Paso 4) | `POST /api/ai/chat-column` (main.py:196) |
| `analyze_column_deep` | Análisis profundo "experto senior" (Paso 3, bajo demanda) | `POST /api/ai/column-deep-analysis` (main.py:251) |
| `build_column_context` | Contexto único compartido: datos ordenados, únicos, missing, distribución, stats (chat + deep-analysis) | `chat-column` y `column-deep-analysis` |

- Modelo: Groq `llama-3.1-8b-instant`. Keys: `GROQ_API_KEY` (chat/recomendaciones) y `Recomendaciones_de_copiloto` (análisis profundo).
- Sin API key → **modo fallback** con recomendaciones basadas en el diagnóstico local.
- Cache por columna para evitar re-consultas en análisis profundo.
- La IA puede proponer acciones `kind: "review_issue"` (ai_advisor.py:260, 622); **no son aplicadas** por `apply_cleaning_actions` (ver §5 del documento de arquitectura).

---

## 5. Acciones de limpieza (`analyzer.py`, `apply_cleaning_actions` L132)

Dispatch por `action["kind"]` (L146): `drop_missing_rows` · `impute_missing` · `fill_missing` · `standardize_text` · `remove_duplicate_rows` · `flag_outliers` · `replace_with_null` · `rename_column` · `replace_value` · `change_type` · `fill_empty`. También `delete_column`.

- Imputación: `_imputation_value` (L1126) — `mean`/`median` numéricas, `mode` por `Counter`, `custom`.
- Estandarización: `_standardize_text` (L1143) — `upper/lower/title`.
- Genera `before`/`after` (re-perfilado), `log`, `changelog` (bitácora por celda) y `clean_csv`.
- Reflejo UI: **Paso 4 "Depurar"** → `renderDepurationBoard` (`app.js:663`), `renderLog` (L1032), chat copiloto; **Paso 5** `renderValidation`; descargas CSV/XLSX limpio (`POST /api/clean` → `csv_to_xlsx` L739, bug de XLSX corregido en commit `c9965ae`).

---

## 6. Matriz: estadística → dónde se refleja

| Cálculo | Backend | Frontend | PDF (reporting.py) |
|---|---|---|---|
| Perfil por columna (tipo, missing, únicos) | analyzer `_profile_column` | Paso 1 `renderProfile` (app.js:440) | Información General |
| Media/mediana/min/max | analyzer `_add_numeric_stats` | Drawer de columna → sección "Estadísticas" | Resumen Ejecutivo |
| Outliers IQR | analyzer `_add_numeric_stats` | Tabla de columnas + Paso 4 `flag_outliers` | Sección "Outliers" |
| Frecuencias | analyzer `_add_value_distribution` | Drawer → "Frecuencias" | Gráficas de distribución |
| Duplicados | analyzer `_count_duplicate_rows` | Paso 2 Reglas (key columns) + Paso 5 | Problemas por Dimensión |
| 4 dimensiones de calidad | analyzer `_quality_scores` | Paso 5 `renderValidation` (app.js:1188) | Evaluación de Calidad |
| 28 categorías | diagnostic.py | Paso 3 `nube.js` (diagnóstico + drawer) | Problemas por Dimensión |
| Recomendaciones | analyzer `_recommendations` + IA | Paso 3 `loadRecommendations` | Plan de Acciones |
| Bitácora por celda | analyzer `apply_cleaning_actions` → `changelog` | Paso 4 `renderLog` (app.js:1032) | Plan de Acciones |
| Gráficas | charts.py | — (solo PDF) | Secciones con gráficos |
