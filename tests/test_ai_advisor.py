"""Tests rigurosos para el advisor de IA.

Cubren:
- compute_column_context: indicadores, frecuencias, estadisticas y ordenamiento
  (SIN porcentajes para evitar falsos positivos)
- _build_chat_context_message: construccion del contexto del chat
- chat_with_column_advisor: ensamblado de mensajes y manejo de errores
- /api/ai/chat-column: integracion del contexto calculado en el endpoint
"""

import base64
import copy
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from backend.app.main import app
from data_engine.ai_advisor import (
    _build_batch_prompt,
    _build_chat_context_message,
    _detect_intent,
    chat_with_column_advisor,
    compute_column_context,
    get_ai_recommendations,
    get_justifications_batch,
)

client = TestClient(app)

_TEST_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SAMPLE_CSV = (
    "id,nombre,ciudad,edad,horas_sueno,litros_agua,completo_reto\n"
    "1,Ana,Bogota,28,7,2.1,si\n"
    "2,Juan,bogota,31,6,1.8,no\n"
    "1,Ana,Bogota,28,7,2.1,si\n"
    "4,Maria,Medellin,,8,2.4,si\n"
    "5,Luis,Medellin,450,2,,no\n"
)


def _encode(payload: str) -> str:
    return base64.b64encode(payload.encode("utf-8")).decode("ascii")


# ---------------------------------------------------------------------------
# Fakes para Groq
# ---------------------------------------------------------------------------

class _FakeMessage:
    def __init__(self, content: str):
        self.content = content


class _FakeResponse:
    def __init__(self, content: str):
        self.choices = [SimpleNamespace(message=_FakeMessage(content))]


class _FakeCompletions:
    def __init__(self, response_text: str = "respuesta de prueba"):
        self._response_text = response_text
        self.last_kwargs: dict | None = None

    def create(self, *args, **kwargs):
        self.last_kwargs = kwargs
        return _FakeResponse(self._response_text)


class _FakeAsyncCompletions(_FakeCompletions):
    async def create(self, *args, **kwargs):
        self.last_kwargs = kwargs
        return _FakeResponse(self._response_text)


class _FlakyCompletions(_FakeCompletions):
    """Falla con status_code rate-limit N veces y luego responde."""

    def __init__(self, fail_codes: list[int], response_text: str = "respuesta tras retry"):
        super().__init__(response_text)
        self.fail_codes = list(fail_codes)
        self.calls: list[dict] = []

    def create(self, *args, **kwargs):
        self.calls.append(copy.deepcopy(kwargs))
        self.last_kwargs = kwargs
        if self.fail_codes:
            code = self.fail_codes.pop(0)
            err = RuntimeError(f"Error code: {code} - rate_limit_exceeded")
            err.status_code = code
            raise err
        return _FakeResponse(self._response_text)


class _FakeClient:
    def __init__(self, response_text: str = "respuesta de prueba", async_mode: bool = False):
        completions = (
            _FakeAsyncCompletions(response_text)
            if async_mode else _FakeCompletions(response_text)
        )
        self.chat = SimpleNamespace(completions=completions)


class _FakeAsyncGroqClientClass:
    pass


# ---------------------------------------------------------------------------
# compute_column_context
# ---------------------------------------------------------------------------

