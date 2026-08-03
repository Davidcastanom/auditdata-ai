# Plan de Refactorización del Motor — AuditData AI (Trazabilidad)

**Fecha de creación:** 2026-08-03 · **Autor:** AuditData AI · **Estado:** APROBADO (inicio)

Este plan consolida **todo lo diagnosticado y recomendado** en sesiones previas:
- `docs/DIAGNOSTICO_MEJORA_MOTOR_28CATEGORIAS.md` (motor 28 categorías + tarjetas)
- `docs/DIAGNOSTICO_ALGORITMO_ANALISIS_LIMPIEZA.md` (algoritmo núcleo: perfilado, scores, duplicados, limpieza, carga)
- Pendientes operativos de trabajos anteriores (migraciones, env vars, historial en la nube)

**Principio rector:** el motor es el *cerebro* del proyecto. Cualquier decisión mal tomada afecta el resultado final (reportes PDF, puntajes, limpieza). Por eso: **tests primero, API estable, despliegue por fases, y cada cambio trazable por ID.**

---

## 1. Principios y reglas de trazabilidad

| Regla | Descripción |
|---|---|
| R1 | Cada hallazgo tiene un **ID permanente** (AP/DM/DG/DU/CL/FE/UI/TS). Se referencia en commits: `fix(AP-01): ...` |
| R2 | **Test-first**: ningún fix se acepta sin su test de regresión en `tests/` (golden datasets). |
| R3 | **No romper contrato de API**: los JSON de `/api/analyze`, `/api/diagnose`, `/api/clean` conservan sus claves; los cambios se agregan sin quitar (p. ej. `signal`, `confidence`). |
| R4 | **Compatibilidad de migraciones**: `001-004` ya aplicadas en Supabase; nuevas migraciones = `005+` y se aplican manualmente por el usuario (como las anteriores). |
| R5 | Cada fase cierra con: tests verdes + commit + actualización de la **tabla maestra** (estado → `HECHO`). |
| R6 | El estado se actualiza en este mismo documento (columna "Estado") — es el registro de trazabilidad. |

**Estados:** `PENDIENTE` · `EN PROGRESO` · `EN PRUEBAS` · `HECHO` · `VERIFICADO PROD`

---

## 2. Inventario consolidado de hallazgos (registro maestro)

