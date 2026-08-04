# Mapa y Diagnóstico del Motor de Diagnóstico (28 categorías)

Objetivo: mapa del pipeline de evaluación de columnas, detección de **falsos positivos (FP)** e **inconsistencias**, y una **especificación concreta** para recodificar el algoritmo y las tarjetas del frontend.

Alcance: `data_engine/diagnostic.py` · `data_engine/domain_rules.py` · `frontend/src/nube.js` · `frontend/src/app.js` · `backend/app/main.py`.

---

## 1. Mapa del pipeline (flujo de datos)

```
nube.js:_startManualMode  ──POST /api/diagnose──▶  main.py:130
                                                     │
                          main.py:136 load_dataset (analyzer)
                                                     ▼
                                        diagnostic.diagnose_dataset(headers, rows, header_row_index)
                                                     │
                              por cada columna ──▶ diagnose_column(header, values, total_rows)
                                                     │
             1. match_column_name(header) ──▶ inferred_domain + confidence      (domain_rules.py:229)
             2. _classify_column_by_frequency(values) ──▶ profiler              (FastTextProfiler v3.0)
             3. _check_missing + _check_duplicates (siempre)
             4. SI (no TEXTO_LIBRE y no IDENTIFICADOR y no CONSTANTE)
                  ─▶ 16 chequeos en cadena (fechas, dominio num, texto, tipo, etc.)
                SINO SI (CATEGORICA o BOOLEANA) ─▶ _check_categorical_suspicious   ⚠ código muerto
                                                     │
                    _check_row_duplicates (nivel dataset, pseudo-columna __dataset__)
                                                     ▼
                                      DatasetDiagnostic.to_dict()  ──▶  UI
                                              │
              nube.js:_renderManualView ──▶ tarjetas por columna (issue.category_code)
              nube.js:openDrawerForColumn ──▶ drawer (issues + profiler + chat)
```

---

## 2. Fuentes de falsos positivos (causa raíz + ubicación)

### A. Inferencia de dominio insegura (`domain_rules.py`)

| # | Problema | Ubicación | Ejemplo de FP |
|---|---|---|---|
| A1 | `match_column_name` usa **substring** (`hint in normalized or normalized in hint`) sin límites de palabra. Cualquier header que contenga "id", "num", "tiempo", "nivel", "nota", "registro"... matchea el dominio equivocado. | domain_rules.py:239 | Columna `validacion` → contiene "id" → dominio `id`. Columna `nivel_estudios` → dominio `score` (rango [0,10], tipo number) → *todas* las celdas "bachiller"/"universitario" → `TYPE_VALIDATION`. Columna `numero_telefono` → contiene "numero" → dominio `quantity` → números de teléfono con guiones → `TYPE_VALIDATION`. |
| A2 | `match_column_name` devuelve el **primer match** (orden arbitrario del arreglo), sin puntuar candidatos ni confirmar con los valores reales. | domain_rules.py:237-241 | `barrio` está en `city` y `address`; gana `city` por posición. |
| A3 | `is_valid_calendar_date` asume siempre **día-primero** para `dd/mm/yyyy` y `detect_date_format` devuelve `%d/%m/%Y` para cualquier `dd/mm/yyyy`. Datos en formato US (`mm/dd/yyyy`) se marcan como "fechas imposibles". | domain_rules.py:277, 288-321 | `12/25/2020` → día=12, mes=25 → `DATE_INVALID` (CRITICA). |
| A4 | `is_hidden_missing` incluye tokens que **son valores legítimos** en la práctica. | domain_rules.py:220-226 | "9999" (código/año), "-1" (descuento/índice), **"pendiente"** (estado muy común), " " → `HIDDEN_MISSING`. |

### B. Motor de diagnóstico (`diagnostic.py`)

