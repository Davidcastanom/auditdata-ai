<div align="center">

# AuditData AI

**Plataforma de limpieza y validación de calidad de datos con reportes académicos PDF e IA**

Diagnostica, documenta y prepara tus datasets antes de usarlos en análisis, visualización o toma de decisiones.

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Groq](https://img.shields.io/badge/Groq-Llama3.1--8B-F55036?style=flat-square&logo=groq&logoColor=white)](https://groq.com)
[![Supabase](https://img.shields.io/badge/Supabase-Auth%20%2B%20DB-3ECF8E?style=flat-square&logo=supabase&logoColor=white)](https://supabase.com)
[![Tests](https://img.shields.io/badge/Tests-272%2F272%20passed-brightgreen?style=flat-square)](tests/)
[![Playwright](https://img.shields.io/badge/E2E-44%20passed-brightgreen?style=flat-square)](tests/frontend)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

</div>

---

## 📖 Contenido

- [Qué es AuditData AI](#qué-es-auditdata-ai)
- [Características](#características)
- [Flujo de trabajo: 7 etapas](#flujo-de-trabajo-7-etapas)
- [Arquitectura](#arquitectura)
- [Motor de diagnóstico (28 chequeos, 20 códigos)](#motor-de-diagnóstico-28-chequeos-20-códigos)
- [Copiloto IA](#copiloto-ia)
- [Acciones de limpieza](#acciones-de-limpieza)
- [API](#api)
- [Puntuación de calidad](#puntuación-de-calidad)
- [Autenticación e historial](#autenticación-e-historial)
- [Instalación](#instalación)
- [Pruebas](#pruebas)
- [Despliegue](#despliegue)
- [Variables de entorno](#variables-de-entorno)
- [Roadmap](#roadmap)
- [Licencia](#licencia)

---

## Qué es AuditData AI

AuditData AI es una herramienta de **Flujo Base** diseñada para diagnosticar, documentar y preparar datasets antes de que sean utilizados en análisis, visualización o toma de decisiones.

**La herramienta no inventa datos.** Calcula hallazgos, documenta riesgos y permite que el usuario valide cada decisión con criterio de negocio. Cada acción queda registrada con justificación técnica para garantizar **trazabilidad completa** desde la carga hasta el reporte final.

## Características

- **Diagnóstico de 28 categorías** de problemas de calidad por columna, con severidad, confianza y señal (`CONFIRMADO` / `A_REVISAR`).
- **4 dimensiones de calidad** cuantificadas: completitud, consistencia, exactitud estructural y unicidad.
- **Copiloto IA** (Groq/Llama3.1) que genera recomendaciones accionables y análisis profundo por columna.
- **10 acciones de limpieza** documentadas, reversibles y con bitácora a nivel de celda.
- **Reportes profesionales**: PDF académico (10 secciones), Markdown, bitácora de cambios y exportación XLSX del dataset limpio.
- **Perfilado robusto**: soporte multi-encoding, delimitadores (coma, punto y coma, tab, pipe), headers dinámicos y separadores decimales ambiguos.
- **Autenticación** con Google OAuth y **historial en la nube** vía Supabase.
- **Panel administrativo** con métricas anónimas de uso y gestión de errores.
- **Paneles en español** e interfaz accesible desde el navegador.

## Flujo de trabajo: 7 etapas

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

| Etapa | Descripción |
|---|---|
| **01 — Comprender** | Define la unidad de análisis, el objetivo y carga el dataset |
| **02 — Perfilar** | Diagnóstico técnico automático por columna: tipos, distribución y frecuencias |
| **03 — Reglas** | Documenta decisiones estructurales: categorización de columnas y claves de duplicados |
| **04 — Diagnóstico** | Detección de 28 categorías de problemas por columna + análisis profundo con IA |
| **05 — Depurar** | Aplica acciones de limpieza guiadas por el Copiloto IA; el analista decide |
| **06 — Validar** | Demuestra la calidad del dataset antes de declararlo listo |
| **07 — Informe** | Compila el Data Cleaning Report: PDF académico, Markdown, bitácora y XLSX |

## Arquitectura

```
auditdata-ai/
├── backend/
│   └── app/
│       ├── main.py              # API FastAPI (endpoints + middlewares)
│       ├── reporting.py         # Generación de PDF (10 secciones)
│       ├── metrics.py           # Métricas anónimas de uso + errores (Supabase)
│       ├── auth.py              # Autenticación Google OAuth + Supabase
│       └── server.py            # Runner de Uvicorn
├── data_engine/
│   ├── analyzer.py              # Motor: carga, perfilado, puntajes, limpieza
│   ├── diagnostic.py            # Diagnóstico de 28 categorías (FastTextProfiler v3.0)
│   ├── ai_advisor.py            # Copiloto IA: Groq/Llama3.1 (chat + análisis profundo)
│   ├── sensitive.py             # Detección de columnas con datos sensibles (autorización)
│   ├── domain_rules.py          # 20 reglas de dominio por tipo de columna
│   ├── charts.py                # Gráficos para el reporte PDF
│   └── missing.py               # Tabla central de valores faltantes
├── frontend/
│   ├── index.html               # UI (wizard de 7 pasos)
│   └── src/
│       ├── app.js               # Orquestación de la UI principal
│       ├── nube.js              # Diagnóstico interactivo (Etapa 04)
│       ├── auth.js              # Autenticación + historial en la nube
│       ├── sensitiveConsent.js  # Modal de autorización de datos sensibles
│       ├── router.js            # Navegación por hash
│       ├── state.js             # Estado de la sesión + undo
│       └── admin.js             # Panel administrativo
├── db/migrations/               # Migraciones SQL de Supabase (001-004)
├── docs/                        # Planes, diagnósticos y trazabilidad
├── samples/                     # Datasets de ejemplo (incl. dataset_sucio.csv)
├── tests/                       # Suite de tests (unitarios + integración + E2E)
├── .github/workflows/ci.yml     # CI: pytest en cada push/PR
├── render.yaml                  # Configuración de despliegue en Render
└── requirements.txt             # Dependencias Python
```

## Motor de diagnóstico (28 chequeos, 20 códigos)

El motor de reglas detecta automáticamente **28 chequeos** de problemas de calidad — algunos códigos cubren más de un escenario — agrupados por señal y severidad:

| Código | Descripción | Señal |
|--------|-------------|-------|
| `MISSING` | Valores faltantes (celdas vacías o NULL) | CONFIRMADO |
| `HIDDEN_MISSING` | Placeholders que ocultan faltantes | CONFIRMADO |
| `DUPLICATE` | Valores repetidos en columna ID / filas duplicadas completas | CONFIRMADO |
| `DATE_FORMAT` | Formatos de fecha mezclados en la misma columna | CONFIRMADO |
| `DATE_INVALID` | Fechas imposibles o inconsistentes | CONFIRMADO |
| `NUMERIC_DOMAIN` | Valores fuera del rango permitido por dominio | CONFIRMADO |
| `TYPE_VALIDATION` | Errores de tipo de dato por celda | CONFIRMADO |
| `TYPE_PER_CELL` | Mezcla de numérico y texto en la misma columna | CONFIRMADO |
| `TEXT_ERROR` | Errores de formato (espacios extra, grafía inconsistente) | CONFIRMADO / A_REVISAR |
| `CATEGORICAL` | Inconsistencia categórica (variantes, sospechosas) | A_REVISAR |
| `BOOL_INCONSISTENCY` | Representación booleana inconsistente | A_REVISAR |
| `MIXED_LANG` | Mezcla de idiomas | A_REVISAR |
| `MULTI_VALUE` | Celdas con múltiples valores | A_REVISAR |
| `SCIENTIFIC` | Notación científica no deseada | A_REVISAR |
| `UNIT_ERROR` | Unidades inconsistentes en una columna | A_REVISAR |
| `TEXT_TRUNCATION` | Truncamiento de texto | A_REVISAR |
| `ENCODING` | Problemas de codificación de caracteres | CONFIRMADO |
| `FORMULA_ERROR` | Fórmulas de hoja de cálculo como texto | CONFIRMADO |
| `GHOST_CHAR` | Caracteres invisibles o no imprimibles | CONFIRMADO |

### Clasificación de columnas (FastTextProfiler v3.0)

- **IDENTIFICADOR** — ≥95% valores únicos
- **CONSTANTE** — un solo valor en ≥95% de las filas
- **BOOLEANA** — solo 2-3 valores principales en ≥95%
- **CATEGORICA** — el top 3/5/10 de valores cubre ≥90%
- **TEXTO_LIBRE** — ninguna regla aplica

### Detección de duplicados con columnas clave

El sistema acepta `duplicate_key_columns` para definir qué columnas usar al detectar duplicados (normaliza acentos, mayúsculas y espacios). Por defecto compara filas completas.

## Copiloto IA

El Copiloto usa **Groq** con el modelo `llama-3.1-8b-instant` (gratuito, ~200 ms de latencia). Se integra en dos puntos del flujo:

### 1. Chat interactivo por columna (Etapa 05 — Depurar)
- Conversación en lenguaje natural sobre problemas y acciones de limpieza
- Respuestas estructuradas como listas con viñetas (no párrafos) para ahorrar tokens
- El analista conserva el control final de cada decisión

### 2. Análisis profundo por columna (Etapa 04 — Diagnóstico)
- Disparador manual ("Ejecutar análisis") para no gastar tokens automáticamente
- Analiza todos los valores reales de la columna como un experto senior
- Cada hallazgo incluye la **fila exacta** del archivo y el **valor de ejemplo**
- Caché por columna para evitar re-consultas

### 3. Honestidad y privacidad
- **No inventa columnas:** si pides una columna inexistente, el copiloto responde un error honesto con las columnas disponibles (sin llamar a Groq).
- **Detección de errores de escritura:** reconoce typos en los valores de la columna (p. ej. `juaan` → `juan`) y los muestra como posibles errores.
- **Política de datos honesta:** los prompts del copiloto prohíben afirmar que "los datos no salen del servidor" o que son "100 % privados"; el aviso de privacidad (`/privacidad`) y los términos (`/terminos`) declaran que la IA envía columnas, preguntas y valores de ejemplo a un proveedor externo (Groq).
- **Datos sensibles — autorización expresa:** si el archivo parece contener datos sensibles o personales de alto riesgo (documento/cédula, email, teléfono, salud, biometría, religión, vida sexual, menores, salario/ingresos), la app lo detecta por el nombre de la columna y exige una **autorización explícita, opcional y revocable** antes de enviar cualquier dato a la IA. Sin autorización, el asistente queda deshabilitado para ese archivo; el diagnóstico y la limpieza siguen funcionando.

> **Modo fallback:** sin API key o ante errores de la API (p. ej. límite de tokens por minuto), el motor conserva la justificación técnica de sus reglas y la plataforma sigue funcionando sin degradación funcional.

## Acciones de limpieza

| Acción | Descripción |
|--------|-------------|
| `delete_column` | Elimina una columna con justificación |
| `drop_missing_rows` | Elimina filas con valores faltantes |
| `fill_missing` | Imputa con media, mediana, moda o valor personalizado |
| `fill_empty` | Rellena celdas vacías con un valor específico |
| `standardize_text` | Estandariza mayúsculas, minúsculas o formato título |
| `remove_duplicate_rows` | Elimina filas duplicadas completas |
| `flag_outliers` | Marca outliers (rango IQR 1.5×) para revisión |
| `rename_column` | Renombra una columna |
| `replace_value` | Reemplaza un valor específico por otro |
| `change_type` | Cambia el tipo de dato de una columna |

Toda acción queda registrada en una **bitácora de cambios a nivel de celda** con fila, columna, valor anterior, valor nuevo y justificación.

## API

### Endpoints públicos

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/health` | Estado del servicio |
| `POST` | `/api/analyze` | Perfilado y puntajes de calidad |
| `POST` | `/api/diagnose` | Diagnóstico de 28 categorías |
| `POST` | `/api/file/preview` | Detección de encoding, delimitador y header |
| `POST` | `/api/clean` | Aplica acciones de limpieza + exporta XLSX |
| `POST` | `/api/ai/recommend` | Recomendaciones IA en lote |
| `POST` | `/api/ai/chat-column` | Chat interactivo por columna |
| `POST` | `/api/ai/column-deep-analysis` | Análisis profundo por columna (experto senior) |
| `POST` | `/api/report/markdown` | Informe en Markdown |
| `POST` | `/api/report/pdf` | Informe PDF académico |
| `POST` | `/api/report/audit-log` | Bitácora de cambios |

### Endpoints administrativos (requieren autenticación)

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/admin/metrics` | Métricas agregadas de uso |
| `GET` | `/api/admin/errors` | Errores recientes (pendientes/resueltos) |
| `POST` | `/api/admin/errors/resolve` | Marca errores como resueltos |
| `POST` | `/api/admin/errors/send` | Envía resumen de errores al webhook |

### Otros

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/` | Frontend web |
| `GET` | `/admin` | Panel administrativo |
| `GET` | `/maintenance` | Página de mantenimiento |
| `GET` | `/privacidad` | Aviso de privacidad (RGPD, Ley 1581/2012, CCPA/CPRA) |
| `GET` | `/terminos` | Términos y Condiciones |
| `GET` | `/docs` | Documentación interactiva (Swagger UI) |

## Puntuación de calidad

Cuatro métricas normalizadas a 0-100 que se agregan en un **overall ponderado**:

| Métrica | Fórmula | Peso |
|---|---|---|
| Completitud | `100 − (celdas vacías / total de celdas × 100)` | 30% |
| Consistencia | `100 − (inconsistencias de formato / total de celdas × 100)` | 20% |
| Exactitud estructural | `100 − ((errores de tipo + valores atípicos) / total de celdas × 100)` | 35% |
| Unicidad | `100 − (filas duplicadas / total de filas × 100)` | 15% |

Los valores atípicos se calculan con **rango intercuartílico (IQR, 1.5×)**. Durante la limpieza, los límites IQR del dataset original se **congelan** para que las acciones correctivas no degraden la exactitud de un dataset que ya fue limpiado.

## Autenticación e historial

- **Login** con Google OAuth gestionado por Supabase Auth.
- **Consentimiento de tratamiento de datos** registrado antes de guardar historial (`user_consents`), versionado (v2.1) con re-aceptación automática al cambiar las políticas.
- **Datos sensibles:** la app pide una **autorización expresa separada** (v1.0, por sesión) antes de que la IA procese archivos que parecen contener datos sensibles; es opcional y revocable (se limpia al cerrar sesión).
- El **historial en la nube** guarda por usuario: ficha del dataset, diagnóstico, sesión de limpieza y PDF (`datasets`, `analyses`, `cleaning_sessions`).
- Cada usuario puede **eliminar su propio historial** (migración 004 + botón en la UI).
- Las **métricas de uso** son anónimas: hash del cliente, endpoint, status y duración — nunca el contenido de los datasets.

## Instalación

### Requisitos

- Python **3.10+**
- Node.js (solo para tests E2E con Playwright)

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/Davidcastanom/auditdata-ai.git
cd auditdata-ai

# 2. Crear y activar el entorno virtual
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus claves (ver tabla de variables)

# 5. Arrancar el servidor de desarrollo
python -m backend.app.server
```

Abrir en el navegador: **http://127.0.0.1:8000**

## Pruebas

```bash
# Suite completa de Python (272 tests)
python -m pytest tests/ -q --ignore=tests/frontend

# Pruebas por módulo
python -m pytest tests/test_api.py -v             # Endpoints de la API
python -m pytest tests/test_ai_advisor.py -v     # Copiloto IA (contexto, typos, datos sensibles)
python -m pytest tests/test_analyzer.py -v        # Motor de análisis
python -m pytest tests/test_characterization.py -v  # Caracterización
python -m pytest tests/test_golden_algoritmo.py -v  # Golden tests del algoritmo
python -m pytest tests/test_golden_motor.py -v    # Golden tests del motor
python -m pytest tests/test_f7_validation.py -v   # Validación E2E de flujo completo

# Tests E2E de frontend (Playwright, 44 tests)
npx playwright test

# Lint
python -m ruff check --select F,E9 data_engine backend
```

## Despliegue

### Render (producción)

- **Repositorio:** [Davidcastanom/auditdata-ai](https://github.com/Davidcastanom/auditdata-ai)
- **URL:** [auditdata-ai-1.onrender.com](https://auditdata-ai-1.onrender.com)
- **Despliegue:** automático desde la rama `main` en GitHub
- **Configuración:** `render.yaml` + variables de entorno en el dashboard

> `GROQ_API_KEY` y `Recomendaciones_de_copiloto` se declaran en `render.yaml` con `sync: false` y se configuran manualmente en el dashboard de Render.

## Variables de entorno

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `SUPABASE_URL` | Sí (nube) | URL del proyecto Supabase |
| `SUPABASE_ANON_KEY` | Sí (nube) | Clave anónima de Supabase |
| `SUPABASE_SERVICE_KEY` | Sí (nube) | Clave `service_role` de Supabase |
| `GROQ_API_KEY` | No | Clave de Groq (chat + recomendaciones) |
| `Recomendaciones_de_copiloto` | No | Clave de Groq (análisis profundo) |
| `METRICS_SECRET` | No | Secreto para métricas anónimas (HMAC) |
| `ADMIN_TOKEN` | No | Token interno para el panel admin |
| `ADMIN_EMAILS` | No | Emails autorizados como administradores |
| `MAKE_WEBHOOK_URL` | No | Webhook para el resumen de errores |
| `ALLOWED_ORIGINS` | No | Orígenes CORS (default: `127.0.0.1:8000`) |
| `HOST` | No | Host del servidor (default: `127.0.0.1`) |
| `PORT` | No | Puerto del servidor (default: `8000`) |

## Roadmap

### Completado

**Motor de datos**
- [x] Motor de análisis con 4 dimensiones de calidad (completitud, consistencia, exactitud, unicidad)
- [x] Diagnóstico de 28 categorías con severidad, confianza y señal
- [x] FastTextProfiler v3.0 (clasificación por frecuencia con guard clause)
- [x] Duplicados configurables por columnas clave (`key_columns`)
- [x] 20 reglas de dominio por tipo de columna
- [x] Carga robusta: multi-encoding, delimitadores, headers dinámicos, separadores ambiguos
- [x] Límites IQR congelados post-limpieza (las acciones correctivas no degradan la calidad)

**Limpieza e IA**
- [x] 10 acciones de limpieza documentadas con bitácora a nivel de celda
- [x] Copiloto IA Groq/Llama3.1: chat por columna + análisis profundo con fila exacta
- [x] Lote de IA optimizado para el límite de tokens por minuto de Groq free
- [x] Contexto estable y cacheado por archivo (sin error 413 de Groq)
- [x] Honestidad del copiloto: columna inexistente responde error real, detección de typos
- [x] Política de datos robusta: modal de consentimiento versionado, aviso de privacidad y términos
- [x] Datos sensibles: autorización expresa, opcional y revocable antes de enviar datos a la IA

**Reportes**
- [x] Reporte PDF académico con 10 secciones y gráficos
- [x] Reporte Markdown y exportación XLSX del dataset limpio
- [x] Bitácora de cambios a nivel de celda

**Plataforma**
- [x] Autenticación Google OAuth + Supabase
- [x] Historial en la nube con consentimiento y borrado propio
- [x] Panel administrativo con métricas anónimas y gestión de errores
- [x] File preview modal (encoding, delimitador, header row dinámico)
- [x] Plantillas de dataset (Ventas, RRHH, Financiero, General)
- [x] CI: pytest en cada push/PR + 272 tests Python + 44 E2E Playwright

### Próximos pasos

- [ ] Aplicar todas las recomendaciones seguras con un solo clic (H1c)
- [ ] Rangos de validación configurables por columna
- [ ] Chat conectado a la detección de duplicados
- [ ] Exportar reporte como DOCX
- [ ] Multi-idioma (español, inglés, portugués)
- [ ] GitHub Actions con cobertura de código y E2E

---

## Licencia

Distribuido bajo la **MIT License**.

---

**AuditData AI** — Flujo Base Data Quality System.

Desarrollado para la comunidad de analistas de datos que necesita herramientas profesionales, documentadas y accesibles.
