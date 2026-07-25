"""
=============================================================================
ADVISOR DE IA PARA AUDITDATA AI
=============================================================================

QUE HACE ESTE ARCHIVO:
-----------------------
Este archivo es el "cerebro de IA" del sistema. Se conecta a Groq API
(ejecuta Llama 3.1 gratis) y genera recomendaciones de limpieza de datos.

FLUJO:
------
1. El diagnostico encuentra problemas (28 categorias)
2. Este archivo envia esos problemas a Groq API
3. Groq responde con recomendaciones de limpieza
4. El analista decide que hacer con cada recomendacion

DEPENDENCIAS:
-------------
- groq: Instalar con `pip install groq`
- Variable de entorno: GROQ_API_KEY

COMO FUNCIONA GROQ API:
-----------------------
Groq es un servicio que ejecuta modelos de IA (como Llama 3.1) de forma
gratuita y rapida (~200ms por peticion).

Para usarla:
1. Crear cuenta en https://console.groq.com
2. Crear API Key
3. Configurar variable de entorno GROQ_API_KEY
4. Este archivo se encarga del resto

EJEMPLO DE USO MANUAL (sin el sistema):
-----------------------------------------
from groq import Groq

client = Groq(api_key="tu_api_key_aqui")
response = client.chat.completions.create(
    model="llama-3.1-8b-instant",
    messages=[{"role": "user", "content": "Hola"}]
)
print(response.choices[0].message.content)

AUTOR: AuditData AI
VERSION: 1.0
=============================================================================
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

try:
    from groq import Groq
except ImportError:
    Groq = None
    logger.warning("groq no instalado. Ejecuta: pip install groq")


# ---------------------------------------------------------------------------
# CONFIGURACION
# ---------------------------------------------------------------------------

# Modelo de IA que usamos (Llama 3.1 es rapido y gratis en Groq)
# Otros modelos disponibles: llama-3.1-70b-versatile, mixtral-8x7b-32768
MODEL = "llama-3.1-8b-instant"

# Limite de tokens para la respuesta (4096 es suficiente para recomendaciones)
MAX_TOKENS = 4096

# Temperatura: 0 = preciso, 1 = creativo. Para recomendaciones técnicas usamos 0.3
TEMPERATURE = 0.3


# ---------------------------------------------------------------------------
# INICIALIZACION DEL CLIENTE
# ---------------------------------------------------------------------------

def init_groq_client() -> Groq | None:
    """
    Crea el cliente de conexion con Groq API.

    COMO FUNCIONA:
    - Lee la variable de entorno GROQ_API_KEY
    - Si existe, crea un cliente Groq y lo retorna
    - Si no existe, retorna None (el sistema funciona sin IA)

    COMO CONFIGURAR LA VARIABLE DE ENTORNO:
    - En Render: Settings → Environment → Add GROQ_API_KEY
    - En local: export GROQ_API_KEY=tu_api_key (Linux/Mac)
    - En Windows: set GROQ_API_KEY=tu_api_key

    RETORNA:
    - Objeto Groq si la key existe
    - None si no hay key (el sistema funciona sin IA)

    EJEMPLO:
    >>> client = init_groq_client()
    >>> if client:
    >>>     print("IA habilitada")
    >>> else:
    >>>     print("IA deshabilitada (sin API key)")
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.warning("GROQ_API_KEY no configurada. IA deshabilitada.")
        return None
    try:
        client = Groq(api_key=api_key)
        logger.info("Cliente Groq inicializado correctamente")
        return client
    except Exception as e:
        logger.error("Error al inicializar Groq: %s", e)
        return None


# ---------------------------------------------------------------------------
# PROMPT SISTEMA (CONTEXTO PARA LA IA)
# ---------------------------------------------------------------------------

