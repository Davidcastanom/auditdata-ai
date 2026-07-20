# AuditData AI — Plan de Implementación de Inteligencia Artificial

**Fecha:** 19 de julio de 2026
**Estado:** Documento de planificación
**Versión del proyecto:** 1.0.0

---

## 1. Visión General

AuditData AI actualmente ejecuta un flujo de 6 etapas: Comprender → Perfilar → Reglas → Depurar → Validar → Informe. El motor de análisis genera diagnósticos técnicos, pero todas las decisiones de limpieza dependen 100% del criterio del usuario.

El objetivo de integrar IA es **reducir la carga cognitiva del analista** sin eliminar su control. La IA sugiere, clasifica y resume, pero el usuario siempre aprueba.

### Principios de la Integración

1. **La IA sugiere, el humano decide.** Nunca se aplican cambios automáticos sin aprobación explícita.
2. **Trazabilidad total.** Cada sugerencia de IA queda documentada en la bitácora con su justificación.
3. **Costo controlado.** Usar Gemini Flash para minimizar costo por dataset (<$0.20 promedio).
4. **Graceful degradation.** Sin API key, la herramienta funciona igual que ahora. La IA es un enhancement, no un requisito.
5. **Contexto primero.** La IA siempre recibe el diagnóstico completo + el contexto del Step 0 antes de sugerir.

---