| # | Problema | Ubicación | Ejemplo de FP |
|---|---|---|---|
| B1 | `_is_id_column` devuelve `True` **solo por el nombre** (match_name) aunque la columna no sea única; combinado con A1, columnas NO-id con headers como "validacion" o "codigo_postal" se tratan como ID. | diagnostic.py:38-49 | `codigo_postal` repetido legítimamente → `DUPLICATE` (ALTA). |
| B2 | Columnas con **cardinalidad ≥95%** (nombres, textos libres, fechas únicas) se clasifican `IDENTIFICADOR` y **se saltan los 16 chequeos**, incluidos los de fecha. Fechas/timestamps únicos → jamás se validan. | diagnostic.py:143-144, 296-299 | Columna `fecha` con timestamps únicos → clasificada `IDENTIFICADOR` → `DATE_INVALID` nunca se evalúa. |
| B3 | `_check_duplicates` marca repetidos en columnas "ID" por cardinalidad aunque repetir sea legítimo (nombres de persona). | diagnostic.py:488-535 | Columna `nombre` 96% única con 2 "Ana" → `DUPLICATE` (ALTA). |
| B4 | **Código muerto**: `elif column_type in ("CATEGORICA","BOOLEANA"): _check_categorical_suspicious(...)` es inalcanzable (esas columnas ya entran por el `if` anterior). Las "categorías sospechosas" del profiler **nunca** salen como tarjeta. | diagnostic.py:301-318 | Columnas categóricas con categorías fuera del conjunto dominante no reportan `CATEGORICAL`. |
| B5 | `_check_boolean_inconsistency` marca como inconsistente una columna booleana **bien formada** con 2 sinónimos canónicos. | diagnostic.py:1079-1117, domain_rules.py:204-209 | Columna `activo` con solo "activo"/"inactivo" → `BOOL_INCONSISTENCY` (aunque es un booleano limpio). |
| B6 | `_check_text_errors` (case): `k != k.title()` se cumple para valores **todos en minúscula** uniformes, no solo para mezclas. | diagnostic.py:672 | Columna de ciudades toda en minúscula ("bogota","bogota") → `TEXT_ERROR`. |
| B7 | `_check_multivalue_cells` marca como multivalor cualquier cadena con ≥3 partes separadas por `/`, `,`, `;`, `|` — **incluidas fechas** `12/03/2020`. | diagnostic.py:962-966, domain_rules.py:331 | Fecha "12/03/2020" → `MULTI_VALUE`. |
| B8 | `_check_mixed_languages` corre sobre columnas numéricas/códigos (heurística de palabras), sin guard de tipo. | diagnostic.py:985-1017 | Códigos que contengan "the"/"el" como subpalabras → `MIXED_LANG`. |
| B9 | `_check_type_validation` dispara `TYPE_VALIDATION` con dominio mal inferido (A1) sin confirmar el dominio con los valores. | diagnostic.py:793-830 | `nivel_estudios` → todos los valores "fallan" tipo number. |
| B10 | `_check_unit_inconsistency` detecta "unidades" cuando un <30% de valores tiene letras, sin distinguir unidades reales. | diagnostic.py:833-864 | Mezcla "10","20","treinta" → `UNIT_ERROR`. |

---

## 3. Inconsistencias de semántica (conteo, porcentaje, severidad)

| # | Inconsistencia | Ubicación | Impacto |
|---|---|---|---|
| C1 | **`count` no significa lo mismo entre chequeos**: unas veces son filas afectadas, otras **todas las filas** (`_check_categorical_inconsistency` y `_check_boolean_inconsistency` usan `len(non_empty_indices)`), otras son ocurrencias sumadas. La tarjeta dice "N filas afectadas" y el número es incorrecto/inflado. | diagnostic.py:753, 1109 | Confusión y sobre-estimación visual. |
| C2 | **Severidad duplicada y divergente**: el backend calcula `severity` (CRITICA/ALTA/MEDIA/BAJA) pero el frontend **la ignora** y recalcula su propio mapa en `_getSeverity(category_code)` (nube.js:350) con códigos inexistentes (`OUT_OF_RANGE`, `TYPE_ERROR`). `DATE_INVALID` (CRITICA) se muestra como "baja"; `SCIENTIFIC` como "media". | nube.js:204, 350-356 | Semáforos incorrectos en las tarjetas. |
| C3 | **`DUPLICATE` doble**: una columna ID con repetidos produce `DUPLICATE` a nivel columna y además la fila duplicada entra en `DUPLICATE` a nivel dataset (`__dataset__`). El resumen `total_issues` los suma → **doble conteo** en el summary. | diagnostic.py:363-374, 425, 523 | Números globales inflados. |
| C4 | **Veredicto y porcentaje**: el veredicto de columna usa `len(issues)` (grupos), el summary usa `issue.count` (filas) → "problemas" significa cosas distintas según nivel. | diagnostic.py:337, 387 | Lectura inconsistente del reporte. |
| C5 | ~~Códigos de categoría inconsistentes entre docstring, código y UI~~ | README.md, diagnostic.py, nube.js | RESUELTO DG-12: tabla README, docstring y _SIGNAL_MAP alineados |
| C6 | **Fila "fila afectada" = índice interno vs Excel**: el offset se aplica en `_shift_issue_rows`, pero `_check_categorical_inconsistency` no desplaza `affected_rows` (usa `[i for i,_ in non_empty_indices]` con índice 0-based) → filas desplazadas solo en algunos chequeos. | diagnostic.py:268-280, 758 | El analista aterriza en la fila equivocada. |
| C7 | **Escapado HTML de nombres de columna** en atributos: `_escHtml` no escapa comillas dentro de atributos `data-column="..."`. | nube.js:36-41, 175-201 | Headers con `"` rompen el HTML / riesgo XSS. |
| C8 | **Las acciones seleccionadas no hacen nada**: `_confirmManualSelection` genera `kind:'review_issue'` y `apply_cleaning_actions` **no tiene rama** para ese `kind` (analyzer.py:146-414). El analista "selecciona problemas" en las tarjetas y se aplican 0 cambios. | nube.js:323-342, analyzer.py:132 | Funcionalidad muerta en el paso 3→4. |