class TestComputeColumnContext(unittest.TestCase):
    def test_numeric_indicators(self):
        data = [(2, "28"), (3, "31"), (4, "28"), (5, ""), (6, "450")]
        ctx = compute_column_context(data, "number")
        self.assertEqual(ctx["unique_count"], 3)
        self.assertEqual(ctx["missing_count"], 1)

    def test_numeric_stats(self):
        data = [(2, "28"), (3, "31"), (4, "28"), (5, ""), (6, "450")]
        ctx = compute_column_context(data, "number")
        stats = ctx["stats_summary"]
        self.assertEqual(stats["min"], 28.0)
        self.assertEqual(stats["max"], 450.0)
        self.assertEqual(stats["mean"], 134.25)
        self.assertEqual(stats["median"], 29.5)
        self.assertIn("stdev", stats)
        self.assertIn("q1", stats)
        self.assertIn("q3", stats)
        self.assertIn("iqr", stats)
        self.assertIn("outliers_bajos", stats)
        self.assertIn("outliers_altos", stats)

    def test_numeric_sorted_ascending(self):
        data = [(2, "450"), (3, "28"), (4, "31"), (5, "28")]
        ctx = compute_column_context(data, "number")
        values = [v for _, v in ctx["sorted_data"]]
        self.assertEqual(values, ["28", "28", "31", "450"])

    def test_numeric_row_numbers_preserved(self):
        data = [(10, "28"), (20, "450"), (30, "31")]
        ctx = compute_column_context(data, "number")
        self.assertEqual(ctx["sorted_data"], [(10, "28"), (30, "31"), (20, "450")])

    def test_comma_decimal_parsed_as_number(self):
        data = [(2, "1,5"), (3, "2,5"), (4, "1,5")]
        ctx = compute_column_context(data, "number")
        self.assertEqual(ctx["stats_summary"]["min"], 1.5)
        self.assertEqual(ctx["stats_summary"]["max"], 2.5)
        self.assertEqual(ctx["stats_summary"]["median"], 1.5)

    def test_text_sorted_case_insensitive(self):
        data = [(2, "Bogota"), (3, "ana"), (4, "Ana"), (5, "bogota")]
        ctx = compute_column_context(data, "text")
        values = [v for _, v in ctx["sorted_data"]]
        self.assertEqual(values, ["ana", "Ana", "Bogota", "bogota"])

    def test_text_sort_tiebreak_by_row_number(self):
        data = [(5, "ana"), (3, "ana"), (4, "Ana")]
        ctx = compute_column_context(data, "text")
        rows = [r for r, _ in ctx["sorted_data"]]
        self.assertEqual(rows, [3, 4, 5])

    def test_value_distribution_counts(self):
        data = [(2, "si"), (3, "no"), (4, "si"), (5, "si")]
        ctx = compute_column_context(data, "text")
        dist = {d["value"]: d["count"] for d in ctx["value_distribution"]}
        self.assertEqual(dist["si"], 3)
        self.assertEqual(dist["no"], 1)

    def test_value_distribution_capped_at_30(self):
        data = [(i, f"v{i}") for i in range(100)]
        ctx = compute_column_context(data, "text")
        self.assertLessEqual(len(ctx["value_distribution"]), 30)

    def test_missing_excluded_from_unique(self):
        data = [(2, ""), (3, "x"), (4, ""), (5, "x"), (6, " ")]
        ctx = compute_column_context(data, "text")
        self.assertEqual(ctx["unique_count"], 1)
        self.assertEqual(ctx["missing_count"], 3)

    def test_empty_column(self):
        data = [(2, ""), (3, ""), (4, "")]
        ctx = compute_column_context(data, "number")
        self.assertEqual(ctx["unique_count"], 0)
        self.assertEqual(ctx["missing_count"], 3)
        self.assertEqual(ctx["value_distribution"], [])
        self.assertEqual(ctx["stats_summary"], {})

    def test_no_percentages_anywhere(self):
        data = [(2, "28"), (3, "31"), (4, "28"), (5, ""), (6, "450")]
        ctx = compute_column_context(data, "number")
        blob = str(ctx)
        self.assertNotIn("%", blob, "No deben incluirse porcentajes (causan falsos positivos)")

    def test_mixed_text_numeric_keeps_non_numeric_last(self):
        data = [(2, "abc"), (3, "30"), (4, "10"), (5, "xyz")]
        ctx = compute_column_context(data, "number")
        values = [v for _, v in ctx["sorted_data"]]
        self.assertEqual(values, ["10", "30", "abc", "xyz"])

    def test_non_numeric_type_leaves_stats_empty(self):
        data = [(2, "28"), (3, "31")]
        ctx = compute_column_context(data, "text")
        self.assertEqual(ctx["stats_summary"], {})


# ---------------------------------------------------------------------------
# _build_chat_context_message
# ---------------------------------------------------------------------------

