"""
=============================================================================
ADVISOR DE IA PARA AUDITDATA AI
=============================================================================

QUE HACE ESTE ARCHIVO:
-----------------------
Este archivo es el "cerebro de IA" del sistema. Se conecta a Groq API
(ejecuta Llama 3.1 gratis) y genera recomendaciónes de limpieza de datos.

FLUJO:
------
1. El diagnóstico encuentra problemas (28 categorías)
2. Este archivo envia esos problemas a Groq API
3. Groq responde con recomendaciónes de limpieza
4. El analista decide que hacer con cada recomendación

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
    from groq import Groq, AsyncGroq
except ImportError:
    Groq = None
    AsyncGroq = None
    logger.warning("groq no instalado. Ejecuta: pip install groq")


# ---------------------------------------------------------------------------
# CONFIGURACION
# ---------------------------------------------------------------------------

MODEL = "llama-3.1-8b-instant"
MAX_TOKENS = 4096
TEMPERATURE = 0.3


# ---------------------------------------------------------------------------
# INICIALIZACION DEL CLIENTE (Síncrono y Asíncrono)
# ---------------------------------------------------------------------------

def init_groq_client() -> Groq | None:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.warning("GROQ_API_KEY no configurada. IA deshabilitada.")
        return None
    try:
        if Groq is None:
            return None
        return Groq(api_key=api_key)
    except Exception as e:
        logger.error("Error al inicializar cliente síncrono Groq: %s", e)
        return None


def init_async_groq_client() -> AsyncGroq | None:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.warning("GROQ_API_KEY no configurada. IA asíncrona deshabilitada.")
        return None
    try:
        if AsyncGroq is None:
            return None
        return AsyncGroq(api_key=api_key)
    except Exception as e:
        logger.error("Error al inicializar cliente asíncrono Groq: %s", e)
        return None


# ---------------------------------------------------------------------------
# PROMPT SISTEMA (ROL ETICO DE COPILOTO Y CONTEXTO)
# ---------------------------------------------------------------------------

def build_system_prompt() -> str:
    return """Eres un Auditor Senior y Copiloto Técnico de Calidad de Datos en AuditData AI.

PRINCIPIOS ÉTICOS Y DE INTERACCIÓN:
1. ROL DE COPILOTO: Tú sugieres recomendaciónes fundamentadas, pero el analista humano SIEMPRE tiene el control absoluto y la decisión final sobre qué acciones ejecutar.
2. IDIOMA: Responde SIEMPRE en ESPAÑOL profesional, claro y directo.
3. FORMATO: Responde ÚNICAMENTE en formato JSON válido.
4. REGLA DE DUPLICADOS: La categoría 'DUPLICATE' aplica EXCLUSIVAMENTE a filas completas del dataset (column="__dataset__"). Tener valores repetidos en una sola columna (ej. repetir "Bogotá" o "30") NO es un error de duplicidad de columna.

REGLAS DE RECOMENDACIÓN:
- Cada recomendación debe tener: category, count, text, action, confidence, affected_rows.
- El 'text' debe ser una justificación técnica profesional clara (1-2 oraciones) indicando el por qué de la sugerencia.
- El 'action' debe ser un objeto con: kind, column, reason y parámetros adicionales como 'method' o 'value'.
- El 'confidence' debe ser un número decimal entre 0.0 y 1.0.

TIPOS DE ACCIONES DISPONIBLES EN EL SISTEMA:
- "fill_missing": Llenar faltantes (method: "mean", "median", "mode", "fixed_value", "forward_fill")
- "drop_duplicates": Eliminar filas duplicadas del dataset (method: "first", "last", "all")
- "standardize_text": Estandarizar texto (method: "lowercase", "trim", "capitalize", "remove_accents")
- "convert_type": Convertir tipo de dato (target_type: "number", "date", "string")
- "drop_rows": Eliminar filas con violaciones críticas
- "fix_format": Corregir formatos de fecha u hora
- "replace_value": Reemplazar un valor específico

