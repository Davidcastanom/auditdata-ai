***Informe de Diagnóstico de Calidad de Datos — Data Cleaning Report***

Página 1 de 18

# INFORME DE DIAGNÓSTICO DE CALIDAD DE DATOS

***(Data Cleaning Report — Guía Transversal de Anomalías de Depuración)***

Catálogo maestro de inconsistencias, errores estructurales y anomalías de captura

encontradas con mayor frecuencia en datasets de cualquier industria

***— previo a cualquier análisis estadístico o exploratorio —***

Elaborado como material de referencia técnica Enfoque: Limpieza y depuración de datos (Data Cleaning) — no incluye análisis estadístico

Fecha: Julio de 2026

---

***Informe de Diagnóstico de Calidad de Datos — Data Cleaning Report***

Página 2 de 18

**Tabla de contenido**

**1. Introducción y objetivo del informe** .................................................................................................. 3

**2. Marco conceptual: precisión terminológica** ...................................................................................... 3

**3. Mapa general de categorías de problemas** ........................................................................................ 5

**4. Catálogo detallado de problemas de calidad de datos** ..................................................................... 6

4.1 Valores faltantes (missing values) ................................................................................................ 6

4.2 Duplicados (exactos y aproximados) ............................................................................................ 7

4.3 Inconsistencias de formato de fecha y hora ................................................................................ 7

4.4 Violaciones de dominio numérico (negativos indebidos) ............................................................ 8

4.5 Errores de redacción y captura de texto libre.............................................................................. 9

4.6 Inconsistencia categórica / semántica ....................................................................................... 10

4.7 Errores de tipo de dato .............................................................................................................. 11

4.8 Inconsistencia de unidades de medida ...................................................................................... 12

4.9 Incoherencias lógicas entre columnas ....................................................................................... 13

4.10 Problemas de codificación de caracteres (encoding) .............................................................. 14

4.11 Problemas estructurales del archivo fuente ............................................................................ 14

4.12 Valores fuera de rango lógico o imposibles ............................................................................. 15

**5. Matriz de severidad y priorización de depuración** .......................................................................... 17

**6. Checklist recomendado de depuración** ............................................................................................ 18

**7. Conclusión** ......................................................................................................................................... 18

---

***Informe de Diagnóstico de Calidad de Datos — Data Cleaning Report***

Página 3 de 18

**1. Introducción y objetivo del informe**

Antes de que un dataset pueda ser sometido a análisis exploratorio, modelado o generación de indicadores, debe pasar por una fase crítica y frecuentemente subestimada: la limpieza y depuración de datos (data cleaning). Este informe tiene como propósito documentar, de forma exhaustiva y transversal a cualquier industria o tipo de dataset, el conjunto de inconsistencias, anomalías estructurales y errores de captura que con mayor frecuencia se encuentran en bases de datos reales.

Es fundamental precisar el alcance: este documento NO aborda el análisis estadístico del dataset (distribución de variables, correlaciones, pruebas de hipótesis, etc.). Su enfoque exclusivo es diagnosticar y catalogar los problemas de calidad de datos que deben resolverse ANTES de iniciar cualquier análisis, para garantizar que los resultados posteriores sean confiables.

El informe está organizado como un catálogo de categorías de problemas, cada una con su definición, ejemplos concretos, método de detección y las industrias donde suele presentarse con mayor frecuencia, cerrando con una matriz de severidad y un checklist de depuración recomendado.

**2. Marco conceptual: precisión terminológica**

Uno de los errores metodológicos más comunes es mezclar dos conceptos que pertenecen a etapas distintas del ciclo de vida del dato. Este informe adopta la siguiente distinción, que se mantiene de forma consistente en todo el documento:

**2.1 Dato atípico (outlier) — NO es el foco de este informe**

Es un concepto propio del análisis estadístico/exploratorio. Se refiere a un valor que, aunque válido y coherente con el dominio de la variable, se aleja significativamente de la tendencia central de la distribución (medido típicamente con rango intercuartílico, desviación estándar o z-score). Un salario de $45.000.000 en un dataset donde el promedio es $3.000.000 puede ser un dato atípico, pero sigue siendo un valor legítimo y posible.

**2.2 Valor inválido / violación de dominio — SÍ es el foco de este informe**

Es un valor que rompe una regla lógica, de negocio o de dominio de la variable, independientemente de su relación con la distribución del resto de los datos. No es un fenómeno estadístico, es un defecto de calidad del dato. Ejemplos: una edad de -5 años, un año de nacimiento de 2130, un porcentaje de 340%, una fecha de finalización anterior a la fecha de inicio.

**2.3 Nomenclatura usada en este informe**

Para evitar la confusión que el usuario correctamente identificó, en este documento NO se usará el término 'dato atípico' para referirse a errores de calidad. En su lugar se usarán los siguientes términos, todos propios de la etapa de limpieza:

● Valor inválido: rompe una regla de dominio (ej. negativos donde la variable es por definición no-negativa).

● Valor imposible o ilógico: contradice una regla de coherencia interna del dataset (ej. fecha de entrega antes que fecha de pedido).

---

***Informe de Diagnóstico de Calidad de Datos — Data Cleaning Report***

Página 4 de 18

● Inconsistencia de formato: el dato es semánticamente correcto pero está mal estructurado (fechas, horas, decimales, mayúsculas).

● Error de captura o redacción: typos, texto libre inconsistente, duplicidad semántica de categorías.

● Valor faltante encubierto (missing disfrazado): datos ausentes representados con placeholders como '0', '- ', 'N/A', '9999', espacios en blanco.

---

***Informe de Diagnóstico de Calidad de Datos — Data Cleaning Report***

Página 5 de 18

**3. Mapa general de categorías de problemas**

A continuación se presenta el panorama completo de las 12 categorías de problemas de calidad de datos que se desarrollan en detalle en la sección 4. Este catálogo cubre de manera transversal los hallazgos más recurrentes reportados en la práctica profesional de limpieza de datos, sin importar el sector o el origen del dataset (encuestas, sistemas transaccionales, sensores IoT, formularios web, bases administrativas, scraping, etc.).

| | | | | | |
| --- | --- | --- | --- | --- | --- |
| | Elemento | | | Descripción | |
| | | | | | |
| | | | | | |
| | 1. Valores faltantes (missing values) | | | Celdas vacías, nulas o con placeholders que ocultan ausencia real de dato. | |
| | | | | | |
| | | | | | |
| 2. Duplicados | | | | Registros exactos o casi-exactos repetidos que inflan conteos y sesgan | |
| | | | | resultados. | |
| | | | | | |
| | | | | | |
| | 3. Inconsistencias de formato de fecha y | | | Formatos mixtos, zonas horarias ausentes, fechas como texto libre, fechas | |
| | hora | | | imposibles (31/02). | |
| | | | | | |
| | | | | | |
| | 4. Violaciones de dominio numérico | | | Valores negativos en variables que por definición son ≥ 0 (edad, años de | |
| | (negativos indebidos) | | | experiencia, cantidades, precios). | |
| | | | | | |
| | | | | | |
| | 5. Errores de redacción y captura de | | | Typos, espacios extra, mayúsculas/minúsculas inconsistentes, acentos | |
| | texto | | | faltantes. | |
| | | | | | |
| | | | | | |
| 6. Inconsistencia categórica / semántica | | | | Mismo valor conceptual escrito de formas distintas ('Bogotá', 'bogota', | |
| | | | | 'BOGOTA D.C.'). | |
| | | | | | |
| | | | | | |
| 7. Errores de tipo de dato | | | | Texto en campos numéricos, números almacenados como texto, | |
| | | | | booleanos mixtos ('Sí'/'1'/'true'). | |
| | | | | | |
| | | | | | |
| | 8. Inconsistencia de unidades de medida | | | Mezcla de kg/lb, km/millas, COP/USD, sin columna que indique la unidad. | |
| | | | | | |
| | | | | | |
| 9. Incoherencias lógicas entre columnas | | | | Reglas de negocio violadas entre dos o más campos (fecha fin < fecha | |
| | | | | inicio, edad vs fecha de nacimiento). | |
| | | | | | |
| | | | | | |
| | 10. Problemas de codificación de | | | Símbolos corruptos (Ã±, Ã©) por mala lectura de UTF-8/Latin-1, pérdida de | |
| | caracteres (encoding) | | | tildes y eñes. | |
| | | | | | |
| | | | | | |
| 11. Problemas estructurales del archivo | | | | Encabezados duplicados, columnas fusionadas, filas de totales mezcladas | |
| | | | | con datos, celdas combinadas (merge). | |
| | | | | | |
| | | | | | |
| | 12. Valores fuera de rango lógico / | | | Valores dentro del tipo de dato correcto pero fuera de un rango | |
| | imposibles por contexto | | | físicamente posible (edad = 250 años). | |
| | | | | | |

---

***Informe de Diagnóstico de Calidad de Datos — Data Cleaning Report***

Página 6 de 18

**4. Catálogo detallado de problemas de calidad de datos**

**4.1. Valores faltantes (missing values) — incluyendo missing encubierto**

Ausencia de información en una celda donde debería existir un valor. El problema no es solo el vacío explícito (NULL, NaN, celda en blanco), sino el missing 'disfrazado': valores centinela que simulan ser datos válidos pero en realidad representan ausencia de información.

**Ejemplos típicos**

● Celdas completamente vacías o con NaN/NULL/None.

● Placeholders usados como sustituto de vacío: '0', '-1', '9999', '-', 'N/A', 'NA', 'S/D', 'Sin dato', espacio en blanco (' ').

● Campos de texto libre con valores como 'desconocido', 'pendiente', 'no aplica' mezclados con datos reales.

● Filas completas ausentes (missing estructural) que rompen la serie temporal o el conteo esperado de registros.

**Cómo se detecta en la etapa de limpieza**

● Conteo de nulos explícitos por columna y su porcentaje sobre el total.

● Revisión de la moda o valores más frecuentes por columna para detectar placeholders sospechosos (ej. '9999' apareciendo con frecuencia anómala en una columna numérica).

● Comparación del número de filas esperado (ej. por periodo de tiempo) contra el número real de filas.