## 2. Arquitectura Actual

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                             │
│  index.html → app.js → state.js + router.js                │
│                                                             │
│  Step 0: Comprender (file upload + contexto)                │
│  Step 1: Perfilar (diagnóstico automático)                  │
│  Step 2: Reglas (eliminar columnas)                         │
│  Step 3: Depurar (acciones de limpieza + bitácora)          │
│  Step 4: Validar (comparación antes/después)                │
│  Step 5: Informe (PDF + Markdown + CSV)                     │
└─────────────────────┬───────────────────────────────────────┘
                      │ JSON
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                     BACKEND API                             │
│  FastAPI (main.py)                                         │
│                                                             │
│  POST /api/analyze  → analyzer.analyze_dataset()            │
│  POST /api/clean    → analyzer.apply_cleaning_actions()     │
│  POST /api/report/* → reporting.build_*_report()            │
│  GET  /api/health   → status check                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   DATA ENGINE                               │
│  analyzer.py (independiente del web)                        │
│                                                             │
│  - load_dataset()        → CSV/XLSX parsing                 │
│  - analyze_dataset()     → ColumnProfile + scores           │
│  - apply_cleaning_actions() → before/after evidence         │
│  - generate_ai_justification() → Gemini API call            │
│  - build_*_report()      → Markdown generation              │
└─────────────────────────────────────────────────────────────┘
```

### Datos que ya están disponibles para la IA

El `analysis` object ya contiene todo lo que la IA necesita:

```json
{
  "filename": "moveup_sample.csv",
  "row_count": 500,
  "column_count": 8,
  "duplicate_rows": 12,
  "scores": {
    "completeness": 94.2,
    "consistency": 87.5,
    "accuracy": 99.8,
    "uniqueness": 97.6,
    "overall": 94.78
  },
  "columns": [
    {
      "name": "edad",
      "detected_type": "number",
      "total_rows": 500,
      "missing": 0,
      "unique_values": 498,
      "format_issues": 0,
      "outliers": 1,
      "outlier_examples": [450],
      "min_value": 18,
      "max_value": 450,
      "mean": 32.4,
      "median": 28.0,
      "format_groups": []
    }
  ],
  "recommendations": [...]
}
```

El contexto del Step 0 (aún no se guarda en el backend) incluye:
- `rowMeaning`: Qué representa cada fila (ej. "participante", "venta")
- `objective`: Objetivo del análisis

---

## 3. Arquitectura Propuesta (Fase 1-5)

```
┌─────────────────────────────────────────────────────────────┐
│                     NUEVOS ENDPOINTS                        │
│                                                             │
│  POST /api/suggest        → Sugerencias automáticas         │
│  POST /api/chat           → Chat asistente                  │
│  POST /api/classify       → Clasificación de outliers       │
│  POST /api/generate-rules → Reglas por industria            │
│  POST /api/narrative      → Resumen narrativo               │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   NUEVO MÓDULO: ai_engine/                  │
│                                                             │
│  ai_engine/                                                │
│  ├── __init__.py                                           │
│  ├── client.py         → Wrapper de Gemini API              │
│  ├── prompts.py        → Templates de prompts               │
│  ├── suggest.py        → Lógica de sugerencias              │
│  ├── chat.py           → Lógica del chat                    │
│  ├── classify.py       → Clasificación de outliers          │
│  ├── rules.py          → Generación de reglas               │
│  └── narrative.py      → Resumen narrativo                  │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   FRONTEND: NUEVOS COMPONENTES              │
│                                                             │
│  SuggestPanel    → Muestra sugerencias post-análisis        │
│  ChatPanel       → Panel de chat con contexto               │
│  OutlierTag      → Badge de clasificación IA en outliers    │
│  RulesPanel      → Reglas sugeridas por industria           │
│  NarrativeEditor → Editor de resumen antes de incluir       │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Detalle por Fase

### FASE 1: Sugerencias Automáticas

**Objetivo:** Después del perfilado, la IA sugiere acciones concretas.

**Archivos a crear:**
- `ai_engine/client.py` — Wrapper reutilizable de Gemini
- `ai_engine/prompts.py` — Templates de prompts
- `ai_engine/suggest.py` — Lógica de sugerencias
- `backend/app/main.py` — Nuevo endpoint `POST /api/suggest`
- `frontend/src/app.js` — Nuevo componente `SuggestPanel`

**Flujo de datos:**
```
Step 1 (Perfilado) completo
  │
  ▼
Frontend envía: { analysis, context: { rowMeaning, objective } }
  │
  ▼
POST /api/suggest
  │
  ▼
suggest.py genera prompt con:
  - Scores de calidad
  - Columnas con problemas
  - Outliers detectados
  - Contexto del usuario
  │
  ▼
Gemini Flash retorna JSON:
  {
    "suggestions": [
      {
        "column": "edad",
        "issue": "outlier",
        "severity": "high",
        "suggested_action": "flag_outliers",
        "reason": "Valor 450 es estadísticamente imposible",
        "confidence": 0.95
      },
      {
        "column": "ciudad",
        "issue": "format_variants",
        "severity": "medium",
        "suggested_action": "standardize_text",
        "reason": "3 variantes detectadas",
        "confidence": 0.90
      }
    ]
  }
  │
  ▼
Frontend muestra panel de sugerencias
  │
  ▼
Usuario acepta/modifica/rechaza cada una
  │
  ▼
Las aceptadas se convierten en acciones documentadas
```

**Prompt base (Gemini):**
```
Eres un Auditor Senior de Calidad de Datos. Analiza el siguiente
diagnóstico y sugiere acciones de limpieza específicas.

Dataset: {filename}
Filas: {row_count} | Columnas: {column_count}
Calidad general: {overall}%

Problemas detectados:
{column_details}

Contexto del análisis:
- Qué representa cada fila: {rowMeaning}
- Objetivo: {objective}

Para cada problema encontrado, sugiere UNA acción específica con:
- Columna afectada
- Tipo de problema (outlier, missing, format, duplicate)
- Severidad (high, medium, low)
- Acción sugerida (delete_column, impute_missing, standardize_text, etc.)
- Razón técnica
- Confianza (0.0 - 1.0)

Responde en JSON válido con la estructura exacta indicada.
```

**Tareas necesarias:**
1. [ ] Crear `ai_engine/client.py` con wrapper de Gemini
2. [ ] Crear `ai_engine/prompts.py` con templates
3. [ ] Crear `ai_engine/suggest.py`
4. [ ] Agregar endpoint `POST /api/suggest` en `main.py`
5. [ ] Crear modelo Pydantic `SuggestRequest` y `SuggestResponse`
6. [ ] Crear componente `SuggestPanel` en frontend
7. [ ] Guardar contexto del Step 0 en el store
8. [ ] Agregar test `test_suggest_endpoint`
9. [ ] Agregar test `test_suggest_with_analysis`

---

### FASE 2: Chat Asistente

**Objetivo:** Panel de chat donde el usuario pregunta sobre su dataset y la IA responde.

**Archivos a crear:**
- `ai_engine/chat.py` — Lógica del chat con contexto
- `backend/app/main.py` — Nuevo endpoint `POST /api/chat`
- `frontend/src/app.js` — Nuevo componente `ChatPanel`

**Flujo de datos:**
```
Usuario escribe pregunta en ChatPanel
  │
  ▼
POST /api/chat
  {
    "message": "¿Por qué hay 450 en edad?",
    "analysis": { ... },
    "context": { rowMeaning, objective },
    "actions_applied": [ ... ],
    "chat_history": [ ... ]
  }
  │
  ▼
chat.py construye prompt con contexto completo:
  - Diagnóstico del dataset
  - Acciones ya aplicadas
  - Historial de la conversación
  │
  ▼
Gemini Flash responde con:
  - Explicación técnica
  - Opciones de acción
  - Cómo aceptar una acción (si aplica)
  │
  ▼
Frontend muestra respuesta con botones de acción rápida
```

**Prompt base (Gemini):**
```
Eres un asistente experto en limpieza de datos. Responde preguntas
sobre el dataset actual de forma clara y técnica.

Dataset: {filename}
Filas: {row_count} | Columnas: {column_count}
Calidad general: {overall}%

Diagnóstico por columna:
{column_details}

Acciones ya aplicadas:
{actions_applied}

Historial de la conversación:
{chat_history}

Pregunta del usuario: {message}

Reglas:
1. Responde en español
2. Sé conciso (máximo 3 párrafos)
3. Si recomiendas una acción, indica el kind exacto
4. Nunca elimines datos sin preguntar
5. Si no tienes suficiente contexto, pide más información
```

**Tareas necesarias:**
1. [ ] Crear `ai_engine/chat.py`
2. [ ] Agregar endpoint `POST /api/chat`
3. [ ] Crear modelo `ChatRequest` y `ChatResponse`
4. [ ] Crear componente `ChatPanel` con UI de chat
5. [ ] Agregar botones de "Aplicar acción" en respuestas de la IA
6. [ ] Persistir historial en localStorage
7. [ ] Agregar test `test_chat_endpoint`

---

### FASE 3: Clasificación de Outliers

**Objetivo:** La IA clasifica cada outlier como "error" o "dato real".

**Archivos a crear:**
- `ai_engine/classify.py` — Lógica de clasificación
- `backend/app/main.py` — Nuevo endpoint `POST /api/classify`
- `frontend/src/app.js` — Badge de clasificación en cards de outliers

**Flujo de datos:**
```
Step 3 (Depurar) detecta outliers
  │
  ▼
Frontend envía: { analysis, context, outliers: [...] }
  │
  ▼
POST /api/classify
  │
  ▼
classify.py para cada outlier:
  - Envía: valor, columna, stats (min, max, mean, median), contexto
  - Gemini clasifica: ERROR / REAL / AMBIGUO
  - Retorna: clasificación + confianza + razón
  │
  ▼
Frontend muestra badge junto a cada outlier:
  🔴 ERROR (95%) → Sugerencia: eliminar fila
  🟡 REAL (85%)  → Sugerencia: marcar para revisión
  ⚪ AMBIGUO     → Sugerencia: revisar con fuente
```

**Prompt base (Gemini):**
```
Clasifica el siguiente valor atípico en un dataset.

Columna: {column_name}
Tipo detectado: {detected_type}
Valor atípico: {outlier_value}
Estadísticas: min={min}, max={max}, media={mean}, mediana={median}
Contexto: Qué representa cada fila: {rowMeaning}

Clasifica como:
- ERROR: Valor imposible o casi seguro error de digitación
- REAL: Valor inusual pero posible en este contexto
- AMBIGUO: No se puede determinar sin consultar la fuente

Responde en JSON: { "classification": "...", "confidence": 0.0-1.0, "reason": "..." }
```

**Tareas necesarias:**
1. [ ] Crear `ai_engine/classify.py`
2. [ ] Agregar endpoint `POST /api/classify`
3. [ ] Crear modelo `ClassifyRequest` y `ClassifyResponse`
4. [ ] Agregar badge visual de clasificación en `renderCleaningBoard()`
5. [ ] Agregar test `test_classify_outliers`

---

### FASE 4: Reglas por Industria

**Objetivo:** La IA genera reglas de validación según el tipo de datos.

**Archivos a crear:**
- `ai_engine/rules.py` — Generación de reglas
- `backend/app/main.py` — Nuevo endpoint `POST /api/generate-rules`
- `frontend/src/app.js` — Panel de reglas sugeridas

**Flujo de datos:**
```
Usuario selecciona industria/tipo en Step 0
  │
  ▼
POST /api/generate-rules
  {
    "industry": "salud",
    "columns": ["edad", "peso", "altura", "presion_arterial"],
    "analysis": { ... }
  }
  │
  ▼
rules.py genera reglas basadas en:
  - Estándares de la industria seleccionada
  - Tipos de datos detectados
  - Rangos estadísticos del dataset
  │
  ▼
Gemini retorna reglas:
  [
    { "column": "edad", "rule": "range", "min": 0, "max": 120, "source": "OMS" },
    { "column": "peso", "rule": "range", "min": 2, "max": 500, "source": "OMS" },
    { "column": "presion_arterial", "rule": "range", "min": 60, "max": 300, "source": "AHA" }
  ]
  │
  ▼
Frontend muestra reglas en Step 2 (Reglas)
  │
  ▼
Usuario aprueba/rechaza cada regla
  │
  ▼
Reglas aprobadas se aplican automáticamente en Step 3
```

**Industrias soportadas (iniciales):**
- Salud
- Educación
- Finanzas
- Retail / E-commerce
- RRHH
- Marketing

**Tareas necesarias:**
1. [ ] Crear `ai_engine/rules.py`
2. [ ] Agregar endpoint `POST /api/generate-rules`
3. [ ] Crear dropdown de industria en Step 0
4. [ ] Crear componente `RulesSuggested` en Step 2
5. [ ] Agregar test `test_generate_rules`

---

### FASE 5: Resumen Narrativo

**Objetivo:** La IA genera un resumen ejecutivo en lenguaje natural para el PDF.

**Archivos a crear:**
- `ai_engine/narrative.py` — Generación de resumen
- `backend/app/main.py` — Nuevo endpoint `POST /api/narrative`
- `backend/app/reporting.py` — Integrar resumen en sección 2

**Flujo de datos:**
```
Step 5 (Informe) - Usuario hace clic en "Generar informe"
  │
  ▼
POST /api/narrative
  {
    "before": { ... },
    "after": { ... },
    "actions": [ ... ],
    "context": { rowMeaning, objective }
  }
  │
  ▼
narrative.py genera prompt con:
  - Comparación antes/después
  - Acciones aplicadas
  - Contexto del análisis
  │
  ▼
Gemini genera párrafo narrativo
  │
  ▼
Se incluye en la sección 2 del PDF
```

**Prompt base (Gemini):**
```
Genera un resumen ejecutivo narrativo (máximo 4 párrafos) para un
informe de limpieza de datos.

Dataset: {filename}
Filas: {row_count} → {row_after}
Calidad: {overall_before}% → {overall_after}%

Acciones aplicadas:
{actions_list}

Problemas principales:
{issues_summary}

El res debe:
1. Explicar qué se hizo y por qué
2. Destacar las mejoras más importantes
3. Señalar riesgos pendientes
4. Ser profesional y claro para un gerente no técnico
```

**Tareas necesarias:**
1. [ ] Crear `ai_engine/narrative.py`
2. [ ] Agregar endpoint `POST /api/narrative`
3. [ ] Integrar resumen en `reporting.py` sección 2
4. [ ] Agregar test `test_narrative_endpoint`

---

## 5. Estructura de Directorios Final

```
auditdata-ai/
├── ai_engine/                    # NUEVO: Módulo de IA
│   ├── __init__.py
│   ├── client.py                 # Wrapper de Gemini API
│   ├── prompts.py                # Templates de prompts
│   ├── suggest.py                # Fase 1: Sugerencias
│   ├── chat.py                   # Fase 2: Chat asistente
│   ├── classify.py               # Fase 3: Clasificación outliers
│   ├── rules.py                  # Fase 4: Reglas por industria
│   └── narrative.py              # Fase 5: Resumen narrativo
├── backend/app/
│   ├── main.py                   # +5 endpoints nuevos
│   ├── reporting.py              # +integración resumen narrativo
│   └── server.py
├── data_engine/
│   └── analyzer.py               # Sin cambios
├── frontend/src/
│   ├── app.js                    # +5 componentes nuevos
│   ├── state.js                  # +context store
│   ├── router.js                 # Sin cambios
│   └── styles/
│       └── design-system.css     # +estilos de chat, sugerencias
├── tests/
│   ├── test_analyzer.py          # Sin cambios
│   ├── test_api.py               # +5 tests nuevos
│   ├── test_ai_engine.py         # NUEVO: Tests del módulo IA
│   └── test_prompts.py           # NUEVO: Tests de prompts
├── samples/
├── docs/
├── .env.example                  # +GEMINI_API_KEY documentada
├── pyproject.toml                # +ai_engine en packages
├── requirements.txt              # Sin cambios (ya tiene google-generativeai)
└── README.md                     # +documentación de IA
```

---

## 6. Modelo de Datos para IA

### Request/Response Patterns

```python
# Fase 1: Sugerencias
class SuggestRequest(BaseModel):
    analysis: dict
    context: dict  # { rowMeaning: str, objective: str }

class Suggestion(BaseModel):
    column: str
    issue: str  # outlier, missing, format, duplicate
    severity: str  # high, medium, low
    suggested_action: str
    reason: str
    confidence: float

class SuggestResponse(BaseModel):
    suggestions: list[Suggestion]
    summary: str

# Fase 2: Chat
class ChatRequest(BaseModel):
    message: str
    analysis: dict
    context: dict
    actions_applied: list[dict]
    chat_history: list[dict]

class ChatResponse(BaseModel):
    response: str
    suggested_action: dict | None  # Si la IA sugiere una acción

# Fase 3: Clasificación
class ClassifyRequest(BaseModel):
    analysis: dict
    context: dict
    outliers: list[dict]  # [{ column, value, stats }]

class OutlierClassification(BaseModel):
    column: str
    value: Any
    classification: str  # ERROR, REAL, AMBIGUO
    confidence: float
    reason: str

class ClassifyResponse(BaseModel):
    classifications: list[OutlierClassification]

# Fase 4: Reglas
class GenerateRulesRequest(BaseModel):
    industry: str
    columns: list[str]
    analysis: dict

class GeneratedRule(BaseModel):
    column: str
    rule: str  # range, not_null, unique, pattern
    params: dict  # { min, max } o { pattern }
    source: str
    confidence: float

class GenerateRulesResponse(BaseModel):
    rules: list[GeneratedRule]

# Fase 5: Narrativa
class NarrativeRequest(BaseModel):
    before: dict
    after: dict
    actions: list[dict]
    context: dict

class NarrativeResponse(BaseModel):
    narrative: str
```

---

## 7. Seguridad y Costos

### Seguridad
- La API key de Gemini se guarda en variables de entorno, nunca en código
- El contenido del dataset NO se envía a Gemini (solo estadísticas y diagnósticos)
- Rate limiting en endpoints de IA (máx 10 requests por minuto por IP)
- Timeout de 30 segundos en llamadas a Gemini

### Costos Estimados (Gemini 2.0 Flash)

| Fase | Input tokens | Output tokens | Costo/dataset |
|------|-------------|---------------|---------------|
| 1. Sugerencias | ~2,000 | ~1,000 | ~$0.002 |
| 2. Chat (5 msgs) | ~5,000 | ~2,500 | ~$0.01 |
| 3. Clasificación | ~1,500 | ~800 | ~$0.002 |
| 4. Reglas | ~1,000 | ~1,500 | ~$0.003 |
| 5. Narrativa | ~3,000 | ~500 | ~$0.002 |
| **Total por dataset** | | | **~$0.02** |

Para 1,000 datasets/mes: **~$20/mes**

---

## 8. Orden de Implementación Recomendado

```
Semana 1: Fase 1 (Sugerencias)
├── Crear ai_engine/client.py + prompts.py
├── Crear ai_engine/suggest.py
├── Agregar endpoint /api/suggest
├── Crear SuggestPanel en frontend
├── Tests unitarios + integración
└── Deploy y testing con dataset real

Semana 2: Fase 5 (Narrativa) + Fase 3 (Clasificación)
├── Crear ai_engine/narrative.py
├── Crear ai_engine/classify.py
├── Agregar endpoints /api/narrative + /api/classify
├── Integrar narrativa en PDF
├── Agregar badges de clasificación
└── Tests

Semana 3: Fase 2 (Chat)
├── Crear ai_engine/chat.py
├── Crear endpoint /api/chat
├── Crear ChatPanel con UI completa
├── Botones de acción rápida
└── Tests

Semana 4: Fase 4 (Reglas por industria)
├── Crear ai_engine/rules.py
├── Crear endpoint /api/generate-rules
├── Dropdown de industria
├── Panel de reglas sugeridas
└── Tests + documentación final
```

---

## 9. Decisiones Pendientes

| Decisión | Opciones | Recomendación |
|----------|----------|---------------|
| Modelo de IA | Gemini Flash / GPT-4o-mini / Claude Haiku | Gemini Flash (ya integrado, más barato) |
| ¿Chat en tiempo real? | WebSocket vs polling | Polling simple (suficiente para MVP) |
| ¿Guardar historial de chat? | Backend (DB) vs frontend (localStorage) | localStorage (sin DB necesaria) |
| ¿Reglas predefinidas o 100% IA? | Mixto | Reglas base predefinidas + IA para personalizar |
| ¿Resumen narrativo siempre? | Automático vs opcional | Opcional con toggle |
| ¿Costo lo paga el usuario? | Free tier limitado vs ilimitado | Free tier: 5 análisis/día con IA |

---

## 10. Checklist de Implementación

### Preparación
- [ ] Verificar que `GEMINI_API_KEY` funciona en Render
- [ ] Crear directorio `ai_engine/`
- [ ] Crear `ai_engine/__init__.py`
- [ ] Crear `ai_engine/client.py` con wrapper reutilizable
- [ ] Crear `ai_engine/prompts.py` con templates base
- [ ] Agregar tests de integración del wrapper

### Fase 1
- [ ] Crear `ai_engine/suggest.py`
- [ ] Agregar `POST /api/suggest` en `main.py`
- [ ] Crear `SuggestRequest` y `SuggestResponse` en Pydantic
- [ ] Guardar contexto del Step 0 en `state.js`
- [ ] Crear componente `SuggestPanel` en `app.js`
- [ ] Agregar estilos `.suggest-*` en `design-system.css`
- [ ] Agregar test `test_suggest_endpoint`
- [ ] Agregar test `test_suggest_with_analysis`
- [ ] Test manual con dataset real
- [ ] Deploy a Render

### Fase 2
- [ ] Crear `ai_engine/chat.py`
- [ ] Agregar `POST /api/chat` en `main.py`
- [ ] Crear `ChatRequest` y `ChatResponse`
- [ ] Crear componente `ChatPanel` con UI de chat
- [ ] Agregar botones de "Aplicar acción" en respuestas
- [ ] Persistir historial en localStorage
- [ ] Agregar test `test_chat_endpoint`

### Fase 3
- [ ] Crear `ai_engine/classify.py`
- [ ] Agregar `POST /api/classify` en `main.py`
- [ ] Crear `ClassifyRequest` y `ClassifyResponse`
- [ ] Agregar badge visual en `renderCleaningBoard()`
- [ ] Agregar test `test_classify_outliers`

### Fase 4
- [ ] Crear `ai_engine/rules.py`
- [ ] Agregar `POST /api/generate-rules` en `main.py`
- [ ] Agregar dropdown de industria en Step 0
- [ ] Crear componente `RulesSuggested` en Step 2
- [ ] Agregar test `test_generate_rules`

### Fase 5
- [ ] Crear `ai_engine/narrative.py`
- [ ] Agregar `POST /api/narrative` en `main.py`
- [ ] Integrar resumen en `reporting.py` sección 2
- [ ] Agregar test `test_narrative_endpoint`

### Final
- [ ] Actualizar README con documentación de IA
- [ ] Actualizar `.env.example` con variables de IA
- [ ] Actualizar `pyproject.toml` con `ai_engine` package
- [ ] Test completo: `pytest tests/ -v` (todos pasando)
- [ ] Deploy final a Render
