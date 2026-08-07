# Mejora Copiloto IA Conversacional — AuditData AI (Trazabilidad)

**Fecha de creación:** 2026-08-07 · **Autor:** AuditData AI · **Estado:** EJECUTADO (commits 0-6 en `main`)

## 1. Por qué se hizo esta mejora

El copiloto de IA (chat por columna en el Side Drawer) presentaba fallas reales reproducidas en local y en producción:

- **Error 413 de Groq reproducido.** Preguntar por una columna de texto largo disparaba:
  `Request too large for model llama-3.1-8b-instant ... tokens per minute (TPM): Limit 6000, Requested 26384`.
  La causa raíz: el contexto del chat incluía `sorted_data[:100]` **sin truncar valores** (hasta 2.000+ caracteres por fila), inflando el prompt a ~26K tokens cuando el tier free permite 6.000 TPM.
- **Sin tolerancia a fallos.** No había retry ni fallback ante 413/429 (rate limit): cualquier pico de tokens rompía la conversación.
- **Recálculo duplicado por turno.** Cada pregunta re-decodificaba el archivo, re-ejecutaba `load_dataset` + `diagnose_dataset` + `compute_column_context`, duplicando cómputo de frecuencias y estadísticas que el motor **ya calcula** en el perfilado (`analyze_dataset` → `value_distribution` con `%`, stats, outliers).
- **Contexto inconsistente entre turnos.** El primer mensaje enviaba contexto completo (`full=True`) y los siguientes uno reducido (`full=False`). El modelo "olvidaba" entre preguntas → no se sentía conversacional.
- **Frontend opaco ante errores.** El backend devuelve `{"status": "error", ...}` pero el frontend pintaba ese texto como si fuera una respuesta normal de la IA (app.js ~1007 y nube.js ~676).

## 2. Cuál era la intención

El objetivo no era solo arreglar el crash, sino que el copiloto **pareciera que entiende** lo que escribe el analista y respondiera según el contexto real de la columna **dentro del dataset completo**, con una conversación estable, barata en tokens y mantenible:

1. **Estable:** sin 413/429, con retry y fallback de contexto reducido.
2. **Barata en tokens:** contexto transversal compacto construido UNA vez a partir de las frecuencias y estadísticas que el motor ya calcula (top-N, valores truncados), reutilizado en toda la conversación.
3. **Conversacional:** la misma base de contexto en todos los turnos + detección de intención por keywords (valores / duplicados / limpieza / estadísticas / dominio) que ajusta el prompt a la pregunta.
4. **Rápida:** cache en memoria por hash del archivo → el 2º mensaje no recalcula nada.
5. **Honesta:** el frontend distingue `status: success | error | no_api_key` y muestra los errores como errores, sin disfrazarlos de respuesta.
6. **Sin código muerto:** nada se duplica; las funciones se modifican in situ o se eliminan si quedan sin uso.

## 3. Plan de ejecución (commits atómicos, test-first)

| Commit | ID | Alcance |
|---|---|---|
| 0 | `chore(ui): fix variables CSS rotas del selector de duplicados (Etapa 03)` — `e026cfd` | Aísla cambios pendientes en working tree (app.js + design-system.css) |
| 1 | `fix(ai CHAT-01): podar y truncar contexto del chat - mata el 413` — `02cc306` | `CONTEXT_SAMPLE_ROWS=15`, `CONTEXT_FREQ_ROWS=15`, `CONTEXT_VALUE_LEN=100`; sorted_data truncado → ~1.5-2K tokens |
| 2 | `fix(ai CHAT-02): retry 413/429 con backoff y fallback de contexto reducido` — `bbb6a69` | Reintentos 0.5s/2s + reintento con `full=False` |
| 3 | `feat(ui CHAT-03): frontend honesto con status:error del copiloto` — `1e1048b` | Burbuja de error visible; no contamina el historial |
| 4 | `feat(ai CHAT-04): contexto transversal estable + prompt conversacional + cache` — `c0df59c` | Cache por hash; contexto idéntico por turno; intención por keywords; bloque OTRAS COLUMNAS |
| 5 | `refactor(ai CHAT-05): unificar deep-analysis y eliminar compute_column_context` | `compute_column_context` → `build_column_context` (fuente única); `analyze_column_deep` recibe el mismo `context`; deep-analysis reutiliza la sesión cacheada |
| 6 | `feat(ai CHAT-06): honestidad ante columnas inexistentes + detección de errores de escritura` | Columna inexistente → `status: error` real sin llamar a Groq (antes inventaba diagnóstico); `_detect_typos` detecta typos en valores de texto (difflib, sin formato/prefijos) → bloque `POSIBLES ERRORES DE ESCRITURA` en chat y deep-analysis |

