# AuditData AI — Plan de Corrección y Plan de Competitividad

**Fecha:** Julio 2026
**Alcance:** Corregir defectos confirmados en `analyzer.py` / `app.js` / landing sin romper lo que ya funciona, y trazar la ruta a un producto competitivo.

---

## PARTE 1 — Plan de corrección de defectos (sin generar fisuras)

### Principio rector

Cada fix se implementa con **comportamiento por defecto = comportamiento actual**. Nada de lo que ya funciona debe cambiar de resultado a menos que el analista active explícitamente la mejora. Esto convierte cada cambio en *aditivo*, no en *reemplazo* — la forma más segura de tocar un motor de análisis que ya está en producción.

### Fase 0 — Red de seguridad (antes de tocar una sola línea)

1. **Crear rama separada:** `fix/integridad-motor-datos`, nunca commitear directo a `main`.
2. **Tests de caracterización:** antes de cambiar nada, escribir tests que capturen el comportamiento *actual* de `_count_duplicate_rows`, `_profile_column` y `_add_numeric_stats` con el dataset `samples/moveup_sample.csv` y con un fixture nuevo (`samples/dataset_sucio_fixture.csv`, el mismo que usamos en nuestra sesión). Estos tests documentan "así se comporta hoy" — sirven como cable a tierra: si algo se rompe sin querer, fallan inmediatamente.
3. **Congelar el contrato del JSON de `analysis`:** documentar en un archivo `docs/ANALYSIS_SCHEMA.md` los campos actuales que devuelve `analyze_dataset()`. Cualquier campo nuevo se agrega, nunca se renombra ni se elimina uno existente — así `app.js` nunca se rompe por un cambio de forma en el backend.
4. **Correr la suite de Playwright existente** (`02_sample_analyze.spec.js`) y confirmar que pasa en verde ANTES de empezar. Es tu línea base.

### Fase 1 — Duplicados por clave configurable (defecto más crítico)

**Problema:** `_count_duplicate_rows` y `_dedupe_rows` comparan las 12 columnas completas; cualquier diferencia de capitalización o un campo vacío en un registro rompe la detección.

**Cambios en `analyzer.py`:**
1. Modificar la firma: `_count_duplicate_rows(headers, rows, key_columns: list[str] | None = None)`. Si `key_columns` es `None`, se comporta exactamente igual que hoy (comparación de fila completa) — **cero riesgo de romper el flujo actual**.
2. Cuando `key_columns` tiene valor, construir la clave solo con esas columnas, normalizando: `strip()` + `lower()` + remover tildes (usar `unicodedata.normalize`). Esta normalización se usa **solo para comparar**, nunca se aplica al dato que se muestra o se exporta.
3. Aplicar el mismo patrón a `_dedupe_rows`.
4. `analyze_dataset()` y `apply_cleaning_actions()` reciben un parámetro opcional `duplicate_key_columns` que viaja desde el frontend; si no llega, `None` por defecto.

**Cambios en `app.js` / UI (Etapa 03 "Reglas"):**
5. Agregar un selector "¿Qué columna identifica a una persona/registro de forma única?" (dropdown con las columnas del dataset, opción "Ninguna — comparar fila completa" seleccionada por defecto). Esto mantiene el comportamiento legado para cualquier usuario que no toque el control.
6. El valor seleccionado se envía en el payload de `/api/analyze` y `/api/clean`.

**Tests que agregar (no reemplazar los existentes):**
7. Unit test: fixture con 6 pares de duplicados reales → con `key_columns=None` debe seguir devolviendo `0` (documenta el comportamiento legado); con `key_columns=["email"]` debe devolver `6`.
8. Playwright: nuevo test que selecciona la columna clave en la UI y verifica que el contador de duplicados cambie.

**Criterio de "no fisuras":** el test de caracterización de la Fase 0 sobre `moveup_sample.csv` debe seguir devolviendo el mismo número de duplicados que antes del cambio, porque nadie tocó el flujo por defecto.

### Fase 2 — Detectar valores no numéricos que hoy desaparecen en silencio

**Problema:** en `_profile_column`, cuando una columna es tipo `"number"`, los valores que no convierten a `float` se descartan sin dejar rastro (no cuentan como faltantes, ni como outliers, ni como nada).

