# AuditData AI

**Herramienta profesional de limpieza y validación de calidad de datos con reportes PDF e IA**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/Tests-18%2F18%20passing-brightgreen.svg)](tests/)
[![Deploy](https://img.shields.io/badge/Deploy-Render-blue.svg)](https://auditdata-ai-1.onrender.com)

---

## Qué es AuditData AI

AuditData AI es una herramienta de **Flujo Base** para diagnosticar, documentar y preparar datasets antes de usarlos en análisis, visualización o toma de decisiones.

La herramienta **no inventa datos**. Calcula hallazgos, documenta riesgos y permite que el usuario valide las decisiones con criterio de negocio. Cada acción queda registrada con justificación técnica para garantizar trazabilidad completa.

---

## Flujo de 7 Etapas

```
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│  01      │  │  02      │  │  03      │  │  04      │
│ Comprender├─▶│ Perfilar ├─▶│ Reglas   ├─▶│Diagnostico│
└──────────┘  └──────────┘  └──────────┘  └──────────┘
                                                    │
┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  07      │  │  06      │  │  05      │            │
│ Informe  ◀─┤ Validar   ◀─┤ Depurar   ◀────────────┘
└──────────┘  └──────────┘  └──────────┘
```

1. **Comprender** — Define unidad de análisis, objetivo y carga el dataset
2. **Perfilar** — Diagnóstico técnico automático por columna (tipos, distribución, frecuencias)
3. **Reglas** — Documenta decisiones estructurales (categorización de columnas)
4. **Diagnóstico** — Detección de 28 categorías de problemas de calidad por columna
5. **Depurar** — Aplica acciones de limpieza con Copiloto IA y control del analista
6. **Validar** — Demuestra la calidad antes de declarar el dataset listo
7. **Informe** — Compila Data Cleaning Report (PDF académico, Markdown, bitácora)

---

## Arquitectura

```
auditdata-ai/
├── backend/app/
│   ├── main.py              # API FastAPI + endpoints
│   ├── reporting.py         # Generación de PDF (10 secciones)
│   └── server.py            # Runner de Uvicorn
├── data_engine/
│   ├── analyzer.py           # Motor de análisis + acciones de limpieza
│   ├── diagnostic.py         # Diagnóstico de 28 categorías de calidad
│   ├── ai_advisor.py         # Copiloto IA (Groq/Llama3.1)
│   ├── charts.py             # Generación de gráficos para PDF
│   └── domain_rules.py       # 20 reglas de dominio por tipo de columna
├── frontend/
│   ├── index.html            # UI principal (wizard 7 pasos)
│   └── src/
│       ├── app.js            # Orquestación UI (modo local)
│       ├── nube.js           # Orquestación UI (modo nube/Supabase)
│       ├── auth.js           # Autenticación Google OAuth + Supabase
│       ├── router.js         # Navegación por hash
│       ├── state.js          # Estado con localStorage + undo
│       └── styles/
│           └── design-system.css
├── tests/
│   ├── test_api.py           # 16 tests de integración
│   ├── test_analyzer.py      # 2 tests del motor
│   └── frontend/             # 34 tests E2E con Playwright
├── docs/                     # Documentación (no modificar)
├── samples/                  # Datasets de ejemplo
├── render.yaml               # Configuración Render
├── requirements.txt          # Dependencias Python
└── .env.example              # Template de variables de entorno
```

---

## Motor de Diagnóstico (28 categorías)

El diagnóstico detecta automáticamente **28 categorías** de problemas agrupadas en:

| Categoría | Descripción |
|-----------|-------------|
| EMPTY | Columnas sin datos |
| DUPLICATE | Filas duplicadas completas |
| TYPE_VALIDATION | Errores de tipo por celda |
| FORMAT_INCONSISTENCY | Formatos mezclados en misma columna |
| CASE_INCONSISTENCY | Mayúsculas/minúsculas inconsistentes |
| ENCODING_ERROR | Caracteres mal codificados |
| TEXT_ERRORS | Errores de escritura |
| SUSPICIOUS_VALUE | Valores fuera de patrón esperado |
| BOOLEAN_NONSTANDARD | Valores booleanos no estándar |
| NUMERIC_OUTLIER | Outliers numéricos (IQR) |
| NUMERIC_RANGE | Valores fuera de rango esperado |
| EMPTY_CELLS | Celdas vacías en columna |
| ... y 16 más | Ver `data_engine/diagnostic.py` |

### Clasificación de columnas (FastTextProfiler v3.0)

- **IDENTIFICADOR**: ≥95% valores únicos
- **CONSTANTE**: Un solo valor ≥95%
- **BOOLEANA**: Solo 2-3 valores principales ≥95%
- **CATEGORICA**: Top 3/5/10 valores ≥90%
- **TEXTO_LIBRE**: Ninguna regla matchea

---

## Copiloto IA (Groq/Llama3.1)

- Recomendaciones de depuración por columna (max 80 caracteres por recomendación)
- Chat interactivo para preguntas sobre el dataset
- Funciona sin API key (recomendaciones fallback basadas en diagnóstico)
- Modelo: `llama-3.1-8b-instant` (gratis, ~200ms latencia)

---

## Acciones de Limpieza

| Acción | Descripción |
|--------|-------------|
| `delete_column` | Eliminar columna con justificación |
| `drop_missing_rows` | Eliminar filas con faltantes |
| `fill_missing` | Imputar con media, mediana, moda o valor personalizado |
| `fill_empty` | Rellenar celdas vacías con valor específico |
| `standardize_text` | Estandarizar mayúsculas/minúsculas/título |
| `remove_duplicate_rows` | Eliminar filas duplicadas completas |
| `flag_outliers` | Marcar outliers para revisión |
| `rename_column` | Renombrar columna |
| `replace_value` | Reemplazar un valor específico |
| `change_type` | Cambiar tipo de dato |

---

## API Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/analyze` | Analizar dataset |
| `POST` | `/api/diagnose` | Diagnóstico de 28 categorías |
| `POST` | `/api/clean` | Aplicar acciones de limpieza |
| `POST` | `/api/file/preview` | Detectar encoding/delimitador |
| `POST` | `/api/ai/recommend` | Recomendaciones IA batch |
| `POST` | `/api/ai/chat-column` | Chat IA por columna |
| `POST` | `/api/ai/column-recommendations` | Recomendación IA por columna |
| `POST` | `/api/report/markdown` | Generar informe Markdown |
| `POST` | `/api/report/pdf` | Generar informe PDF |
| `POST` | `/api/report/audit-log` | Generar bitácora de cambios |
| `GET` | `/api/health` | Health check |
| `GET` | `/` | Frontend web |
| `GET` | `/docs` | Documentación Swagger |

---

## Variables de Entorno

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `SUPABASE_URL` | Sí (nube) | URL del proyecto Supabase |
| `SUPABASE_ANON_KEY` | Sí (nube) | Key anon de Supabase |
| `SUPABASE_SERVICE_KEY` | Sí (nube) | Key service_role de Supabase |
| `GROQ_API_KEY` | No | API key de Groq para IA |
| `ALLOWED_ORIGINS` | No | Orígenes CORS (default: `127.0.0.1:8000`) |
| `HOST` | No | Host del servidor (default: `127.0.0.1`) |
| `PORT` | No | Puerto del servidor (default: `8000`) |

---

## Instalación

```bash
# Clonar
git clone https://github.com/Davidcastanom/auditdata-ai.git
cd auditdata-ai

# Entorno virtual
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux

# Dependencias
pip install -r requirements.txt

# Variables de entorno
cp .env.example .env
# Editar .env con tus keys

# Ejecutar
python -m backend.app.server
```

Abrir: **http://127.0.0.1:8000**

---

## Deploy

### Docker

```bash
docker-compose up --build
```

### Render (producción)

- Repo: [Davidcastanom/auditdata-ai](https://github.com/Davidcastanom/auditdata-ai)
- URL: [auditdata-ai-1.onrender.com](https://auditdata-ai-1.onrender.com)
- Variables configuradas en `render.yaml`

---

## Testing

```bash
# Tests Python (18/18)
python -m pytest tests/ -v

# Tests E2E (34/34)
npx playwright test

# Todos
python -m pytest tests/ -v && npx playwright test
```

---

## Paleta de Colores

| Color | Hex | Uso |
|-------|-----|-----|
| Azul eléctrico | `#0066FF` | Botones, links, acentos principales |
| Cian | `#00D4FF` | Acentos especiales, tags |
| Negro | `#0A0A0F` | Fondo principal |
| Gris oscuro | `#12121A` | Tarjetas, superficies |
| Blanco suave | `#F0F0F5` | Texto principal |
| Gris metálico | `#9090A0` | Texto secundario |

---

## Roadmap

### Completado
- [x] Motor de análisis con 4 dimensiones (completitud, consistencia, exactitud, unicidad)
- [x] Diagnóstico de 28 categorías de calidad
- [x] 10 acciones de limpieza documentadas
- [x] Copiloto IA con Groq/Llama3.1 (recomendaciones + chat)
- [x] Reporte PDF con 10 secciones (formato académico, gráficos light theme)
- [x] Reporte Markdown con mismas secciones
- [x] Bitácora de cambios a nivel de celda
- [x] Autenticación Google OAuth + Supabase
- [x] Guardar historial en la nube
- [x] File preview modal (encoding, delimitador, header row)
- [x] Detección automática de dominios de columna (20 reglas)
- [x] FastTextProfiler v3.0 (clasificación por frecuencia)
- [x] 18 tests Python + 34 tests E2E

### Próximo
- [ ] Exportar reporte como DOCX
- [ ] Soporte para múltiples datasets en un mismo proyecto
- [ ] Multi-idioma (español, inglés, portugués)
- [ ] Descripción de cada columna con contexto del negocio

---

## Licencia

MIT License

---

## Autor

**AuditData AI** — Flujo Base Data Quality System

Desarrollado para la comunidad de analistas de datos que necesita herramientas profesionales, documentadas y accesibles.