| ID | Hallazgo | Origen | Fase | Estado | Fecha obj. |
|---|---|---|---|---|---|
| FE-01 | Delimitador detectado nunca se usa en analyze/clean (CSV `;`→1 columna) | Algo. F1 | F1 | HECHO | 2026-08-07 |
| FE-02 | Detección de delimitador sin respetar comillas | Algo. F2 | F1 | HECHO | 2026-08-07 |
| FE-03 | Detección de header inconsistente entre preview y análisis | Algo. F3 | F1 | HECHO | 2026-08-10 |
| FE-04 | Encodings distintos entre preview y análisis | Algo. F4 | F1 | HECHO | 2026-08-10 |
| FE-05 | XLSX `data_only=True` → celdas calculadas vacías | Algo. F5 | F1 | PENDIENTE | 2026-08-10 |
| AP-01 | `_to_float` confunde miles con decimales (45,000 → 45.0) | Algo. P1 | F2 | HECHO | 2026-08-13 |
| AP-02 | `_detect_type`: number antes que date (20240101) | Algo. P2 | F2 | HECHO | 2026-08-13 |
| AP-03 | Umbral 75% rígido + `invalid_type_count` sin uso | Algo. P3/S1 | F2 | HECHO | 2026-08-14 |
| AP-04 | Unificar tablas de missing (analyzer vs domain_rules) | Algo. P4 / X1 | F3 | HECHO | 2026-08-17 |
| AP-05 | Outliers con IQR=0 se omiten sin aviso | Algo. P5 | F2 | HECHO | 2026-08-14 |
| AP-06 | `format_groups`/`format_issues` sin semántica de filas | Algo. P6 | F2 | HECHO | 2026-08-14 |
| AP-07 | Scores: accuracy=outliers, overall no ponderado, columnas vacías | Algo. S1-S4 | F2 | HECHO | 2026-08-14 |
| DU-01 | Duplicados: definición distinta entre analyzer y diagnostic | Algo. X2/D1 | F3 | PENDIENTE | 2026-08-17 |
| DU-02 | `remove_duplicate_rows` ignora `duplicate_key_columns` + NFKD | Algo. D2/D3 | F3 | PENDIENTE | 2026-08-18 |
| CL-01 | `change_type` boolean no usa sinónimos ("activo"→"no") | Algo. C1 | F3 | PENDIENTE | 2026-08-18 |
| CL-02 | `fill_empty` ignora `target_rows` | Algo. C2 | F3 | PENDIENTE | 2026-08-18 |
| CL-03 | `flag_outliers` no marca filas reales (cosmético) | Algo. C3 | F3 | PENDIENTE | 2026-08-19 |
| CL-04 | `review_issue` sin rama en `apply_cleaning_actions` (tarjetas muertas) | Motor C8 / Algo. C4 | F6 | PENDIENTE | 2026-09-01 |
| CL-05 | `target_rows - 2` hardcodeado (header_row_index real) | Algo. C5 | F3 | PENDIENTE | 2026-08-19 |
| CL-06 | Consolidar impute_missing/fill_missing/fill_empty | Algo. C6 | F3 | PENDIENTE | 2026-08-19 |
| CL-07 | IA por acción (Gemini serial, 2 proveedores) → lote Groq unificado | Algo. C7 | F5 | PENDIENTE | 2026-08-27 |
| CL-08 | `after` se re-parsea desde CSV → re-perfilar en memoria | Algo. C8 | F3 | PENDIENTE | 2026-08-19 |
| DM-01 | `match_column_name` substring → tokens + confirmación por valores | Motor A1/A2/B9 | F4 | PENDIENTE | 2026-08-24 |
| DM-02 | Fechas: asumir formato detectado (dd/mm vs mm/dd) | Motor A3 | F4 | PENDIENTE | 2026-08-24 |
| DM-03 | `MISSING_TOKENS_EXTENDED` depurado ("9999","-1","pendiente"," ") | Motor A4 | F4 | HECHO | 2026-08-24 |
| DG-01 | `_is_id_column` solo por nombre → requiere nombre+cardinalidad | Motor B1/B3 | F5 | PENDIENTE | 2026-08-27 |
| DG-02 | Fechas únicas clasificadas IDENTIFICADOR → tipo DATE/NUMERIC | Motor B2 | F5 | PENDIENTE | 2026-08-27 |
| DG-03 | Rama muerta `_check_categorical_suspicious` (elif inalcanzable) | Motor B4 | F5 | PENDIENTE | 2026-08-27 |
| DG-04 | `BOOL_INCONSISTENCY` en booleanos bien formados | Motor B5 | F5 | PENDIENTE | 2026-08-27 |
| DG-05 | `TEXT_ERROR` en texto uniforme (solo grafías mixtas) | Motor B6 | F5 | PENDIENTE | 2026-08-27 |
| DG-06 | `MULTI_VALUE` marca fechas (12/03/2020) | Motor B7 | F5 | PENDIENTE | 2026-08-27 |
| DG-07 | `MIXED_LANG`/`UNIT_ERROR`/`SCIENTIFIC` sin guard de tipo | Motor B8/B10 | F5 | PENDIENTE | 2026-08-27 |
| DG-08 | Semántica unificada de `count` = filas afectadas | Motor C1 | F5 | PENDIENTE | 2026-08-28 |
| DG-09 | Severidad única desde backend (CRITICA/ALTA/MEDIA/BAJA) | Motor C2 | F5 | PENDIENTE | 2026-08-28 |
| DG-10 | Deduplicar conteo DUPLICATE (columna + dataset) | Motor C3 | F5 | PENDIENTE | 2026-08-28 |
| DG-11 | `confidence`/`signal` (CONFIRMADO vs A_REVISAR) por hallazgo | Motor 4.5 | F5 | PENDIENTE | 2026-08-28 |
| DG-12 | Alinear nombres/códigos de categorías (docstring vs código vs UI) | Motor C5 | F5 | PENDIENTE | 2026-08-28 |
| UI-01 | Tarjetas con severidad del backend + badge signal | Motor C2/C4 | F6 | PENDIENTE | 2026-08-31 |
| UI-02 | `escapeAttr` en headers (XSS/HTML roto) | Motor C7 | F6 | PENDIENTE | 2026-08-31 |
| UI-03 | Drawer unificado (misma severidad/signal/confianza) | Motor 5.4 | F6 | PENDIENTE | 2026-08-31 |
| UI-04 | "Marcar revisado" + aceptar confirmadas/omitir a_revisar | Motor 5.2 | F6 | PENDIENTE | 2026-08-31 |
| TS-01 | Golden tests motor 28 categorías (9 casos) | Doc 1 §7 | F0 | HECHO | 2026-08-07 |
| TS-02 | Golden tests algoritmo (8 casos) | Doc 2 §9 | F0 | HECHO | 2026-08-07 |
| TS-03 | CI GitHub Actions (pytest en cada PR) | Doc 2 §6 | F0 | HECHO | 2026-08-07 |
| OP-01 | Aplicar migración 004 en Supabase (DELETE) | Trabajo previo | F0 | PENDIENTE | 2026-08-05 |
| OP-02 | Configurar env vars métricas en Render | Trabajo previo | F0 | PENDIENTE | 2026-08-05 |
| OP-03 | Verificar botón X historial en producción | Trabajo previo | F0 | PENDIENTE | 2026-08-05 |