**Buenas prácticas y recomendaciones de tratamiento**

● Nunca asumir que un campo vacío significa 'cero': confirmar con el área de negocio si el vacío es ausencia de dato o un valor real de cero.

● Reemplazar placeholders disfrazados ('9999', '-', 'N/A') por NULL explícito antes de decidir cómo tratarlos.

● Documentar el porcentaje de faltantes por columna; si supera un umbral (ej. 40-50%), evaluar si la columna aporta valor o debe excluirse del análisis.

● Elegir el tratamiento según el tipo de variable: eliminación de la fila solo si el % de nulos es bajo y el campo es crítico; imputación (media/mediana/moda, o modelos predictivos) cuando se requiere conservar el registro; o creación de una categoría 'No reportado' para variables categóricas.

● Si el missing tiene un patrón (no es aleatorio, ej. siempre falta en un mismo canal o fecha), investigar la causa raíz en el proceso de captura antes de imputar.

● Dejar trazabilidad: agregar una columna indicadora (flag) de qué valores fueron imputados, para no perder esa información de cara al análisis posterior.

**Dónde aparece con más frecuencia (por industria)**

● Salud: campos clínicos no diligenciados por el personal médico en la historia clínica electrónica.

● Retail/e-commerce: campos opcionales del checkout (segundo teléfono, dirección de facturación).

● Encuestas y RRHH: preguntas omitidas o saltadas por lógica de formulario.

● IoT/sensores: pérdida de lecturas por caídas de conectividad, mostradas como 0 en lugar de NULL.

**4.2. Duplicados (exactos y aproximados)**

---

***Informe de Diagnóstico de Calidad de Datos — Data Cleaning Report***

Página 7 de 18

Registros que representan la misma entidad del mundo real pero aparecen más de una vez en el dataset, ya sea de forma idéntica (duplicado exacto) o con pequeñas variaciones (duplicado aproximado o 'fuzzy').

**Ejemplos típicos**

● Duplicado exacto: la fila completa se repite carácter por carácter.

● Duplicado por clave: mismo ID único pero con otros campos distintos (indica error de actualización, no de captura).

● Duplicado aproximado: mismo cliente registrado como 'Juan Pérez', 'Juan Perez' y 'JUAN PEREZ G.'

● Duplicado por reingreso: mismo evento/transacción capturado dos veces por reintento de un formulario o sistema.

**Cómo se detecta en la etapa de limpieza**

● Conteo de filas exactamente idénticas.

● Verificación de unicidad sobre la(s) columna(s) que deberían ser llave primaria (ID, cédula, número de factura).

● Comparación por similitud de texto (distancia de Levenshtein, fonética) para identificar duplicados aproximados en campos de nombre/dirección.

**Buenas prácticas y recomendaciones de tratamiento**

● Antes de eliminar, decidir un criterio de conservación (ej. quedarse con el registro más reciente, el más completo, o el de la fuente más confiable).

● Para duplicados exactos: eliminación directa es segura una vez confirmado que la fila completa es idéntica.

● Para duplicados por clave con datos distintos: no eliminar sin investigar; puede tratarse de una actualización legítima que requiere conservar el histórico (versión anterior vs. vigente).

● Para duplicados aproximados: aplicar coincidencia difusa (fuzzy matching) con revisión humana antes de fusionar, nunca fusionar automáticamente sin validación cuando el impacto es alto (ej. historia clínica, cuentas financieras).

● Definir y documentar la llave de deduplicación (qué combinación de columnas identifica un registro único) y dejarla como regla reutilizable para cargas futuras.

● Registrar cuántos registros se eliminaron y por qué criterio, para poder auditar la limpieza.

**Dónde aparece con más frecuencia (por industria)**

● CRM y ventas: mismo cliente registrado varias veces por distintos asesores comerciales.

● Salud: mismo paciente con múltiples historias clínicas por errores de identificación.

● Logística: mismo envío registrado dos veces por reintentos del sistema de tracking.

● Gobierno/datos abiertos: mismo beneficiario de un programa social inscrito bajo variantes del nombre.

**4.3. Inconsistencias de formato de fecha y hora**

La fecha/hora es una de las variables con mayor tasa de error en cualquier dataset, porque su formato depende de la configuración regional del sistema de origen y porque frecuentemente se captura como texto libre en lugar de un tipo de dato fecha nativo.

**Ejemplos típicos**

---

***Informe de Diagnóstico de Calidad de Datos — Data Cleaning Report***

Página 8 de 18

● Formatos mixtos dentro de la misma columna: '2024-03-15', '15/03/2024', 'March 15, 2024', '15-Mar-24'.

● Ambigüedad DD/MM vs MM/DD (ej. '03/04/2024' ¿es 3 de abril o 4 de marzo?).

● Fechas imposibles: 31 de febrero, 30 de febrero, mes 13, día 32.

● Horas en formato 12h sin especificar AM/PM, o mezcla de formato 12h y 24h.

● Ausencia de zona horaria en timestamps de sistemas distribuidos o internacionales.

● Fecha almacenada como texto (string) en vez de tipo fecha, lo que impide ordenar u operar correctamente.

● Separadores inconsistentes: '/', '-', '.', espacio.

● Años de 2 dígitos ambiguos ('24' ¿1924 o 2024?).

**Cómo se detecta en la etapa de limpieza**

● Intentar parsear la columna completa con un formato estándar (ISO 8601) y registrar cuántos valores fallan la conversión.

● Búsqueda de patrones de fecha mediante expresiones regulares para identificar formatos distintos coexistiendo en la misma columna.

● Validación de rangos lógicos: día entre 1-31, mes entre 1-12, hora entre 0-23.

**Buenas prácticas y recomendaciones de tratamiento**

● Estandarizar toda fecha/hora a formato ISO 8601 (AAAA-MM-DD, HH:MM:SS en 24h) como estándar único del dataset.

● Convertir la columna a un tipo de dato fecha/hora nativo (datetime), nunca dejarla como texto libre una vez limpia.

● Cuando el formato original es ambiguo (DD/MM vs MM/DD), resolverlo cruzando con el país/sistema de origen o con valores de referencia (ej. si el 'mes' supera 12, la ambigüedad se resuelve sola).

● Registrar y aislar las fechas imposibles (31/02, mes 13) en una lista aparte para revisión manual, en vez de forzarlas a una fecha válida arbitraria.

● Si el dataset combina zonas horarias, estandarizar a UTC y conservar la zona horaria original en una columna separada si es relevante para el negocio.

● Validar rangos lógicos (ej. ninguna fecha de nacimiento en el futuro, ninguna fecha de transacción anterior a la fundación del sistema).

**Dónde aparece con más frecuencia (por industria)**

● Finanzas: conciliación de transacciones entre sistemas con distinta configuración regional (formato US vs. formato latinoamericano).

● Logística: fechas de despacho/entrega capturadas manualmente por transportistas.

● Salud: fecha de nacimiento capturada en formularios en papel y luego digitalizada.

● Sistemas integrados de múltiples países: mezcla de formatos por proveniencia del sistema origen.

**4.4. Violaciones de dominio numérico: valores negativos indebidos**

Se presentan cuando una variable tiene, por definición conceptual, un dominio restringido a valores no- negativos (o positivos estrictos), pero el dataset contiene valores negativos. Es importante subrayar: esto es un

---

***Informe de Diagnóstico de Calidad de Datos — Data Cleaning Report***

Página 9 de 18

ERROR DE VALIDACIÓN DE DOMINIO, no un dato atípico, porque el valor negativo es lógicamente imposible para esa variable, sin importar qué tan cerca o lejos esté de la media.

**Ejemplos típicos**

● Años de experiencia laboral = -3.

● Edad = -1 o edad = 0 usada por error para representar 'sin dato'.

● Cantidad de unidades vendidas = -10 (válido solo si representa explícitamente una devolución/reverso, y debe estar documentado como tal).

● Precio o valor monetario = -150.000 sin que exista una columna de tipo de movimiento que lo justifique.

● Duración en minutos/segundos negativa (ej. tiempo de llamada = -45 segundos).

● Distancia recorrida, peso, altura o área con signo negativo.

**Cómo se detecta en la etapa de limpieza**

● Definir explícitamente, columna por columna, el dominio matemático esperado (¿[0, ∞)? ¿(0, ∞)? ¿puede ser negativo bajo alguna regla de negocio documentada?).

● Filtrar y contar registros donde valor < 0 para cada variable de dominio no-negativo.

● Verificar si existe una columna adicional (tipo de transacción, motivo) que legitime el signo negativo antes de marcarlo como error.

**Buenas prácticas y recomendaciones de tratamiento**

● Documentar en un diccionario de datos el dominio matemático exacto de cada variable (≥0, >0, rango cerrado, etc.) antes de limpiar, para no tomar decisiones ad-hoc.

● No convertir automáticamente el negativo a positivo (valor absoluto) sin entender la causa: puede ocultar un error real de captura o de signo invertido en el sistema origen.

● Si existe una columna de tipo de movimiento/transacción que legitima el signo negativo (ej. devolución, reverso, ajuste), conservarlo y documentarlo; si no existe, tratarlo como error de captura.

● Para errores confirmados: decidir entre corregir el signo (si se puede inferir el valor correcto), marcar como nulo para imputación, o excluir el registro, según la criticidad del campo.

● Establecer una regla de validación automatizada (constraint) que impida la entrada de futuros negativos indebidos en el sistema origen, no solo corregir el histórico.

**Dónde aparece con más frecuencia (por industria)**

● RRHH y reclutamiento: años de experiencia, edad, antigüedad en el cargo.

● Retail e inventarios: unidades en stock, cantidad vendida, precio unitario.

● Finanzas: montos de transacción sin distinguir débito/crédito mediante una columna de signo o tipo.

● Logística: tiempos de tránsito, distancias, peso de la carga.

**4.5. Errores de redacción y captura de texto libre**

Anomalías que surgen de la digitación manual o de la falta de estandarización en campos de texto, sin llegar a cambiar el significado del dato pero afectando su procesabilidad.

**Ejemplos típicos**

---

***Informe de Diagnóstico de Calidad de Datos — Data Cleaning Report***

