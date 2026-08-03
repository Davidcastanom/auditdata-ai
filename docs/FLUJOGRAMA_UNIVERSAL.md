# Flujograma Universal — AuditData AI

Diagrama canónico e integral del proyecto. Cubre: frontend, backend, motor de datos, IA, conexiones externas (Supabase, Groq, Make.com, Render), autenticación, historial en la nube, métricas anónimas y panel admin.

- Repo: https://github.com/Davidcastanom/auditdata-ai.git
- Deploy: https://auditdata-ai-1.onrender.com
- Documentos complementarios: `docs/ARQUITECTURA_Y_FLUJO.md` · `docs/MAPEO_ANALISIS_ESTADISTICO.md`

---

## 1. Diagrama universal (Mermaid)

```mermaid
flowchart TD
    USR[("👤 Analista de datos")]

    subgraph FE["FRONTEND — SPA vanilla JS (frontend/)"]
        ROUTER[router.js · navegación por hash]
        APP[app.js · orquestación wizard 7 pasos]
        NUBE[nube.js · diagnóstico paso 3-4 · drawer de columna]
        AUTH[auth.js · Google OAuth + Supabase · historial]
        STATE[state.js · localStorage + undo]
        STYLE[design-system.css]
        ADMINUI[admin.html + admin.js · panel admin]
    end

    subgraph API["BACKEND — FastAPI (backend/app/)"]
        MAIN[main.py · endpoints REST + admin]
        REP[reporting.py · PDF reportlab · 10 secciones]
        MET[metrics.py · métricas anónimas + errores]
        AUTHBE[auth.py · verify_token + Supabase service key]
    end

    subgraph ENGINE["MOTOR DE DATOS (data_engine/)"]
        ANL[analyzer.py · perfilado + limpieza + scores 4D]
        DIA[diagnostic.py · 28 categorías + FastTextProfiler]
        DOM[domain_rules.py · 20 reglas de dominio]
        CHT[charts.py · gráficas matplotlib para PDF]
        AI[ai_advisor.py · copiloto IA Groq/Llama3.1]
    end

    subgraph EXT["SERVICIOS EXTERNOS"]
        SB[Supabase · auth + historial + métricas]
        GQ[Groq API · chat + deep analysis]
        MK[Make.com · webhook de errores admin]
        RD[Render · deploy · env vars]
    end

    USR -->|carga CSV/XLSX · define objetivo| APP
    USR -->|confirma acciones y decisiones| APP
    APP --> ROUTER
    APP --> NUBE
    APP --> AUTH
    APP --> STATE
    APP -->|HTTP JSON + base64| MAIN
    NUBE -->|HTTP JSON + base64| MAIN
    AUTH -->|JWT Supabase| SB
    MAIN --> ANL
    MAIN --> DIA
    MAIN --> DOM
    MAIN --> REP
    MAIN --> CHT
    MAIN --> AI
    REP --> CHT
    AI -->|chat + recomendaciones| GQ
    DIA --> DOM
    MAIN -->|métricas + errores| MET
    MET -->|guarda métricas| SB
    MET -->|resumen errores| MK
    AUTHBE -->|service key| SB
    ADMINUI -->|JWT admin| MAIN
    RD -->|deploy uvicorn| MAIN
    RD -->|variables de entorno| GQ
    RD -->|variables de entorno| SB
    RD -->|variables de entorno| MK
```

---

## 2. Flujo del wizard — 7 etapas (0-6) con endpoints

```mermaid
flowchart LR
    S0[Paso 0 · Comprender<br/>objetivo + archivo] -->|POST /api/file/preview| PREV
    S0 -->|confirmar vista previa| S1
    S1[Paso 1 · Perfilar] -->|POST /api/analyze| ANLZ
    S1 -->|perfilado completado| S2
    S2[Paso 2 · Reglas<br/>categorías + key columns] -->|sin red · local| S3
    S3[Paso 3 · Diagnóstico] -->|POST /api/ai/recommend| REC
    S3 -->|POST /api/diagnose| DG
    S3 -.->|POST /api/ai/column-deep-analysis · bajo demanda| DEEP
    S3 -->|revisar todas las columnas| S4
    S4[Paso 4 · Depurar] -->|POST /api/ai/chat-column| CHAT
    S4 -->|POST /api/clean| CLN
    S4 -->|aplicar limpieza y validar| S5
    S5[Paso 5 · Validar<br/>antes vs después] -->|umbrales ≥95/0/≥90| S6
    S6[Paso 6 · Informe] -->|POST /api/report/pdf| PDF
    S6 -->|POST /api/report/markdown| MD
    S6 -->|POST /api/report/audit-log| LOG
    S6 -->|guardar en la nube| CLOUD

    PREV[file/preview: encoding · delimitador · header]
    ANLZ[analyze: perfil + scores 4D + recomendaciones]
    REC[IA recomendaciones batch]
    DG[diagnóstico 28 categorías]
    DEEP[análisis profundo IA · cache]
    CHAT[copiloto conversacional]
    CLN[clean: before/after + changelog + CSV/XLSX]
    PDF[PDF académico 10 secciones + gráficas]
    MD[Markdown]
    LOG[bitácora de cambios]
    CLOUD[Supabase: datasets · analyses · cleaning_sessions]
```