class TestBuildChatContextMessage(unittest.TestCase):
    def _context(self, **overrides):
        ctx = {
            "unique_count": 3,
            "missing_count": 1,
            "value_distribution": [
                {"value": "28", "count": 2},
                {"value": "31", "count": 1},
                {"value": "450", "count": 1},
            ],
            "stats_summary": {
                "min": 28.0,
                "max": 450.0,
                "mean": 134.25,
                "median": 29.5,
                "stdev": 243.5,
                "q1": 28.0,
                "q3": 450.0,
                "iqr": 422.0,
                "outliers_bajos": 0,
                "outliers_altos": 0,
            },
            "sorted_data": [(2, "28"), (4, "28"), (3, "31"), (6, "450")],
        }
        ctx.update(overrides)
        return ctx

    def test_first_message_includes_sorted_data(self):
        msg = _build_chat_context_message(
            "edad", None, self._context(),
            total_rows=5, total_columns=7,
            headers=["id", "nombre", "edad"],
            detected_type="number", inferred_domain="edad en anios",
            full=True,
        )
        self.assertIn("DATOS ORDENADOS", msg)
        self.assertIn("Fila 2=28", msg)

    def test_followup_message_omits_sorted_data(self):
        msg = _build_chat_context_message(
            "edad", None, self._context(),
            total_rows=5, total_columns=7,
            detected_type="number", full=False,
        )
        self.assertNotIn("DATOS ORDENADOS", msg)
        self.assertIn("INDICADORES", msg)

    def test_includes_indicators(self):
        msg = _build_chat_context_message(
            "edad", None, self._context(),
            total_rows=5, total_columns=7, detected_type="number",
        )
        self.assertIn("Valores unicos: 3", msg)
        self.assertIn("Valores vacios: 1", msg)

    def test_includes_dataset_context(self):
        msg = _build_chat_context_message(
            "edad", None, self._context(),
            total_rows=5, total_columns=7,
            headers=["id", "nombre", "edad"],
            detected_type="number",
        )
        self.assertIn("5 filas x 7 columnas", msg)
        self.assertIn("id, nombre, edad", msg)

    def test_includes_frequencies_and_stats(self):
        msg = _build_chat_context_message(
            "edad", None, self._context(),
            total_rows=5, total_columns=7, detected_type="number",
        )
        self.assertIn('"28": 2 ocurrencia(s)', msg)
        self.assertIn("Media: 134.25", msg)
        self.assertIn("Outliers bajos: 0", msg)

    def test_no_percentages(self):
        msg = _build_chat_context_message(
            "edad", None, self._context(),
            total_rows=5, total_columns=7, detected_type="number",
        )
        self.assertNotIn("%", msg)

    def test_includes_diagnostic_issues(self):
        diag = {
            "issues": [
                {"category_code": "MISSING_VALUES", "count": 1},
                {"category_code": "OUTLIER", "count": 1},
            ]
        }
        msg = _build_chat_context_message("edad", diag, None, detected_type="number")
        self.assertIn("2 problema(s) detectado(s)", msg)
        self.assertIn("MISSING_VALUES (1 filas)", msg)
        self.assertIn("OUTLIER (1 filas)", msg)

    def test_includes_type_and_domain(self):
        msg = _build_chat_context_message(
            "edad", None, None,
            detected_type="number", inferred_domain="edad en anios",
        )
        self.assertIn("Tipo: number", msg)
        self.assertIn("Dominio: edad en anios", msg)

    def test_empty_context_is_graceful(self):
        msg = _build_chat_context_message("edad", None, {}, detected_type="unknown")
        self.assertIn("OBJETO/COLUMNA CONSULTADO: edad", msg)
        self.assertIn("DIAGNOSTICO TECNICO:", msg)

    def test_dataset_mode(self):
        msg = _build_chat_context_message(
            "__dataset__", None, None,
            total_rows=5, total_columns=7,
            detected_type="unknown",
        )
        self.assertIn("__dataset__", msg)
        self.assertIn("5 filas x 7 columnas", msg)

    def test_includes_other_columns_transversal_context(self):
        msg = _build_chat_context_message(
            "edad", None, self._context(),
            total_rows=5, total_columns=7, detected_type="number",
            other_columns=[
                {"name": "nombre", "detected_type": "text", "total_categories": 4, "issue_count": 2},
                {"name": "ingreso", "detected_type": "number", "total_categories": None, "issue_count": 0},
                {"name": "nota" * 30, "detected_type": "text"},
            ],
        )
        self.assertIn("OTRAS COLUMNAS (contexto del dataset)", msg)
        self.assertIn("- nombre (text) (4 categorias, 2 problemas)", msg)
        self.assertIn("- ingreso (number) (0 problemas)", msg)


