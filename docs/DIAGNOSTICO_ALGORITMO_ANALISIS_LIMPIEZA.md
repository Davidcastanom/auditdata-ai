# Mapa y Diagnóstico del Algoritmo Núcleo (`analyzer.py`)

Compañero de `docs/DIAGNOSTICO_MEJORA_MOTOR_28CATEGORIAS.md`. Aquí se diagnostica el **algoritmo central**: carga de archivos, perfilado, outliers, scores 4D, duplicados, imputación y acciones de limpieza.

Alcance: `data_engine/analyzer.py` · `frontend/src/app.js` (pasos 0,1,2,4,5,6).

---

## 1. Mapa del algoritmo

```
POST /api/analyze ──▶ analyze_dataset (L110)
  ├─ load_dataset (L94) → _load_csv (771) | _load_xlsx (795)
  ├─ _count_duplicate_rows (1026)     → duplicate_rows
  ├─ [_profile_column (905) por columna]
  │    ├─ _normalize_missing (938)    → missing
  │    ├─ _detect_type (943)          → number|date|boolean|text
  │    ├─ _add_numeric_stats (989)    → min/max/mean/median + outliers IQR
  │    └─ _add_format_groups (1013)   → format_issues
  ├─ _quality_scores (1055)           → 4 dimensiones + overall
  └─ _recommendations (1080)

POST /api/clean ──▶ apply_cleaning_actions (132)
  ├─ analyze_dataset (before)
  ├─ por acción: dispatch por kind → muta headers/rows + changelog + log
  │    (cada acción llama generate_ai_justification → Gemini, L38)
  └─ analyze_dataset (after, sobre CSV limpio) → before/after/actions/changelog/clean_csv
```

---

## 2. Diagnóstico de perfilado

| # | Hallazgo | Ubicación | Impacto |
|---|---|---|---|
| P1 | **`_to_float` confunde separador de miles con decimal**: `str.replace(",", ".")`. `"1,234"` (miles US) → `1.234`, y `"45,000"` (sueldo) → `45.0`. La media/mediana/outliers quedan **distorsionados** en cualquier dataset con formato de miles. | analyzer.py:960-964 | Errores silenciosos en todas las estadísticas numéricas. |
| P2 | `_detect_type` evalúa `number` **antes que `date`**: fechas numéricas (`20240101`) y "0/1" se clasifican como number. Una columna `01/01/2020` con `/` no parsea como float → OK, pero `20240101` → number. | analyzer.py:943-957 | Tipo incorrecto → stats numéricas irrelevantes y outliers absurdos. |
| P3 | Umbral fijo 75%: una columna 70% numérica y 30% texto → clasificada `text` → **no calcula outliers ni stats** y reporta `invalid_type_count` que **nadie usa** (ni scores ni recomendaciones). | analyzer.py:925-933, 1055 | Datos parcialmente numéricos quedan sin diagnóstico estadístico. |
| P4 | **Dos tablas de "missing" distintas**: `analyzer.MISSING_TOKENS` (`analyzer.py:35` = `na/n/a/null/none/nan/-`) vs `domain_rules.MISSING_TOKENS_EXTENDED` (incluye `9999`, `-1`, `pendiente`, `" "`...). | analyzer.py:35 vs domain_rules.py:220 | El **mismo dataset reporta missing distinto** entre Paso 1 (perfil) y Paso 3 (diagnóstico): en Paso 1 "pendiente" es dato, en Paso 3 es `HIDDEN_MISSING`. |
| P5 | Outliers: `IQR == 0` → se omite **silenciosamente** (no marca `outlier_analysis_skipped`); columnas constantes casi no reciben aviso. Además no hay umbral de tamaño para el set (`len(values) < 4` → skip). | analyzer.py:997-1010 | Falta transparencia en columnas sin IQR. |
| P6 | `_add_format_groups` agrupa por key `lowercase + colapso espacios` → case/espacios. Bien, pero las "variantes" se cuentan como `format_issues` = número de variantes, no de filas → el conteo no coincide con filas afectadas (mismo problema de semántica C1 del otro doc). | analyzer.py:1013-1023 | Números de inconsistencias poco interpretables. |

---

## 3. Diagnóstico de scores 4D (`_quality_scores`)

| # | Hallazgo | Ubicación | Impacto |
|---|---|---|---|
| S1 | **`accuracy` solo mide outliers IQR** pero se etiqueta "exactitud". Un dataset lleno de errores de tipo (columnas texto en campo numérico) da **100% de exactitud**. `invalid_type_count` existe pero no entra en la fórmula. | analyzer.py:1063 | El score "exactitud" es engañoso. |
| S2 | `consistency` solo mide `format_issues` (case/espacios). No incorpora formatos de fecha, booleanos mezclados, unidades, etc. | analyzer.py:1062 | La "consistencia" es subestimada (sobreestimada el score). |
| S3 | **Escalas de denominador mezcladas**: completeness/consistency/accuracy usan `total_cells`; uniqueness usa `row_count`. `overall` es la media aritmética simple → una dimensión dominante (completitud, con miles de celdas) eclipsa el resto. | analyzer.py:1056-1065 | El overall no es robusto ni ponderado. |
| S4 | Scores sobre **toda la muestra**, sin manejar columnas 100% vacías de forma especial (una columna vacía entera penaliza `total_cells` igual que una con 1 missing). | analyzer.py:1055-1073 | Columnas irrelevantes afectan el global. |

