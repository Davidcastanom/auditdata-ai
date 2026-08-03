# Arquitectura y Flujo — AuditData AI

Documento integral del sistema: arquitectura, flujo de 7 etapas, endpoints por paso, algoritmos, conexiones externas, métricas anónimas y recomendaciones/fallas/inconsistencias detectadas.

Repo: https://github.com/Davidcastanom/auditdata-ai.git · Deploy: https://auditdata-ai-1.onrender.com

---

## 1. Arquitectura general

```
                    ┌─────────────────────────────────────────────────────┐
                    │  FRONTEND (SPA vanilla JS, sin framework)          │
                    │  frontend/index.html                               │
                    │  ├── src/app.js        Orquestación del wizard      │
                    │  ├── src/nube.js       Paso 3-4 (diagnóstico+chat) │
                    │  ├── src/auth.js       Google OAuth + Supabase      │
                    │  ├── src/router.js     Navegación por hash          │
                    │  ├── src/state.js      Estado localStorage + undo  │
                    │  ├── src/admin.js      Panel admin (frontend/admin)│
                    │  └── src/styles/design-system.css                  │
                    └───────────────┬─────────────────────────────────────┘
                                    │ HTTP JSON (base64 de archivos)
                    ┌───────────────▼─────────────────────────────────────┐
                    │  BACKEND (FastAPI)  backend/app/                    │
                    │  ├── main.py        Endpoints REST + admin          │
                    │  ├── auth.py        JWT Supabase + Google login     │
                    │  ├── metrics.py     Métricas anónimas + errores     │
                    │  └── reporting.py   PDF reportlab (10 secciones)    │
                    └───────────────┬─────────────────────────────────────┘
                                    │
                    ┌───────────────▼─────────────────────────────────────┐
                    │  MOTOR DE DATOS  data_engine/                       │
                    │  ├── analyzer.py     Perfilado + limpieza + scores  │
                    │  ├── diagnostic.py   Diagnóstico 28 categorías      │
                    │  ├── domain_rules.py 20 reglas de dominio           │
                    │  ├── charts.py       Gráficas matplotlib (PDF)      │
                    │  └── ai_advisor.py   Copiloto IA (Groq/Llama3.1)    │
                    └───────────────┬─────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────────┐
        │                           │                               │
   ┌────▼─────┐              ┌──────▼──────┐                  ┌─────▼──────┐
   │ Supabase │              │   Groq API  │                  │ Make.com   │
   │ · Auth    │              │ · IA chat/  │                  │ · Webhook  │
   │   Google  │              │   deep      │                  │   errores  │
   │ · Historial│              └─────────────┘                  └────────────┘
   │ · Métricas│
   └──────────┘
```

---

## 2. Flujo de 7 etapas (wizard, pasos 0-6)

Router por hash (`frontend/src/router.js`); `goToStep` en `app.js:1280`, `onNext` en `app.js:1259` con lógica especial en pasos 3 y 4.

```
[0 Comprender] ─▶ [1 Perfilar] ─▶ [2 Reglas] ─▶ [3 Diagnóstico]
                                                   │
[6 Informe] ◀── [5 Validar] ◀── [4 Depurar] ◀──────┘
```

### Paso 0 — Comprender
- UI: `index.html` + `app.js` (file input, dropzone, preview modal).
- Usuario: unidad de análisis, objetivo, carga de archivo (CSV/XLSX, máx 10MB).
- **Endpoint:** `POST /api/file/preview` (`main.py:145`) → detecta encoding, delimitador y fila de encabezado (`detect_file_settings`), devuelve vista previa → `showFilePreview` (`app.js:376`).
- `_previewSettings` guarda encoding/delimitador/headerRow para el análisis.

### Paso 1 — Perfilar
- **Endpoint:** `POST /api/analyze` (`main.py:119`) → `analyze_dataset` (analyzer.py:110): perfilado por columna + 4 dimensiones de calidad + recomendaciones.
- UI: `renderProfile` (`app.js:440`), `renderRules` (L549), `renderDepurationBoard` (L663), `renderLog` (L1032).
- `loadSample` (L323) usa dataset de ejemplo interno.

### Paso 2 — Reglas
- Sin llamada de red. Documenta decisiones estructurales: categorización de columnas y `duplicate_key_columns` (claves de duplicados). Los duplicados se calculan con normalización NFKD (analyzer.py:1026-1052).
- `renderRules` (L549) + `populateAdvancedColumns`.

### Paso 3 — Diagnóstico (lógica especial en `onNext`)
- Al entrar: `nube.loadRecommendations(filename, base64)` (`app.js:1304`).
- **Endpoints:**
  - `POST /api/ai/recommend` (`main.py:168`) → recomendaciones IA batch (`get_ai_recommendations_async`).
  - `POST /api/diagnose` (`main.py:130`, llamado en `nube.js:92`) → diagnóstico 28 categorías del backend.
  - `POST /api/ai/column-deep-analysis` (`main.py:251`, `nube.js:282`) → análisis profundo por columna, **bajo demanda** (botón "Ejecutar análisis"), con cache.
