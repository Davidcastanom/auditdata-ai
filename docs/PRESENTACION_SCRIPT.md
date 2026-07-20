# AuditData AI — Guion de Presentación

**Formato:** Storytelling para audiencia (analistas, gerentes, comunidad de datos)
**Duración estimada:** 15-20 minutos
**Objetivo:** Mostrar el problema, la solución, lo que se construyó y hacia dónde va

---

## ACTO 1: EL PROBLEMA (3 min)

### Slide 1 — La realidad del analista

> "Imagínense esto: les llega un dataset de 500 filas. Lo abren en Excel. Ven filas vacías, ciudades escritas diferente, una edad de 450 años. Y alguien les dice: 'Límpialo y dame un reporte para el lunes.'"

**Dato duro:**
- El 80% del tiempo de un proyecto de datos se gasta en limpiar y preparar datos
- Solo el 20% restante es análisis real y generación de valor
- No existe una herramienta estándar que documente qué se hizo, por qué y con qué resultado

### Slide 2 — El problema real no es limpiar

> "Limpiar datos no es el problema. Cualquiera puede borrar una fila vacía. El problema es que no queda registro de por qué la borraste. Y tres meses después, alguien te pregunta: '¿Por qué esta fila no está?' Y no tienes respuesta."

**El problema real:**
- Falta de trazabilidad
- Falta de documentación metodológica
- Decisiones tomadas sin criterio documentado
- Reportes que no siguen un formato estándar

### Slide 3 — La metodología que inspira

> "Este proyecto nace de una metodología de análisis de datos enseñada en 4 sesiones: Comprensión, Perfilado, Reglas, Depuración, Validación y Reporte. La pregunta fue: ¿y si automatizamos el proceso pero mantenemos el criterio humano?"

**La metodología Sesiones 4-7:**
1. Entender qué representa cada fila antes de borrar
2. Nunca inventar datos
3. Diferenciar errores de outliers
4. Documentar cada decisión
5. Validar antes de declarar listo

---

## ACTO 2: LA SOLUCIÓN (5 min)

### Slide 4 — ¿Qué es AuditData AI?

> "AuditData AI es una herramienta web que acompaña al analista en las 6 etapas del proceso de limpieza: desde entender el dataset hasta generar el informe final en PDF."

**Definición técnica:**
- Herramienta web (FastAPI + JavaScript vanilla)
- Motor de análisis en Python independiente del servidor
- Reportes PDF con formato académico de 10 secciones
- Justificaciones generadas con IA (Google Gemini)

### Slide 5 — El flujo visual

> "El analista sigue un camino claro. Cada paso tiene un propósito. Nada se salta. Nada se pierde."

```
📁 Carga el dataset
   ↓
📊 Perfila automáticamente (tipos, faltantes, outliers, duplicados)
   ↓
📋 Revisa columnas y elimina las que no aportan (con justificación)
   ↓
🔧 Depura con criterio: imputar, estandarizar, eliminar duplicados
   ↓
✅ Valida calidad antes vs después
   ↓
📄 Genera informe PDF de 10 secciones + dataset limpio CSV
```

### Slide 6 — Lo que el usuario ve

> "No es una caja negra. El usuario ve cada problema, decide qué hacer, y justifica por qué. La herramienta acompaña, no reemplaza."

**Capturas de pantalla sugeridas:**
- Step 1: Tabla de perfilado con métricas por columna
- Step 3: Cards de problemas con acciones sugeridas
- Step 4: Tabla comparativa antes/después
- Step 5: Preview del informe con secciones documentadas

---

## ACTO 3: LO QUE SE CONSTRUYÓ (5 min)

### Slide 7 — Motor de análisis (el cerebro)

> "El motor de análisis es independiente del servidor. Puede usarse desde una línea de comandos, un notebook, o una API. No depende de la interfaz web."