Página 10 de 18

● Espacios en blanco al inicio o final del texto (' Medellín' vs 'Medellín').

● Espacios dobles o múltiples entre palabras.

● Mezcla de mayúsculas y minúsculas sin criterio ('MEDELLIN', 'medellin', 'Medellín').

● Tildes y eñes faltantes o mal digitadas ('Bogota' vs 'Bogotá').

● Errores ortográficos evidentes ('Medellin', 'Medelin', 'Medeyin').

● Abreviaturas inconsistentes ('Cra.', 'Cra', 'Carrera', 'CR').

● Caracteres especiales o de control invisibles copiados desde Excel/Word (saltos de línea dentro de una celda, tabulaciones).

**Cómo se detecta en la etapa de limpieza**

● Conteo de valores únicos por columna categórica: si una columna que debería tener pocas categorías (ej. ciudad, departamento) muestra decenas de valores únicos, es señal de fragmentación por errores de redacción.

● Normalización de prueba (trim, lower-case, remoción de tildes) y comparación de cuántos valores únicos se reducen tras la limpieza.

● Revisión manual de las categorías con menor frecuencia (colas largas) que suelen concentrar los errores tipográficos.

**Buenas prácticas y recomendaciones de tratamiento**

● Aplicar limpieza básica estándar a todo campo de texto: trim (quitar espacios al inicio/final), colapsar espacios múltiples a uno solo, y capitalización consistente (Título, MAYÚSCULAS o minúsculas según el estándar definido).

● Normalizar tildes y eñes de forma consciente: corregir la falta de tildes, nunca eliminarlas como estrategia de limpieza, porque cambia el significado en español.

● Usar distancia de edición (Levenshtein) o similitud fonética para agrupar variantes del mismo valor antes de decidir la corrección manual.

● Para campos de alto volumen y repetitivos (ciudad, país, cargo), migrar a lista desplegable o autocompletado en el sistema de origen para prevenir el problema en la fuente, no solo corregirlo después.

● Mantener un diccionario de correcciones (texto original → texto corregido) versionado, para aplicar la misma limpieza de forma reproducible en cargas futuras.

**Dónde aparece con más frecuencia (por industria)**

● Encuestas y formularios web: campos de texto libre sin lista desplegable.

● Atención al cliente: campos de nombre, dirección y ciudad digitados manualmente por agentes.

● Educación: nombres de instituciones, programas académicos capturados sin estandarización.

● Gobierno: nombres de municipios/barrios en registros administrativos históricos.

**4.6. Inconsistencia categórica / semántica**

Ocurre cuando distintas etiquetas representan el mismo concepto sin que exista un catálogo o diccionario de valores controlado (esto va más allá del typo simple: incluye sinónimos, códigos vs. nombres, y niveles de agregación distintos).

---

***Informe de Diagnóstico de Calidad de Datos — Data Cleaning Report***

Página 11 de 18

**Ejemplos típicos**

● Género: 'M', 'Masculino', 'Hombre', 'H' usados indistintamente para el mismo concepto.

● Estado civil: 'Soltero', 'Soltera', 'SOLTERO(A)' como categorías separadas cuando deberían unificarse.

● País: 'Colombia', 'COL', 'CO', 'Republica de Colombia' sin estandarizar a un código ISO único.

● Categorías de producto que mezclan nivel de detalle distinto ('Bebidas' vs. 'Gaseosa Cola 350ml').

**Cómo se detecta en la etapa de limpieza**

● Tabla de frecuencia de valores únicos por columna categórica ordenada de menor a mayor frecuencia.

● Construcción de un diccionario de mapeo (categoría original → categoría estandarizada) validado con el área de negocio.

**Buenas prácticas y recomendaciones de tratamiento**

● Construir un diccionario/catálogo maestro de valores válidos por variable categórica, validado con el área de negocio dueña del dato.

● Migrar de texto libre a códigos estandarizados internacionales cuando existan (ISO 3166 para países, CIE- 10 para diagnósticos, DIVIPOLA para municipios en Colombia).

● Separar siempre el nivel de agregación: mantener una jerarquía explícita (categoría > subcategoría > producto) en vez de mezclar niveles distintos en una sola columna.

● Cuando dos categorías parecen sinónimos pero no se está seguro, consultarlo con el área de negocio antes de fusionarlas: fusionar categorías que en realidad son distintas es tan grave como no fusionar las que sí son iguales.

● Versionar el catálogo de categorías: si cambia con el tiempo, documentar desde qué fecha aplica cada versión para no romper comparaciones históricas.

**Dónde aparece con más frecuencia (por industria)**

● RRHH: catálogos de cargos, áreas y niveles jerárquicos sin estandarizar entre sedes.

● Salud: codificación de diagnósticos (CIE-10) capturada como texto libre en vez de código.

● Retail multicanal: categorías de producto distintas entre el canal físico y el canal e-commerce.

**4.7. Errores de tipo de dato**

El valor está almacenado en un tipo de dato distinto al que le corresponde conceptualmente, lo que impide operaciones matemáticas, ordenamientos o validaciones correctas.

**Ejemplos típicos**

● Números almacenados como texto ('1.234' interpretado como string, no como numérico).

● Texto en un campo que debería ser 100% numérico (ej. 'diez' en vez de '10', o 'N/A' en una columna de edad).

● Booleanos representados de formas distintas dentro de la misma columna: 'Sí'/'No', 'S'/'N', '1'/'0', 'true'/'false', 'Verdadero'/'Falso'.

● Separador decimal inconsistente: coma (1.234,56 - formato LatAm/Europa) vs. punto (1,234.56 - formato US) mezclados en la misma columna.

---

***Informe de Diagnóstico de Calidad de Datos — Data Cleaning Report***

Página 12 de 18

● IDs numéricos que pierden ceros a la izquierda al ser interpretados como número (ej. código postal '00501' guardado como 501).

**Cómo se detecta en la etapa de limpieza**

● Intento de conversión forzada (cast) de toda la columna al tipo esperado y conteo de errores de conversión.

● Inspección del tipo de dato inferido automáticamente por la herramienta (pandas dtypes, tipo de columna en Excel/Power Query) contra el tipo conceptual esperado.

**Buenas prácticas y recomendaciones de tratamiento**

● Definir explícitamente el tipo de dato esperado por columna en el diccionario de datos antes de cargar el archivo (numérico, texto, fecha, booleano, categórico).

● Estandarizar el separador decimal y de miles a un único estándar antes de convertir a numérico, verificando la configuración regional de origen.

● Para campos identificadores con ceros a la izquierda (códigos postales, cédulas), forzar el tipo texto desde la importación, nunca dejar que se infiera como numérico.

● Unificar todas las variantes de booleano ('Sí'/'No', 'S'/'N', '1'/'0') a un único par de valores estándar (ej. True/False o 1/0) mediante un mapeo documentado.

● Registrar cuántos valores fallan al forzar la conversión de tipo (errores de cast) y tratarlos como missing o error de captura según corresponda, en vez de que la conversión falle silenciosamente.

**Dónde aparece con más frecuencia (por industria)**

● Finanzas: montos con separador decimal inconsistente al consolidar reportes de distintos países.

● Sistemas heredados (legacy): exportaciones desde sistemas antiguos que truncan ceros a la izquierda en códigos.

● Encuestas: campos de respuesta booleana capturados con distinta codificación entre versiones del formulario.

**4.8. Inconsistencia de unidades de medida**

El dato es numéricamente válido pero la unidad de medida no está estandarizada ni documentada, lo que hace que valores de la misma columna no sean comparables entre sí.

**Ejemplos típicos**

● Peso mezclando kilogramos y libras sin columna que indique la unidad.

● Distancia mezclando kilómetros y millas.

● Montos monetarios mezclando COP, USD y EUR sin columna de moneda.

● Tiempo mezclando minutos, horas y segundos en una misma columna 'duración'.

**Cómo se detecta en la etapa de limpieza**

● Revisión de rangos de valores por columna: saltos abruptos de escala (valores entre 1-10 mezclados con valores entre 1.000-10.000) suelen indicar mezcla de unidades.

● Verificación de existencia de una columna explícita de unidad/moneda; si no existe, es en sí mismo un hallazgo de calidad de datos.

---

***Informe de Diagnóstico de Calidad de Datos — Data Cleaning Report***

Página 13 de 18

**Buenas prácticas y recomendaciones de tratamiento**

● Elegir una unidad estándar única por variable (ej. todo en kg, todo en km, todo en COP) y convertir el resto en el momento de la carga, no después del análisis.

● Si la conversión depende de una tasa variable (moneda, tipo de cambio), documentar la fecha y fuente de la tasa usada para cada conversión.

● Agregar siempre una columna explícita de unidad/moneda junto al valor numérico, incluso después de estandarizar, como trazabilidad y control de calidad futuro.

● Validar con el área de negocio o el proveedor de datos cuál es la unidad real de origen antes de asumir una, especialmente en integraciones con terceros.

**Dónde aparece con más frecuencia (por industria)**

● Comercio internacional/importaciones: mezcla de sistema métrico e imperial según el país de origen del proveedor.

● Finanzas multinacionales: consolidación de reportes en distintas monedas sin tasa de conversión documentada.

● Logística internacional: peso y volumen de carga capturados en unidades distintas por transportista.

**4.9. Incoherencias lógicas entre columnas**

El valor de cada columna, visto de forma aislada, puede ser válido, pero la combinación entre dos o más columnas rompe una regla de negocio o de coherencia temporal/lógica.

**Ejemplos típicos**

● Fecha de finalización anterior a la fecha de inicio de un proceso, contrato o proyecto.

● Edad reportada que no coincide con la fecha de nacimiento reportada.

● Fecha de entrega de un pedido anterior a la fecha en que fue realizado.

● Total de una factura que no coincide con la suma de sus líneas de detalle.

● Estado 'Activo' en un registro cuya fecha de terminación ya pasó.

● Ciudad que no pertenece al departamento/estado reportado en otra columna.

**Cómo se detecta en la etapa de limpieza**

● Reglas de validación cruzada (cross-field validation) definidas explícitamente y aplicadas a todo el dataset.