class TestDetectIntent(unittest.TestCase):
    def test_values_keyword(self):
        self.assertIn("VALORES", _detect_intent("¿Cuál es el valor más frecuente?"))

    def test_duplicates_keyword(self):
        self.assertIn("DUPLICADOS", _detect_intent("¿hay filas duplicadas?"))

    def test_cleaning_keyword(self):
        self.assertIn("LIMPIEZA", _detect_intent("¿cómo limpio los vacíos?"))

    def test_stats_keyword(self):
        self.assertIn("ESTADISTICAS", _detect_intent("¿cuál es la media de la columna?"))

    def test_domain_keyword(self):
        self.assertIn("SIGNIFICADO", _detect_intent("¿qué significa esta columna?"))

    def test_no_match_returns_empty(self):
        self.assertEqual(_detect_intent("hola"), "")

    def test_long_values_are_truncated_in_sorted_data(self):
        """CHAT-01: valores de 2000 chars no deben inflar el prompt (413 de Groq)."""
        long_vals = [(i, "x" * 2000) for i in range(50)]
        ctx = {
            "unique_count": 1,
            "missing_count": 0,
            "value_distribution": [{"value": "x" * 2000, "count": 50}],
            "stats_summary": {},
            "sorted_data": long_vals,
        }
        msg = _build_chat_context_message("nota", None, ctx, full=True)
        self.assertIn("DATOS ORDENADOS", msg)
        for line in msg.splitlines():
            if "Fila " in line:
                self.assertLess(len(line), 200, f"Valor no truncado en: {line[:60]}...")

    def test_sorted_data_limited_to_constant(self):
        """CHAT-01: sorted_data[:100] -> limite configurable CONTEXT_SAMPLE_ROWS."""
        many = [(i, f"v{i}") for i in range(300)]
        ctx = {
            "unique_count": 300,
            "missing_count": 0,
            "value_distribution": [{"value": "v0", "count": 1}],
            "stats_summary": {},
            "sorted_data": many,
        }
        msg = _build_chat_context_message("col", None, ctx, full=True)
        lines = [l for l in msg.splitlines() if l.startswith("Fila ")]
        self.assertLessEqual(len(lines), 20, "Demasiadas filas en sorted_data")


# ---------------------------------------------------------------------------
# chat_with_column_advisor
# ---------------------------------------------------------------------------