---

## 3. Fases (cronograma 2026-08-03 → 2026-09-05)

### F0 — Cimientos y pendientes operativos (2026-08-03 → 2026-08-07)
- **Objetivo:** blindar regresión y saldar pendientes de producción.
- **Alcance:** TS-01, TS-02, TS-03, OP-01, OP-02, OP-03.
- **Tareas:**
  1. Congelar comportamiento actual: correr suite completa y registrar baseline (conteo de tests, outputs de `/api/analyze`, `/api/diagnose`, `/api/clean`).
  2. Construir harness de golden tests con los 9+8 casos documentados (esperados explícitos).
  3. Configurar GitHub Actions: `python -m pytest tests/ -v` en cada push/PR.
  4. Recordar al usuario aplicar `004_delete_history.sql` en Supabase; verificar botón X en prod.
  5. Configurar `METRICS_SECRET`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `MAKE_WEBHOOK_URL` en Render.
- **Aceptación:** suite 100% verde + CI activo + métricas visibles en panel admin + historial eliminable en prod.
- **Riesgo:** bajo.

### F1 — Carga de archivos (2026-08-06 → 2026-08-10) — **bug de mayor impacto**
- **Objetivo:** que un CSV se analice con el delimitador/encoding/header que el preview detectó.
- **Alcance:** FE-01, FE-02, FE-03, FE-04, FE-05.
- **Tareas:**
  1. `_load_csv(payload, delimiter, encoding)` acepta parámetros; `load_dataset` los recibe.
  2. Frontend envía `_previewSettings` (delimiter/encoding/headerRow) en `/api/analyze` y `/api/clean` (app.js:348-352).
  3. Parser de delimitador con respeto de comillas (regex estado de cita).
  4. Detección de header única y compartida (un solo `_find_header_row` para CSV y XLSX).
  5. Mismo orden de encodings en ambos caminos; XLSX sin `data_only` cuando no haya fórmulas.
- **Aceptación:** CSV `;`/tab/pipe analizado correctamente; texto con comas no rompe; golden tests FE.
- **Dependencias:** F0 (TS-02).
- **Riesgo:** medio (toca contrato interno de `load_dataset`), mitigado con R3.

