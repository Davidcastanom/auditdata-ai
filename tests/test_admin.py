"""Tests de métricas anónimas y panel administrador.

Cubren:
- hash_client: HMAC determinístico e irreversible
- No-op sin Supabase (la app nunca falla por métricas)
- Endpoints admin: 401 sin token, 401 token inválido, 200 con token válido,
  JWT de Supabase admin (200) y no-admin (403)
- build_errors_report y notify_make_webhook (Make.com)
"""

import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from backend.app import metrics
from backend.app.main import app

client = TestClient(app)


class TestHashClient(unittest.TestCase):
    def test_deterministic(self):
        with patch.object(metrics, "METRICS_SECRET", "secreto"):
            self.assertEqual(
                metrics.hash_client("abc-123"),
                metrics.hash_client("abc-123"),
            )

    def test_different_inputs_different_hash(self):
        with patch.object(metrics, "METRICS_SECRET", "secreto"):
            self.assertNotEqual(
                metrics.hash_client("user-a"),
                metrics.hash_client("user-b"),
            )

    def test_never_returns_original_value(self):
        with patch.object(metrics, "METRICS_SECRET", "secreto"):
            h = metrics.hash_client("correo@example.com")
            self.assertNotIn("correo", h)

    def test_empty_secret_returns_empty(self):
        with patch.object(metrics, "METRICS_SECRET", ""):
            self.assertEqual(metrics.hash_client("abc"), "")

    def test_length_is_sha256_hex(self):
        with patch.object(metrics, "METRICS_SECRET", "secreto"):
            self.assertEqual(len(metrics.hash_client("abc")), 64)


class TestMetricsNoOp(unittest.TestCase):
    """Sin Supabase configurado, nada se escribe y nada rompe."""

    def test_metrics_disabled_without_env(self):
        with patch.dict(metrics.os.environ, {}, clear=False):
            pass
        self.assertFalse(metrics.metrics_enabled())

    def test_record_usage_event_noop(self):
        with patch.dict(metrics.os.environ, {}, clear=False):
            metrics.record_usage_event(
                client_id="x", endpoint="/api/analyze", status_code=200, duration_ms=1.0
            )

    def test_record_error_ignores_success_status(self):
        with patch.dict(metrics.os.environ, {}, clear=False):
            metrics.record_error(client_id="x", endpoint="/api/x", status_code=200, error_type="X")

    def test_get_admin_metrics_returns_empty(self):
        self.assertEqual(metrics.get_admin_metrics(), {"daily": [], "sessions": []})

    def test_get_admin_errors_returns_empty(self):
        self.assertEqual(metrics.get_admin_errors(), [])

    def test_build_errors_report_shape(self):
        report = metrics.build_errors_report()
        self.assertIn("generated_at", report)
        self.assertIn("summary", report)
        self.assertIn("errors", report)
        self.assertIn("recent_daily", report)


class TestNotifyMakeWebhook(unittest.IsolatedAsyncioTestCase):
    async def test_no_webhook_url(self):
        with patch.object(metrics, "MAKE_WEBHOOK_URL", ""):
            result = await metrics.notify_make_webhook({"a": 1})
        self.assertEqual(result["status"], "no_webhook")

    async def test_sends_payload_to_webhook(self):
        fake_resp = AsyncMock()
        fake_resp.status_code = 200

        async def fake_post(url, json=None):
            return fake_resp

        fake_client = AsyncMock()
        fake_client.post.side_effect = fake_post
        fake_client.__aenter__ = AsyncMock(return_value=fake_client)
        fake_client.__aexit__ = AsyncMock(return_value=False)

        with patch.object(metrics, "MAKE_WEBHOOK_URL", "https://hook.make.com/abc"), \
             patch("httpx.AsyncClient", return_value=fake_client):
            result = await metrics.notify_make_webhook({"errors": []})

        self.assertEqual(result["status"], "sent")
        fake_client.post.assert_awaited_once()

    async def test_webhook_failure_reported(self):
        async def fake_post(url, json=None):
            raise RuntimeError("conexión falló")

        fake_client = AsyncMock()
        fake_client.post.side_effect = fake_post
        fake_client.__aenter__ = AsyncMock(return_value=fake_client)
        fake_client.__aexit__ = AsyncMock(return_value=False)

        with patch.object(metrics, "MAKE_WEBHOOK_URL", "https://hook.make.com/abc"), \
             patch("httpx.AsyncClient", return_value=fake_client):
            result = await metrics.notify_make_webhook({"errors": []})

        self.assertEqual(result["status"], "failed")