- `nube.js` también corre un diagnóstico manual de 28 categorías por columna (drawer con secciones colapsables). `onAllReviewed` habilita el paso 4.
- `onNext` en paso 3: `enableStep(4)`, `nube._handleSkipValidation()`, navega a 4.

### Paso 4 — Depurar (lógica especial en `onNext`)
- `renderDepurationBoard` (L663) + drawer de columna + copiloto.
- **Endpoints:**
  - `POST /api/ai/chat-column` (`main.py:196`; `app.js:984`, `nube.js:618`) → chat interactivo.
  - `POST /api/clean` (`main.py:290`; `runCleaning` `app.js:1144`) → aplica acciones (`apply_cleaning_actions`), re-perfila before/after, genera `changelog`, `clean_csv` y `xlsx_base64` (vía `csv_to_xlsx`).
- `onNext` en paso 4: `runCleaning().then(...)` → habilita pasos 5-6 y navega a 5.

### Paso 5 — Validar
- Sin llamada de red. `renderValidation` (`app.js:1188`): tabla de validación con umbrales (Completitud/Consistencia/Exactitud ≥95, Unicidad = 0, Calidad ≥90, Documentación >0) y grid de comparación antes/después.

### Paso 6 — Informe
- **Endpoints:**
  - `POST /api/report/pdf` (`main.py:334`) → PDF académico reportlab, 10 secciones, con gráficas (`reporting.py` + `charts.py`).
  - `POST /api/report/markdown` (`main.py:311`) → informe Markdown.
  - `POST /api/report/audit-log` (`main.py:358`) → bitácora de cambios.
- Descargas locales: CSV limpio, XLSX limpio (`downloadCleanCsv`/`downloadCleanXlsx`).
- Botón "Guardar en la nube" → historial Supabase (`auth.js saveToHistory`).

---

## 3. Endpoints REST (backend/app/main.py)

| Método | Ruta | Línea | Uso en wizard |
|---|---|---|---|
| GET | `/api/health` | 115 | Health check |
| POST | `/api/analyze` | 119 | Paso 1 |
| POST | `/api/diagnose` | 130 | Paso 3 |
| POST | `/api/file/preview` | 145 | Paso 0 |
| POST | `/api/ai/recommend` | 168 | Paso 3 |
| POST | `/api/ai/chat-column` | 196 | Paso 4 |
| POST | `/api/ai/column-deep-analysis` | 251 | Paso 3 (bajo demanda) |
| POST | `/api/clean` | 290 | Paso 4 |
| POST | `/api/report/markdown` | 311 | Paso 6 |
| POST | `/api/report/pdf` | 334 | Paso 6 |
| POST | `/api/report/audit-log` | 358 | Paso 6 |
| GET | `/api/admin/metrics` | 420 | Panel admin |
| GET | `/api/admin/errors` | 429 | Panel admin |
| POST | `/api/admin/errors/resolve` | 451 | Panel admin |
| POST | `/api/admin/errors/send` | 465 | Webhook Make.com |
| GET | `/` | 477 | Frontend |
| GET | `/admin` | 482 | Panel admin |

Límite de archivos: `MAX_FILE_SIZE` = 10MB (`_decode_payload`, main.py:108).

---

## 4. Conexiones externas

| Servicio | Uso | Config |
|---|---|---|
| **Supabase** | Auth Google OAuth (login), historial en la nube (`datasets`, `analyses`, `cleaning_sessions`), JWT admin (`verify_token`, auth.py), métricas | `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY` |
| **Render** | Deploy (uvicorn, `render.yaml`/`Procfile`/`Dockerfile`), auto-deploy desde `main` | Env vars en dashboard |
| **Groq** | IA copiloto: chat + recomendaciones batch (`GROQ_API_KEY`) y análisis profundo (`Recomendaciones_de_copiloto`). Modelo `llama-3.1-8b-instant`. Fallback local sin key | Keys `sync:false` en `render.yaml` |
| **Make.com** | Webhook de notificación de errores admin (`notify_make_webhook`) | URL del webhook (env) |

---

## 5. Recomendaciones, fallas e inconsistencias detectadas

1. **`review_issue` se ignora silenciosamente.** La IA genera acciones `kind: "review_issue"` (`ai_advisor.py:260, 622`), pero `apply_cleaning_actions` (`analyzer.py:132`) no tiene rama para ese `kind` → se descarta sin avisar al usuario. Considerar: registrar como "pendiente de revisión" en la bitácora en lugar de ignorarla.

2. **Exactitud ≈ outliers (aproximación).** `_quality_scores` (analyzer.py:1055) calcula `accuracy` solo con outliers IQR. No es exactitud real (no hay fuente de verdad). Documentar esta limitación en el informe.