**Cambios en `analyzer.py`:**
1. Agregar un campo nuevo a `ColumnProfile`: `invalid_type_count: int = 0` (default `0` — cualquier código que lea este objeto y no conozca el campo nuevo sigue funcionando igual).
2. En el bloque `if detected_type == "number":`, calcular `invalid_type_count = len(present) - len(numeric_values)` antes de descartar los valores no convertibles.
3. Incluir `invalid_type_count` en el JSON de salida de cada columna.
4. En `_recommendations()`, agregar una recomendación de prioridad **Alta** cuando `invalid_type_count > 0`: *"La columna '{nombre}' tiene {n} valores no numéricos ocultos que no se están analizando."*

**Cambios en `app.js`:**
5. Mostrar el nuevo campo en la tabla de perfilado (columna nueva o badge junto a "Faltantes"). Usar `?? 0` al leerlo, para que si el backend viejo todavía no tiene el campo, la UI no truene — permite desplegar frontend y backend en momentos ligeramente distintos sin romper nada.

**Tests que agregar:**
6. Unit test: columna con valores `["34", "29", "treinta y ocho", "45"]` → `invalid_type_count == 1`, y el valor no debe contarse en `missing` (ya se contaba como "presente", eso no cambia) ni inflar el `numeric_values`.

**Criterio de "no fisuras":** los tests de caracterización de columnas 100% numéricas de la Fase 0 deben seguir devolviendo `invalid_type_count == 0` sin cambiar ningún otro número.

### Fase 3 — Avisar cuando no hay suficientes datos para calcular outliers

**Problema:** `_add_numeric_stats` retorna en silencio si hay menos de 4 valores numéricos, dejando `outliers = 0` (que se lee como "revisado y sin problemas", cuando en realidad "no se revisó").

**Cambios en `analyzer.py`:**
1. Agregar `outlier_analysis_skipped: bool = False` a `ColumnProfile`.
2. Cuando `len(values) < 4`, poner `profile.outlier_analysis_skipped = True` antes de retornar, en vez de solo `return`.

**Cambios en `app.js`:**
3. Si `outlier_analysis_skipped` es verdadero, mostrar una nota discreta ("Muestra insuficiente para detectar outliers") en vez de dar a entender silenciosamente que la columna está limpia.

**Tests que agregar:**
4. Unit test: columna con 2 valores numéricos → `outlier_analysis_skipped == True`, `outliers == 0` (el conteo se mantiene en 0, pero ahora hay una bandera que aclara que no es una garantía de calidad).

### Fase 4 — Corregir la promesa de privacidad falsa (prioridad de confianza, no técnica)

**Problema:** la landing dice "tus datos nunca salen de tu navegador / 100% privado, sin servidores externos", pero `/api/analyze`, `/api/clean` y los endpoints de IA reciben el archivo completo en base64.

**Pasos:**
1. **Auditar primero, no asumir:** confirmar si el backend persiste el archivo en disco/base de datos en algún punto (búsqueda de `open(`, `.save(`, inserts a Supabase con el contenido del archivo) o si solo lo procesa en memoria y lo descarta al responder. Esto determina qué tan fuerte puede ser la promesa real.
2. **Reescribir la copia** con lenguaje verificable, por ejemplo: *"Tu archivo se procesa en un servidor seguro únicamente para generar el análisis y no se almacena de forma permanente, salvo que decidas guardarlo en tu historial con tu cuenta."* — ajustar exactamente a lo que confirme el paso 1.
3. Este cambio es **solo de texto**, cero riesgo técnico — conviene hacerlo primero porque no depende de ningún otro fix y elimina el mayor riesgo reputacional inmediato.

### Fase 5 — Limpieza cosmética (última, sin riesgo)

- Corregir tildes: "Caracteristicas" → "Características", "Como funciona" → "Cómo funciona", "Distribucion %" → "Distribución %", "acompana" → "acompaña", "observacíones" → "observaciones", "recomendaciónes" → "recomendaciones".
- Sincronizar el README con la realidad: documentar las 7 etapas reales (no 6), y actualizar la sección de "Detección de filas duplicadas" para reflejar el nuevo comportamiento configurable una vez implementada la Fase 1.

### Checklist de despliegue seguro (aplica a cada fase)

- [ ] Test de caracterización en verde antes de empezar la fase
- [ ] Cambios aditivos (campos/parámetros nuevos con default = comportamiento actual)
- [ ] Tests nuevos escritos y en verde
- [ ] Playwright suite completa en verde
- [ ] Prueba manual con `dataset_sucio.csv` real y con `moveup_sample.csv`
- [ ] Deploy a Render, smoke test manual antes de anunciar el cambio

---

## PARTE 2 — Plan de implementación de mejoras para competitividad

### Horizonte 1 — Quick wins (1-2 semanas, después de cerrar la Parte 1)