### F2 — Perfilado y scores (2026-08-11 → 2026-08-14)
- **Objetivo:** estadísticas numéricas y puntajes honestos y sin distorsión.
- **Alcance:** AP-01, AP-02, AP-03, AP-05, AP-06, AP-07.
- **Tareas:**
  1. `_to_float` con detección de separador por mayoría (miles vs decimal); ambigüedad → no parsear + contabilizar.
  2. `_detect_type`: probar `date` antes que `number`; "0/1" resuelto por dominio o `boolean`.
  3. Umbral configurable (default 70%) y `invalid_type_count` incluido en `accuracy`.
  4. `IQR=0` → `outlier_analysis_skipped=True` (transparencia).
  5. `format_issues` contando filas afectadas (no variantes).
  6. `overall` = media ponderada (pesos configurables) y manejo de columnas 100% vacías.
- **Aceptación:** golden tests P; los números del PDF cambian solo donde había errores.
- **Riesgo:** medio (cambia scores existentes → actualizar golden tests de caracterización).

### F3 — Duplicados y limpieza (2026-08-14 → 2026-08-19)
- **Objetivo:** definiciones coherentes y acciones que respetan la selección del analista.
- **Alcance:** AP-04, DU-01, DU-02, CL-01, CL-02, CL-03, CL-05, CL-06, CL-08.
- **Tareas:**
  1. Tabla única de missing en un módulo compartido (analyzer + diagnostic usan la misma).
  2. Duplicados: misma firma (NFKD + lower) en detección y en `remove_duplicate_rows`, respetando `key_columns`.
  3. `change_type` boolean con `BOOLEAN_SYNONYMS`.
  4. `fill_empty` respeta `target_rows`; consolidar impute/fill en una acción con `method` explícito.
  5. `flag_outliers` recibe filas reales del perfilado y las registra en changelog.
  6. Offset dinámico: `header_row_index` real en vez de `-2`.
  7. `after` re-perfilado en memoria (sin re-parsear CSV).
- **Aceptación:** golden tests DU/CL; bitácora muestra filas correctas y exactas.
- **Riesgo:** alto (toca `apply_cleaning_actions` y la bitácora) — mitigado con R3 + tests.

### F4 — Inferencia de dominio (2026-08-19 → 2026-08-24) — **elimina la mayoría de FP**
- **Objetivo:** solo se aplican chequeos de dominio si el dominio está confirmado con los valores reales.
- **Alcance:** DM-01, DM-02, DM-03.
- **Tareas:**
  1. `match_column_name` por tokens con score de candidatos; confirmación por valores (≥90% parseable para number/date, regex para email).
  2. `confidence < 0.7` → dominio `null` → se omiten TYPE_VALIDATION/NUMERIC_DOMAIN/UNIT/CATEGORICAL gender-country.
  3. `is_valid_calendar_date` con el formato detectado (no asumir día-primero).
  4. Depurar `MISSING_TOKENS_EXTENDED`: quitar `9999`, `-1`, `pendiente`, `" "`; lista opcional configurable por dataset.
- **Aceptación:** casos `nivel_estudios`, `validacion`, `12/25/2020` sin FP; golden tests DM.
- **Riesgo:** alto (núcleo) — hacer con mutaciones pequeñas y cada fix por separado.

### F5 — Clasificación y chequeos (2026-08-24 → 2026-08-28)
- **Objetivo:** chequeos exactos, sin ramas muertas y con semántica de salida unificada.
- **Alcance:** DG-01..DG-12, CL-07.
- **Tareas:**
  1. `_is_id_column`: nombre AND (cardinalidad ≥95% O patrón ID); excluir dominios ciudad/género/pais.
  2. Tipos DATE/NUMERIC explícitos en el profiler (las fechas únicas sí se validan).
  3. Activar `_check_categorical_suspicious` para CATEGORICA/BOOLEANA (en vez de los 16 chequeos de texto).
  4. Correcciones puntuales: BOOL (solo mezclas reales), TEXT (solo grafías mixtas), MULTI_VALUE (excluir fechas/números), guard de tipo para MIXED_LANG/UNIT/SCIENTIFIC.
  5. `count` = filas distintas afectadas en todos; `percentage` vs total.
  6. Severidad única del backend; dedup de DUPLICATE; `confidence`/`signal`.
  7. Alinear códigos de categoría en docstring/código/UI.
  8. IA: lote asíncrono con Groq (un solo proveedor).