3. **Outliers con `IQR == 0` se omiten sin aviso** (analyzer.py:1004-1005); columnas constantes/casi constantes quedan sin `outlier_analysis_skipped`. Considerar `outlier_analysis_skipped = True` en ese caso también.

4. **`invalid_type_count` solo para tipo numérico** (analyzer.py:927); columnas date/text no reportan errores de tipo por celda a nivel de perfilado (eso sí lo cubre `diagnostic.py` con `TYPE_PER_CELL`).

5. **Nomenclatura de las "28 categorías" difiere entre README y código.** README lista `EMPTY`, `FORMAT_INCONSISTENCY`, `CASE_INCONSISTENCY`, `NUMERIC_OUTLIER`, etc.; los códigos reales en `diagnostic.py` son `MISSING`, `DATE_FORMAT`, `BOOL_INCONSISTENCY`, `TYPE_PER_CELL`, etc. Validar el conteo 12+16=28 y alinear la documentación.

6. **README desactualizado en tests.** Afirma "53/53 tests" y "16+2+35"; la suite actual supera 126 tests (se sumaron pruebas de regresión XLSX y de nuevos módulos). Actualizar badge y sección Testing.

7. **README no lista los endpoints admin** ni refleja `metrics.py`, `auth.py` en el árbol de arquitectura.

8. **Contraste del panel admin corregido** (`3648b96`): `.admin-table th` heredaba el fondo oscuro del design system; ahora `#f8fafc` con texto `#334155`.

9. **Botón X de eliminación de historial en la nube** implementado pero **sin commitear ni desplegar** (migración `004_delete_history.sql` pendiente). Incluye políticas DELETE por usuario en Supabase.

10. **Bug XLSX resuelto** (`c9965ae`): `_clean_filename` devolvía extensión original y `apply_cleaning_actions` re-analizaba el CSV limpio como XLSX. Ahora siempre `.csv`; test de regresión agregado.

11. **Métricas anónimas requieren env vars en Render** (no-op sin ellas). Verificar que `SUPABASE_URL`/`SERVICE_KEY` + consent estén activos para que el panel admin muestre datos.

12. **Endpoint IA de deep analysis** devuelve `{"analysis": ..., "status": "error"}` con HTTP 200 en caso de fallo (main.py:287); conviene código de error apropiado para consistencia con el resto de la API.

13. **`_detect_type` orden de evaluación**: prioriza `number` antes que `date`; fechas numéricas (ej. `20240101`) pueden clasificarse como `number`.

14. **Carga completa de archivos vía base64** en cada request de IA (re-`load_dataset` por endpoint). Con 10MB el payload se re-transfiere en cada llamada; candidato a caché/token por sesión.

---

## 6. Esqueleto del flujograma para generar imagen con IA

Formato árbol (compatible con prompt de generación de imágenes). Estructura jerárquica:

```
Flujo AuditData AI (wizard 7 pasos)

[Paso 0 · Comprender]
  ├─ Usuario: unidad de análisis, objetivo, archivo CSV/XLSX
  ├─ POST /api/file/preview  (encodig, delimitador, header)
  └─ Vista previa modal → confirmar

[Paso 1 · Perfilar]
  └─ POST /api/analyze
       └─ Motor (analyzer.py)
            ├─ Tipo por columna (≥75% regla)
            ├─ missing, únicos, ejemplos, frecuencias
            ├─ stats numéricas (mean/median/min/max)
            ├─ outliers IQR (1.5·IQR)
            ├─ duplicados (NFKD, key_columns)
            └─ scores 4D: completitud/consistencia/exactitud/unicidad

[Paso 2 · Reglas]
  └─ Categorización de columnas + claves de duplicados (local)

[Paso 3 · Diagnóstico]
  ├─ POST /api/diagnose  → 28 categorías (diagnostic.py)
  ├─ POST /api/ai/recommend  → recomendaciones IA (Groq)
  ├─ POST /api/ai/column-deep-analysis  (bajo demanda, cache)
  └─ Drawer de columna (diagnóstico/frecuencias/stats/chat)

[Paso 4 · Depurar]
  ├─ POST /api/ai/chat-column  → copiloto conversacional
  └─ POST /api/clean  → aplica acciones
       └─ before/after + changelog (bitácora por celda) + CSV/XLSX limpio

[Paso 5 · Validar]
  └─ Comparación antes/después con umbrales (≥95 / 0 / ≥90)

[Paso 6 · Informe]
  ├─ POST /api/report/pdf  (10 secciones + gráficas)
  ├─ POST /api/report/markdown
  ├─ POST /api/report/audit-log
  └─ Guardar en la nube (Supabase)

Servicios externos: Supabase (auth+historial+métricas) · Groq (IA) · Make.com (errores) · Render (deploy)
```