class TestChatWithColumnAdvisor(unittest.IsolatedAsyncioTestCase):
    async def test_no_api_key(self):
        with patch("data_engine.ai_advisor.init_async_groq_client", return_value=None), \
             patch("data_engine.ai_advisor.init_groq_client", return_value=None):
            result = await chat_with_column_advisor("edad", "¿Cómo trato los vacíos?")
        self.assertEqual(result["status"], "no_api_key")

    async def test_success_sync_path(self):
        fake = _FakeClient()
        with patch("data_engine.ai_advisor.init_async_groq_client", return_value=None), \
             patch("data_engine.ai_advisor.init_groq_client", return_value=fake):
            result = await chat_with_column_advisor(
                "edad", "¿Cómo trato los vacíos?",
                context=compute_column_context([(2, "28")], "number"),
            )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["response"], "respuesta de prueba")

    async def test_first_message_has_full_context(self):
        fake = _FakeClient()
        ctx = compute_column_context([(2, "28"), (3, "31"), (4, "28")], "number")
        with patch("data_engine.ai_advisor.init_async_groq_client", return_value=None), \
             patch("data_engine.ai_advisor.init_groq_client", return_value=fake):
            await chat_with_column_advisor(
                "edad", "¿Qué ves?", context=ctx,
                total_rows=3, total_columns=7,
                headers=["id", "edad"], detected_type="number",
            )
        messages = fake.chat.completions.last_kwargs["messages"]
        user_msg = messages[-1]["content"]
        self.assertIn("DATOS ORDENADOS", user_msg)
        self.assertIn("INDICADORES", user_msg)
        self.assertIn("PREGUNTA DEL ANALISTA: ¿Qué ves?", user_msg)

    async def test_followup_message_keeps_full_context(self):
        """CHAT-04: el contexto base es identico en todos los turnos (estable)."""
        fake = _FakeClient()
        ctx = compute_column_context([(2, "28"), (3, "31"), (4, "28")], "number")
        history = [
            {"role": "user", "content": "¿Qué ves?"},
            {"role": "assistant", "content": "Respuesta anterior"},
        ]
        with patch("data_engine.ai_advisor.init_async_groq_client", return_value=None), \
             patch("data_engine.ai_advisor.init_groq_client", return_value=fake):
            await chat_with_column_advisor(
                "edad", "¿Y los nulos?", context=ctx,
                total_rows=3, total_columns=7,
                detected_type="number", chat_history=history,
            )
        messages = fake.chat.completions.last_kwargs["messages"]
        self.assertEqual(len(messages), 4)  # system + 2 historial + 1 usuario
        user_msg = messages[-1]["content"]
        self.assertIn("DATOS ORDENADOS", user_msg)
        self.assertIn("Valores unicos", user_msg)

    async def test_async_path_used_when_async_client(self):
        fake = _FakeClient(async_mode=True)
        fake.__class__ = _FakeAsyncGroqClientClass
        with patch("data_engine.ai_advisor.init_async_groq_client", return_value=fake), \
             patch("data_engine.ai_advisor.AsyncGroq", _FakeAsyncGroqClientClass):
            result = await chat_with_column_advisor(
                "edad", "Hola", context={}, total_rows=0,
            )
        self.assertEqual(result["status"], "success")
        self.assertEqual(fake.chat.completions.last_kwargs["model"], "llama-3.1-8b-instant")

    async def test_exception_returns_error(self):
        class _ExplodingClient:
            def __init__(self):
                self.chat = SimpleNamespace(
                    completions=SimpleNamespace(create=self._boom)
                )

            def _boom(self, *args, **kwargs):
                raise RuntimeError("exploto")

        with patch("data_engine.ai_advisor.init_async_groq_client", return_value=None), \
             patch("data_engine.ai_advisor.init_groq_client", return_value=_ExplodingClient()):
            result = await chat_with_column_advisor("edad", "Hola")
        self.assertEqual(result["status"], "error")
        self.assertIn("exploto", result["response"])

    async def test_system_prompt_forbids_inventing_metrics(self):
        fake = _FakeClient()
        with patch("data_engine.ai_advisor.init_async_groq_client", return_value=None), \
             patch("data_engine.ai_advisor.init_groq_client", return_value=fake):
            await chat_with_column_advisor("edad", "Hola")
        messages = fake.chat.completions.last_kwargs["messages"]
        system_prompt = messages[0]["content"]
        self.assertIn("base en los datos del contexto", system_prompt)

    async def test_intent_instruction_appended_to_system_prompt(self):
        fake = _FakeClient()
        with patch("data_engine.ai_advisor.init_async_groq_client", return_value=None), \
             patch("data_engine.ai_advisor.init_groq_client", return_value=fake):
            await chat_with_column_advisor("edad", "¿hay filas duplicadas?")
        system_prompt = fake.chat.completions.last_kwargs["messages"][0]["content"]
        self.assertIn("ENFOQUE DE ESTA PREGUNTA", system_prompt)
        self.assertIn("DUPLICADOS", system_prompt)

    async def test_retry_recovers_from_rate_limit_413(self):
        """CHAT-02: un 413 transitorio no rompe la conversacion; se reintenta."""
        fake = _FakeClient()
        fake.chat.completions = _FlakyCompletions([413])
        with patch("data_engine.ai_advisor.init_async_groq_client", return_value=None), \
             patch("data_engine.ai_advisor.init_groq_client", return_value=fake), \
             patch("data_engine.ai_advisor.asyncio.sleep", AsyncMock()):
            result = await chat_with_column_advisor("edad", "Hola")
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(fake.chat.completions.calls), 2)

    async def test_retry_recovers_from_rate_limit_429(self):
        """CHAT-02: 429 (tokens por minuto) tambien se reintenta."""
        fake = _FakeClient()
        fake.chat.completions = _FlakyCompletions([429, 429])
        with patch("data_engine.ai_advisor.init_async_groq_client", return_value=None), \
             patch("data_engine.ai_advisor.init_groq_client", return_value=fake), \
             patch("data_engine.ai_advisor.asyncio.sleep", AsyncMock()):
            result = await chat_with_column_advisor("edad", "Hola")
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(fake.chat.completions.calls), 3)

    async def test_persistent_rate_limit_returns_clean_error(self):
        """CHAT-02: si siempre falla, se devuelve status error con mensaje claro."""
        fake = _FakeClient()
        fake.chat.completions = _FlakyCompletions([413, 413, 413, 413])
        with patch("data_engine.ai_advisor.init_async_groq_client", return_value=None), \
             patch("data_engine.ai_advisor.init_groq_client", return_value=fake), \
             patch("data_engine.ai_advisor.asyncio.sleep", AsyncMock()):
            result = await chat_with_column_advisor("edad", "Hola")
        self.assertEqual(result["status"], "error")
        self.assertIn("Lo siento", result["response"])

    async def test_retry_uses_reduced_context_on_second_attempt(self):
        """CHAT-02: el reintento tras 413 cae a contexto compacto (sin DATOS ORDENADOS)."""
        fake = _FakeClient()
        fake.chat.completions = _FlakyCompletions([413])
        ctx = compute_column_context([(2, "28"), (3, "31"), (4, "28")], "number")
        with patch("data_engine.ai_advisor.init_async_groq_client", return_value=None), \
             patch("data_engine.ai_advisor.init_groq_client", return_value=fake), \
             patch("data_engine.ai_advisor.asyncio.sleep", AsyncMock()):
            await chat_with_column_advisor(
                "edad", "¿Qué ves?", context=ctx, total_rows=3, total_columns=7,
                detected_type="number",
            )
        calls = fake.chat.completions.calls
        self.assertIn("DATOS ORDENADOS", calls[0]["messages"][-1]["content"])
        self.assertNotIn("DATOS ORDENADOS", calls[1]["messages"][-1]["content"])



