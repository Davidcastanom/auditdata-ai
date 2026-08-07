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
# El tier gratuito de Groq limita llama-3.1-8b-instant a 6000 TPM (input + output).
# Las llamadas batch (recomendaciones/justificaciones) piden menos tokens de salida
# para que el request completo (prompt + salida) quepa en el limite.
BATCH_MAX_TOKENS = 2048
TEMPERATURE = 0.3

# CHAT-01: presupuesto de contexto del chat. El tier free de Groq limita
# llama-3.1-8b-instant a 6000 TPM (input + output). Con valores largos el prompt
# pedía 26K tokens y Groq respondia 413. Se poda y trunca para que el request
# quepa holgado en el limite.
CONTEXT_SAMPLE_ROWS = 15
CONTEXT_FREQ_ROWS = 15
CONTEXT_VALUE_LEN = 100


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
# JUSTIFICACIONES BATCH (reemplaza Gemini serial por Groq unico)
# ---------------------------------------------------------------------------

_JUSTIFICATION_BATCH_SYSTEM = (
    "Actua como un Auditor Senior de Calidad de Datos. "
    "Para cada accion de limpieza que se te presenta, redacta una "
    "justificacion tecnica formal y profesional de UNA sola oracion."
)


def get_justifications_batch(
    items: list[tuple[str, str, str]],
) -> list[str]:
    """Genera justificaciones profesionales en UNA sola llamada Groq.

    Parameters
    ----------
    items : list[tuple[column, action, reason]]
        Tuplas con los datos de cada accion a justificar.

    Returns
    -------
    list[str]
        Lista de justificaciones en el mismo orden que ``items``.
        Si no hay cliente Groq o hay error, retorna ``reason`` original.
    """
    fallback = [r for _, _, r in items]
    if not items:
        return []

    client = init_groq_client()
    if not client:
        return fallback

    lines = [
        f"{i + 1}. Columna: '{col}', Accion: '{act}', Razon original: '{reason}'"
        for i, (col, act, reason) in enumerate(items)
    ]
    user_prompt = (
        "Genera UNA justificacion tecnica por cada accion:\n\n"
        + "\n".join(lines)
        + "\n\n"
        "Responde con un array JSON de strings, uno por accion, en orden."
    )

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": _JUSTIFICATION_BATCH_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=BATCH_MAX_TOKENS,
            temperature=TEMPERATURE,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        import json as _json
        parsed = _json.loads(raw)

        if isinstance(parsed, dict):
            for key in ("justificaciones", "justifications", "results"):
                if key in parsed and isinstance(parsed[key], list):
                    parsed = parsed[key]
                    break
            else:
                parsed = list(parsed.values())
                if parsed and isinstance(parsed[0], dict):
                    parsed = [v.get("justificacion", v.get("justification", str(v))) for v in parsed]

        if isinstance(parsed, list) and len(parsed) == len(items):
            return [str(j).strip() or fallback[i] for i, j in enumerate(parsed)]

        logger.warning("Groq batch justificaciones: longitud inesperada (%d vs %d)", len(parsed), len(items))
        return fallback
    except Exception as e:
        logger.warning("Groq batch justificaciones error: %s", e)
        return fallback


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
            max_tokens=BATCH_MAX_TOKENS,
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
                        "text": f"Problema {iss.get('category_code', iss.get('category', ''))} "
                                f"[{iss.get('signal', 'A_REVISAR')}]: "
                                f"{iss.get('count', 0)} ocurrencias. "
                                f"Filas afectadas: {iss.get('affected_rows', [])[:10]}. "
                                f"Requiere revision manual.",
                        "action": {
                            "kind": "review_issue",
                            "column": col_name,
                            "reason": f"Problema {iss.get('category_code', '')} detectado por diagnóstico",
                        },
                        "confidence": iss.get("confidence", 80) / 100,
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
            f"  - {iss.get('category_code', iss.get('category', ''))} "
            f"[{iss.get('signal', 'A_REVISAR')}]: "
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
                for e in exs[:2]:
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
                examples_text += f"\n  [{cat}]: Filas afectadas: {rows[:4]}"

        samples_text = ", ".join(sample_values[:4]) if sample_values else "No disponibles"

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
            max_tokens=BATCH_MAX_TOKENS,
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