---

## 4. Especificación para recodificar el algoritmo (evitar FP)

### 4.1 Fase 0 — Normalización y guardas globales
- `MIN_ROWS = 5`, `MIN_NON_EMPTY = 5`: los chequeos no corren sobre muestras mínimas (evita FP en datasets diminutos).
- Unificar **`count` = nº de filas distintas afectadas** (set de índices) en TODOS los chequeos; `percentage = count / total_rows * 100`.
- Clasificación de fecha **antes** que la clasificación por frecuencia: si `_looks_like_date` (analyzer.py:967) cubre ≥75% → tipo `date` y los chequeos de fecha corren **siempre**, incluso con cardinalidad alta.

### 4.2 Fase 1 — Inferencia de dominio con confirmación por valores (reemplazar `match_column_name`)
```
1. Tokenizar el header (split por _/espacio/-).
2. Generar CANDIDATOS de dominio por tokens (match de palabra completa, sin substring),
   cada uno con score = nº de hints token-match + peso.
3. Descartar candidatos cuyo tipo esperado NO se confirme con los valores reales:
   - expected_type number → ≥90% parsea float
   - expected_type date → ≥90% cumple algún formato de fecha
   - pattern (email) → ≥90% cumple el regex
   - text → confirmación débil (solo se exige para checks de dominio)
4. Quedarse con el candidato de mayor score y confidence = f(score, valor_confirmación).
5. confidence < umbral (0.7) → DOMINIO = null → se omiten chequeos dependientes de dominio
   (TYPE_VALIDATION, NUMERIC_DOMAIN, UNIT_ERROR, CATEGORICAL gender/country).
```
Esto elimina A1, A2, B9.

### 4.3 Fase 2 — Clasificación de columna (FastTextProfiler) revisada
- Añadir tipo `DATE` (de 4.1) y `NUMERIC` explícito (≥90% parseable) para que las columnas numéricas corran NUMERIC/OUTLIER/SCIENTIFIC y no se clasifiquen como CATEGORICA accidental.
- `_is_id_column`: exigir **nombre match AND (cardinalidad ≥95% O patrón de ID)**; nunca por nombre solo (elimina B1, B3). Además, excluir dominios conocidos (ciudad, genero, pais) de ser "ID".
- Eliminar la rama muerta: `_check_categorical_suspicious` debe llamarse para CATEGORICA/BOOLEANA **en lugar de** los 16 chequeos de texto (elimina B4).

### 4.4 Fase 3 — Corrección puntual de cada chequeo
- **HIDDEN_MISSING**: remover `9999`, `-1`, `pendiente`, `" "` de `MISSING_TOKENS_EXTENDED`; moverlos a una lista opcional configurable (elimina A4).
- **BOOL_INCONSISTENCY**: disparar solo si el nº de representaciones distintas > nº de significados (True/False), i.e., >2 etiquetas distintas O la misma etiqueta mapea a ambos significados (elimina B5).
- **TEXT_ERROR (case)**: solo si el mismo valor normalizado aparece en ≥2 grafías distintas (e.g., "bogota" y "Bogota"); un patrón uniforme no se marca (elimina B6).
- **MULTI_VALUE**: excluir si el valor parsea como fecha o número con separadores de miles; exigir ≥2 separadores distintos o tokens no numéricos (elimina B7).
- **MIXED_LANG / UNIT_ERROR / SCIENTIFIC**: añadir guard de tipo (solo texto libre; no numéricas/códigos) y umbral mínimo de valores (elimina B8, B10).
- **DATE**: `is_valid_calendar_date` debe usar el formato detectado (dd/mm vs mm/dd) en lugar de asumir día-primero (elimina A3).
- **DUPLICATE**: a nivel columna-ID reportar solo grupos; en `summary.total_issues`, deduplicar filas ya contadas por `__dataset__` (elimina C3).

### 4.5 Fase 4 — Confianza por hallazgo (anti-FP de percepción)
Cada `IssueGroup` suma `confidence` (0-100) y `signal`:
- `signal = "CONFIRMADO"` si cumple guardas estrictas (cobertura, mínimos, no-ambigüedad).
- `signal = "A_REVISAR"` si es sugestivo pero no concluyente (e.g., posible dominio erróneo).
El frontend debe mostrar ambas categorías separadas (ver sección 5) y **nunca** como algo definitivo cuando es `A_REVISAR`.