CATEGORÍAS DE PROBLEMAS (28):
1. MISSING: Valores faltantes o nulos
2. DUPLICATE: Filas duplicadas del dataset (solo en __dataset__)
3. DATE_FORMAT: Formatos de fecha inconsistentes
4. NUMERIC_DOMAIN: Valores fuera de rango numérico
5. TEXT_ERROR: Errores de texto (espacios, mayúsculas)
6. CATEGORICAL: Inconsistencia categórica
7. TYPE_ERROR: Tipo de dato incorrecto
8. UNIT_ERROR: Unidades inconsistentes
9. ENCODING: Problemas de codificación
10. OUT_OF_RANGE: Valores fuera de rango lógico
11-28: Errores de fórmula, notación científica, caracteres fantasma, etc.

RESPUESTA ESPERADA (JSON):
{
  "recommendations": [
    {
      "column": "nombre_columna_o___dataset__",
      "category": "MISSING",
      "count": 10,
      "text": "Justificación técnica clara del problema...",
      "action": {
        "kind": "tipo_de_acción",
        "column": "nombre_columna",
        "method": "metodo",
        "reason": "Justificación de la acción"
      },
      "confidence": 0.85,
      "affected_rows": [1, 5, 12]
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
    Genera recomendaciónes de IA para todos los problemas encontrados.

    OPTIMIZACION: Envia TODAS las columnas en UN SOLO prompt a Groq
    en vez de una llamada por columna. Esto reduce N llamadas API a 1.
    """
    client = init_groq_client()
    if not client:
        return {
            "recommendations": [],
            "message": "IA deshabilitada. Configura GROQ_API_KEY para habilitar.",
            "status": "no_api_key"
        }

    system_prompt = build_system_prompt()
    columns = diagnostic.get("columns", [])

    columns_with_issues = [
        col for col in columns if col.get("issues")
    ]

    if not columns_with_issues:
        return {
            "recommendations": [],
            "message": "No se encontraron problemas de calidad",
            "status": "success"
        }

    user_prompt = _build_batch_prompt(columns_with_issues, sample_rows)

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

        response_text = response.choices[0].message.content
        parsed = json.loads(response_text)

        raw_recs = parsed.get("recommendations", [])
        if isinstance(parsed, dict) and not raw_recs and any(
            k in parsed for k in ("columns", "column")
        ):
            raw_recs = [parsed]

        grouped: dict[str, list[dict]] = {}
        for rec in raw_recs:
            if not isinstance(rec, dict):
                continue
            col_name = rec.get("column", "unknown")
            clean_rec = {
                "category": rec.get("category", "UNKNOWN"),
                "count": rec.get("count", 0),
                "text": rec.get("text", "Sin justificación"),
                "action": rec.get("action", {}),
                "confidence": min(max(rec.get("confidence", 0.5), 0.0), 1.0),
                "affected_rows": rec.get("affected_rows", []),
            }
            grouped.setdefault(col_name, []).append(clean_rec)

        all_recommendations = []
        for col_data in columns_with_issues:
            col_name = col_data.get("column", "")
            issues = col_data.get("issues", [])
            recs_for_col = grouped.get(col_name, [])

            if not recs_for_col:
                recs_for_col = [
                    {
                        "category": iss.get("category", iss.get("category_code", "UNKNOWN")),
                        "count": iss.get("count", 0),
                        "text": f"Problema {iss.get('category_code', iss.get('category', ''))}: "
                                f"{iss.get('count', 0)} ocurrencias. "
                                f"Filas afectadas: {iss.get('affected_rows', [])[:10]}. "
                                f"Requiere revision manual.",
                        "action": {
                            "kind": "review_issue",
                            "column": col_name,
                            "reason": f"Problema {iss.get('category_code', '')} detectado por diagnóstico",
                        },
                        "confidence": 0.3,
                        "affected_rows": iss.get("affected_rows", []),
                    }
                    for iss in issues
                ]

            all_recommendations.append({
                "column": col_name,
                "inferred_domain": col_data.get("inferred_domain", ""),
                "issues_summary": f"{len(issues)} problema(s) detectado(s)",
                "recommendations": recs_for_col,
            })

        return {
            "recommendations": all_recommendations,
            "message": f"Procesadas {len(all_recommendations)} columnas con problemas",
            "status": "success",
        }

    except Exception as e:
        logger.error("Error en batch AI recommendation: %s", e)
        all_recommendations = []
        for col_data in columns_with_issues:
            col_name = col_data.get("column", "")
            issues = col_data.get("issues", [])
            all_recommendations.append({
                "column": col_name,
                "inferred_domain": col_data.get("inferred_domain", ""),
                "issues_summary": f"{len(issues)} problema(s) detectado(s)",
                "recommendations": [
                    {
                        "category": iss.get("category_code", "UNKNOWN"),
                        "count": iss.get("count", 0),
                        "text": f"Error de IA: {e}. Problema detectado pero sin recomendación automatica.",
                        "action": {},
                        "confidence": 0.1,
                    }
                    for iss in issues
                ],
            })
        return {
            "recommendations": all_recommendations,
            "message": f"Error de IA. {len(all_recommendations)} columnas con fallback manual.",
            "status": "error",
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
2. Justifica técnicamente por que esa acción es correcta
3. Asigna un nivel de confianza (0.0 a 1.0)
4. Responde en formato JSON como se indico en el sistema

IMPORTANTE: 
- Si hay múltiples problemas, recomienda acciones para CADA uno
- Prioriza acciones que no pierdan datos (imputar antes que eliminar)
- Si hay dudas, indica confidence baja (< 0.5)"""


def _build_batch_prompt(
    columns_with_issues: list[dict[str, Any]],
    sample_rows: list[dict[str, Any]] | None
) -> str:
    """
    Construye UN SOLO prompt para todas las columnas con problemas.
    Incluye filas afectadas y valores específicos para cada problema.
    """
    parts = [
        "ANALIZA TODAS LAS SIGUIENTES COLUMNAS Y RECOMIENDA ACCIONES DE LIMPIEZA PARA CADA UNA.",
        "Responde con UN SOLO JSON que contenga todas las recomendaciónes agrupadas por columna.",
        "IMPORTANTE: Cada recomendación debe incluir 'affected_rows' con los numeros de fila afectados.",
        "",
    ]

    for col_data in columns_with_issues:
        col_name = col_data.get("column", "")
        issues = col_data.get("issues", [])
        domain = col_data.get("inferred_domain", "")
        total = col_data.get("total_rows", 0)
        sample_values = _get_sample_values(col_name, sample_rows)

        issues_text = "\n".join([
            f"  - {iss.get('category_code', iss.get('category', ''))}: "
            f"{iss.get('count', 0)} ocurrencias ({iss.get('percentage', 0):.1f}%)"
            for iss in issues
        ])

        examples_text = ""
        for iss in issues:
            cat = iss.get('category_code', iss.get('category', ''))
            exs = iss.get('examples', [])
            rows = iss.get('affected_rows', [])
            if exs:
                ex_strs = []
                for e in exs[:3]:
                    if isinstance(e, dict):
                        if 'row' in e and 'value' in e:
                            ex_strs.append(f"    Fila {e['row']}: valor='{e['value']}'")
                        elif 'row' in e and 'detail' in e:
                            ex_strs.append(f"    Fila {e['row']}: {e['detail']}")
                        elif 'row' in e and 'original' in e:
                            ex_strs.append(f"    Fila {e['row']}: '{e['original']}' -> '{e.get('standard', '')}'")
                        elif 'row' in e and 'format' in e:
                            ex_strs.append(f"    Fila {e['row']}: formato='{e['format']}'")
                        elif 'rows' in e:
                            ex_strs.append(f"    Filas {e['rows']}: coinciden al {e.get('match', '?')}")
                if ex_strs:
                    examples_text += f"\n  [{cat}]:\n" + "\n".join(ex_strs)
            elif rows:
                examples_text += f"\n  [{cat}]: Filas afectadas: {rows[:8]}"

        samples_text = ", ".join(sample_values[:8]) if sample_values else "No disponibles"

        parts.append(f"--- COLUMNA: {col_name} ---")
        parts.append(f"Dominio: {domain or 'desconocido'} | Filas: {total}")
        parts.append("Problemas:")
        parts.append(issues_text)
        if examples_text:
            parts.append("Detalles por fila:" + examples_text)
        parts.append(f"Ejemplos generales: {samples_text}")
        parts.append("")

    parts.append("FORMATO DE RESPUESTA JSON:")
    parts.append("""{
  "recommendations": [
    {
      "column": "nombre_columna",
      "category": "MISSING",
      "count": 10,
      "affected_rows": [3, 7, 12, 15],
      "text": "Justificación técnica (1-2 oraciones) con referencia a filas especificas",
      "action": {
        "kind": "tipo_de_acción",
        "column": "nombre_columna",
        "method": "metodo",
        "reason": "Justificación de la acción"
      },
      "confidence": 0.85
    }
  ]
}""")

    parts.append("")
    parts.append("REGLAS:")
    parts.append("- Genera recomendaciónes para TODOS los problemas de TODAS las columnas")
    parts.append("- Cada recomendación DEBE incluir 'affected_rows' con los numeros de fila")
    parts.append("- En 'text', referencia las filas especificas (ej: 'Filas 3,7,12 tienen valores negativos')")
    parts.append("- Prioriza acciones que no pierdan datos")
    parts.append("- Si hay dudas, confidence < 0.5")

    return "\n".join(parts)


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
    - Si falla, crea un JSON básico con el texto original
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
            "text": "justificación",
            "action": {...},
            "confidence": 0.85
          }
        ]
      }

    MANEJO DE ERRORES:
    - Si el JSON es invalido, retorna el texto como recomendación
    - Si falta información, completa con valores por defecto
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
            # Si no tiene "recommendations", crear estructura básica
            data = {"recommendations": [data] if isinstance(data, dict) else []}

        # Validar cada recomendación
        valid_recommendations = []
        for rec in data.get("recommendations", []):
            if isinstance(rec, dict):
                # Asegurar que tenga los campos minimos
                valid_recommendations.append({
                    "category": rec.get("category", "UNKNOWN"),
                    "count": rec.get("count", 0),
                    "text": rec.get("text", "Sin justificación"),
                    "action": rec.get("action", {}),
                    "confidence": min(max(rec.get("confidence", 0.5), 0.0), 1.0)
                })

        return {"recommendations": valid_recommendations}

    except json.JSONDecodeError as e:
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