- **Aceptación:** golden tests DG; sin FP en los 9 casos documentados; veredicto consistente.
- **Riesgo:** alto (cambia el JSON de diagnóstico: se agregan `signal`/`confidence`, se conserva el resto).

### F6 — Frontend: tarjetas funcionales (2026-08-28 → 2026-09-02)
- **Objetivo:** las tarjetas reflejan el diagnóstico real y sus decisiones sí se ejecutan.
- **Alcance:** UI-01, UI-02, UI-03, UI-04, CL-04.
- **Tareas:**
  1. Tarjetas usan `category` (etiqueta) + `severity` backend + `signal` badge.
  2. `escapeAttr` para headers en atributos.
  3. Drawer con la misma fuente de severidad/confianza.
  4. "Marcar revisado", "Aceptar confirmadas", "Omitir A_REVISAR".
  5. `review_issue` funcional en `apply_cleaning_actions`: registra `revision_manual` en changelog (sin modificar datos), antes=después.
- **Aceptación:** smoke E2E del wizard con dataset real; seleccionar un problema queda documentado en la bitácora.
- **Riesgo:** medio.

### F7 — Integración, validación y despliegue (2026-09-03 → 2026-09-05)
- **Objetivo:** verificar en producción sin regresiones.
- **Tareas:**
  1. Suite completa + golden tests verdes.
  2. Validación manual E2E en local con 3 datasets reales (CSV `;`, CSV `,`, XLSX).
  3. Comparar PDF antes/después para confirmar que los cambios son coherentes.
  4. Commit final + push; auto-deploy Render.
  5. Verificación en prod: `/api/analyze`, `/api/diagnose`, `/api/clean`, panel admin, historial.
  6. Marcar en la tabla maestra los IDs como `VERIFICADO PROD`.
- **Aceptación:** checklist de verificación en prod completado.
- **Riesgo:** bajo (todo probado antes).

---

## 4. Matriz de riesgos

| Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|
| Cambios en scores alteran PDFs y tests de caracterización | Media | Alto | Golden tests + comparar PDF antes/después (F7) |
| Refactor de `load_dataset` rompe XLSX (regresión del fix c9965ae) | Baja | Alto | Mantener tests de XLSX existentes + golden FE |
| API contract roto para el frontend | Baja | Alto | Regla R3 (solo agregar claves) |
| Eliminar FP en una categoría introduce FN (deja de detectar) | Media | Medio | `signal` A_REVISAR en vez de omitir; revisión manual de casos |
| Falta de tiempo por fase → fase incompleta | Media | Medio | Cortar alcance por fase, no por día; cada fix es reversible |
| Regresión en duplicados con key_columns | Media | Alto | Tests dedicados DU-02 |

---

## 5. Cronograma resumido

| Fase | Periodo | Foco | IDs |
|---|---|---|---|
| F0 | 03-07 ago | Cimientos + pendientes prod | TS-01/02/03, OP-01/02/03 |
| F1 | 06-10 ago | Carga de archivos (delimitador) | FE-01..05 |
| F2 | 11-14 ago | Perfilado y scores | AP-01..07 |
| F3 | 14-19 ago | Duplicados y limpieza | AP-04, DU-01/02, CL-01/02/03/05/06/08 |
| F4 | 19-24 ago | Inferencia de dominio | DM-01/02/03 |
| F5 | 24-28 ago | Clasificación y chequeos | DG-01..12, CL-07 |
| F6 | 28 ago-02 sep | Tarjetas funcionales | UI-01..04, CL-04 |
| F7 | 03-05 sep | Validación y deploy | Todos |

**Próxima sesión (sugerida):** ejecutar **F0** — congelar baseline, escribir los golden tests y activar CI. Así el resto de fases quedan blindadas.

---

## 6. Cómo leer este plan

1. Al terminar cada tarea: correr tests, hacer commit con `ID` en el mensaje, y actualizar la columna **Estado** de la tabla maestra.
2. Las fechas son objetivo; si una fase se retrasa, ajustar solo esa fase (no el alcance) y anotar el nuevo estado.
3. Los entregables de cada fase son los golden tests verdes + commit + tabla actualizada.