---

## 3. Procesamiento interno del motor (analyzer.py)

```mermaid
flowchart TD
    IN([Archivo base64 + filename]) --> LD[load_dataset · CSV/XLSX]
    LD --> PF[analyze_dataset]
    PF --> PC[per_column: _profile_column]
    PC --> T[_detect_type · ≥75% number/date/boolean/text]
    PC --> M[_normalize_missing · MISSING_TOKENS]
    PC --> NS{¿tipo number?}
    NS -->|sí| STATS[_add_numeric_stats<br/>min·max·mean·median]
    STATS --> O{¿outliers?}
    O -->|IQR · 1.5·IQR| OUT[outliers + ejemplos]
    NS -->|no| VD[_add_value_distribution · Counter]
    NS -->|no| FG[_add_format_groups · variantes]
    PF --> DUP[_count_duplicate_rows · NFKD + key_columns]
    PF --> QS[_quality_scores · 4D]
    QS --> S[completeness · consistency · accuracy · uniqueness · overall]
    PF --> R[_recommendations · prioridad Alta/Media/Baja]
    DUP --> R
    R --> OUT2([analysis JSON → frontend paso 1])
```

---

## 4. Autenticación y nube (auth.js + auth.py)

```mermaid
flowchart TD
    LOGIN[Login screen] -->|click Google| OA[Google OAuth redirect]
    OA -->|código| SB[Supabase auth]
    SB -->|JWT + sesión| AUTH
    AUTH[auth.js · getCurrentUser] --> RESTORE[Restaurar sesión tras OAuth]
    AUTH --> SAVE[saveToHistory<br/>datasets · analyses · cleaning_sessions]
    SAVE --> CONSENT{¿consentimiento?}
    CONSENT -->|no| PROMPT[acceptConsent · registrar consentimiento 002]
    CONSENT -->|sí| WRITE[insertar historial]
    AUTH --> DEL[deleteHistorySession · botón X]
    DEL --> POL[Políticas DELETE por usuario · migración 004]
    AUTH -->|JWT Bearer| ADMIN{auth.py · verify_token}
    ADMIN -->|app_metadata.role = admin o ADMIN_EMAILS| OK[Acceso admin]
    ADMIN -->|ADMIN_TOKEN| OK2[Acceso script/Make]
    ADMIN -->|sin permisos| 403[403 · registrado en errores]
```

---

## 5. Panel admin y métricas anónimas (metrics.py)

```mermaid
flowchart TD
    ADMINUI[frontend/admin.html] -->|GET /api/admin/metrics| REQ{_require_admin}
    REQ -->|GET /api/admin/errors · ?resolved=false/true/all| ERR[error_logs agrupados]
    REQ -->|POST /api/admin/errors/resolve| RES[resolve_errors · migración 003]
    REQ -->|POST /api/admin/errors/send| WEB[notify_make_webhook → Make.com email]
    MAIN[main.py middleware] -->|hash anónimo · endpoint · status · duración| MET[métricas tabla · consentimiento 001/002]
    MET -->|no env vars| NOOP[no-op sin registro]
    MET -->|env vars configuradas| WR[guardar en Supabase]
```

---

## 6. Flujo IA (ai_advisor.py + Groq)

```mermaid
flowchart TD
    REQ[Petición IA] --> KEY{¿GROQ_API_KEY?}
    KEY -->|no| FALLBACK[Modo fallback · recomendaciones locales desde diagnóstico]
    KEY -->|sí| GROQ[Groq llama-3.1-8b-instant]
    GROQ --> REC[get_ai_recommendations_async · batch]
    GROQ --> CHAT[chat_with_column_advisor · lista con viñetas]
    GROQ --> DEEP[analyze_column_deep · hallazgos + fila exacta · cache]
    DEEP --> CACHE[Cache por columna · evitar re-consultas]
    REC --> PARSE1[Parsear JSON · validar claves]
    CHAT --> PARSE2[Parsear JSON · validar claves]
    REC -.-> ACT[acciones kind=review_issue · no aplicadas por apply_cleaning_actions]
```