# ---------------------------------------------------------------------------
# /api/ai/chat-column (integracion)
# ---------------------------------------------------------------------------

class TestChatColumnEndpointContext(unittest.TestCase):
    def test_endpoint_passes_computed_context(self):
        mock_advisor = AsyncMock(return_value={"response": "ok", "status": "success"})
        with patch("data_engine.ai_advisor.chat_with_column_advisor", mock_advisor):
            response = client.post(
                "/api/ai/chat-column",
                json={
                    "filename": "test.csv",
                    "content_base64": _encode(SAMPLE_CSV),
                    "column": "edad",
                    "user_query": "¿Cómo trato los vacíos?",
                    "detected_type": "number",
                    "inferred_domain": "edad en anios",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"response": "ok", "status": "success"})

        call_kwargs = mock_advisor.call_args.kwargs
        ctx = call_kwargs["context"]
        self.assertEqual(call_kwargs["column_name"], "edad")
        self.assertEqual(call_kwargs["detected_type"], "number")
        self.assertEqual(call_kwargs["inferred_domain"], "edad en anios")
        self.assertEqual(call_kwargs["total_rows"], 5)
        self.assertEqual(call_kwargs["total_columns"], 7)
        self.assertIn("id", call_kwargs["headers"])

        self.assertEqual(ctx["unique_count"], 3)
        self.assertEqual(ctx["missing_count"], 1)
        self.assertEqual(ctx["value_distribution"], [
            {"value": "28", "count": 2},
            {"value": "31", "count": 1},
            {"value": "450", "count": 1},
        ])
        self.assertEqual(ctx["stats_summary"]["min"], 28.0)
        self.assertEqual(ctx["stats_summary"]["max"], 450.0)
        self.assertEqual(ctx["stats_summary"]["median"], 29.5)
        self.assertEqual(ctx["sorted_data"], [(2, "28"), (4, "28"), (3, "31"), (6, "450"), (5, "")])

    def test_endpoint_defaults_type_to_unknown(self):
        mock_advisor = AsyncMock(return_value={"response": "ok", "status": "success"})
        with patch("data_engine.ai_advisor.chat_with_column_advisor", mock_advisor):
            response = client.post(
                "/api/ai/chat-column",
                json={
                    "filename": "test.csv",
                    "content_base64": _encode(SAMPLE_CSV),
                    "column": "edad",
                    "user_query": "¿Qué ves?",
                },
            )
        self.assertEqual(response.status_code, 200)
        call_kwargs = mock_advisor.call_args.kwargs
        self.assertEqual(call_kwargs["detected_type"], "unknown")
        self.assertEqual(call_kwargs["context"]["stats_summary"], {})

    def test_endpoint_unknown_column_still_works(self):
        mock_advisor = AsyncMock(return_value={"response": "ok", "status": "success"})
        with patch("data_engine.ai_advisor.chat_with_column_advisor", mock_advisor):
            response = client.post(
                "/api/ai/chat-column",
                json={
                    "filename": "test.csv",
                    "content_base64": _encode(SAMPLE_CSV),
                    "column": "no_existe",
                    "user_query": "¿Qué ves?",
                },
            )
        self.assertEqual(response.status_code, 200)
        ctx = mock_advisor.call_args.kwargs["context"]
        self.assertEqual(ctx["missing_count"], 5)
        self.assertEqual(ctx["unique_count"], 0)

    def test_endpoint_caches_heavy_work_per_file(self):
        """CHAT-04: el 2º mensaje del mismo archivo+columna no recalcula load_dataset."""
        from data_engine import analyzer

        calls = {"n": 0}
        real_load = analyzer.load_dataset

        def counting_load(*args, **kwargs):
            calls["n"] += 1
            return real_load(*args, **kwargs)

        mock_advisor = AsyncMock(return_value={"response": "ok", "status": "success"})
        body = {
            "filename": "test.csv",
            "content_base64": _encode(SAMPLE_CSV),
            "column": "cache_probe",
            "user_query": "¿Qué ves?",
        }
        with patch("data_engine.analyzer.load_dataset", side_effect=counting_load), \
             patch("data_engine.ai_advisor.chat_with_column_advisor", mock_advisor):
            r1 = client.post("/api/ai/chat-column", json=body)
            r2 = client.post("/api/ai/chat-column", json=body)
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(calls["n"], 1)