def _truncate(value: Any, max_len: int = CONTEXT_VALUE_LEN) -> str:
    """Recorta un valor para el contexto del chat (CHAT-01): evita que valores
    largos inflen el prompt y disparen el 413 de Groq (limite 6000 TPM)."""
    text = str(value)
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _build_chat_context_message(
    column_name: str,
    column_diagnostic: dict[str, Any] | None,
    context: dict[str, Any] | None,
    total_rows: int = 0,
    total_columns: int = 0,
    headers: list[str] | None = None,
    detected_type: str = "unknown",
    inferred_domain: str = "",
    full: bool = True,
) -> str:
    """Construye el bloque de contexto del chat con indicadores, frecuencias,
    estadisticas y datos ordenados. Nunca incluye porcentajes (evita falsos positivos)."""
    parts = []

    domain_str = f", Dominio: {inferred_domain}" if inferred_domain else ""
    parts.append(
        f"OBJETO/COLUMNA CONSULTADO: {column_name}"
        f" (Tipo: {detected_type}{domain_str})"
    )
    if total_rows:
        parts.append(
            f"DATASET: {total_rows} filas x {total_columns} columnas"
        )
    if headers:
        parts.append(f"COLUMNAS: {', '.join(headers)}")

    if context:
        parts.append(
            "INDICADORES:\n"
            f"- Valores unicos: {context.get('unique_count', 0)}\n"
            f"- Valores vacios: {context.get('missing_count', 0)}"
        )

        dist = context.get("value_distribution") or []
        if dist:
            top_n = dist[:CONTEXT_FREQ_ROWS]
            lines = "\n".join(
                f'- "{_truncate(d.get("value", ""))}": {d.get("count", 0)} ocurrencia(s)'
                for d in top_n
            )
            parts.append(f"TABLA DE FRECUENCIAS (top {len(top_n)}):\n{lines}")

        stats = context.get("stats_summary") or {}
        if stats:
            parts.append(
                "RESUMEN ESTADISTICO (numero):\n"
                f"- Min: {stats.get('min')}\n"
                f"- Max: {stats.get('max')}\n"
                f"- Media: {stats.get('mean')}\n"
                f"- Mediana: {stats.get('median')}\n"
                f"- Desv. est.: {stats.get('stdev')}\n"
                f"- Q1: {stats.get('q1')}\n"
                f"- Q3: {stats.get('q3')}\n"
                f"- IQR: {stats.get('iqr')}\n"
                f"- Outliers bajos: {stats.get('outliers_bajos', 0)}\n"
                f"- Outliers altos: {stats.get('outliers_altos', 0)}"
            )

    issues_summary = ""
    if column_diagnostic:
        issues = column_diagnostic.get("issues", [])
        issues_summary = (
            f"Diagnóstico de '{column_name}': {len(issues)} problema(s) detectado(s). "
            + ", ".join(
                [f"{i.get('category_code', 'ERROR')} ({i.get('count', 0)} filas)" for i in issues]
            )
        )
    parts.append(f"DIAGNOSTICO TECNICO: {issues_summary}")

    if context and full:
        sorted_data = context.get("sorted_data") or []
        if sorted_data:
            sample = sorted_data[:CONTEXT_SAMPLE_ROWS]
            sample_str = "\n".join([f"Fila {r}={_truncate(v)}" for r, v in sample])
            parts.append(f"DATOS ORDENADOS (primeras {len(sample)} filas de {len(sorted_data)}):\n{sample_str}")

    return "\n\n".join(parts)