# ---------------------------------------------------------------------------
# FUNCIONES ASÍNCRONAS Y CHAT INTERACTIVO POR COLUMNA
# ---------------------------------------------------------------------------

async def get_ai_recommendations_async(
    diagnostic: dict[str, Any],
    sample_rows: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Versión asíncrona para respuesta ultrarrápida usando AsyncGroq."""
    client = init_async_groq_client()
    if not client:
        # Fallback a versión síncrona si no hay cliente async
        return get_ai_recommendations(diagnostic, sample_rows)

    system_prompt = build_system_prompt()
    columns = diagnostic.get("columns", [])
    columns_with_issues = [col for col in columns if col.get("issues")]

    if not columns_with_issues:
        return {
            "recommendations": [],
            "message": "No se encontraron problemas de calidad.",
            "status": "success"
        }

    user_prompt = _build_batch_prompt(columns_with_issues, sample_rows)

    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            response_format={"type": "json_object"}
        )

        response_text = response.choices[0].message.content
        parsed = json.loads(response_text)

        raw_recs = parsed.get("recommendations", [])
        if isinstance(parsed, dict) and not raw_recs and any(
            k in parsed for k in ("columns", "column")
        ):
            raw_recs = [parsed]

        grouped: dict[str, list[dict]] = {}
        for rec in raw_recs:
            if not isinstance(rec, dict):
                continue
            col_name = rec.get("column", "unknown")
            clean_rec = {
                "category": rec.get("category", "UNKNOWN"),
                "count": rec.get("count", 0),
                "text": rec.get("text", "Sin justificación"),
                "action": rec.get("action", {}),
                "confidence": min(max(rec.get("confidence", 0.5), 0.0), 1.0),
                "affected_rows": rec.get("affected_rows", []),
            }
            grouped.setdefault(col_name, []).append(clean_rec)

        all_recommendations = []
        for col_data in columns_with_issues:
            col_name = col_data.get("column", "")
            issues = col_data.get("issues", [])
            recs_for_col = grouped.get(col_name, [])

            if not recs_for_col:
                recs_for_col = [
                    {
                        "category": iss.get("category", iss.get("category_code", "UNKNOWN")),
                        "count": iss.get("count", 0),
                        "text": f"Problema {iss.get('category_code', iss.get('category', ''))}: "
                                f"{iss.get('count', 0)} ocurrencias. Requiere revisión manual.",
                        "action": {
                            "kind": "review_issue",
                            "column": col_name,
                            "reason": f"Problema {iss.get('category_code', '')} detectado por diagnóstico",
                        },
                        "confidence": 0.3,
                        "affected_rows": iss.get("affected_rows", []),
                    }
                    for iss in issues
                ]

            all_recommendations.append({
                "column": col_name,
                "inferred_domain": col_data.get("inferred_domain", ""),
                "issues_summary": f"{len(issues)} problema(s) detectado(s)",
                "recommendations": recs_for_col,
            })

        return {
            "recommendations": all_recommendations,
            "message": f"Procesadas {len(all_recommendations)} columnas con problemas",
            "status": "success",
        }
    except Exception as e:
        logger.error("Error en get_ai_recommendations_async: %s", e)
        return get_ai_recommendations(diagnostic, sample_rows)


async def get_column_depuration_recommendations(
    column_name: str,
    column_diagnostic: dict[str, Any],
    sample_rows: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Genera recomendaciónes de depuración enfocadas en una sola columna."""
    client = init_async_groq_client() or init_groq_client()
    if not client:
        return _build_fallback_recommendations(column_name, column_diagnostic)

    system_prompt = (
        "Eres el Copiloto de Calidad de Datos de AuditData AI. "
        "Genera recomendaciónes de depuración para UNA COLUMNA específica.\n"
        "REGLAS CRÍTICAS:\n"
        "1. Respetas la soberanía del analista — él decide finalmente.\n"
        "2. Español profesional.\n"
        "3. DUPLICADOS: Solo aplican a filas completas del dataset.\n"
        "4. El campo 'text' DEBE ser MÁXIMO 1 ORACIÓN CORTA (máx 80 caracteres). "
        "NO des explicaciones largas. Solo di qué acción aplicar y por qué en una frase.\n"
        "5. Cada recomendación DEBE tener un 'action' válido con 'kind' y 'column'.\n"
        "6. Genera UNA recomendación por cada categoría de error encontrada.\n"
        "7. El 'text' es para mostrar al analista como título rápido. "
        "La justificación completa va en el campo 'action.reason'.\n"
    )

    issues = column_diagnostic.get("issues", [])
    issues_text = ""
    for issue in issues:
        cat = issue.get("category_code", "UNKNOWN")
        count = issue.get("count", 0)
        pct = issue.get("percentage", 0)
        desc = issue.get("description", "")
        issues_text += f"  - {cat}: {count} ocurrencias ({pct:.1f}%). {desc}\n"
        for ex in issue.get("examples", [])[:3]:
            if "row" in ex:
                issues_text += f"    Fila {ex['row']}: valor='{ex.get('value', '')}'\n"
            elif "rows" in ex:
                issues_text += f"    Filas {ex['rows']}: coinciden al {ex.get('match', '?')}\n"

    samples = _get_sample_values(column_name, sample_rows) if column_name != "__dataset__" else []
    samples_str = ", ".join(samples[:8]) if samples else "No disponibles"
    domain = column_diagnostic.get("inferred_domain", "desconocido")
    total = column_diagnostic.get("total_rows", 0)

    user_prompt = (
        f"COLUMNA: {column_name}\n"
        f"Dominio: {domain} | Filas totales: {total}\n"
        f"PROBLEMAS DETECTADOS:\n{issues_text}"
        f"Valores de ejemplo: {samples_str}\n\n"
        f"Para CADA problema detectado, genera UNA recomendación con action válido.\n"
        f"IMPORTANTE: 'text' = máxima 1 oración corta (80 chars). "
        f"'action.reason' = justificación completa.\n"
        f"ACCIONES DISPONIBLES:\n"
        f"- fill_missing (method: mean/median/mode) → para MISSING\n"
        f"- standardize_text (method: trim/lowercase/title) → para TEXT_ERROR, CATEGORICAL\n"
        f"- change_type (value: number/text) → para TYPE_VALIDATION\n"
        f"- replace_value (method: valor_original, value: nuevo_valor) → para valores específicos\n"
        f"- drop_missing_rows → para filas con faltantes críticos\n"
        f"FORMATO JSON:\n"
        f'{{"recommendations": [{{\n'
        f'  "category": "MISSING",\n'
        f'  "count": 5,\n'
        f'  "affected_rows": [3,7],\n'
        f'  "text": "Imputar faltantes con mediana (5 celdas vacías)",\n'
        f'  "action": {{"kind": "fill_missing", "column": "{column_name}", "method": "median", "reason": "Justificación completa aquí"}},\n'
        f'  "confidence": 0.85\n'
        f'}}]}}'
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    try:
        if isinstance(client, AsyncGroq):
            res = await client.chat.completions.create(
                model=MODEL, messages=messages, max_tokens=2048, temperature=0.3
            )
        else:
            res = client.chat.completions.create(
                model=MODEL, messages=messages, max_tokens=2048, temperature=0.3
            )
        answer = res.choices[0].message.content
        parsed = _parse_ai_response(answer)
        recs = parsed.get("recommendations", []) if isinstance(parsed, dict) else []
        return {"recommendations": recs, "status": "success"}
    except Exception as e:
        logger.error("Error en get_column_depuration_recommendations: %s", e)
        return _build_fallback_recommendations(column_name, column_diagnostic)


CATEGORY_ACTION_MAP = {
    "MISSING": ("fill_missing", "mode"),
    "TEXT_ERROR": ("standardize_text", "trim"),
    "CATEGORICAL": ("standardize_text", "trim"),
    "TYPE_ERROR": ("change_type", "text"),
    "OUT_OF_RANGE": ("flag_outliers", "flag"),
    "NUMERIC_DOMAIN": ("flag_outliers", "flag"),
    "DATE_FORMAT": ("standardize_text", "trim"),
    "UNIT_ERROR": ("standardize_text", "trim"),
    "ENCODING": ("standardize_text", "trim"),
    "DUPLICATE": ("drop_duplicates", "first"),
}


def _build_fallback_recommendations(
    column_name: str,
    column_diagnostic: dict[str, Any]
) -> dict[str, Any]:
    """Genera recomendaciónes sin IA a partir del diagnóstico."""
    issues = column_diagnostic.get("issues", [])
    recs = []
    for issue in issues:
        cat = issue.get("category_code", issue.get("category", "UNKNOWN"))
        count = issue.get("count", 0)
        rows = issue.get("affected_rows", [])[:10]
        desc = issue.get("description", issue.get("text", ""))
        kind, method = CATEGORY_ACTION_MAP.get(cat, ("flag_outliers", "flag"))

        if kind == "fill_missing":
            text = f"Imputar {count} vacío(s) con {method}"
        elif kind == "standardize_text":
            text = f"Estandarizar {count} valor(es) de formato"
        elif kind == "replace_value":
            text = f"Reemplazar {count} valor(es) inconsistentes"
        elif kind == "flag_outliers":
            text = f"Revisar {count} outlier(s) detectado(s)"
        else:
            text = f"{cat}: {count} ocurrencia(s) detectada(s)"

        recs.append({
            "category": cat,
            "count": count,
            "text": text[:80],
            "action": {
                "kind": kind,
                "column": column_name,
                "method": method,
                "reason": desc or f"Detección automática: {cat}",
            },
            "confidence": 0.6,
            "affected_rows": rows,
        })

    return {"recommendations": recs, "status": "fallback"}


async def chat_with_column_advisor(
    column_name: str,
    user_query: str,
    column_diagnostic: dict[str, Any] | None = None,
    sample_rows: list[dict[str, Any]] | None = None,
    chat_history: list[dict[str, str]] | None = None
) -> dict[str, Any]:
    """Procesa preguntas de lenguaje natural en el Side Drawer para una columna o dataset."""
    client = init_async_groq_client() or init_groq_client()
    if not client:
        return {
            "response": "IA deshabilitada. Configura GROQ_API_KEY para conversar.",
            "status": "no_api_key"
        }

    system_prompt = (
        "Eres el Copiloto de Calidad de Datos de AuditData AI. "
        "Estás asesorando a un analista de datos sobre una columna o problemática específica de un dataset.\n"
        "REGLAS ÉTICAS Y DE COMUNICACIÓN:\n"
        "1. Responde de forma concisa, técnica y didáctica (máximo 2-3 párrafos corta duración).\n"
        "2. Respeta la soberanía del analista: él toma las decisiones finales.\n"
        "3. Idioma: Español profesional por defecto.\n"
        "4. Si te pregunta sobre duplicados ('__dataset__'), aclara que los duplicados aplican a filas completas del dataset, no a celdas aisladas."
    )

    issues_summary = ""
    if column_diagnostic:
        issues = column_diagnostic.get("issues", [])
        issues_summary = f"Diagnóstico de '{column_name}': {len(issues)} problema(s) detectado(s). " + \
            ", ".join([f"{i.get('category_code', 'ERROR')} ({i.get('count', 0)} filas)" for i in issues])

    samples = _get_sample_values(column_name, sample_rows) if column_name != "__dataset__" else []
    samples_str = f" Ejemplos de celdas: {', '.join(samples[:6])}" if samples else ""

    context_msg = (
        f"OBJETO/COLUMNA CONSULTADO: {column_name}\n"
        f"CONTEXTO TÉCNICO: {issues_summary}{samples_str}\n"
        f"Por favor responde como Copiloto orientando la mejor decisión técnica de depuración."
    )

    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    if chat_history:
        messages.extend(chat_history[-10:])
    messages.append({"role": "user", "content": f"{context_msg}\n\nPREGUNTA DEL ANALISTA: {user_query}"})

    try:
        if isinstance(client, AsyncGroq):
            res = await client.chat.completions.create(
                model=MODEL,
                messages=messages,
                max_tokens=1024,
                temperature=0.4
            )
        else:
            res = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                max_tokens=1024,
                temperature=0.4
            )
        answer = res.choices[0].message.content
        return {"response": answer, "status": "success"}
    except Exception as e:
        logger.error("Error en chat_with_column_advisor: %s", e)
        return {
            "response": f"Lo siento, ocurrió un error al consultar la IA: {e}",
            "status": "error"
        }