● Recalculo de campos derivados (edad a partir de fecha de nacimiento, total a partir del detalle) y comparación contra el valor almacenado.

**Buenas prácticas y recomendaciones de tratamiento**

● Priorizar como fuente de verdad el campo más 'primario' o menos propenso a error manual (ej. recalcular la edad desde la fecha de nacimiento, en vez de confiar en un campo de edad digitado aparte).

● Documentar cada regla de coherencia como una validación formal (ej. 'fecha_fin >= fecha_inicio') y aplicarla de forma sistemática a todo el dataset, no caso por caso.

● Cuando se detecta una incoherencia, no corregir automáticamente sin criterio: aislar los casos para revisión manual o para devolución al área que capturó el dato, especialmente si son pocos registros.

---

***Informe de Diagnóstico de Calidad de Datos — Data Cleaning Report***

Página 14 de 18

● Si la incoherencia es sistemática (afecta un gran porcentaje de registros), la causa probablemente está en el proceso o sistema de captura, y debe corregirse en el origen, no solo en el dataset.

**Dónde aparece con más frecuencia (por industria)**

● Proyectos y contratos: fechas de inicio/fin y cronogramas.

● E-commerce y logística: coherencia entre fecha de pedido, despacho y entrega.

● Finanzas y facturación: coherencia entre totales y detalle de líneas.

● RRHH: coherencia entre fecha de ingreso, fecha de nacimiento y edad reportada.

**4.10. Problemas de codificación de caracteres (encoding)**

Ocurren cuando un archivo fue guardado o leído con una codificación de caracteres distinta a la que realmente le corresponde, generando texto corrupto especialmente en idiomas con tildes y caracteres especiales como el español.

**Ejemplos típicos**

● Aparición de secuencias como 'Ã±' en vez de 'ñ', o 'Ã©' en vez de 'é' (error clásico UTF-8 leído como Latin-1 o viceversa).

● Pérdida completa de tildes y eñes al exportar/importar entre sistemas.

● Símbolos de caja o rombos con interrogación ( ) donde debería haber un carácter especial.

● Comillas tipográficas o guiones largos mal interpretados al copiar desde Word/Excel.

**Cómo se detecta en la etapa de limpieza**

● Búsqueda de patrones de caracteres corruptos conocidos (Ã,  ) en todas las columnas de texto.

● Verificación de la codificación declarada del archivo fuente (UTF-8, Latin-1/ISO-8859-1, Windows-1252) contra la codificación real detectada.

**Buenas prácticas y recomendaciones de tratamiento**

● Estandarizar todo el pipeline de datos a codificación UTF-8 desde el punto de lectura del archivo, en vez de corregir el texto ya corrupto símbolo por símbolo.

● Si el archivo ya se corrompió, identificar la codificación original real (frecuentemente Latin-1/ISO-8859-1 o Windows-1252) y releerlo desde el archivo fuente con esa codificación, en lugar de intentar 'adivinar' reemplazos de texto.

● Evitar reprocesar un archivo ya corrupto múltiples veces entre sistemas distintos, porque cada re-lectura con la codificación incorrecta puede corromper el texto de forma no reversible.

● Incluir una validación de encoding como primer paso del pipeline (antes de cualquier otra limpieza), ya que un texto mal codificado invalida las correcciones posteriores de redacción y categorías.

**Dónde aparece con más frecuencia (por industria)**

● Sistemas heredados (legacy) migrados entre distintas plataformas o bases de datos.

● Integraciones entre sistemas de distintos proveedores/países.

● Datos abiertos gubernamentales exportados desde sistemas antiguos en Latin-1.

---

***Informe de Diagnóstico de Calidad de Datos — Data Cleaning Report***

Página 15 de 18

**4.11. Problemas estructurales del archivo fuente**

Anomalías que no están en el contenido de los datos en sí, sino en cómo está organizado el archivo (Excel, CSV, etc.), lo que provoca errores de lectura o interpretación incorrecta de filas y columnas.

**Ejemplos típicos**

● Encabezados de columna duplicados o vacíos.

● Celdas combinadas (merge) en Excel que rompen la estructura tabular al exportar a CSV.

● Filas de subtotales o totales generales mezcladas entre las filas de detalle.

● Encabezado que no está en la primera fila (logos, títulos o notas antes de la tabla real).

● Número de columnas inconsistente entre filas de un CSV (delimitador presente dentro de un valor de texto sin comillas).

● Hojas de cálculo con múltiples tablas dentro de la misma hoja sin separación clara.

**Cómo se detecta en la etapa de limpieza**

● Verificación del número de columnas por fila al leer el archivo (filas con conteo de columnas distinto al esperado).

● Inspección visual de las primeras y últimas filas del archivo antes de cargarlo por completo.

● Validación de que los nombres de columna sean únicos y no estén vacíos.

**Buenas prácticas y recomendaciones de tratamiento**

● Separar siempre los datos de detalle (filas transaccionales) de las filas de resumen/totales en hojas o archivos distintos antes de cualquier procesamiento.

● Eliminar celdas combinadas (merge) en el archivo fuente; reemplazarlas por el valor repetido en cada fila correspondiente, ya que el merge rompe la lectura tabular.

● Validar que la fila de encabezado esté en la posición correcta y que cada columna tenga un nombre único y no vacío antes de nombrar las columnas del dataset limpio.

● Para archivos con múltiples tablas en una misma hoja, separarlas físicamente en archivos u hojas independientes antes de consolidar.

● Establecer una plantilla estándar de captura (con validaciones de Excel o formulario estructurado) para prevenir estos problemas en la fuente, en vez de corregirlos cada vez de forma manual.

**Dónde aparece con más frecuencia (por industria)**

● Reportes financieros y contables generados manualmente en Excel.

● Datos abiertos gubernamentales publicados como exportación directa de un sistema de reportes.

● Consolidados armados manualmente por distintas áreas de una empresa (copiado y pegado entre hojas).

**4.12. Valores fuera de rango lógico o físicamente imposibles**

El tipo de dato es correcto y el signo puede incluso ser válido, pero el valor está fuera del rango físicamente o lógicamente posible para esa variable según el conocimiento de dominio. A diferencia del dato atípico (que es estadísticamente raro pero posible), aquí el valor es imposible por definición del mundo real.

**Ejemplos típicos**

---

***Informe de Diagnóstico de Calidad de Datos — Data Cleaning Report***

Página 16 de 18

● Edad humana de 250 años.

● Porcentaje de 340% en un campo que representa una proporción (debería estar entre 0% y 100%).

● Fecha de nacimiento en el año 1800 para un registro de empleado activo actual.

● Latitud/longitud fuera del rango válido (-90 a 90 / -180 a 180).

● Calificación de satisfacción de 8 en una escala definida de 1 a 5.

● Nota académica de 15 en una escala de 0 a 10 (o de 6.5 en una escala de 0 a 5).

**Cómo se detecta en la etapa de limpieza**

● Definición explícita del rango físico o lógico válido para cada variable, documentado en un diccionario de datos.

● Filtrado de registros fuera de ese rango y conteo por columna.

● Cruce con reglas de dominio del negocio (ej. escalas de evaluación, rangos regulatorios).

**Buenas prácticas y recomendaciones de tratamiento**

● Documentar el rango físico o lógico válido de cada variable en el diccionario de datos (mínimo y máximo posibles), no solo el tipo de dato.

● Cuando el valor está fuera de rango por un probable error de digitación (ej. un dígito de más o de menos), evaluar si se puede inferir el valor correcto contra otra fuente antes de descartarlo.

● Si no es posible corregir el valor con certeza, tratarlo como faltante (NULL) para imputación, en vez de dejarlo distorsionando el dataset o de 'recortarlo' arbitrariamente al límite del rango sin evidencia.

● Cuando el rango incorrecto proviene de mezclar dos escalas distintas (ej. calificación 0-10 vs 0-100), identificar el origen de cada registro y reconvertir a una escala única antes de unificar el dataset.

● Implementar validaciones de rango en el formulario o sistema de captura de origen (mínimos y máximos permitidos) para prevenir la recurrencia del problema.

**Dónde aparece con más frecuencia (por industria)**

● Educación: escalas de calificación mezcladas entre sistemas (0-5, 0-10, 0-100).

● Geolocalización y logística: coordenadas mal capturadas por errores de GPS o de digitación.

● Encuestas de satisfacción: escalas Likert mal codificadas o mal migradas entre versiones del formulario.

● RRHH y demografía: edades o fechas de nacimiento con error de digitación en el año.

---

***Informe de Diagnóstico de Calidad de Datos — Data Cleaning Report***

Página 17 de 18

**5. Matriz de severidad y priorización de depuración**

No todos los problemas de calidad de datos tienen el mismo impacto. Esta matriz permite priorizar el esfuerzo de limpieza según la severidad típica del problema y su facilidad relativa de corrección, como guía general aplicable a la mayoría de los datasets.