async def chat_with_column_advisor(
    column_name: str,
    user_query: str,
    column_diagnostic: dict[str, Any] | None = None,
    chat_history: list[dict[str, str]] | None = None,
    context: dict[str, Any] | None = None,
    total_rows: int = 0,
    total_columns: int = 0,
    headers: list[str] | None = None,
    detected_type: str = "unknown",
    inferred_domain: str = "",
) -> dict[str, Any]:
    """Procesa preguntas de lenguaje natural en el Side Drawer para una columna o dataset."""
    client = init_async_groq_client() or init_groq_client()
    if not client:
        return {
            "response": "IA deshabilitada. Configura GROQ_API_KEY para conversar.",
            "status": "no_api_key"
        }

    is_first_message = not chat_history or len(chat_history) == 0
    verbosity_rule = (
        "PRIMER MENSAJE: Puedes dar una visión general estructurada con viñetas, "
        "pero sé directo y profesional.\n"
        "MENSAJES SIGUIENTES: Sé aún más conciso. Responde en 1-2 líneas o 3-4 viñetas máximo. "
        "Ahorra tokens. Ve al grano."
    ) if is_first_message else (
        "RESPUESTA MUY CONCISA: Máximo 3 viñetas. Una línea por idea. "
        "Sé directo, formal y técnico. Ahorra tokens al máximo. "
        "No repitas información del historial."
    )

    system_prompt = (
        "Eres el Copiloto de Calidad de Datos de AuditData AI. "
        "Asesoras a un analista sobre una columna específica de un dataset.\n"
        "REGLAS:\n"
        "1. Idioma: SIEMPRE español profesional, formal y directo.\n"
        "2. Formato: Estructura tu respuesta como LISTA con viñetas (- item). "
        "Cada viñeta = una idea completa. No uses párrafos largos.\n"
        "3. Usa **negritas** para conceptos clave y `código` para valores/filas.\n"
        "4. Sé soberano: el analista decide. No ordenes, sugiere.\n"
        "5. Duplicados: solo aplican a filas completas del dataset, no a celdas.\n"
        "6. Responder SIEMPRE con base en los datos del contexto. Si una métrica no está "
        "en el contexto, dilo explícitamente en vez de inventarla.\n"
        f"7. {verbosity_rule}"
    )

    context_msg = _build_chat_context_message(
        column_name=column_name,
        column_diagnostic=column_diagnostic,
        context=context,
        total_rows=total_rows,
        total_columns=total_columns,
        headers=headers,
        detected_type=detected_type,
        inferred_domain=inferred_domain,
        full=is_first_message,
    )
    context_msg += f"\n\nPREGUNTA DEL ANALISTA: {user_query}"

    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    if chat_history:
        messages.extend(chat_history[-10:])
    messages.append({"role": "user", "content": context_msg})

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


# ---------------------------------------------------------------------------
# ANALISIS PROFUNDO DE COLUMNA (Recomendacion de Copiloto)
# ---------------------------------------------------------------------------

DEEP_MODEL = "llama-3.1-8b-instant"
DEEP_MAX_TOKENS = 1536
DEEP_TEMPERATURE = 0.2


def _get_deep_client() -> Groq | AsyncGroq | None:
    """Inicializa cliente Groq con la API key de recomendaciones (si existe) o la principal."""
    api_key = os.getenv("Recomendaciones_de_copiloto") or os.getenv("RECOMENDACIONES_GROQ_KEY") or os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.warning("Sin API key para análisis profundo.")
        return None
    try:
        if AsyncGroq is not None:
            return AsyncGroq(api_key=api_key)
        return Groq(api_key=api_key)
    except Exception as e:
        logger.error("Error al inicializar cliente deep: %s", e)
        return None