class TestChatColumnEndpointLive(unittest.TestCase):
    def test_chat_column_valid_csv_no_api_key(self):
        response = client.post(
            "/api/ai/chat-column",
            json={
                "filename": "test.csv",
                "content_base64": _encode(SAMPLE_CSV),
                "column": "edad",
                "user_query": "¿Cómo trato los vacíos?",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("response", data)
        self.assertIn(data["status"], ("success", "no_api_key", "error"))


# ---------------------------------------------------------------------------
# /api/ai/column-deep-analysis (integracion tras refactor con helper compartido)
# ---------------------------------------------------------------------------

class TestColumnDeepAnalysisEndpointContext(unittest.TestCase):
    def test_endpoint_passes_computed_context(self):
        mock_advisor = AsyncMock(return_value={"analysis": "ok", "status": "success"})
        with patch("data_engine.ai_advisor.analyze_column_deep", mock_advisor):
            response = client.post(
                "/api/ai/column-deep-analysis",
                json={
                    "filename": "test.csv",
                    "content_base64": _encode(SAMPLE_CSV),
                    "column": "edad",
                    "detected_type": "number",
                    "inferred_domain": "edad en anios",
                },
            )
        self.assertEqual(response.status_code, 200)

        call_kwargs = mock_advisor.call_args.kwargs
        self.assertEqual(call_kwargs["column_name"], "edad")
        self.assertEqual(call_kwargs["detected_type"], "number")
        self.assertEqual(call_kwargs["inferred_domain"], "edad en anios")
        self.assertEqual(call_kwargs["total_rows"], 5)
        self.assertEqual(call_kwargs["total_columns"], 7)
        self.assertIn("id", call_kwargs["headers"])
        self.assertEqual(call_kwargs["unique_count"], 3)
        self.assertEqual(call_kwargs["missing_count"], 1)
        self.assertEqual(call_kwargs["value_distribution"][0], {"value": "28", "count": 2})
        self.assertEqual(call_kwargs["stats_summary"]["min"], 28.0)
        # Recibe datos YA ordenados desde el helper compartido
        self.assertEqual(call_kwargs["column_data"], [(2, "28"), (4, "28"), (3, "31"), (6, "450"), (5, "")])

    def test_endpoint_without_api_key_returns_graceful(self):
        with patch("data_engine.ai_advisor._get_deep_client", return_value=None):
            response = client.post(
                "/api/ai/column-deep-analysis",
                json={
                    "filename": "test.csv",
                    "content_base64": _encode(SAMPLE_CSV),
                    "column": "edad",
                    "detected_type": "number",
                },
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "no_api_key")
        self.assertTrue(
            "response" in data or "analysis" in data,
            "Debe incluir un mensaje explicativo de IA deshabilitada",
        )


# ---------------------------------------------------------------------------
# CL-07: justificaciones batch (Groq unico, sin Gemini)
# ---------------------------------------------------------------------------

from data_engine.analyzer import apply_cleaning_actions


class TestGetJustificationsBatch(unittest.TestCase):

    def test_empty_input_returns_empty(self):
        result = get_justifications_batch([])
        self.assertEqual(result, [])

    def test_no_api_key_returns_original_reasons(self):
        with patch("data_engine.ai_advisor.init_groq_client", return_value=None):
            items = [
                ("edad", "replace_value", "outlier detected"),
                ("nombre", "standardize_text", "case variants"),
            ]
            result = get_justifications_batch(items)
        self.assertEqual(result, ["outlier detected", "case variants"])

    def test_batch_returns_one_justification_per_action(self):
        batch_response = json.dumps({
            "justificaciones": [
                "Se reemplazaron valores atipicos en edad segun protocolo de deteccion de outliers.",
                "Se estandarizaron variantes de caso en nombre para uniformizar el dataset.",
            ]
        })
        fake = _FakeClient(response_text=batch_response)
        with patch("data_engine.ai_advisor.init_groq_client", return_value=fake):
            items = [
                ("edad", "replace_value", "outlier detected"),
                ("nombre", "standardize_text", "case variants"),
            ]
            result = get_justifications_batch(items)
        self.assertEqual(len(result), 2)
        self.assertIn("outliers", result[0].lower())
        self.assertIn("nombre", result[1].lower())

    def test_batch_list_key_direct(self):
        batch_response = json.dumps(["Justificacion A", "Justificacion B"])
        fake = _FakeClient(response_text=batch_response)
        with patch("data_engine.ai_advisor.init_groq_client", return_value=fake):
            items = [("col1", "act1", "r1"), ("col2", "act2", "r2")]
            result = get_justifications_batch(items)
        self.assertEqual(result, ["Justificacion A", "Justificacion B"])

    def test_groq_error_returns_fallback(self):
        def _boom(*a, **kw):
            raise Exception("boom")
        fake = _FakeClient()
        fake.chat.completions.create = _boom
        with patch("data_engine.ai_advisor.init_groq_client", return_value=fake):
            items = [("col", "act", "reason")]
            result = get_justifications_batch(items)
        self.assertEqual(result, ["reason"])

    def test_apply_cleaning_actions_uses_batch_not_gemini(self):
        csv_payload = b"id,name,age\n1,Alice,30\n2,Bob,25\n"
        actions = [
            {"kind": "delete_column", "column": "age", "reason": "Columna irrelevante"},
        ]
        result = apply_cleaning_actions("test.csv", csv_payload, actions)
        changelog = result["changelog"]
        self.assertEqual(len(changelog), 1)
        self.assertIn("reason", changelog[0])
        self.assertTrue(len(changelog[0]["reason"]) > 10)


# ── F5/CL-07 (fix TPM 413): presupuesto de tokens para llama-3.1-8b-instant ──
# El tier gratuito de Groq limita llama-3.1-8b-instant a 6000 TPM (input + output).
# El prompt batch + max_tokens=4096 superaba el limite (413) -> fallback manual.

class TestBatchPromptTokenBudget(unittest.TestCase):
    """El prompt batch y el max_tokens de salida deben caber en el TPM free (6000)."""

    MAX_CHARS = 7000

    def _build_dirty_columns(self):
        import base64 as _b64
        from fastapi.testclient import TestClient as _TC
        from backend.app.main import app as _app
        c = _TC(_app)
        with open(os.path.join(_TEST_ROOT, "samples", "dataset_sucio.csv"), "rb") as f:
            payload = _b64.b64encode(f.read()).decode()
        r = c.post("/api/file/preview", json={"filename": "d.csv", "content_base64": payload})
        pv = r.json()
        settings = {"delimiter": pv["delimiter"], "encoding": pv["encoding"], "header_row_index": pv["detected_header_row"]}
        r = c.post("/api/diagnose", json={"filename": "d.csv", "content_base64": payload, **settings})
        return [col for col in r.json()["diagnostic"]["columns"] if col.get("issues")]

    def test_prompt_cabe_en_budget_de_tokens(self):
        """Con 11 columnas sucias (dataset real), el prompt no debe superar
        el presupuesto estimado para TPM 6000 con max_tokens de salida."""
        cols = self._build_dirty_columns()
        self.assertGreaterEqual(len(cols), 8)
        prompt = _build_batch_prompt(cols, None)
        # estimacion conservadora: ~1 token / 2.5 chars en espanol
        est_input_tokens = len(prompt) // 2
        est_total = est_input_tokens + 2048  # max_tokens de salida reducido
        self.assertLessEqual(len(prompt), self.MAX_CHARS,
                             f"prompt {len(prompt)} chars excede presupuesto")
        self.assertLess(est_total, 6000,
                        f"est. {est_total} tokens >= TPM 6000")

    def test_recommendations_usa_max_tokens_reducido(self):
        """get_ai_recommendations debe pedir max_tokens <= 2048 para caber en TPM."""
        cols = self._build_dirty_columns()
        fake = _FakeClient(response_text=json.dumps({"recommendations": []}))
        with patch("data_engine.ai_advisor.init_groq_client", return_value=fake):
            get_ai_recommendations({"columns": cols}, [])
        self.assertIsNotNone(fake.chat.completions.last_kwargs)
        mt = fake.chat.completions.last_kwargs.get("max_tokens")
        self.assertLessEqual(mt, 2048, f"max_tokens={mt} demasiado alto para TPM 6000")


if __name__ == "__main__":
    unittest.main(verbosity=2)
