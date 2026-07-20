# AuditData AI

**Herramienta profesional de limpieza y validación de calidad de datos con reportes PDF**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/Tests-13%2F13%20passing-brightgreen.svg)](tests/)
[![Deploy](https://img.shields.io/badge/Deploy-Render-blue.svg)](https://auditdata-ai-1.onrender.com)

---

## ¿Qué es AuditData AI?

AuditData AI es una herramienta de **Flujo Base** para diagnosticar, documentar y preparar datasets antes de usarlos en análisis, visualización o toma de decisiones.

La herramienta **no inventa datos**. Calcula hallazgos, documenta riesgos y permite que el usuario valide las decisiones con criterio de negocio. Cada acción queda registrada con justificación técnica para garantizar trazabilidad completa.

### Flujo de 6 Etapas

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  01         │    │  02         │    │  03         │
│  Comprender │───▶│  Perfilar   │───▶│  Reglas     │
└─────────────┘    └─────────────┘    └─────────────┘
                                              │
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  06         │    │  05         │    │  04         │
│  Informe    │◀───│  Validar    │◀───│  Depurar    │
└─────────────┘    └─────────────┘    └─────────────┘
```

1. **Comprender** — Define la unidad de análisis y carga el dataset
2. **Perfilar** — Diagnóstico técnico automático por columna
3. **Reglas** — Clasifica columnas y documenta decisiones estructurales
4. **Depurar** — Aplica acciones de limpieza con criterio documentado
5. **Validar** — Demuestra la calidad antes de declarar el dataset listo
6. **Informe** — Compila Data Cleaning Report en PDF (formato académico) y Markdown

---

## Instalación

### Requisitos

- Python 3.10 o superior
- pip

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/Davidcastanom/auditdata-ai.git
cd auditdata-ai

# 2. Crear entorno virtual
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. (Opcional) Instalar con dependencias de IA y desarrollo
pip install -e ".[ai,dev]"

# 5. Copiar variables de entorno
cp .env.example .env

# 6. Ejecutar la aplicación
python -m backend.app.server
```

Abrir en el navegador: **http://127.0.0.1:8000**

---

## Estructura del Proyecto

```
auditdata-ai/
├── backend/
│   └── app/
│       ├── main.py          # API FastAPI + Pydantic v2
│       ├── reporting.py     # Generación de PDF (10 secciones)
│       └── server.py        # Runner de Uvicorn
├── data_engine/
│   └── analyzer.py          # Motor de análisis de calidad
├── frontend/
│   ├── index.html           # UI principal
│   └── src/
│       ├── app.js           # Orquestación de la UI
│       ├── router.js        # Navegación por hash
│       ├── state.js         # Estado con localStorage + undo individual
│       └── styles/
│           └── design-system.css
├── tests/
│   ├── test_analyzer.py     # Tests del motor
│   └── test_api.py          # Tests de integración (13 tests)
├── samples/
│   └── moveup_sample.csv    # Dataset de ejemplo
├── docs/
│   ├── architecture/
│   └── brand/
├── .env.example
├── pyproject.toml
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## Funcionalidades

### Motor de Análisis (`data_engine/analyzer.py`)

- Detección automática de tipos: texto, número, fecha, booleano
- Conteo de valores faltantes por columna
- Detección de filas duplicadas completas
- Detección de inconsistencias de formato y variantes de texto
- Detección de outliers numéricos con IQR (rango intercuartílico)
- Score de calidad por dimensión (completitud, consistencia, exactitud, unicidad)
- Recomendaciones automáticas priorizadas
- Análisis independiente del web server (reutilizable desde CLI, notebook o automatización)

### Acciones de Limpieza

| Acción | Descripción |
|--------|-------------|
| `delete_column` | Eliminar columna con justificación |
| `drop_missing_rows` | Eliminar filas con faltantes |
| `impute_missing` | Imputar con media, mediana, moda o valor personalizado |
| `standardize_text` | Estandarizar mayúsculas/minúsculas/título |
| `remove_duplicate_rows` | Eliminar filas duplicadas completas |
| `flag_outliers` | Marcar outliers para revisión |
| `rename_column` | Renombrar columna |
| `replace_value` | Reemplazar un valor específico |
| `change_type` | Cambiar tipo de dato |

### Bitácora de Decisiones

- Cada acción queda documentada: problema, tratamiento, justificación y resultado
- **Botón ✕ individual** en cada entrada para deshacer una acción específica sin afectar las demás
- Botón global "Deshacer" para quitar la última acción rápidamente
- Justificaciones generadas con IA (Gemini) cuando la API key está configurada

### Reportes PDF (Formato Académico)

El informe PDF contiene **10 secciones** completas:

| Sección | Contenido |
|---------|-----------|
| 1. Información General | Dataset, analista, registros antes/después, fecha, herramienta |
| 2. Resumen Ejecutivo | Narrativa con conteos de problemas y % de calidad |
| 3. Indicadores Clave | Tabla antes/después de las 4 dimensiones + general |
| 4. Problemas Encontrados | 6 subsecciones: faltantes, duplicados, escritura, formatos, categorías, atípicos |
| 5. Outliers y Fuera de Rango | Tabla detallada con min, max, media, mediana, ejemplos |
| 6. Plan y Acciones | Tabla numerada con columna, acción, justificación, resultado |
| 7. Evaluación de Calidad | Comparación antes/después con cambio calculado |
| 8. Checklist | 6 criterios de validación con estado |
| 9. Riesgos | Lista dinámica según scores |
| 10. Metodología y Conclusión | Fórmulas de cálculo y recomendación final |

### Otros Formatos

- **Markdown** — Informe transparente y versionable (mismas 10 secciones)
- **CSV** — Dataset limpio descargable

---

## API Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/analyze` | Analizar dataset |
| `POST` | `/api/clean` | Aplicar acciones de limpieza |
| `POST` | `/api/report/markdown` | Generar informe Markdown |
| `POST` | `/api/report/pdf` | Generar informe PDF |
| `GET` | `/api/health` | Health check |
| `GET` | `/` | Frontend web |
| `GET` | `/docs` | Documentación Swagger |

### Ejemplo de Request

```bash
# Analizar un dataset
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "datos.csv",
    "content_base64": "aWQsbm9tYnJlCjEsQW5hCjIsSnVhbg=="
  }'
```

---

## Deploy

### Opción 1: Docker

```bash
docker-compose up --build
```

### Opción 2: Render (producción actual)

1. Repositorio conectado: [Davidcastanom/auditdata-ai](https://github.com/Davidcastanom/auditdata-ai)
2. Deploy activo en: [auditdata-ai-1.onrender.com](https://auditdata-ai-1.onrender.com)
3. Variables de entorno configuradas:
   - `ALLOWED_ORIGINS`: URL del deploy
   - `GEMINI_API_KEY`: (opcional) Para justificaciones con IA

### Opción 3: Local

```bash
python -m backend.app.server
```

---

## Paleta de Colores

| Color | Hex | Uso |
|-------|-----|-----|
| Azul eléctrico | `#0066FF` | Botones, links, acentos principales |
| Azul oscuro | `#0052CC` | Hover, énfasis secundario |
| Cian | `#00D4FF` | Acentos especiales, tags |
| Negro | `#0A0A0F` | Fondo principal |
| Gris oscuro | `#12121A` | Tarjetas, superficies |
| Blanco suave | `#F0F0F5` | Texto principal |
| Gris metálico | `#9090A0` | Texto secundario |

---

## Testing

```bash
# Ejecutar todos los tests
python -m pytest tests/ -v

# Output:
# test_analyze_dataset ................... PASSED
# test_cleaning_actions ................. PASSED
# test_health ........................... PASSED
# test_root_returns_html ................ PASSED
# test_docs_available ................... PASSED
# test_analyze_valid_csv ................ PASSED
# test_analyze_invalid_format ........... PASSED
# test_analyze_invalid_base64 ........... PASSED
# test_clean_with_actions ............... PASSED
# test_cleaning_markdown_report ......... PASSED
# test_cleaning_pdf_report .............. PASSED
# test_markdown_report_from_analysis .... PASSED
# test_pdf_report_from_analysis ......... PASSED
# -----------------------------------------------
# 13 passed in ~3s
```

---

## Variables de Entorno

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `GEMINI_API_KEY` | No | API key de Google Gemini para justificaciones con IA |
| `HOST` | No | Host del servidor (default: `127.0.0.1`) |
| `PORT` | No | Puerto del servidor (default: `8000`) |
| `ALLOWED_ORIGINS` | No | Orígenes permitidos para CORS (separados por coma) |

---

## Roadmap

### Completado
- [x] Motor de análisis de calidad con 4 dimensiones
- [x] 9 acciones de limpieza documentadas
- [x] Reporte PDF con 10 secciones (formato académico)
- [x] Reporte Markdown con mismas 10 secciones
- [x] Justificaciones con IA (Gemini)
- [x] Deshacer individual por acción
- [x] Loading overlay con spinner
- [x] Paleta de colores unificada en todo el stack
- [x] Tests automatizados (13/13)
- [x] Deploy en Render

### Próximo
- [ ] **IA: Sugerencia automática de acciones de limpieza** basada en el diagnóstico
- [ ] **IA: Chat asistente** para resolver dudas sobre el dataset
- [ ] **IA: Clasificación automática de outliers** (error vs dato real)
- [ ] **IA: Generación de reglas de validación** por tipo de industria
- [ ] Descripción de cada columna con contexto del negocio
- [ ] Soporte para múltiples datasets en un mismo proyecto
- [ ] Historial de análisis en base de datos
- [ ] Autenticación de usuarios
- [ ] Exportar reporte como DOCX
- [ ] Multi-idioma (español, inglés, portugués)

---

## Licencia

MIT License

---

## Autor

**AuditData AI** — Flujo Base Data Quality System

Desarrollado para la comunidad de analistas de datos que necesita herramientas profesionales, documentadas y accesibles.