def build_system_prompt() -> str:
    """
    Crea el "contexto" que le da a la IA para que entienda las 28 categorias.

    QUE HACE:
    - Construye un prompt largo con instrucciones
    - Incluye las 28 categorias de problemas de datos
    - Indica que debe responder en formato JSON
    - Define que informacion debe incluir cada recomendacion

    POR QUE ES IMPORTANTE:
    - Sin este contexto, la IA no sabe que problemas buscar
    - Sin este contexto, la IA no sabe como responder
    - El prompt es como "entrenar" a la IA para este trabajo especifico

    RETORNA:
    - String con el prompt completo (aprox 2000 caracteres)

    EJEMPLO DE USO:
    >>> prompt = build_system_prompt()
    >>> print(prompt[:100])
    >>> "Eres un Auditor Senior de Calidad de Datos..."
    """
    return """Eres un Auditor Senior de Calidad de Datos con 15 anos de experiencia.
Tu trabajo es analizar problemas en datasets y recomendar acciones de limpieza.

REGLAS IMPORTANTES:
1. Responde SOLO en formato JSON valido
2. Cada recomendacion debe tener: text, action, confidence
3. El text debe ser una justificacion tecnica clara (1-2 oraciones)
4. El action debe ser un objeto con: kind, column, reason
5. El confidence es un numero de 0.0 a 1.0

TIPOS DE ACCIONES DISPONIBLES:
- "fill_missing": Llenar valores faltantes
  - method: "mean", "median", "mode", "fixed_value", "forward_fill"
  - value: valor a usar (si es fixed_value)
- "drop_duplicates": Eliminar duplicados
  - method: "first", "last", "all"
- "standardize_text": Estandarizar texto
  - method: "lowercase", "trim", "capitalize", "remove_accents"
- "standardize_synonyms": Unificar sinonimos
  - mapping: {"valor_malo": "valor_bueno"}
- "convert_type": Convertir tipo de dato
  - target_type: "number", "date", "string"
- "drop_rows": Eliminar filas
  - condition: condicion para eliminar
- "fix_format": Corregir formato
  - format: formato destino
- "merge_columns": Combinar columnas
  - columns: ["col1", "col2"]
- "split_column": Dividir columna
  - separator: ","
- "encode_categorical": Codificar categorias
  - method: "one_hot", "label"

CATEGORIAS DE PROBLEMAS (28):
1. MISSING: Valores faltantes o nulos
2. DUPLICATE: Filas duplicadas
3. DATE_FORMAT: Formatos de fecha inconsistentes
4. NUMERIC_DOMAIN: Valores fuera de rango numerico
5. TEXT_ERROR: Errores de texto (espacios, mayusculas)
6. CATEGORICAL: Inconsistencia categorica
7. TYPE_ERROR: Tipo de dato incorrecto
8. UNIT_ERROR: Unidades inconsistentes
9. ENCODING: Problemas de codificacion
10. OUT_OF_RANGE: Valores fuera de rango
11. FORMULA_ERROR: Errores de Excel
12. SCIENTIFIC: Notacion cientifica no deseada
13. MULTI_VALUE: Multiples valores en una celda
14. MIXED_LANG: Mezcla de idiomas
15. GHOST_CHAR: Caracteres invisibles
16. TEXT_TRUNCATION: Texto truncado
17. BOOL_INCONSISTENCY: Booleanos inconsistentes
18. TYPE_PER_CELL: Tipos mezclados por celda
19. UNEXPECTED_TYPE: Tipo inesperado
20-28: Anexos (orfandos FK, granularidad, etc.)

RESPUESTA ESPERADA (JSON):
{
  "recommendations": [
    {
      "category": "NOMBRE_CATEGORIA",
      "count": 10,
      "text": "Justificacion tecnica del problema y por que la accion recomendada es correcta",
      "action": {
        "kind": "tipo_de_accion",
        "column": "nombre_columna",
        "method": "metodo",
        "reason": "Justificacion de la accion"
      },
      "confidence": 0.85
    }
  ]
}"""


# ---------------------------------------------------------------------------
# FUNCION PRINCIPAL
# ---------------------------------------------------------------------------