### Verificación al cierre

- Suite Python: **257 passed** (248 + 9 nuevos de CHAT-06). E2E Playwright: **41 passed**. `ruff --select F,E9`: limpio.
- Prueba real contra Groq (columna `nombre` con `juan`/`juaan`/`Juan`): el chat detecta `"juaan"` como typo de `"juan"`; el deep-analysis cita filas exactas (18, 19, 20) con el valor mal escrito; columna inexistente responde en **0.0s** `La columna 'no_existe' no existe en el dataset. Columnas disponibles: ...` sin gastar tokens ni inventar.
- Cache validado en la misma prueba: el 2º mensaje del mismo archivo pasó de 0.3s a ~0.0s (sin recálculo).

## 4. Calificación ANTES vs DESPUÉS

Evaluación honesta con base en el 413 reproducido y el código existente:

| Dimensión | ANTES | DESPUÉS |
|---|---|---|
| Estabilidad | 3/10 | 9/10 |
| Costo de tokens | 2/10 | 9/10 |
| Conversacionalidad | 4/10 | 8/10 |
| Contexto real del motor | 6/10 | 9/10 |
| Manejo de errores UX | 3/10 | 9/10 |
| Rendimiento por turno | 5/10 | 9/10 |
| Mantenibilidad | 6/10 | 9/10 |
| Validación (lo que existe) y typos | 4/10 | 9/10 |
| **Promedio ponderado** | **4.1/10** | **8.9/10** |

**Conclusión:** sube de nivel de forma significativa (2.2× en nivel). El 413 deja de existir, el costo de tokens cae ~10×, la conversación es estable y contextual, y el código queda con fuente única de contexto (sin duplicación con el motor).

## 5. Archivos afectados

- `data_engine/ai_advisor.py` — `_build_chat_context_message`, `chat_with_column_advisor`, constantes de contexto (CHAT-01/02/04), `_detect_intent` (CHAT-04), `build_column_context` y `analyze_column_deep` con contexto compartido (CHAT-05), `_strip_format` + `_detect_typos` + bloque `POSIBLES ERRORES DE ESCRITURA` (CHAT-06).
- `backend/app/main.py` — endpoint `/api/ai/chat-column` + `_get_chat_session` con cache por hash (CHAT-04) y `column_exists` (CHAT-06).
- `frontend/src/app.js` + `frontend/src/nube.js` — render de errores (CHAT-03).
- `frontend/src/styles/design-system.css` — fix visual del dropdown (Commit 0) + `.chat-bubble--error` (CHAT-03).
- `tests/test_ai_advisor.py` — tests nuevos + actualización de contrato `full=True/False` (cambio de contrato planificado y documentado).
- `tests/` E2E — `07_depuration_28_categories.spec.js` (CHAT-03).

## 6. Garantías

- Cada commit cierra con: suite Python 248 y E2E 41 verdes + `ruff --select F,E9` limpio.
- Cambio de contrato explícito y documentado: solo el test de `full=True/False` en `test_ai_advisor.py` (CHAT-04: `test_followup_message_compact` → `keeps_full_context`).
- Cache en memoria apto para 1 instancia Render; sin persistencia entre reinicios (pendiente conocido, no oculto).