---

## 4. Diagnóstico de duplicados

| # | Hallazgo | Ubicación | Impacto |
|---|---|---|---|
| D1 | **Dos definiciones de duplicado**: `analyzer._count_duplicate_rows` (L1026) por defecto compara fila completa **sensible a mayúsculas/acentos** (solo `strip`); `diagnostic._check_row_duplicates` (L397) compara **insensible** (`strip + lower`). → Paso 1 y Paso 3 reportan **conteos distintos**. | analyzer.py:1039 vs diagnostic.py:403 | El número de duplicados cambia entre pasos del wizard. |
| D2 | `remove_duplicate_rows` en limpieza usa firma completa sensible a mayúsculas **e ignora `duplicate_key_columns`** (L298) aunque el análisis los haya configurado. → Se "arreglan" duplicados que no son los que el analista definió. | analyzer.py:295-310 | Inconsistencia entre definición (Paso 2) y acción (Paso 4). |
| D3 | Con `duplicate_key_columns` la normalización (NFKD + lower) **solo** se aplica en `_count_duplicate_rows` (L1037-1043), no en la limpieza. | analyzer.py:1036-1044 | Detección ≠ limpieza. |

---

## 5. Diagnóstico de acciones de limpieza (`apply_cleaning_actions`)

| # | Hallazgo | Ubicación | Impacto |
|---|---|---|---|
| C1 | **`change_type` a boolean no usa la tabla de sinónimos**: solo `{si,sí,true,1}` → "si"; todo lo demás → "no". `"activo"`, `"yes"`, `"verdadero"`, `"0"`→"no" (perdida de datos). `domain_rules.BOOLEAN_SYNONYMS` sí conoce "activo"/"yes"/"verdadero". | analyzer.py:400-402 vs domain_rules.py:204 | Conversión booleana corrupta. |
| C2 | **`fill_empty` ignora `target_rows`**: a diferencia de las demás acciones, recorre TODAS las filas sin `target_set` → el analista no puede limitar el alcance. | analyzer.py:414-429 | Comportamiento inconsistente entre acciones. |
| C3 | **`flag_outliers` no marca filas reales**: sin `target_rows` solo escribe "Sin cambios destructivos". Los outliers del perfilado (L1008-1010) tienen `outlier_examples` pero nunca llegan como filas a marcar → el changelog no las registra. | analyzer.py:313-317 | La acción "marcar outliers" es cosmética. |
| C4 | **`review_issue` no existe** en el dispatch → las tarjetas del Paso 3 (que generan `kind:'review_issue'`) **no producen ninguna acción**. | analyzer.py:146-429 | Tarjetas no funcionales (C8 del otro doc). |
| C5 | **`target_rows - 2` hardcodeado**: convierte filas de Excel con offset fijo 2, pero el encabezado real puede estar en otra fila (`header_row_index` de `_load_csv`/`_find_header_row`). Con archivos que tienen metadatos arriba, **las filas objetivo son incorrectas**. | analyzer.py:150-151 vs diagnostic.py:355 | Se eliminan/imputan filas equivocadas. |
| C6 | **`impute_missing`/`fill_missing`/`fill_empty` se solapan**: 3 acciones casi idénticas (rellenar vacíos) con diferencias sutiles (NULL, método, scope). Duplicación conceptual. | analyzer.py:192-251, 414-429 | UI confusa y mantenimiento difícil. |
| C7 | **Rendimiento**: `generate_ai_justification` (Gemini) se llama **por cada acción** (L154), síncrono y bloqueante. Con 20 acciones = 20 llamadas HTTP seriales (sin timeout configurado). Y mezcla dos proveedores IA (Groq en `ai_advisor.py`, Gemini aquí). | analyzer.py:38-66, 154 | Limpiezas lentas; inconsistencia de stack IA. |
| C8 | **`before` y `after` se recalculan re-analizando el CSV limpio** (L431-432) → doble costo y el `after` re-detecta el encabezado del CSV limpio (posible re-clasificación). | analyzer.py:431-433 | Costo y deriva en métricas antes/después. |

---

## 6. Diagnóstico de carga de archivos (`_load_csv`, `detect_file_settings`)