**Qué hace:**
- Detecta tipos automáticamente (texto, número, fecha, booleano)
- Cuenta faltantes por columna (incluyendo 'na', 'null', 'nan', '-')
- Detecta filas duplicadas completas
- Identifica variantes de texto ('Bogota', 'bogota', 'BOGOTA')
- Calcula outliers con IQR (rango intercuartílico)
- Genera scores por dimensión: completitud, consistencia, exactitud, unicidad

### Slide 8 — Reportes PDF formatо académico

> "El informe no es una tabla random. Son 10 secciones que siguen el estándar académico de reportes de limpieza de datos."

**Las 10 secciones:**
1. Información General
2. Resumen Ejecutivo
3. Indicadores Clave (antes/después)
4. Problemas Encontrados (6 dimensiones)
5. Outliers y Fuera de Rango
6. Plan y Acciones de Limpieza
7. Evaluación de Calidad
8. Checklist de Validación
9. Riesgos Identificados
10. Metodología de Cálculo y Conclusión

### Slide 9 — Bitácora de decisiones

> "Cada acción queda registrada. Qué se hizo, por qué, con qué resultado. Y si te arrepientes, puedes deshacer una acción individual sin afectar las demás."

**Características:**
- Cada acción tiene: columna, tratamiento, justificación, resultado
- Botón ✕ individual para deshacer (no solo el último)
- Justificaciones generadas con IA cuando hay API key
- Trazabilidad completa para auditoría

### Slide 10 — Números del proyecto

> "Veamos qué hay detrás."

| Métrica | Valor |
|---------|-------|
| Archivos de código | 12 archivos core |
| Tests automatizados | 13/13 pasando |
| Acciones de limpieza soportadas | 9 tipos |
| Secciones del reporte PDF | 10 |
| Endpoints API | 7 |
| Despliegue | Render (producción activa) |
| Dependencias Python | 4 principales |

---

## ACTO 4: VENTAJAS Y DESVENTAJAS (3 min)

### Slide 11 — Ventajas

> "¿Por qué usar esto en vez de limpiar manualmente en Excel?"

**Ventajas clave:**
1. **Documentación automática** — Cada decisión queda registrada con justificación
2. **Formato estándar** — El reporte PDF sigue un formato académico consistente
3. **Sin inventar datos** — La herramienta nunca corrige sin que el usuario apruebe
4. **Trazabilidad** — Tres meses después puedes responder por qué borraste esa fila
5. **IA integrada** — Justificaciones profesionales generadas automáticamente
6. **Gratuita** — Código abierto, sin licencias
7. **Reutilizable** — El motor funciona desde CLI, notebook o API

### Slide 12 — Desventajas y limitaciones

> "Ninguna herramienta es perfecta. Seamos honestos."

**Limitaciones actuales:**
1. **Sin autenticación** — Cualquiera con la URL puede usarla
2. **Límite de 10MB** — Datasets grandes no se pueden cargar
3. **IA dependiente de API key** — Sin Gemini key, no hay justificaciones con IA
4. **Un dataset a la vez** — No soporta comparación multi-dataset
5. **Sin base de datos** — Los datos se pierden al cerrar el navegador (solo localStorage)
6. **Single-user** — No está diseñada para múltiples usuarios simultáneos
7. **Sin historial** — No hay registro de análisis anteriores

### Slide 13 — ¿Para quién SÍ es?

> "Esta herramienta no es para todos. Pero para el analista que necesita documentar sus decisiones, es exactamente lo que falta."

**Público ideal:**
- Analistas de datos que entregan reportes a clientes
- Equipos de BI que necesitan trazabilidad
- Estudiantes de análisis de datos
- Consultores que deben justificar cada decisión
- Cualquiera que limpie datos más de 2 veces al mes

---

## ACTO 5: HACIA DÓNDE VA (3 min)

### Slide 14 — El roadmap de IA

> "El siguiente paso es inyectar inteligencia artificial. No para reemplazar al analista, sino para reducir su carga cognitiva."

**5 fases de IA:**