| | | | | | | | | | | | |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Categoría de problema | | | | Severidad | | | Facilidad de | | Justificación | | |
| | | | | típica | | | corrección | | | | |
| | | | | | | | | | | | |
| | | | | | | | | | | | |
| | Incoherencias lógicas entre | | Crítica | | | Media | | | | Puede invalidar por completo un registro o | |
| | columnas (4.9) | | | | | | | | | un cálculo derivado. | |
| | | | | | | | | | | | |
| | | | | | | | | | | | |
| | Duplicados por clave / duplicado | | Crítica | | | Alta | | | | Infla conteos, sesga totales y métricas | |
| | exacto (4.2) | | | | | | | | | agregadas. | |
| | | | | | | | | | | | |
| | | | | | | | | | | | |
| | Violaciones de dominio numérico | | Crítica | | | Alta | | | | Valores imposibles que distorsionan sumas, | |
| | (4.4) | | | | | | | | | promedios y modelos. | |
| | | | | | | | | | | | |
| | | | | | | | | | | | |
| Errores de tipo de dato (4.7) | | | Alta | | | Alta | | | | Impide operaciones matemáticas u | |
| | | | | | | | | | | ordenamientos correctos. | |
| | | | | | | | | | | | |
| | | | | | | | | | | | |
| Valores faltantes encubiertos (4.1) | | | Alta | | | Media | | | | Subestima la tasa real de datos ausentes si | |
| | | | | | | | | | | no se detectan. | |
| | | | | | | | | | | | |
| | | | | | | | | | | | |
| Inconsistencias de fecha/hora (4.3) | | | Alta | | | Media | | | | Rompe series temporales y cálculos de | |
| | | | | | | | | | | duración. | |
| | | | | | | | | | | | |
| | | | | | | | | | | | |
| Valores fuera de rango lógico (4.12) | | | Alta | | | Media-Alta | | | | Distorsiona promedios y valida mal reglas | |
| | | | | | | | | | | de negocio. | |
| | | | | | | | | | | | |
| | | | | | | | | | | | |
| | Problemas estructurales del archivo | | Alta | | | Baja-Media | | | | Puede impedir la carga correcta de todo el | |
| | (4.11) | | | | | | | | | dataset. | |
| | | | | | | | | | | | |
| | | | | | | | | | | | |
| | Inconsistencia de unidades de | | Media-Alta | | | Media | | | | Hace que valores no sean comparables | |
| | medida (4.8) | | | | | | | | | entre sí. | |
| | | | | | | | | | | | |
| | | | | | | | | | | | |
| | Inconsistencia categórica/semántica | | Media | | | Alta | | | | Fragmenta categorías y distorsiona conteos | |
| | (4.6) | | | | | | | | | por grupo. | |
| | | | | | | | | | | | |
| | | | | | | | | | | | |
| Problemas de encoding (4.10) | | | Media | | | Alta | | | | Afecta legibilidad y agrupación de texto, | |
| | | | | | | | | | | poco impacto numérico. | |
| | | | | | | | | | | | |
| | | | | | | | | | | | |
| Errores de redacción y captura (4.5) | | | Baja-Media | | | Alta | | | | Molesto pero generalmente corregible con | |
| | | | | | | | | | | normalización estándar. | |
| | | | | | | | | | | | |

---

***Informe de Diagnóstico de Calidad de Datos — Data Cleaning Report***

Página 18 de 18

**6. Checklist recomendado de depuración (orden sugerido)**

Se recomienda ejecutar la limpieza en el siguiente orden, ya que cada paso depende parcialmente de que el anterior esté resuelto:

● 1. Corregir problemas estructurales del archivo (encabezados, columnas fusionadas, filas de totales).

● 2. Estandarizar codificación de caracteres (encoding) para evitar pérdida de información en texto.

● 3. Corregir tipos de dato por columna (forzar tipo numérico, fecha, booleano según corresponda).

● 4. Estandarizar formatos de fecha y hora a un único estándar (recomendado: ISO 8601).

● 5. Identificar y tratar duplicados (exactos primero, luego aproximados).

● 6. Detectar y tratar valores faltantes explícitos y encubiertos.

● 7. Validar dominios numéricos (negativos indebidos, rangos lógicos y físicamente posibles).

● 8. Estandarizar unidades de medida y monedas, documentando la unidad final elegida.

● 9. Normalizar texto libre (trim, capitalización, tildes) y consolidar categorías equivalentes.

● 10. Validar coherencia lógica entre columnas relacionadas.

● 11. Documentar todas las decisiones de limpieza en un diccionario de datos / log de transformaciones.

Solo después de completar este proceso el dataset queda listo para la fase de análisis estadístico y exploratorio, que corresponde a un informe distinto y posterior a este.

**7. Conclusión**

La calidad de cualquier análisis de datos está limitada por la calidad de los datos de entrada ('garbage in, garbage out'). Las doce categorías descritas en este informe representan el conjunto de problemas más recurrentes que un analista de datos encuentra, independientemente de la industria, el tamaño del dataset o la herramienta utilizada.

Mantener la separación conceptual entre 'valor inválido / inconsistencia de calidad' (etapa de limpieza) y 'dato atípico' (etapa de análisis estadístico) no es solo una cuestión terminológica: garantiza que las decisiones tomadas en cada etapa sean las correctas, evitando eliminar información legítima por confundirla con un error, o dejar pasar errores reales por asumir que son simplemente parte de la variabilidad natural de los datos.

Este catálogo puede usarse como checklist de auditoría para cualquier dataset nuevo, como material de formación en programas de analítica de datos, o como base para construir reglas de validación automatizadas dentro de un pipeline de datos.


# Anexo — Inconsistencias Adicionales de Menor Frecuencia o Más Técnicas

### Complemento al *Informe de Diagnóstico de Calidad de Datos (Data Cleaning Report)*

> **Alcance de este anexo:** este documento complementa el informe principal, que cubrió las 12 categorías de inconsistencias más transversales y frecuentes en cualquier dataset. Aquí se documentan categorías adicionales que, si bien no aparecen con la misma frecuencia universal, son comunes en escenarios específicos (especialmente en archivos Excel/CSV, bases relacionales y series de tiempo) y deben conocerse para un diagnóstico verdaderamente exhaustivo.
>
> Igual que en el informe principal, el enfoque es exclusivamente **limpieza y depuración de datos**, no análisis estadístico. Se mantiene la misma nomenclatura: se habla de *valores inválidos*, *inconsistencias*, *errores estructurales* — nunca de "datos atípicos" (concepto reservado para la etapa estadística).

---

## Tabla de contenido