| # | Hallazgo | Ubicación | Impacto |
|---|---|---|---|
| F1 | **BUG CRÍTICO — delimitador detectado nunca se usa**: `detect_file_settings` detecta `;`/`tab`/`|` (L867-873), pero `/api/analyze` y `/api/clean` llaman a `load_dataset` → `_load_csv`, que **siempre usa coma** (`csv.DictReader`, L789). El frontend guarda `_previewSettings.delimiter` (app.js:392) pero **no lo envía** en `/api/analyze` (app.js:348-352). | analyzer.py:771-792, 867-876 · app.js:348, 392 | Un CSV con `;` se analiza como UNA sola columna (todo pegado). Los pasos 1-6 quedan corruptos. |
| F2 | Detección de delimitador **no respeta comillas** (`line.count(",")`): texto con comas dentro de campos infla el conteo y elige coma de forma incorrecta. | analyzer.py:868-873 | Delimitador mal elegido con texto con comas. |
| F3 | `_load_csv` detecta encabezado dividiendo por `,` sin comillas (L783) → inconsistente con `detect_file_settings` que usa el delimitador detectado (L880). | analyzer.py:783 vs 880 | Header mal detectado en archivos con comillas. |
| F4 | Encodings: `_load_csv` solo prueba `utf-8-sig`/`latin-1`; `detect_file_settings` prueba 5. Un CSV cp1252 con caracteres especiales puede fallar en análisis pero mostrarse bien en preview. | analyzer.py:772-775 vs 852-861 | Inconsistencia preview vs análisis. |
| F5 | `_load_xlsx` con `data_only=True` lee **valores cacheados** (no fórmulas): celdas con fórmula sin valor cacheado → None → vacías. | analyzer.py:801 | Celdas calculadas pueden verse vacías. |

---

## 7. Inconsistencias entre módulos (cross-module)

| # | Concepto | analyzer.py | diagnostic.py/domain_rules.py | Consecuencia |
|---|---|---|---|---|
| X1 | Missing | `MISSING_TOKENS` (corto) | `MISSING_TOKENS_EXTENDED` (largo) | Conteos distintos Paso 1 vs Paso 3 |
| X2 | Duplicados | case-sensitive (default) | case-insensitive | Conteos distintos Paso 1 vs Paso 3 |
| X3 | Severidad de outliers | sin severidad | `NUMERIC_DOMAIN` CRITICA | Paso 1 vs Paso 3 no coinciden |
| X4 | Fila de encabezado | offset 2 fijo en limpieza | `header_row_index + 2` | Filas objetivo difieren con metadatos |
| X5 | Booleanos | solo `si/sí/true/1` | tabla completa de sinónimos | `change_type` difiere del diagnóstico |

---

## 8. Especificación de mejoras (algoritmo)

1. **`_to_float` con contexto**: detectar separador por mayoría (si aparecen `1,234` y `45,000` con patrón `\d{1,3}(,\d{3})+` → miles; si `\d+,\d+` con 1 dígito decimal → decimal). Si es ambiguo, no parsear (reportar `invalid_type_count`).
2. **`_detect_type`**: probar `date` antes que `number` cuando el patrón coincide (`20240101`, `01/01/2020`); para "0/1" decidir por dominio (columna con nombre booleano) o reportar como `boolean` si hay 2 valores.
3. **Usar `invalid_type_count` en `accuracy`** y renombrar el score a algo honesto ("exactitud estructural") o computarlo como 1 − (type_errors + outliers)/total_cells.
4. **Unificar tablas de missing** en un solo módulo (un único `MISSING_TOKENS`), con lista base + lista extensible configurable por dataset.
5. **`remove_duplicate_rows`** debe respetar `duplicate_key_columns` + normalización NFKD (idéntico a `_count_duplicate_rows`).
6. **`target_rows` offset dinámico**: usar el `header_row_index` real (pasarlo desde la API), no restar 2 a ciegas.
7. **`change_type` boolean** debe usar `domain_rules.BOOLEAN_SYNONYMS` y devolver `si`/`no` sin perder "activo"/"yes"/"verdadero".
8. **`flag_outliers`**: recibir las filas reales de outliers del perfilado (ya se calculan en `_add_numeric_stats`) y registrarlas en el changelog; no dejar la acción vacía.
9. **`fill_empty`**: respetar `target_rows` como el resto.
10. **IA por lote**: mover `generate_ai_justification` a un solo lote asíncrono (o fallback local si no hay `GEMINI_API_KEY`), unificar con `ai_advisor.py` (Groq) en vez de dos proveedores.
11. **`before/after` sin re-parseo**: derivar `after` re-perfilando las filas mutadas en memoria (no re-serializar a CSV), conservando `headers` y `header_row_index`.
12. **Delimitador real en análisis (F1)**: enviar `delimiter`/`encoding`/`headerRow` desde el frontend (ya están en `_previewSettings`) a `/api/analyze` y `/api/clean`, y que `_load_csv` los acepte como parámetros. **Es el bug de mayor impacto.**

---

## 9. Golden tests para el algoritmo

| Caso | Esperado |
|---|---|
| CSV con `;` (delimitador detectado) | Se analiza con `;`, no 1 sola columna |
| Columna `45,000` / `1,234` | Media correcta sin confundir miles con decimales |
| Fila con encabezado en fila 3 (metadatos) | `target_rows` apuntan a la fila correcta |
| `change_type` boolean con "activo"/"yes"/"verdadero" | → "si" (no "no") |
| Duplicados definidos por key_columns | `remove_duplicate_rows` elimina exactamente esos |
| "pendiente" en columna de estado | NO es missing en Paso 1 ni Paso 3 (después de unificar) |
| Imputación con media | No altera `mean` a 4 decimales de forma inestable |