class TestAdminEndpointsAuth(unittest.TestCase):
    """Protección del panel admin: token + rol."""

    def _get(self, path, token=None):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        return client.get(path, headers=headers)

    def test_requires_token(self):
        with patch.object(metrics, "ADMIN_TOKEN", "admin-secret"):
            r = self._get("/api/admin/metrics")
        self.assertEqual(r.status_code, 401)

    def test_invalid_token_rejected(self):
        with patch.object(metrics, "ADMIN_TOKEN", "admin-secret"):
            r = self._get("/api/admin/metrics", token="malo")
        self.assertEqual(r.status_code, 401)

    def test_admin_token_accepted(self):
        with patch.object(metrics, "ADMIN_TOKEN", "admin-secret"):
            r = self._get("/api/admin/metrics", token="admin-secret")
        self.assertEqual(r.status_code, 200)
        self.assertIn("metrics", r.json())

    def test_admin_token_accepted_on_errors(self):
        with patch.object(metrics, "ADMIN_TOKEN", "admin-secret"):
            r = self._get("/api/admin/errors", token="admin-secret")
        self.assertEqual(r.status_code, 200)
        self.assertIn("errors", r.json())

    def test_supabase_jwt_admin_user(self):
        admin_user = {"role": "admin", "email": "admin@auditdata.ai", "user_metadata": {}, "app_metadata": {"role": "admin"}}
        with patch("backend.app.auth.verify_token", return_value=admin_user):
            r = self._get("/api/admin/metrics", token="jwt-valid-admin")
        self.assertEqual(r.status_code, 200)

    def test_user_metadata_role_does_not_grant_admin(self):
        # user_metadata es editable por el cliente: NO debe otorgar permisos admin.
        user = {"role": "", "email": "user@x.com", "user_metadata": {"role": "admin"}, "app_metadata": {}}
        with patch("backend.app.auth.verify_token", return_value=user), \
             patch.dict("os.environ", {"ADMIN_EMAILS": "dev@auditdata.ai"}, clear=False):
            r = self._get("/api/admin/metrics", token="jwt-user-metadata-admin")
        self.assertEqual(r.status_code, 403)

    def test_supabase_jwt_allowlist_email(self):
        user = {"role": "", "email": "dev@auditdata.ai", "user_metadata": {}}
        with patch("backend.app.auth.verify_token", return_value=user), \
             patch.dict("os.environ", {"ADMIN_EMAILS": "dev@auditdata.ai"}, clear=False):
            r = self._get("/api/admin/metrics", token="jwt-valid")
        self.assertEqual(r.status_code, 200)

    def test_supabase_jwt_non_admin_rejected(self):
        user = {"role": "", "email": "user@x.com", "user_metadata": {}}
        with patch("backend.app.auth.verify_token", return_value=user), \
             patch.dict("os.environ", {"ADMIN_EMAILS": "dev@auditdata.ai"}, clear=False):
            r = self._get("/api/admin/metrics", token="jwt-regular")
        self.assertEqual(r.status_code, 403)

    def test_invalid_supabase_jwt_rejected(self):
        with patch("backend.app.auth.verify_token", return_value=None):
            r = self._get("/api/admin/metrics", token="jwt-no-user")
        self.assertEqual(r.status_code, 401)

    def test_send_errors_requires_token(self):
        r = client.post("/api/admin/errors/send")
        self.assertEqual(r.status_code, 401)

    def test_send_errors_with_token_no_webhook(self):
        with patch.object(metrics, "ADMIN_TOKEN", "admin-secret"), \
             patch.object(metrics, "MAKE_WEBHOOK_URL", ""):
            r = client.post(
                "/api/admin/errors/send",
                headers={"Authorization": "Bearer admin-secret"},
            )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["result"]["status"], "no_webhook")
        self.assertIn("report", data)


class TestAdminPageRoute(unittest.TestCase):
    def test_admin_page_served(self):
        r = client.get("/admin")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Panel Administrador", r.text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