def get_ai_recommendations(
    diagnostic: dict[str, Any],
    sample_rows: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """
    FUNCION PRINCIPAL: Genera recomendaciones de IA para cada problema encontrado.

    COMO FUNCIONA:
    1. Recibe el diagnostico (resultados de las 28 categorias)
    2. Para cada columna con problemas, construye un prompt
    3. Envia el prompt a Groq API
    4. Groq responde con recomendaciones
    5. Convierte la respuesta a JSON estructurado

    PARAMETROS:
    - diagnostic: Diccionario con el resultado del diagnostico
      Ejemplo: {"columns": [...], "summary": {...}}
    - sample_rows: Lista de filas de ejemplo para contexto
      Ejemplo: [{"nombre": "Juan", "edad": "25"}, ...]

    RETORNA:
    - Diccionario con recomendaciones para cada columna
      Ejemplo: {"recommendations": [...]}

    SI NO HAY API KEY:
    - Retorna un mensaje indicando que la IA esta deshabilitada
    - El sistema funciona normalmente sin IA

    EJEMPLO DE USO:
    >>> from data_engine.diagnostic import diagnose_dataset
    >>> from data_engine.ai_advisor import get_ai_recommendations
    >>>
    >>> # 1. Diagnosticar el dataset
    >>> diagnostic = diagnose_dataset(headers, rows)
    >>>
    >>> # 2. Obtener recomendaciones de IA
    >>> recommendations = get_ai_recommendations(
    >>>     diagnostic=diagnostic.to_dict(),
    >>>     sample_rows=rows[:5]
    >>> )
    >>>
    >>> # 3. Mostrar recomendaciones
    >>> for rec in recommendations["recommendations"]:
    >>>     print(f"Columna: {rec['column']}")
    >>>     print(f"Problemas: {rec['issues_summary']}")
    >>>     for r in rec["recommendations"]:
    >>>         print(f"  - {r['text']}")
    >>>         print(f"    Accion: {r['action']}")
    """
    # Paso 1: Verificar si hay cliente Groq disponible
    client = init_groq_client()
    if not client:
        return {
            "recommendations": [],
            "message": "IA deshabilitada. Configura GROQ_API_KEY para habilitar.",
            "status": "no_api_key"
        }

    # Paso 2: Preparar el contexto con la guia maestra
    system_prompt = build_system_prompt()

    # Paso 3: Procesar cada columna que tenga problemas
    all_recommendations = []
    columns = diagnostic.get("columns", [])

    for col_data in columns:
        column_name = col_data.get("column", "")
        issues = col_data.get("issues", [])
        inferred_domain = col_data.get("inferred_domain", "")

        # Solo procesar columnas que tengan problemas
        if not issues:
            continue

        # Paso 4: Obtener valores de ejemplo de esta columna
        sample_values = _get_sample_values(column_name, sample_rows)

        # Paso 5: Construir el prompt para esta columna
        user_prompt = _build_prompt_for_column(
            column_name=column_name,
            issues=issues,
            sample_values=sample_values,
            inferred_domain=inferred_domain,
            total_rows=col_data.get("total_rows", 0)
        )

        # Paso 6: Enviar a Groq y obtener respuesta
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                response_format={"type": "json_object"}
            )

            # Paso 7: Extraer y parsear la respuesta
            response_text = response.choices[0].message.content
            parsed = _parse_ai_response(response_text)

            # Paso 8: Agregar a la lista de recomendaciones
            all_recommendations.append({
                "column": column_name,
                "inferred_domain": inferred_domain,
                "issues_summary": f"{len(issues)} problema(s) detectado(s)",
                "recommendations": parsed.get("recommendations", [])
            })

        except Exception as e:
            logger.error("Error al obtener recomendaciones para %s: %s", column_name, e)
            all_recommendations.append({
                "column": column_name,
                "inferred_domain": inferred_domain,
                "issues_summary": f"{len(issues)} problema(s) detectado(s)",
                "recommendations": [],
                "error": str(e)
            })

    return {
        "recommendations": all_recommendations,
        "message": f"Procesadas {len(all_recommendations)} columnas con problemas",
        "status": "success"
    }


# ---------------------------------------------------------------------------
# FUNCIONES AUXILIARES (CONSTRUIR PROMPTS)
# ---------------------------------------------------------------------------

def _build_prompt_for_column(
    column_name: str,
    issues: list[dict[str, Any]],
    sample_values: list[str],
    inferred_domain: str,
    total_rows: int
) -> str:
    """
    Construye el prompt especifico para una columna con problemas.

    QUE HACE:
    - Toma el nombre de la columna, los problemas y ejemplos
    - Los formatea en un prompt claro para la IA
    - Incluye informacion del dominio inferido

    PARAMETROS:
    - column_name: Nombre de la columna (ej: "edad")
    - issues: Lista de problemas encontrados
    - sample_values: Valores de ejemplo de la columna
    - inferred_domain: Dominio inferido (ej: "age", "currency")
    - total_rows: Numero total de filas

    RETORNA:
    - String con el prompt formateado

    EJEMPLO:
    >>> prompt = _build_prompt_for_column(
    ...     column_name="edad",
    ...     issues=[{"category_code": "MISSING", "count": 15}],
    ...     sample_values=["25", "NA", "30"],
    ...     inferred_domain="age",
    ...     total_rows=100
    ... )
    """
    issues_text = "\n".join([
        f"- {issue.get('category', '')}: {issue.get('count', 0)} ocurrencias ({issue.get('percentage', 0):.1f}%)"
        for issue in issues
    ])

    samples_text = ", ".join(sample_values[:10]) if sample_values else "No disponibles"

    return f"""ANALIZA LA SIGUIENTE COLUMNA Y RECOMIENDA ACCIONES DE LIMPIEZA:

COLUMNA: {column_name}
DOMINIO INFERIDO: {inferred_domain or "desconocido"}
TOTAL FILAS: {total_rows}

PROBLEMAS ENCONTRADOS:
{issues_text}

VALORES DE EJEMPLO: {samples_text}

INSTRUCCIONES:
1. Para cada problema, indica que tipo de limpieza es mejor
2. Justifica tecnicamente por que esa accion es correcta
3. Asigna un nivel de confianza (0.0 a 1.0)
4. Responde en formato JSON como se indico en el sistema

IMPORTANTE: 
- Si hay multiples problemas, recomienda acciones para CADA uno
- Prioriza acciones que no pierdan datos (imputar antes que eliminar)
- Si hay dudas, indica confidence baja (< 0.5)"""