---

## 7. Versión ASCII (para generar imagen con IA)

```
                        ┌───────────────────────────────────────────────┐
    USUARIO ───────────▶│   FRONTEND (SPA vanilla JS)                  │
                        │  app.js · nube.js · auth.js · router.js      │
                        │  state.js · design-system.css · admin.js     │
                        └───────────────┬───────────────────────────────┘
                                        │ HTTP JSON + base64
                    ┌───────────────────▼───────────────────────────────┐
                    │   BACKEND (FastAPI)   backend/app/                │
                    │  main.py · reporting.py · metrics.py · auth.py    │
                    └───────────────────┬───────────────────────────────┘
                                        │
                    ┌───────────────────▼───────────────────────────────┐
                    │   MOTOR DE DATOS   data_engine/                   │
                    │  analyzer.py ── perfilado + limpieza + scores 4D   │
                    │  diagnostic.py ── 28 categorías + FastTextProfiler │
                    │  domain_rules.py ── 20 reglas de dominio           │
                    │  charts.py ── gráficas matplotlib (PDF)           │
                    │  ai_advisor.py ── copiloto IA                      │
                    └───┬───────────┬───────────────┬──────────┬────────┘
                        │           │               │          │
                   ┌────▼───┐  ┌────▼────┐   ┌──────▼────┐ ┌────▼─────┐
                   │Supabase│  │  Groq   │   │  Make.com │ │  Render  │
                   │auth+hist│  │LLaMA3.1│   │webhook err│ │  deploy  │
                   │métricas │  └─────────┘   └───────────┘ └──────────┘
                   └────────┘
```

---

## 8. Inventario universal de flujos

| Flujo | Origen → Destino | Archivos clave | Estado |
|---|---|---|---|
| Wizard 7 pasos | app.js → endpoints `/api/*` | `frontend/src/app.js` · `backend/app/main.py` | Activo |
| Perfilado estadístico | `/api/analyze` → analyzer.py → UI paso 1 | `data_engine/analyzer.py` | Activo |
| Diagnóstico 28 categorías | `/api/diagnose` + nube.js → UI paso 3 | `data_engine/diagnostic.py` · `domain_rules.py` | Activo |
| Limpieza | `/api/clean` → apply_cleaning_actions → XLSX/CSV | `analyzer.py` · `csv_to_xlsx` | Activo (bug XLSX corregido `c9965ae`) |
| IA copiloto | `/api/ai/*` → Groq → chat/deep | `data_engine/ai_advisor.py` | Activo (fallback sin key) |
| Informes | `/api/report/pdf` · `markdown` · `audit-log` | `reporting.py` · `charts.py` | Activo |
| Autenticación | Google OAuth → Supabase → JWT | `auth.js` · `auth.py` | Activo |
| Historial en la nube | saveToHistory / getHistory / deleteHistorySession | `auth.js` · migraciones 001-004 | Activo (botón X listo para deploy) |
| Métricas anónimas | middleware → tabla metrics (con consentimiento) | `metrics.py` · migraciones 001/002 | Activo · requiere env vars en Render |
| Errores admin | error_logs → agrupación → resolve/send | `metrics.py` · migración 003 | Activo · botón resolver `f55da04` |
| Deploy | GitHub `main` → Render auto-deploy | `render.yaml` · `Procfile` · `Dockerfile` | Activo |

---

## 9. Leyenda de conexiones externas

| Servicio | Protocolo | Secretos | Uso |
|---|---|---|---|
| **Supabase** | REST/HTTPS (anónimo JWT + service key) | `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY` | Auth, historial, métricas |
| **Groq** | HTTPS (API key) | `GROQ_API_KEY`, `Recomendaciones_de_copiloto` | IA chat/deep/recomendaciones |
| **Make.com** | HTTPS (webhook) | URL de webhook | Notificación de errores admin |
| **Render** | HTTPS | env vars del dashboard | Host de la API + frontend estático |

---

# Anexo A — Flujograma para personas no técnicas

*Sección pensada para stakeholders, clientes o analistas sin conocimientos de programación. Explica qué hace la herramienta y en qué orden, sin mencionar código, servidores ni tecnologías.*

## ¿Qué hace AuditData AI en una frase?

Toma un archivo de datos (como una hoja de Excel), **lo examina**, **detecta errores**, te **ayuda a corregirlos con la guía de una inteligencia artificial**, y al final **te entrega un informe profesional** de todo lo que encontró y lo que se hizo.