1. [Problemas de integridad relacional](#1-problemas-de-integridad-relacional)
   - 1.1 [Claves foráneas huérfanas](#11-claves-foráneas-huérfanas-orphaned-foreign-keys)
   - 1.2 [Inconsistencia de granularidad](#12-inconsistencia-de-granularidad-grain-mixing)
2. [Problemas específicos de Excel y CSV](#2-problemas-específicos-de-excel-y-csv)
   - 2.1 [Autoconversión de texto a fecha](#21-autoconversión-de-texto-a-fecha-excel-date-coercion)
   - 2.2 [Errores de fórmula guardados como texto](#22-errores-de-fórmula-guardados-como-texto)
   - 2.3 [Notación científica no deseada](#23-notación-científica-no-deseada)
   - 2.4 [Pérdida de precisión decimal / overflow](#24-pérdida-de-precisión-decimal-y-desbordamiento-overflow)
   - 2.5 [Delimitadores rotos en CSV](#25-delimitadores-rotos-dentro-de-un-valor-csv-injection-estructural)
3. [Problemas de texto más específicos](#3-problemas-de-texto-más-específicos)
   - 3.1 [Campos multivaluados en una sola celda](#31-campos-multivaluados-en-una-sola-celda)
   - 3.2 [Mezcla de idiomas](#32-mezcla-de-idiomas-dentro-del-mismo-campo-categórico)
   - 3.3 [Comillas o caracteres fantasma](#33-comillas-o-caracteres-fantasma-de-copiado)
   - 3.4 [Truncamiento de texto](#34-truncamiento-de-texto-por-límite-de-longitud)
4. [Problemas temporales más avanzados](#4-problemas-temporales-más-avanzados)
   - 4.1 [Bug de fecha base 1900 vs 1904](#41-bug-de-fecha-base-1900-vs-1904-en-excel)
   - 4.2 [Series de tiempo con huecos irregulares](#42-series-de-tiempo-con-huecos-irregulares)
   - 4.3 [Mezcla de timezone-naive y timezone-aware](#43-mezcla-de-fechas-timezone-naive-y-timezone-aware)
5. [Problemas de esquema a través del tiempo](#5-problemas-de-esquema-a-través-del-tiempo)
   - 5.1 [Schema drift](#51-schema-drift-deriva-de-esquema)
   - 5.2 [Cambio de formato del identificador único](#52-cambio-de-formato-del-identificador-único-en-el-tiempo)
6. [Matriz de severidad — anexo](#6-matriz-de-severidad-de-las-categorías-adicionales)
7. [Checklist adicional de depuración](#7-checklist-adicional-de-depuración)
8. [Conclusión del anexo](#8-conclusión-del-anexo)

---

## 1. Problemas de integridad relacional

### 1.1 Claves foráneas huérfanas (Orphaned Foreign Keys)

**Definición:** ocurre cuando un registro "hijo" contiene una clave foránea (ID de referencia) que apunta a un registro "padre" que no existe, fue eliminado, o nunca fue cargado en la tabla correspondiente. Es un problema típico de bases de datos relacionales o de datasets que combinan múltiples tablas (joins).

**Ejemplos típicos**
- Una línea de factura que referencia un `id_cliente` que no existe en la tabla de clientes.
- Un registro de ventas que referencia un `id_producto` eliminado del catálogo.
- Un empleado con `id_jefe_directo` apuntando a un ID que ya no está activo en la tabla de empleados.

**Cómo se detecta**
- Ejecutar un `LEFT JOIN` (o equivalente) entre la tabla hija y la tabla padre, y contar cuántos registros de la tabla hija no encuentran coincidencia (`NULL` en la columna del padre).
- Validar la cardinalidad esperada (uno-a-muchos, muchos-a-muchos) contra la cardinalidad real observada.

**Buenas prácticas y recomendaciones de tratamiento**
- No eliminar automáticamente los registros huérfanos sin investigar la causa: puede deberse a una eliminación en cascada mal ejecutada, una carga incompleta, o un error real de captura.
- Si la tabla padre efectivamente perdió información histórica, reconstruir o marcar el registro padre como "inactivo/histórico" en vez de dejar la referencia colgante.
- Establecer restricciones de integridad referencial (foreign key constraints) en el sistema de origen para prevenir la recurrencia, no solo corregir el histórico.
- Documentar cuántos registros huérfanos existen y su impacto potencial antes de decidir si se excluyen del análisis.

**Dónde aparece con más frecuencia**
- Sistemas ERP y CRM con eliminaciones manuales de catálogos maestros.
- Data warehouses alimentados por múltiples sistemas fuente con distintos ciclos de actualización.
- Bases de datos migradas entre plataformas donde no se preservaron las relaciones originales.

---

### 1.2 Inconsistencia de granularidad (Grain Mixing)

**Definición:** sucede cuando una misma tabla mezcla filas que representan distintos niveles de detalle (grano), por ejemplo, filas de transacciones individuales junto con filas de subtotales o agregados. Esto rompe cualquier suma o conteo posterior, porque duplica la información.

**Ejemplos típicos**
- Una hoja de ventas donde después de las filas de cada producto vendido aparece una fila de "Total mes" con la suma, y esa fila se procesa como si fuera una transacción más.
- Un dataset de inventario que mezcla el nivel "unidad individual" con el nivel "lote" sin una columna que distinga el tipo de fila.
- Reportes financieros que combinan el detalle por centro de costo con una fila de "Consolidado" en la misma tabla.

**Cómo se detecta**
- Revisar si la suma de una columna numérica, agrupada por una dimensión, coincide con el "total" reportado; si el total real duplica el valor esperado, hay mezcla de granularidad.
- Buscar filas cuyo campo identificador contenga palabras como "total", "subtotal", "consolidado", "resumen".

**Buenas prácticas y recomendaciones de tratamiento**
- Separar físicamente las filas de detalle de las filas de agregado en tablas o archivos distintos antes de cualquier procesamiento.
- Si se requiere conservar el agregado, mantenerlo en una tabla resumen aparte, nunca mezclado con el detalle transaccional.
- Definir explícitamente el grano de cada tabla en la documentación del dataset (qué representa una fila) antes de consolidar fuentes distintas.

**Dónde aparece con más frecuencia**
- Reportes financieros y contables exportados directamente desde Excel.
- Reportes de ventas con subtotales por vendedor, zona o periodo insertados manualmente.
- Data marts construidos a partir de reportes ya "pre-agregados" en el sistema origen.

---

## 2. Problemas específicos de Excel y CSV

### 2.1 Autoconversión de texto a fecha (Excel Date Coercion)

**Definición:** Excel interpreta automáticamente ciertos valores de texto como fechas, incluso cuando el usuario no lo desea, corrompiendo silenciosamente el dato original. Es uno de los errores más conocidos y documentados en la comunidad de análisis de datos (célebre en genética, donde nombres de genes como "MARCH1" se convertían en fechas).

**Ejemplos típicos**
- Códigos de producto tipo "3-4" convertidos automáticamente a "3 de abril".
- Identificadores tipo "1/2" convertidos a "1 de febrero".
- Nombres de gen, lote o referencia técnica reinterpretados como fecha al abrir el CSV en Excel.

**Cómo se detecta**
- Comparar el archivo CSV original (abierto como texto plano) contra la versión abierta en Excel; cualquier diferencia en columnas que deberían ser texto es señal de autoconversión.
- Buscar patrones de fecha inesperados en columnas que conceptualmente son identificadores o códigos, no fechas.

**Buenas prácticas y recomendaciones de tratamiento**
- Al abrir o importar CSV en Excel, usar siempre el asistente de importación de texto y forzar manualmente el tipo de columna a "Texto" para los campos de código/identificador, en vez de dejar la detección automática.
- Preferir herramientas de lectura programática (Python/pandas, R) sobre Excel para la carga inicial de archivos con códigos alfanuméricos sensibles.
- Si el archivo ya fue corrompido por Excel, recuperarlo desde el CSV original en texto plano; la conversión a fecha generalmente no es reversible una vez guardado el archivo.

**Dónde aparece con más frecuencia**
- Bioinformática y ciencias de la salud (nombres de genes, códigos de laboratorio).
- Manufactura (referencias de lote, códigos de pieza tipo "10-32").
- Cualquier dataset con identificadores que contienen guiones o barras similares a separadores de fecha.

---

### 2.2 Errores de fórmula guardados como texto

**Definición:** cuando un archivo de Excel con fórmulas se exporta o guarda con errores de cálculo, estos quedan como texto literal en la celda, mezclados entre los valores numéricos válidos.

**Ejemplos típicos**
- `#REF!` cuando una fórmula referencia una celda o rango eliminado.
- `#DIV/0!` cuando una fórmula divide entre cero.
- `#N/A` cuando una función de búsqueda (`VLOOKUP`/`BUSCARV`) no encuentra coincidencia.
- `#VALUE!` cuando el tipo de dato de un argumento no es el esperado por la fórmula.
- `#NOMBRE?` o `#NAME?` por un nombre de función mal escrito.

**Cómo se detecta**
- Búsqueda directa de los patrones de error conocidos de Excel (`#REF!`, `#DIV/0!`, `#N/A`, `#VALUE!`, `#NOMBRE?`, `#NULL!`, `#NUM!`) en cualquier columna que debería ser numérica.
- Verificación del tipo de dato inferido por columna: la presencia de errores de fórmula suele forzar que toda la columna se lea como texto en vez de numérico.

**Buenas prácticas y recomendaciones de tratamiento**
- Nunca reemplazar estos errores por cero de forma automática: cada tipo de error tiene una causa distinta que debe investigarse (celda eliminada, división entre cero, búsqueda fallida) antes de decidir el tratamiento.
- Tratar estos valores como faltantes (NULL) para efectos de limpieza, documentando la causa original del error si es identificable.
- Corregir la fórmula en el archivo fuente cuando sea posible, en vez de solo limpiar el resultado exportado.

**Dónde aparece con más frecuencia**
- Reportes financieros y de gestión construidos sobre hojas de cálculo con fórmulas encadenadas.
- Consolidados que dependen de tablas dinámicas o `BUSCARV`/`VLOOKUP` entre múltiples hojas.

---

### 2.3 Notación científica no deseada

**Definición:** Excel y otras herramientas convierten automáticamente números largos a notación científica al alcanzar cierta cantidad de dígitos, lo cual destruye la precisión de identificadores que deberían tratarse como texto.

**Ejemplos típicos**
- Un código de barras de 13 dígitos mostrado como `1.23E+12`.
- Un número de tarjeta, cédula o cuenta bancaria larga convertido a notación científica y truncado en sus últimos dígitos.
- Números de teléfono internacionales largos perdiendo precisión.

**Cómo se detecta**
- Búsqueda de patrones tipo `E+` o `e+` en columnas que deberían contener identificadores numéricos largos.
- Verificación de la longitud de dígitos esperada contra la longitud real tras la conversión.

**Buenas prácticas y recomendaciones de tratamiento**
- Forzar el formato de columna a "Texto" antes de ingresar o importar identificadores numéricos largos (códigos de barras, números de cuenta, cédulas largas).
- Si el dato ya se perdió por truncamiento de notación científica, no es recuperable desde el archivo corrupto; debe recuperarse desde la fuente original.
- Para identificadores, preferir siempre el tipo texto sobre el tipo numérico desde el diseño del sistema de captura.

**Dónde aparece con más frecuencia**
- Retail (códigos de barras EAN/UPC).
- Banca y finanzas (números de cuenta, tarjetas).
- Telecomunicaciones (números telefónicos internacionales).

---

### 2.4 Pérdida de precisión decimal y desbordamiento (overflow)

**Definición:** ocurre cuando un valor numérico excede el rango o la precisión que el tipo de dato de la columna puede almacenar, causando truncamiento, redondeo no deseado, o un error de desbordamiento.

**Ejemplos típicos**
- Montos monetarios muy grandes truncados a un número menor de decimales del necesario para cálculos financieros exactos.
- Cálculos con muchos decimales que se acumulan en errores de redondeo (particularmente en operaciones financieras encadenadas).
- Campos definidos con un tipo de dato numérico de rango insuficiente (ej. entero de 16 bits) que se desbordan al recibir valores más grandes de lo previsto originalmente.

**Cómo se detecta**
- Revisar los metadatos del tipo de columna (precisión y escala definidas) contra el rango real de valores del negocio.
- Comparar sumas o totales calculados a distinta precisión para detectar diferencias de redondeo acumuladas.

**Buenas prácticas y recomendaciones de tratamiento**
- Definir la precisión decimal necesaria según el dominio del negocio (ej. 2 decimales para moneda local, más decimales para tasas de cambio) desde el diseño del sistema.
- Evitar conversiones intermedias innecesarias entre tipos de dato que puedan introducir redondeos acumulados en cálculos financieros.
- Documentar la regla de redondeo aplicada (redondeo bancario, truncamiento, etc.) para que sea reproducible.

**Dónde aparece con más frecuencia**
- Finanzas y contabilidad con cálculos encadenados (intereses, impuestos, conversiones de moneda).
- Sistemas científicos o de ingeniería con mediciones de alta precisión.

---

### 2.5 Delimitadores rotos dentro de un valor (CSV estructuralmente inválido)

**Definición:** cuando un valor de texto contiene el mismo carácter usado como delimitador del archivo (comúnmente la coma) sin estar correctamente encerrado entre comillas, el archivo CSV se desalinea: el contenido de una celda se reparte incorrectamente entre varias columnas.

**Ejemplos típicos**
- Un campo de dirección como `Calle 10, Apto 502` en un CSV delimitado por comas, sin comillas, que rompe el conteo de columnas de esa fila.
- Nombres de empresa con comas internas (`Empresa, S.A.S.`) mal exportados desde un sistema origen.
- Saltos de línea dentro de una celda de texto libre que el lector de CSV interpreta como el inicio de una fila nueva.

**Cómo se detecta**
- Verificar que el número de columnas sea idéntico en todas las filas del archivo al leerlo; filas con conteo distinto son señal directa de este problema.
- Revisar si el archivo fuente utilizó comillas (`"..."`) para encerrar los campos de texto que contienen el carácter delimitador.

**Buenas prácticas y recomendaciones de tratamiento**
- Re-exportar el archivo fuente asegurando que todo campo de texto que pueda contener el delimitador esté correctamente encerrado entre comillas dobles (estándar RFC 4180 para CSV).
- Si no es posible reexportar, usar un lector de CSV tolerante a errores que permita identificar y aislar las filas problemáticas para corrección manual, en vez de descartarlas silenciosamente.
- Preferir formatos menos ambiguos cuando el contenido de texto es complejo (ej. TSV con tabulador, o formatos como Parquet/JSON para datos con texto libre extenso).

**Dónde aparece con más frecuencia**
- Exportaciones de sistemas administrativos con campos de dirección o razón social en texto libre.
- Datos abiertos gubernamentales exportados sin control de calidad del formato CSV.

---

## 3. Problemas de texto más específicos

### 3.1 Campos multivaluados en una sola celda

**Definición:** una celda contiene múltiples valores independientes concatenados (con comas, punto y coma, u otro separador) cuando conceptualmente deberían representarse como registros o columnas separadas, violando el principio de "un valor por celda" de los datos bien estructurados (forma normal).

**Ejemplos típicos**
- Una columna "Habilidades" con el valor `Python, SQL, Excel` en una sola celda para un mismo candidato.
- Una columna "Teléfonos" con `3001234567 / 3007654321`.
- Una columna "Síntomas" en un registro clínico con varios diagnósticos separados por punto y coma.

**Cómo se detecta**
- Búsqueda de separadores comunes (coma, punto y coma, barra, guion) dentro de campos que conceptualmente deberían ser atómicos.
- Revisión de la longitud y complejidad del texto en columnas categóricas: valores inusualmente largos con puntuación interna sugieren multivaluación.

**Buenas prácticas y recomendaciones de tratamiento**
- Decidir según el caso de uso: si se necesita analizar cada valor individualmente, separar (`explode`) la celda en múltiples filas (una fila por valor, repitiendo el resto de columnas) o en múltiples columnas binarias (una columna por valor posible, tipo *one-hot*).
- Documentar el separador usado y estandarizarlo si varía dentro del mismo dataset (a veces coma, a veces punto y coma).
- Si el campo permite selección múltiple en el sistema de origen, evaluar rediseñar la captura como una tabla relacionada en vez de un campo de texto concatenado.

**Dónde aparece con más frecuencia**
- RRHH (habilidades, certificaciones).
- Salud (síntomas, diagnósticos múltiples, medicamentos).
- Encuestas con preguntas de selección múltiple exportadas como texto plano.

---

### 3.2 Mezcla de idiomas dentro del mismo campo categórico

**Definición:** una misma columna categórica contiene valores capturados en distintos idiomas para representar el mismo concepto, generalmente por operación en múltiples países o por integración de sistemas con distinto idioma de interfaz.

**Ejemplos típicos**
- Una columna "País" con `Colombia`, `Brazil`, `Brasil`, `USA`, `Estados Unidos` mezclados.
- Una columna de estado de pedido con `Enviado`, `Shipped`, `Delivered`, `Entregado`.
- Nombres de mes o día de la semana en español e inglés dentro de la misma columna de texto.

**Cómo se detecta**
- Tabla de frecuencia de valores únicos por columna categórica: la coexistencia de palabras claramente de distintos idiomas para el mismo concepto es fácil de identificar visualmente en esa tabla.

**Buenas prácticas y recomendaciones de tratamiento**
- Migrar a códigos estandarizados internacionales quando sea posible (ISO 3166 para países, ISO 639 para idiomas), que son agnósticos al idioma de captura.
- Si no existe estándar aplicable, construir un diccionario de mapeo multiidioma → valor único estandarizado, igual que para la inconsistencia categórica general.
- Definir el idioma oficial de captura del sistema para evitar la recurrencia, especialmente en operaciones multipaís.

**Dónde aparece con más frecuencia**
- Empresas multinacionales o con operación en varios países de Latinoamérica.
- E-commerce con proveedores logísticos internacionales.

---

### 3.3 Comillas o caracteres "fantasma" de copiado

**Definición:** caracteres invisibles o "casi invisibles" que quedan incrustados en el texto al copiar y pegar desde otras aplicaciones (Word, PDF, páginas web), que no se ven a simple vista pero rompen comparaciones exactas de texto y búsquedas.

**Ejemplos típicos**
- Comillas tipográficas curvas (" ") en vez de comillas rectas ("), copiadas desde Word.
- Guiones largos (—) o guiones especiales en vez de guion simple (-).
- Espacios de ancho no separable (*non-breaking space*, `\u00A0`) que visualmente parecen un espacio normal pero no lo son para el sistema.
- Caracteres de control invisibles (retorno de carro `\r`, marcas de orden de bytes *BOM*) al inicio de un archivo o celda.

**Ejemplos típicos**
- Un valor `"Bogotá"` con espacio de ancho no separable no hace match con `"Bogotá"` con espacio normal en un cruce (join) de tablas, aunque se vean idénticos.

**Cómo se detecta**
- Inspección del código de carácter (ord/unicode) de los espacios y comillas en campos que fallan cruces (joins) inesperadamente pese a parecer idénticos.
- Búsqueda del carácter BOM al inicio del archivo, común en archivos exportados desde ciertas versiones de Excel o sistemas Windows.

**Buenas prácticas y recomendaciones de tratamiento**
- Aplicar una normalización Unicode estándar (NFKC/NFKD) a todos los campos de texto antes de cualquier comparación o cruce entre tablas.
- Reemplazar sistemáticamente comillas tipográficas y espacios especiales por sus equivalentes estándar (comilla recta, espacio simple) como parte del pipeline de limpieza de texto.
- Verificar y remover el BOM al leer archivos si la herramienta de lectura no lo maneja automáticamente.

**Dónde aparece con más frecuencia**
- Datos copiados manualmente desde documentos Word o PDF hacia Excel/CSV.
- Archivos exportados desde sistemas Windows hacia sistemas Unix/Linux o viceversa.

---

### 3.4 Truncamiento de texto por límite de longitud

**Definición:** el sistema de origen (o de destino) impone un límite máximo de caracteres a un campo de texto, y cualquier valor que exceda ese límite se corta silenciosamente, perdiendo información sin generar ningún error visible.

**Ejemplos típicos**
- Un campo de "Nombre completo" limitado a 30 caracteres que corta nombres compuestos largos.
- Una dirección completa truncada porque el campo del sistema origen solo permite 50 caracteres.
- Comentarios u observaciones de texto libre cortados abruptamente a mitad de una palabra.

**Cómo se detecta**
- Revisión de la distribución de longitud de caracteres por columna de texto: una acumulación anómala de valores que terminan exactamente en la misma longitud máxima es la señal característica de truncamiento.
- Comparación contra la fuente original (si está disponible) para confirmar pérdida de información.

**Buenas prácticas y recomendaciones de tratamiento**
- Identificar el límite de longitud del sistema de origen y ampliarlo si el negocio lo requiere, en vez de solo lidiar con el síntoma en el dataset limpio.
- Marcar como "posiblemente truncado" (no como error de otro tipo) los registros que llegan exactamente al límite detectado, para que no se traten igual que un dato completo.
- Si el campo truncado es crítico (ej. dirección para envío), gestionar la recuperación del valor completo desde la fuente original antes de continuar el proceso.

**Dónde aparece con más frecuencia**
- Sistemas legacy con campos de longitud fija definidos hace muchos años.
- Migraciones de datos entre sistemas con distintos límites de longitud de campo.

---

## 4. Problemas temporales más avanzados

### 4.1 Bug de fecha base 1900 vs 1904 en Excel

**Definición:** Excel almacena internamente las fechas como un número de días desde una fecha base, pero existen dos sistemas distintos según la plataforma de origen del archivo (sistema 1900, usado por Excel para Windows, y sistema 1904, usado históricamente por Excel para Mac). Si un archivo se interpreta con el sistema base incorrecto, todas sus fechas quedan desplazadas por un margen fijo de días.

**Ejemplos típicos**
- Fechas que aparecen consistentemente desplazadas por exactamente 4 años (1462 días) al abrir un archivo creado en Mac con una herramienta que asume el sistema 1900.
- Además, el sistema 1900 de Excel contiene un error histórico conocido: trata 1900 como año bisiesto (no lo es), lo que puede generar un desfase adicional de 1 día para fechas anteriores a marzo de 1900.

**Cómo se detecta**
- Si todas las fechas de una columna están desplazadas por el mismo número exacto de días respecto a un valor de referencia conocido, es indicio de este problema, no de errores de captura individuales.
- Revisar la configuración del sistema de fecha del archivo Excel origen (`Opciones > Avanzadas > Al calcular este libro`).

**Buenas prácticas y recomendaciones de tratamiento**
- Identificar y documentar explícitamente qué sistema de fecha base usa cada archivo fuente antes de consolidar datos provenientes de distintas versiones de Excel (Windows vs. Mac).
- Aplicar la corrección de desplazamiento de forma sistemática a toda la columna una vez confirmado el sistema incorrecto, nunca corregir fecha por fecha manualmente.
- Al migrar datos, convertir siempre a un formato de fecha estándar y no ambiguo (ISO 8601) para eliminar la dependencia del sistema base de Excel.

**Dónde aparece con más frecuencia**
- Organizaciones con usuarios mixtos de Excel para Windows y Excel para Mac.
- Archivos históricos migrados desde versiones muy antiguas de Excel.

---

### 4.2 Series de tiempo con huecos irregulares

**Definición:** en un dataset que debería tener mediciones a una frecuencia regular (diaria, horaria, mensual), existen periodos faltantes que no siguen un patrón uniforme, lo cual es distinto al simple "valor faltante" en una fila existente: aquí faltan filas completas de ciertos momentos en el tiempo.

**Ejemplos típicos**
- Una serie de ventas diarias que debería tener 365 registros al año, pero tiene solo 340, con huecos en fechas específicas sin patrón aparente.
- Lecturas de sensores IoT con frecuencia esperada cada 5 minutos que presentan huecos de horas completas por caídas de conectividad.
- Reportes mensuales de un indicador que saltan meses completos sin publicación.

**Cómo se detecta**
- Generar la secuencia completa de fechas/periodos esperada según la frecuencia teórica del dataset, y comparar contra las fechas realmente presentes para identificar los huecos exactos.
- Calcular la diferencia entre timestamps consecutivos y detectar valores que excedan significativamente el intervalo esperado.

**Buenas prácticas y recomendaciones de tratamiento**
- No rellenar los huecos automáticamente con interpolación sin antes entender la causa (¿el negocio realmente no operó ese día, o fue una falla de captura?).
- Si el hueco corresponde a un periodo sin operación real (ej. fin de semana en un negocio que no abre), no tratarlo como faltante sino como ausencia esperada y documentarla como tal.
- Si el hueco es una falla real de captura, decidir entre interpolación (lineal, estacional) o dejarlo explícitamente como faltante según el uso posterior de la serie.
- Documentar la frecuencia teórica esperada de la serie como metadato del dataset, para que cualquier análisis futuro pueda validar completitud automáticamente.

**Dónde aparece con más frecuencia**
- IoT y sensores (telemetría, monitoreo ambiental).
- Series financieras y de mercado (días no hábiles vs. fallas reales de reporte).
- Reportes gubernamentales periódicos con publicaciones irregulares.

---

### 4.3 Mezcla de fechas timezone-naive y timezone-aware

**Definición:** dentro de la misma columna coexisten timestamps que incluyen información de zona horaria (*timezone-aware*) con timestamps que no la incluyen (*timezone-naive*), lo que hace imposible comparar u ordenar correctamente los valores sin ambigüedad.

**Ejemplos típicos**
- Una columna de "fecha de transacción" donde algunos registros vienen en UTC explícito y otros en hora local sin especificar cuál zona horaria representan.
- Integración de dos sistemas donde uno registra timestamps con offset (`2026-07-24T10:00:00-05:00`) y otro sin offset (`2026-07-24T10:00:00`).

**Cómo se detecta**
- Revisar si el patrón de formato de la columna de fecha/hora incluye o no el sufijo de zona horaria (`Z`, `+HH:MM`, `-HH:MM`) de forma consistente en todos los registros.
- Comparar timestamps de eventos que deberían ser simultáneos entre sistemas distintos para detectar desfases sistemáticos de horas completas.

**Buenas prácticas y recomendaciones de tratamiento**
- Estandarizar todo el dataset a UTC con zona horaria explícita como estándar interno de almacenamiento, y convertir a hora local únicamente en la capa de presentación/visualización.
- Para los registros *timezone-naive*, documentar y validar con el área de negocio cuál era la zona horaria real de captura antes de asignarla, en vez de asumir una por defecto.
- Incluir el offset de zona horaria como parte del formato estándar (ISO 8601 con offset) en todas las integraciones futuras entre sistemas.

**Dónde aparece con más frecuencia**
- Empresas con operación en múltiples zonas horarias o países.
- Integraciones entre sistemas locales y servicios en la nube (que suelen operar en UTC por defecto).

---

## 5. Problemas de esquema a través del tiempo

### 5.1 Schema drift (deriva de esquema)

**Definición:** ocurre cuando la estructura del dataset (nombres de columnas, tipos de dato, presencia/ausencia de columnas) cambia entre distintas cargas o periodos de tiempo del mismo proceso, sin que ese cambio esté documentado, rompiendo la comparabilidad histórica.

**Ejemplos típicos**
- Una columna llamada `telefono` en los datos de 2023 que pasa a llamarse `numero_contacto` en 2024, tratándose ambas como si fueran la misma variable sin mapeo explícito.
- Una columna que era de tipo texto en cargas antiguas y pasa a ser numérica en cargas recientes.
- Una columna que existía en versiones anteriores del sistema y desaparece por completo en versiones nuevas, dejando un hueco estructural al consolidar el histórico.

**Cómo se detecta**
- Comparar el esquema (nombres y tipos de columna) de cada carga o periodo contra el esquema base de referencia, y registrar cualquier diferencia detectada.
- Revisar los metadatos de versión del sistema de origen que generó cada carga del dataset.

**Buenas prácticas y recomendaciones de tratamiento**
- Mantener un diccionario de datos versionado que documente explícitamente cuándo cambió cada columna (nombre, tipo, significado) y por qué.
- Construir una capa de mapeo/normalización de esquema como primer paso del pipeline, antes de consolidar datos de distintos periodos, para unificar nombres y tipos de columna equivalentes.
- Implementar validación automática de esquema (schema validation) en cada nueva carga de datos, que alerte de inmediato si el esquema difiere del esperado, en vez de descubrirlo después en el análisis.

**Dónde aparece con más frecuencia**
- Datasets históricos consolidados a partir de múltiples versiones de un mismo sistema a lo largo de los años.
- Integraciones de datos abiertos gubernamentales, donde el formato de publicación cambia entre periodos administrativos.

---

### 5.2 Cambio de formato del identificador único en el tiempo

**Definición:** el campo que actúa como identificador único de una entidad (persona, producto, transacción) cambia de formato, longitud o esquema de codificación a lo largo del tiempo, dificultando el cruce y la deduplicación entre registros históricos y recientes.

**Ejemplos típicos**
- Cédulas de ciudadanía que pasan de 8 a 10 dígitos, o que incluyen ceros a la izquierda en un periodo y no en otro.
- Códigos de producto (SKU) que cambian de esquema alfanumérico tras una migración de sistema de inventario.
- Números de historia clínica que cambian de formato tras la fusión de dos instituciones de salud.

**Cómo se detecta**
- Análisis de la longitud y patrón (expresión regular) del campo identificador segmentado por periodo de tiempo, buscando cambios sistemáticos.
- Verificación de tasas de "no-match" anómalamente altas al cruzar datos históricos con datos recientes usando el identificador como llave.

**Buenas prácticas y recomendaciones de tratamiento**
- Construir y mantener una tabla de equivalencias (identificador antiguo → identificador nuevo) cuando el cambio de formato es conocido y documentado por el área de negocio.
- Nunca asumir que dos identificadores con formato distinto son automáticamente la misma entidad ni automáticamente entidades distintas: requiere validación con una fuente autorizada.
- Generar, cuando sea posible, un identificador único interno y estable (surrogate key) que no dependa del identificador operativo externo, precisamente para blindar el dataset ante estos cambios futuros.

**Dónde aparece con más frecuencia**
- Fusiones y adquisiciones de empresas o instituciones (unificación de bases de clientes/pacientes).
- Cambios regulatorios en el formato de documentos de identificación a nivel país.

---

## 6. Matriz de severidad de las categorías adicionales

| Categoría de problema | Severidad típica | Facilidad de corrección | Justificación |
|---|:---:|:---:|---|
| Claves foráneas huérfanas (1.1) | Crítica | Media | Puede invalidar joins completos y ocultar pérdida real de información. |
| Delimitadores rotos en CSV (2.5) | Crítica | Media | Puede desalinear la totalidad de las columnas del archivo. |
| Autoconversión de texto a fecha (2.1) | Crítica | Baja | La pérdida de información suele ser irreversible una vez guardado el archivo. |
| Notación científica no deseada (2.3) | Crítica | Baja | Trunca dígitos de identificadores de forma irreversible. |
| Inconsistencia de granularidad (1.2) | Alta | Media | Duplica sumas y totales si no se separa a tiempo. |
| Bug fecha base 1900/1904 (4.1) | Alta | Alta | Desplaza fechas de forma sistemática, pero es corregible en bloque una vez identificado. |
| Mezcla timezone-naive/aware (4.3) | Alta | Media | Genera ambigüedad de horas que afecta reportes y SLAs. |
| Schema drift (5.1) | Alta | Media | Rompe la comparabilidad histórica de todo el dataset. |
| Cambio de formato de ID en el tiempo (5.2) | Alta | Media-Baja | Dificulta deduplicación y trazabilidad histórica de entidades. |
| Errores de fórmula como texto (2.2) | Media-Alta | Alta | Fácil de detectar por patrón, pero requiere entender la causa antes de tratarla. |
| Series de tiempo con huecos (4.2) | Media-Alta | Media | Afecta el análisis de tendencia si no se documenta la causa del hueco. |
| Campos multivaluados en una celda (3.1) | Media | Media | Requiere transformación estructural (explode) pero es predecible. |
| Truncamiento de texto (3.4) | Media | Baja-Media | La recuperación depende de si la fuente original sigue disponible. |
| Pérdida de precisión / overflow (2.4) | Media | Media | Relevante principalmente en cálculos financieros o científicos sensibles. |
| Mezcla de idiomas (3.2) | Baja-Media | Alta | Corregible con diccionario de mapeo estándar. |
| Comillas/caracteres fantasma (3.3) | Baja | Alta | Invisible pero fácil de normalizar con procesamiento de texto estándar. |

---

## 7. Checklist adicional de depuración

Se recomienda ejecutar estas validaciones **después** del checklist de las 12 categorías principales del informe base, ya que varias de estas son casos más específicos que requieren el dataset ya parcialmente limpio:

1. Validar integridad referencial entre tablas relacionadas (claves foráneas).
2. Confirmar que el grano (nivel de detalle) de cada tabla es único y no mezcla agregados con detalle.
3. Verificar el número de columnas por fila en todo archivo CSV antes de la carga completa.
4. Forzar el tipo de dato "texto" en identificadores numéricos largos y códigos alfanuméricos sensibles antes de abrir en Excel.
5. Buscar patrones de error de fórmula de Excel en columnas numéricas.
6. Auditar la distribución de longitud de campos de texto para detectar truncamiento.
7. Confirmar el sistema de fecha base (1900/1904) de archivos Excel históricos antes de consolidar.
8. Validar consistencia de zona horaria en todas las columnas de timestamp.
9. Comparar el esquema de cada carga nueva contra el esquema de referencia documentado (schema drift).
10. Verificar si el identificador único ha cambiado de formato a lo largo del histórico del dataset.

---

## 8. Conclusión del anexo

Las categorías descritas en este anexo son menos universales que las 12 del informe principal, pero se vuelven críticas en contextos específicos: integraciones entre sistemas, consolidación de históricos de varios años, archivos Excel con fórmulas complejas, y datasets con series de tiempo o múltiples fuentes. Un diagnóstico de calidad de datos verdaderamente exhaustivo debe revisar primero las 12 categorías transversales del informe base, y luego contrastar el dataset contra este catálogo adicional según el tipo de fuente y el contexto del proyecto (relacional, Excel/CSV, series de tiempo, o consolidación histórica).

Al igual que en el informe principal, se recomienda mantener siempre la distinción entre **error de calidad de datos** (lo que se corrige en esta etapa) y **dato atípico** (lo que se analiza en la etapa estadística posterior), incluso para estas categorías más técnicas.