| Mejora | Por qué importa |
|---|---|
| Exportar dataset limpio también en `.xlsx` con fórmulas, no solo CSV | La mayoría de tus usuarios reales van a seguir trabajando el archivo en Excel |
| Cronómetro visible de tiempo de procesamiento en la UI | Convierte tu velocidad real en un argumento de venta visible, no asumido |
| Modo "aplicar todas las recomendaciones seguras" en un clic | Reduce fricción del wizard para datasets simples; el modo paso a paso queda para casos complejos |
| Plantillas de reglas por tipo de dataset (ventas, RRHH, financiero) que preconfiguran columna clave de duplicados y rangos típicos | Elimina la fase de "definir criterios desde cero" que hoy consume más tiempo que la limpieza misma |

### Horizonte 2 — Mediano plazo (mes)

| Mejora | Por qué importa |
|---|---|
| Reglas de rango configurables por campo (ej. edad 0-100, no solo IQR estadístico) | Cierra el hueco que detectamos: IQR no sustituye reglas de negocio conocidas |
| Copiloto IA sugiere automáticamente la columna clave de duplicados al perfilar | Conecta tu diferenciador de IA directamente con el defecto que corregiste en la Fase 1 |
| Clasificación de outliers asistida por IA (error vs. dato real) — ya está en tu roadmap | Es exactamente la división de trabajo ganadora: motor determinístico + IA solo para el juicio |
| Chat del copiloto conectado a la bitácora ("¿por qué se marcó la fila 14?") | Diferenciador que un chat de IA genérico no puede igualar sin tu estructura de datos |

### Horizonte 3 — Largo plazo / diferenciador estratégico (2-3 meses)

| Mejora | Por qué importa |
|---|---|
| Generación de reglas de validación por industria (ya en tu roadmap) | Es el salto de "herramienta genérica" a "producto vertical" |
| Multi-dataset por proyecto + autenticación robusta | Habilita uso en equipo, no solo individual |
| Modo de procesamiento 100% en el navegador para el flujo "sin cuenta" | La única forma de que la promesa de privacidad sea 100% verdadera, no solo corregida en texto |
| Exportar informe también en DOCX (ya en tu roadmap) | Cierra la brecha con el formato que pediste que yo generara en nuestra sesión |

---

## PARTE 3 — Calificación del proyecto: antes y después

| Dimensión | Antes | Después de Parte 1 + Horizonte 1-2 | Justificación |
|---|---|---|---|
| Confiabilidad del motor (duplicados, tipos inválidos, outliers) | **4/10** | **8/10** | Pasa de detectar solo duplicados 100% idénticos y perder datos en silencio, a tener clave configurable, señales de tipos inválidos y avisos de muestra insuficiente |
| Trazabilidad y auditoría | **8/10** | **9/10** | Ya tenías bitácora, undo y notas; se suma trazabilidad de los nuevos hallazgos |
| Accesibilidad para no-técnicos | **8/10** | **8.5/10** | El wizard ya era fuerte; las plantillas y el modo un-clic reducen aún más la fricción |
| Velocidad de ejecución real | **7/10** | **9/10** | El motor ya era rápido; las plantillas y el modo automático eliminan el tiempo de definición manual de criterios |
| Diferenciador de IA (copiloto) | **7/10** | **8.5/10** | Ya estaba implementado de verdad (no maqueta); se vuelve más útil al conectarse con duplicados y outliers |
| Honestidad de la propuesta de valor (privacidad y copy) | **3/10** | **9/10** | La promesa de privacidad falsa era el mayor riesgo de credibilidad del proyecto; corregirla es el cambio de mayor impacto por menor esfuerzo |
| Madurez de producto (tests, documentación) | **6/10** | **8/10** | Un solo archivo de test hoy; con la Parte 1 tendrás cobertura de regresión real y documentación sincronizada |

**Nota global antes: 6.1/10 — un MVP con una base de UI/UX notablemente más madura de lo que sugiere en un primer vistazo, pero con un motor que puede reportar datasets "limpios" que no lo están, y una promesa de privacidad que no se sostiene bajo inspección.**

**Nota global después: 8.6/10 — un producto donde la confiabilidad del motor deja de ser el punto débil, la propuesta de valor es honesta y verificable, y el diferenciador de IA (que ya tenías construido) queda respaldado por un motor determinístico que de verdad detecta lo que promete.**

El salto más grande no viene de features nuevas — viene de que el motor deje de mentir por omisión. Eso es lo que separa una herramienta que "se ve profesional" de una que efectivamente lo es.