## El recorrido del analista, de principio a fin

```mermaid
flowchart TD
    A[1️⃣ Me subo mi archivo de datos<br/>e indico para qué lo voy a usar] --> B[2️⃣ La herramienta lo revisa sola<br/>y me muestra un "chequeo médico"<br/>de cada columna]
    B --> C[3️⃣ Me explica qué reglas aplicar<br/>y deja que yo decida]
    C --> D[4️⃣ Detecta problemas típicos<br/>faltantes · repetidos · errores de escritura<br/>valores raros · formatos mezclados]
    D --> E[5️⃣ Me propone soluciones y converso<br/>con el asistente de IA si tengo dudas]
    E --> F[6️⃣ Aplico las correcciones que elijo<br/>y veo el antes vs el después]
    F --> G[7️⃣ Reviso que el dato quedó listo]
    G --> H[8️⃣ Descargo el informe + el archivo limpio]
    H --> I[🏁 Dato listo para analizar<br/>con decisiones documentadas]
```

## Explicación paso a paso (sin tecnicismos)

| Paso | Qué hace | En palabras simples |
|---|---|---|
| **1. Comprender** | Cargas tu archivo (CSV/Excel) y escribes el objetivo del análisis | "Dime qué quieres lograr y muéstrame tu archivo." |
| **2. Perfilar** | La herramienta examina cada columna automáticamente | Es como un médico que toma signos vitales: cuántas filas, cuántas columnas, qué tipo de dato hay, cuántos faltantes. |
| **3. Reglas** | Defines qué columnas se comparan para encontrar repetidos | "Para detectar duplicados, ¿comparamos todo o solo ciertos campos?" |
| **4. Diagnóstico** | Detecta 28 tipos de problemas con la guía de una IA | Señala con luz roja/amarilla/verde cada problema y te da una recomendación en lenguaje claro. |
| **5. Depurar** | Conversas con el asistente de IA y aplicas correcciones | Puedes preguntar "¿qué hago con esta columna?" y luego decides si aceptas la sugerencia. |
| **6. Validar** | Comparas el archivo antes y después | Tablero tipo semáforo: cada dimensión de calidad pasa de rojo a verde. |
| **7. Informe** | Generas el reporte final | Un PDF profesional (también Markdown y bitácora) con todo documentado, ideal para presentar o auditar. |

## ¿Qué problemas detecta la herramienta? (en lenguaje humano)

- ✅ Celdas vacías donde debería haber un dato
- ✅ Filas repetidas (duplicadas)
- ✅ Fechas escritas en formatos diferentes dentro de la misma columna
- ✅ Mayúsculas y minúsculas inconsistentes ("bogota" vs "Bogotá")
- ✅ Valores imposibles o fuera de rango (una edad de 450 años)
- ✅ Números extremos que pueden ser errores de captura
- ✅ Palabras mal escritas o con caracteres raros
- ✅ Mezclas de idiomas o unidades dentro de una misma columna

## Conceptos clave en una frase

| Término técnico | Explicación simple |
|---|---|
| **Calidad de datos** | Qué tan confiable y completa está tu información para tomar decisiones |
| **Outlier** | Un valor que se sale mucho del resto y podría ser un error |
| **Faltante (missing)** | Un dato que no se llenó y deja la celda vacía |
| **Duplicado** | Una fila que repite otra ya existente |
| **Imputar** | Rellenar un valor faltante (con el promedio, la mediana o el más frecuente) |
| **Bitácora** | El registro de cada decisión que se tomó y por qué — trazabilidad total |
| **Copiloto IA** | Un asistente que te guía conversando, pero **la última palabra siempre es tuya** |
| **Informe PDF** | El documento final de 10 secciones que resume diagnóstico, acciones y resultados |

## Lo que la herramienta NO hace

- ❌ No inventa datos que no existen
- ❌ No decide por ti: cada corrección requiere tu confirmación
- ❌ No expone ni comparte tu información (todo queda documentado solo para tu proyecto, y las métricas de uso son anónimas y opcionales)

## Resumen visual en una imagen

```
 SUBIR ─▶ REVISAR ─▶ REGLAS ─▶ DIAGNÓSTICO ─▶ CORREGIR ─▶ VALIDAR ─▶ INFORME
 archivo    chequeo     cómo       problemas     con IA      antes vs     PDF +
            médico      comparar   + consejos    y tu ok     después      archivo limpio
```

**En una palabra:** *AuditData AI es tu asistente para dejar tu base de datos limpia, documentada y lista para analizar.*