---

## 5. Especificación para recodificar las tarjetas (frontend)

### 5.1 Contrato de datos (usar el del backend, no recomputar)
- Mostrar `issue.category` (etiqueta humana) como título y `category_code` como badge técnico.
- **Severidad = `issue.severity` del backend** (eliminar `_getSeverity` de nube.js — C2). Mapeo CSS: CRITICA→`alta`/rojo, ALTA→`alta`, MEDIA→`media`, BAJA→`baja`.
- `count` = filas afectadas (semántica unificada de 4.1); `percentage` relativo a total.
- Añadir badge de `confidence`/`signal` (CONFIRMADO vs A_REVISAR) — 4.5.

### 5.2 Estructura de la tarjeta por columna
```
[Columna] [dominio] [n filas | m columnas] [Inspeccionar]
┌──────────────────────────────────────────────┐
│ [CRITICA] Fechas imposibles  · 3 filas (0.5%) │   ← category + severity + count
│ Detalle: valores con día/mes inválidos        │   ← description
│ Confirmado (confianza 95)  [Marcar revisado]  │   ← signal + acción del analista
│ Ejemplos: Fila 12: 2020-02-30                │
│ Filas: 12, 14, 31                            │
└──────────────────────────────────────────────┘
```
- Checkbox "Marcar revisado" guarda la decisión del analista (sin desmarcar el problema).
- Botones globales: "Aceptar todas las confirmadas" / "Omitir todas las A_REVISAR".

### 5.3 Conectar las tarjetas con la limpieza (eliminar C8)
- `review_issue` debe tener **rama real** en `apply_cleaning_actions`: registrar en el `changelog` como `revision_manual` (columna, categoría, filas, decisión) **sin modificar datos**, y re-perfilar `after` igual al `before`. El "problema" queda documentado y trazable.
- Alternativa (si se quiere acción real): las tarjetas proponen acciones concretas (`fill_missing`, `standardize_text`, `flag_outliers`...) derivadas del chequeo, y el checkbox confirma esa acción.

### 5.4 Drawer
- Usar la misma severidad/signal/confianza del backend (hoy duplica lógica en nube.js:555-563).
- Escapar correctamente headers en atributos (reemplazar `_escHtml` por `escapeAttr` que escapa `"`, `'`, `<`, `>`, `&`) — C7.

---

## 6. Plan de implementación (propuesta)

| Fase | Trabajo | Archivos | Riesgo |
|---|---|---|---|
| 1 | Normalización + guardas + semántica `count` | `diagnostic.py` | Bajo |
| 2 | Inferencia de dominio por tokens + confirmación por valores | `domain_rules.py` (+ tests) | Medio (núcleo) |
| 3 | Clasificación revisada (DATE/NUMERIC, `_is_id_column`, rama muerta) | `diagnostic.py` | Medio |
| 4 | Corrección puntual de 8 chequeos (4.4) | `diagnostic.py` + `domain_rules.py` | Medio |
| 5 | `confidence`/`signal` por hallazgo | `diagnostic.py` | Bajo |
| 6 | Tarjetas: severidad backend + signal + escapeAttr | `nube.js` + CSS | Bajo |
| 7 | `review_issue` funcional en limpieza | `analyzer.py` | Bajo |
| 8 | Golden tests (dataset con FP conocidos) para regresión | `tests/` | — |

**Orden recomendado para arrancar**: fases 1 → 4 (quita el 80% de los FP) y fase 7 (vuelve funcionales las tarjetas).

---

## 7. Ejemplos de regresión para el harness (golden tests)

| Dataset de prueba | Resultado esperado |
|---|---|
| `estado` con "pendiente"/"activo" | SIN `HIDDEN_MISSING` |
| `nivel_estudios` (bachiller/universitario) | SIN `TYPE_VALIDATION` (dominio no confirmado) |
| `validacion` (si/no) | SIN `DUPLICATE` (no es ID) |
| `fecha` única (`2020-01-01`... ) | CORRE `DATE_INVALID`/`DATE_FORMAT` (no se salta por cardinalidad) |
| `activo` solo "activo"/"inactivo" | SIN `BOOL_INCONSISTENCY` |
| `ciudad` minúscula uniforme | SIN `TEXT_ERROR` |
| `12/03/2020` (fecha) | SIN `MULTI_VALUE` |
| booleano mezclado si/sí/true | `BOOL_INCONSISTENCY` CONFIRMADO |
| edad 450 | `NUMERIC_DOMAIN` CRITICA CONFIRMADO |
| columna con "bogota" y "Bogotá" | `CATEGORICAL` A_REVISAR (sinónimo/case) |
