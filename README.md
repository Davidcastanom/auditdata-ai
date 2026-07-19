# AuditData AI

AuditData AI es una herramienta de Flujo Base para diagnosticar, documentar y preparar datasets antes de usarlos en analisis, visualizacion o toma de decisiones.

La aplicacion combina:

- Frontend web modular.
- Backend local en Python.
- Motor reutilizable de calidad de datos.
- Exportacion de reportes en Markdown y PDF.
- Design System basado en la paleta oficial del proyecto.

## Objetivo

Convertir la limpieza de datos en un proceso profesional, explicable y reutilizable para cualquier dataset CSV o XLSX.

La herramienta no inventa datos. Calcula hallazgos, documenta riesgos y permite que el usuario valide las decisiones con criterio de negocio.

## Paleta estandar

| Color | Hex | Uso |
|---|---|---|
| Azul electrico | `#0066FF` | Botones, links, acentos principales |
| Azul oscuro | `#0052CC` | Hover, enfasis secundario |
| Cian | `#00D4FF` | Acentos especiales, tags |
| Negro | `#0A0A0F` | Fondo principal |
| Gris oscuro | `#12121A` | Tarjetas, superficies |
| Blanco suave | `#F0F0F5` | Texto principal |
| Gris metalico | `#9090A0` | Texto secundario, fechas |

Colores complementarios definidos para estados:

- Exito: `#22C55E`
- Advertencia: `#F59E0B`
- Error: `#EF4444`
- Borde tecnico: `#242436`
- Superficie secundaria: `#181824`

## Arquitectura

```text
auditdata-ai/
  backend/
    app/
      reporting.py       # Generacion de PDF profesional
      server.py          # API local y servidor del frontend
  data_engine/
    analyzer.py          # Cerebro Python reutilizable
  frontend/
    index.html           # Pagina principal
    src/
      app.js             # Orquestacion de la UI
      styles/
        design-system.css
  docs/
    architecture/
    brand/
  samples/
  templates/
    reports/
  output/
  README.md
```

## Como ejecutar

Desde la raiz del proyecto:

```bash
python -m backend.app.server
```

Luego abre:

```text
http://127.0.0.1:8000
```

Si usas el runtime incluido de Codex en Windows, tambien puedes ejecutar con la ruta completa del Python incluido.

## Funcionalidades actuales

- Carga de archivos `.csv`, `.xlsx` y `.xlsm`.
- Deteccion automatica de tipos: texto, numero, fecha y booleano.
- Conteo de valores faltantes.
- Deteccion de filas duplicadas completas.
- Deteccion de inconsistencias simples de formato.
- Deteccion de outliers numericos con IQR.
- Score de calidad por dimension.
- Vista previa de hallazgos por columna.
- Reporte Markdown descargable.
- Reporte PDF descargable con paleta del proyecto.

## Cerebro Python

El archivo `data_engine/analyzer.py` concentra la logica de calidad de datos.

Esta separacion permite reutilizar el motor en:

- una API profesional con FastAPI,
- automatizaciones,
- notebooks,
- jobs programados,
- integraciones futuras con IA,
- flujos de GitHub Actions.

## IA

La implementacion de IA sigue en pie, pero debe integrarse de forma segura.

Regla tecnica:

- La IA no debe ejecutarse con credenciales expuestas en el navegador.
- El backend debe actuar como intermediario.
- La IA debe sugerir criterios, narrativa y reglas de negocio.
- El motor Python debe calcular los hallazgos reales.

## Roadmap recomendado

1. Agregar FastAPI para una API mas robusta.
2. Integrar proveedor de IA desde backend con variables de entorno.
3. Agregar historial de acciones de limpieza.
4. Permitir aplicar transformaciones y exportar dataset limpio.
5. Crear plantillas PDF avanzadas por tipo de cliente.
6. Agregar pruebas unitarias al motor Python.
7. Configurar repositorio GitHub con Issues, Releases y GitHub Actions.

## Subir a GitHub

Cuando el repositorio local este listo:

```bash
git init
git add .
git commit -m "Initial AuditData AI architecture"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/auditdata-ai.git
git push -u origin main
```

Nota: en esta carpeta existe una entrada `.git`, pero `git status` no la reconoce como repositorio valido. Antes de subir, conviene revisar si esa carpeta esta vacia o corrupta.

## Biblioteca Estrategica Flujo Base

Categorias aplicables:

- Desarrollo
- UX
- Diseno
- Brand Book
- Automatizacion
- GitHub
- Documentacion
- Negocio