| Fase | Qué hace | Impacto |
|------|----------|---------|
| 1. Sugerencias | La IA sugiere acciones después del perfilado | Alto |
| 2. Chat | Panel de preguntas sobre el dataset | Alto |
| 3. Clasificación | IA clasifica outliers como error vs real | Medio |
| 4. Reglas por industria | Genera reglas de validación por sector | Alto |
| 5. Resumen narrativo | Genera el resumen ejecutivo del PDF | Medio |

### Slide 15 — Ejemplo de la Fase 1

> "Imaginen esto: carga el dataset, la herramienta lo perfila, y automáticamente aparecen sugerencias."

```
┌─ La IA sugiere ──────────────────────────────────────┐
│                                                       │
│ 🔴 "edad" → Valor 450 es imposible.                  │
│    Acción: Revisar con fuente original.               │
│    Confianza: 95%                                     │
│                                                       │
│ 🟡 "ciudad" → 3 variantes detectadas.                 │
│    Acción: Estandarizar a Title Case.                 │
│    Confianza: 90%                                     │
│                                                       │
│ 🟢 "horas_sueno" → Solo 2 vacíos.                    │
│    Acción: Imputar con mediana.                       │
│    Confianza: 85%                                     │
│                                                       │
│    [Aceptar todas] [Revisar una por una] [Ignorar]    │
└───────────────────────────────────────────────────────┘
```

### Slide 16 — Costos de la IA

> "¿Cuánto cuesta? Para 1,000 datasets al mes, approximately $20 USD."

| Concepto | Costo |
|----------|-------|
| Gemini Flash (modelo usado) | ~$0.002 / dataset |
| 5 fases completas por dataset | ~$0.02 / dataset |
| 1,000 datasets/mes | ~$20 / mes |
| Sin API key | La herramienta funciona igual |

---

## ACTO 6: CIERRE (2 min)

### Slide 17 — El mensaje central

> "AuditData AI no es una herramienta que limpia datos por ti. Es una herramienta que te acompaña mientras limpias, documenta lo que haces, y genera el reporte que necesitas entregar. El criterio es tuyo. La trazabilidad es nuestra."

### Slide 18 — Demo en vivo (opcional)

> "Ahora les muestro cómo funciona en la práctica."

**Demo de 3 minutos:**
1. Cargar dataset de ejemplo (muestra)
2. Ver perfilado automático
3. Eliminar una columna con justificación
4. Imputar faltantes
5. Ver comparación antes/después
6. Descargar PDF

### Slide 19 — Call to action

> "Esto es código abierto. Está disponible en GitHub. Pueden probarlo ahora mismo en producción."

- **URL producción:** auditdata-ai-1.onrender.com
- **Repositorio:** github.com/Davidcastanom/auditdata-ai
- **Documentación:** README.md + docs/AI_IMPLEMENTATION_PLAN.md

### Slide 20 — Preguntas

> "¿Qué dudas tienen?"

---

## NOTAS PARA EL PRESENTADOR

### Consejos de entrega
1. **Empieza con el problema**, no con la solución. La audiencia necesita sentir el dolor antes de ver la cura.
2. **Usa el dataset de ejemplo** para la demo. No intentes limpiar un dataset real en vivo.
3. **Menciona la metodología** (Sesiones 4-7). Esto legitima el enfoque académico.
4. **Sé honesto sobre limitaciones**. La audiencia respeta la transparencia.
5. **Termina con la IA**. Es lo más emocionante y deja buzz en la audiencia.

### Preguntas frecuentes esperadas
- **¿Es mejor que Excel?** → No es una competencia. Es complementario. Excel no documenta decisiones.
- **¿Cuánto cuesta?** → Gratis. Código abierto. La IA cuesta ~$0.02/dataset.
- **¿Funciona con datasets grandes?** → Límite actual: 10MB. Próxima versión: procesamiento por lotes.
- **¿Puedo integrarlo con mi sistema?** → Sí. El motor es independiente y tiene API REST.

### Métricas para mencionar
- 13 tests automatizados pasando
- 10 secciones en el reporte PDF
- 9 acciones de limpieza disponibles
- 5 fases de IA planeadas
- ~$0.02 costo por dataset con IA