# ---------------------------------------------------------------------------
# FUNCIONES AUXILIARES (OBTENER EJEMPLOS)
# ---------------------------------------------------------------------------

def _get_sample_values(
    column_name: str,
    sample_rows: list[dict[str, Any]] | None,
    max_samples: int = 10
) -> list[str]:
    """
    Obtiene valores de ejemplo de una columna para dar contexto a la IA.

    QUE HACE:
    - Toma las primeras N filas del dataset
    - Extrae los valores de la columna especificada
    - Retorna una lista de strings

    PARAMETROS:
    - column_name: Nombre de la columna
    - sample_rows: Lista de filas de ejemplo
    - max_samples: Maximo de valores a retornar (default 10)

    RETORNA:
    - Lista de strings con valores de ejemplo
      Ejemplo: ["25", "30", "NA", "45"]

    POR QUE ES IMPORTANTE:
    - La IA necesita ver ejemplos para entender el tipo de dato
    - Sin ejemplos, la IA podria recomendar acciones incorrectas

    EJEMPLO:
    >>> samples = _get_sample_values("edad", rows, max_samples=5)
    >>> print(samples)
    ['25', '30', 'NA', '45', '35']
    """
    if not sample_rows:
        return []

    values = []
    for row in sample_rows[:max_samples]:
        val = row.get(column_name, "")
        values.append(str(val))

    return values


# ---------------------------------------------------------------------------
# FUNCIONES AUXILIARES (PARSear RESPUESTAS)
# ---------------------------------------------------------------------------

def _parse_ai_response(response_text: str) -> dict[str, Any]:
    """
    Convierte la respuesta de Groq en formato JSON estructurado.

    QUE HACE:
    - Recibe el texto de respuesta de Groq
    - Intenta parsearlo como JSON
    - Si falla, crea un JSON basico con el texto original
    - Valida que tenga la estructura correcta

    PARAMETROS:
    - response_text: Respuesta de Groq en texto plano

    RETORNA:
    - Diccionario con estructura:
      {
        "recommendations": [
          {
            "category": "NOMBRE",
            "count": 10,
            "text": "justificacion",
            "action": {...},
            "confidence": 0.85
          }
        ]
      }

    MANEJO DE ERRORES:
    - Si el JSON es invalido, retorna el texto como recomendacion
    - Si falta informacion, completa con valores por defecto
    - Nunca falla, siempre retorna algo util

    EJEMPLO:
    >>> response = '{"recommendations": [{"category": "MISSING", "text": "..."}]}'
    >>> parsed = _parse_ai_response(response)
    >>> print(parsed["recommendations"][0]["category"])
    "MISSING"
    """
    try:
        # Intentar parsear como JSON
        data = json.loads(response_text)

        # Validar que tenga la estructura correcta
        if "recommendations" not in data:
            # Si no tiene "recommendations", crear estructura basica
            data = {"recommendations": [data] if isinstance(data, dict) else []}

        # Validar cada recomendacion
        valid_recommendations = []
        for rec in data.get("recommendations", []):
            if isinstance(rec, dict):
                # Asegurar que tenga los campos minimos
                valid_recommendations.append({
                    "category": rec.get("category", "UNKNOWN"),
                    "count": rec.get("count", 0),
                    "text": rec.get("text", "Sin justificacion"),
                    "action": rec.get("action", {}),
                    "confidence": min(max(rec.get("confidence", 0.5), 0.0), 1.0)
                })

        return {"recommendations": valid_recommendations}

    except json.JSONDecodeError as e:
        # Si el JSON es invalido, crear recomendacion con el texto original
        logger.warning("Error al parsear respuesta JSON: %s", e)
        return {
            "recommendations": [{
                "category": "AI_RESPONSE",
                "count": 0,
                "text": response_text,
                "action": {},
                "confidence": 0.5
            }]
        }
    except Exception as e:
        # Cualquier otro error
        logger.error("Error inesperado al parsear respuesta: %s", e)
        return {
            "recommendations": [{
                "category": "ERROR",
                "count": 0,
                "text": f"Error al procesar respuesta: {e!s}",
                "action": {},
                "confidence": 0.0
            }]
        }
