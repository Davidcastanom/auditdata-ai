# AuditData AI

**Herramienta profesional de limpieza y validación de calidad de datos con reportes PDF**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/Tests-10%2F10%20passing-brightgreen.svg)](tests/)

---

## ¿Qué es AuditData AI?

AuditData AI es una herramienta de **Flujo Base** para diagnosticar, documentar y preparar datasets antes de usarlos en análisis, visualización o toma de decisiones.

La herramienta **no inventa datos**. Calcula hallazgos, documenta riesgos y permite que el usuario valide las decisiones con criterio de negocio.

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
6. **Informe** — Compila Data Cleaning Report en PDF y Markdown

---

## Instalación

### Requisitos

- Python 3.10 o superior
- pip

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/TU_USUARIO/auditdata-ai.git
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
│       ├── main.py          # API FastAPI
│       ├── reporting.py     # Generación de PDF
│       └── server.py        # Runner de Uvicorn
├── data_engine/
│   └── analyzer.py          # Motor de análisis de calidad
├── frontend/
│   ├── index.html           # UI principal
│   └── src/
│       ├── app.js           # Orquestación de la UI
│       ├── router.js        # Navegación por hash
│       ├── state.js         # Estado con localStorage
│       └── styles/
│           └── design-system.css
├── tests/
│   ├── test_analyzer.py     # Tests del motor
│   └── test_api.py          # Tests de integración
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
- Detección de inconsistencias de formato
- Detección de outliers numéricos con IQR
- Score de calidad por dimensión (completitud, consistencia, exactitud, unicidad)
- Recomendaciones automáticas priorizadas

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

### Reportes

- **PDF** — Informe ejecutivo profesional con paleta del proyecto
- **Markdown** — Informe transparente y versionable
- **CSV** — Dataset limpio descargable

---

## API Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/analyze` | Analizar dataset |
| `POST` | `/api/clean` | Aplicar acciones de limpieza |
| `POST` | `/api/report/markdown` | Generar informe Markdown |
| `POST` | `/api/report/pdf` | Generar informe PDF |
| `GET` | `/` | Frontend web |
| `GET` | `/docs` | Documentación Swagger |

---

## Deploy

### Opción 1: Docker

```bash
docker-compose up --build
```

### Opción 2: Railway / Render

1. Subir el repositorio a GitHub
2. Conectar el repositorio en Railway o Render
3. Configurar variables de entorno:
   - `ALLOWED_ORIGINS`: URL de tu deploy
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
python -m unittest discover -s tests -v

# Output esperado:
# test_analyze_dataset ... ok
# test_cleaning_actions ... ok
# test_analyze_valid_csv ... ok
# test_analyze_invalid_format ... ok
# test_analyze_invalid_base64 ... ok
# test_clean_with_actions ... ok
# test_root_returns_html ... ok
# test_docs_available ... ok
# test_markdown_report_from_analysis ... ok
# test_pdf_report_from_analysis ... ok
# ---
# Ran 10 tests in 0.082s
# OK
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

- [ ] Autenticación de usuarios
- [ ] Historial de análisis en base de datos
- [ ] Integración con IA para sugerir reglas automáticas
- [ ] Plantillas PDF avanzadas por tipo de cliente
- [ ] Multi-idioma (español, inglés, portugués)
- [ ] API pública con rate limiting
- [ ] Deploy automático con GitHub Actions

---

## Licencia

MIT License - Ver [LICENSE](LICENSE) para detalles.

---

## Autor

**AuditData AI** — Flujo Base Data Quality System

Desarrollado para la comunidad de analistas de datos que necesita herramientas profesionales, documentadas y accesibles.