def compute_column_context(
    column_data: list[tuple[int, str]],
    detected_type: str = "unknown",
) -> dict[str, Any]:
    """
    Construye un paquete de contexto completo de una columna para la IA.

    Incluye:
    - unique_count: valores unicos (SIN porcentajes para evitar falsos positivos)
    - missing_count: cantidad de vacios
    - value_distribution: tabla de frecuencias (top 30, solo conteos)
    - stats_summary: resumen estadistico numerico (min, max, mean, median, IQR)
    - sorted_data: datos ordenados (alfabetico o numerico segun tipo)

    column_data: lista de (numero_fila_en_archivo, valor)
    """
    import statistics
    from collections import Counter

    values = [v for _, v in column_data]
    present = [v for v in values if v and v.strip()]
    missing_count = len(values) - len(present)
    unique_count = len(set(present))

    freq = Counter(present)
    value_distribution = [
        {"value": v, "count": c}
        for v, c in freq.most_common(30)
    ]

    stats_summary = {}
    if detected_type == "number":
        numeric_vals = []
        for v in present:
            try:
                numeric_vals.append(float(v.replace(",", ".")))
            except (ValueError, AttributeError):
                pass
        if numeric_vals:
            numeric_vals.sort()
            n = len(numeric_vals)
            q1 = numeric_vals[n // 4]
            q3 = numeric_vals[3 * n // 4]
            iqr = q3 - q1
            stats_summary = {
                "min": numeric_vals[0],
                "max": numeric_vals[-1],
                "mean": round(statistics.mean(numeric_vals), 4),
                "median": round(statistics.median(numeric_vals), 4),
                "stdev": round(statistics.stdev(numeric_vals), 4) if n > 1 else 0,
                "q1": q1,
                "q3": q3,
                "iqr": iqr,
                "outliers_bajos": sum(1 for v in numeric_vals if v < q1 - 1.5 * iqr),
                "outliers_altos": sum(1 for v in numeric_vals if v > q3 + 1.5 * iqr),
            }

    if detected_type == "number":
        def _num_sort_key(item):
            try:
                return (0, float(item[1].replace(",", ".")))
            except (ValueError, AttributeError):
                return (1, str(item[1]).lower())
        sorted_data = sorted(column_data, key=_num_sort_key)
    else:
        sorted_data = sorted(column_data, key=lambda x: (str(x[1]).lower(), x[0]))

    return {
        "unique_count": unique_count,
        "missing_count": missing_count,
        "value_distribution": value_distribution,
        "stats_summary": stats_summary,
        "sorted_data": sorted_data,
    }


async def analyze_column_deep(
    column_name: str,
    column_data: list[tuple[int, str]],
    total_rows: int = 0,
    total_columns: int = 0,
    headers: list[str] | None = None,
    detected_type: str = "unknown",
    inferred_domain: str = "",
    unique_count: int = 0,
    missing_count: int = 0,
    value_distribution: list[dict] | None = None,
    stats_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Analiza una columna como experto senior y devuelve hallazgos + recomendaciones.
    Recibe contexto completo: indicadores, frecuencias, estadisticas y headers.
    column_data: lista de (numero_fila_en_archivo, valor)
    """
    client = _get_deep_client()
    if not client:
        return {
            "analysis": "IA deshabilitada. Configura RECOMENDACIONES_GROQ_KEY o GROQ_API_KEY.",
            "status": "no_api_key",
        }

    n_total = total_rows or len(column_data)

    # --- Sort data for better pattern detection ---
    if detected_type == "number":
        def _num_sort_key(item):
            try:
                return (0, float(item[1].replace(",", ".")))
            except (ValueError, AttributeError):
                return (1, str(item[1]).lower())
        sorted_data = sorted(column_data, key=_num_sort_key)
    else:
        sorted_data = sorted(column_data, key=lambda x: (str(x[1]).lower(), x[0]))

    # Sample: take up to 200 rows from sorted data
    sample_size = min(200, len(sorted_data))
    sample_rows = sorted_data[:sample_size]
    sample_str = "; ".join([f"Fila {r}={v}" for r, v in sample_rows])

    # --- Build dataset context ---
    headers_str = ", ".join(headers) if headers else ""
    dataset_context = f"Dataset: {n_total} filas x {total_columns} columnas\n"
    if headers_str:
        dataset_context += f"Columnas del dataset: {headers_str}\n"

    # --- Build indicators section (NO percentages) ---
    indicators = (
        f"- **Unicos**: {unique_count}\n"
        f"- **Vacios**: {missing_count}\n"
    )

    # --- Build frequency table (top 20, counts only) ---
    freq_str = ""
    if value_distribution:
        freq_lines = [
            f"  {i+1}. \"{d['value']}\": {d['count']} ocurrencias"
            for i, d in enumerate(value_distribution[:20])
        ]
        freq_str = "**Tabla de Frecuencias (top 20):**\n" + "\n".join(freq_lines) + "\n"

    # --- Build statistical summary (numeric only) ---
    stats_str = ""
    if stats_summary and detected_type == "number":
        stats_lines = [
            f"- **{k.replace('_', ' ').capitalize()}**: {v}"
            for k, v in stats_summary.items()
        ]
        stats_str = "**Resumen Estadistico:**\n" + "\n".join(stats_lines) + "\n"

    # --- Build prompts ---
    system_prompt = (
        "Eres un analista senior de calidad de datos con 15 anios de experiencia. "
        "Tu especialidad es detectar anomalias, patrones sucios e inconsistencias en columnas de datasets. "
        "Responde UNICAMENTE en el formato de lista numerada que se indica. "
        "Se directo, tecnico y profesional. Idioma: espanol."
    )

    user_prompt = (
        f"COLUMNA: '{column_name}' (Tipo: {detected_type}, Dominio: {inferred_domain or 'general'})\n"
        f"{dataset_context}\n"
        f"INDICADORES:\n{indicators}\n"
        f"{freq_str}\n"
        f"{stats_str}\n"
        f"Datos ordenados (fila=valor, primeros {len(sample_rows)} de {n_total}):\n{sample_str}\n\n"
        "INSTRUCCIONES:\n"
        "- Identifica SOLO anomalias reales (no describas datos normales)\n"
        "- Si NO hay anomalias responde exactamente: No hay hallazgos significativos.\n"
        "- Por cada hallazgo incluye: numero(s) de FILA exacto(s) y el VALOR de ejemplo\n"
        "- Clasifica cada hallazgo por tipo de error\n"
        "- Da una recomendacion ACCIONABLE y CONCRETA\n"
        "- Sin introduccion, sin despedida, sin texto adicional\n\n"
        "FORMATO EXACTO:\n"
        "1. **NOMBRE_HALLAZGO** (Filas 5, 12, 18)\n"
        "   Valor ejemplo: \"juan.perez@\"\n"
        "   -> **Recomendacion**: accion especifica.\n\n"
        "2. **SIGUIENTE_HALLAZGO** (Filas 3, 7)\n"
        "   Valor ejemplo: \"NA\"\n"
        "   -> **Recomendacion**: accion especifica.\n"
        "---\n"
        "Si no hay errores:\n"
        "No hay hallazgos significativos.\n"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        if isinstance(client, AsyncGroq):
            res = await client.chat.completions.create(
                model=DEEP_MODEL, messages=messages,
                max_tokens=DEEP_MAX_TOKENS, temperature=DEEP_TEMPERATURE,
            )
        else:
            res = client.chat.completions.create(
                model=DEEP_MODEL, messages=messages,
                max_tokens=DEEP_MAX_TOKENS, temperature=DEEP_TEMPERATURE,
            )
        answer = res.choices[0].message.content
        return {"analysis": answer, "status": "success"}
    except Exception as e:
        logger.error("Error en analyze_column_deep: %s", e)
        return {
            "analysis": f"Error al analizar columna: {e}",
            "status": "error",
        }
