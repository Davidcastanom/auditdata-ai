"""
=============================================================================
MÉTRICAS ANÓNIMAS DE USO PARA AUDITDATA AI
=============================================================================

POLÍTICA DE SEGURIDAD:
-----------------------
- NUNCA se almacenan datos clasificados de los usuarios: ni contenido de
  CSVs, ni nombres de columnas, ni textos del chat, ni emails.
- Solo se guardan métricas anónimas de comportamiento del producto:
  hash del cliente (HMAC, irreversible), endpoint, status code y duración.
- Si Supabase no está configurado (env vars ausentes), TODAS las funciones
  son no-op: la aplicación nunca falla por culpa de las métricas.

CÓMO SE USA:
-------------
1. Un middleware mide cada request /api/* (duración + status).
2. Cada evento se inserta en usage_events (en un hilo, sin bloquear).
3. Los errores (status >= 400) van además a error_logs.
4. El panel admin consulta las vistas v_daily_metrics, v_session_stats
   y v_error_summary (ver db/migrations/001_metrics.sql).
5. Un webhook de Make.com puede recibir el resumen de errores por email.

AUTOR: AuditData AI
VERSION: 1.0
=============================================================================
"""

import hashlib
import hmac
import logging
import os
import threading
from typing import Any

logger = logging.getLogger(__name__)

METRICS_SECRET = os.getenv("METRICS_SECRET", "")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
MAKE_WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_URL", "")


def metrics_enabled() -> bool:
    """Las métricas solo escriben si hay secreto y credenciales de Supabase."""
    return bool(
        METRICS_SECRET
        and os.getenv("SUPABASE_URL")
        and os.getenv("SUPABASE_SERVICE_KEY")
    )


def hash_client(client_id: str) -> str:
    """HMAC-SHA256 del id de cliente. Irreversible: nadie puede volver al id real."""
    if not METRICS_SECRET:
        return ""
    return hmac.new(
        METRICS_SECRET.encode("utf-8"),
        str(client_id or "").encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _insert(table: str, payload: dict) -> None:
    try:
        from backend.app.auth import get_supabase_client

        client = get_supabase_client()
        client.table(table).insert(payload).execute()
    except Exception as e:
        logger.warning("Métricas: no se pudo insertar en %s: %s", table, e)


def record_usage_event(
    *,
    client_id: str,
    session_id: str = "",
    endpoint: str,
    method: str = "GET",
    status_code: int = 200,
    duration_ms: float = 0.0,
) -> None:
    """Registra una llamada a un endpoint. Sin bloqueo y sin datos del usuario."""
    if not metrics_enabled():
        return
    payload = {
        "client_hash": hash_client(client_id),
        "session_id": session_id or "",
        "endpoint": endpoint,
        "method": method,
        "status_code": int(status_code),
        "duration_ms": round(float(duration_ms), 2),
    }
    threading.Thread(target=_insert, args=("usage_events", payload), daemon=True).start()


def classify_error(status_code: int, error_type: str = "") -> str:
    """Traduce un status HTTP a un tipo de error legible.

    El middleware captura el nombre de la excepción (error_type) solo para
    fallos no controlados; para respuestas HTTP manejadas (400/403/422...)
    este valor llega vacío y aquí se deriva una etiqueta comprensible.
    """
    if error_type:
        return (error_type or "unknown")[:120]
    if status_code == 401:
        return "no_autorizado"
    if status_code == 403:
        return "prohibido"
    if status_code == 404:
        return "no_encontrado"
    if status_code == 422:
        return "validacion"
    if status_code == 400:
        return "peticion_invalida"
    if status_code >= 500:
        return "error_interno"
    return f"http_{status_code}"


def record_error(
    *,
    client_id: str,
    endpoint: str,
    status_code: int,
    error_type: str = "",
) -> None:
    """Registra un error (status >= 400). Solo tipo, nunca el detalle del dato."""
    if not metrics_enabled() or int(status_code) < 400:
        return
    payload = {
        "client_hash": hash_client(client_id),
        "endpoint": endpoint,
        "status_code": int(status_code),
        "error_type": classify_error(int(status_code), error_type),
    }
    threading.Thread(target=_insert, args=("error_logs", payload), daemon=True).start()


def _fetch_view(view_name: str, limit: int = 100) -> list[dict]:
    if not metrics_enabled():
        return []
    try:
        from backend.app.auth import get_supabase_client

        client = get_supabase_client()
        res = client.table(view_name).select("*").limit(limit).execute()
        return list(res.data or [])
    except Exception as e:
        logger.warning("Métricas: no se pudo consultar %s: %s", view_name, e)
        return []


def get_admin_metrics() -> dict[str, Any]:
    """Resumen para el panel admin: actividad diaria + duración de sesiones."""
    return {
        "daily": _fetch_view("v_daily_metrics"),
        "sessions": _fetch_view("v_session_stats"),
    }


def get_admin_errors(limit: int = 50, resolved: bool | None = None) -> list[dict]:
    if not metrics_enabled():
        return []
    try:
        from backend.app.auth import get_supabase_client

        client = get_supabase_client()
        query = client.table("error_logs").select("*")
        if resolved is True:
            query = query.not_.is_("resolved_at", "null")
        elif resolved is False:
            query = query.is_("resolved_at", "null")
        res = (
            query.order("created_at", desc=True)
            .limit(int(limit))
            .execute()
        )
        return list(res.data or [])
    except Exception as e:
        logger.warning("Métricas: no se pudo consultar error_logs: %s", e)
        return []


def resolve_errors(ids: list[str] | None = None) -> int:
    """Marca errores como resueltos (resolved_at = now()).

    Si ids está vacío o es None, resuelve todos los pendientes.
    Devuelve cuántos registros se actualizaron.
    """
    if not metrics_enabled():
        return 0
    try:
        from datetime import datetime, timedelta, timezone

        from backend.app.auth import get_supabase_client

        client = get_supabase_client()
        updates = {"resolved_at": datetime.now(timezone.utc).isoformat()}
        if ids:
            res = (
                client.table("error_logs")
                .update(updates)
                .in_("id", list(ids))
                .execute()
            )
        else:
            res = (
                client.table("error_logs")
                .update(updates)
                .is_("resolved_at", "null")
                .execute()
            )
        return len(list(res.data or []))
    except Exception as e:
        logger.warning("Métricas: no se pudieron resolver errores: %s", e)
        return 0


def build_errors_report() -> dict:
    """Arma el payload JSON que se envía al webhook de Make.com (errores pendientes)."""
    daily = get_admin_metrics().get("daily", [])
    errors = get_admin_errors(limit=50, resolved=False)
    return {
        "generated_at": _now_iso(),
        "summary": {
            "total_pending_errors": len(errors),
            "active_users_today": sum(
                int(d.get("active_users", 0)) for d in daily
            ),
        },
        "errors": errors[:20],
        "recent_daily": daily[:10],
    }


async def notify_make_webhook(payload: dict) -> dict:
    """Envía el resumen al webhook de Make.com (flujo automatizado de email)."""
    if not MAKE_WEBHOOK_URL:
        return {"status": "no_webhook", "detail": "MAKE_WEBHOOK_URL no configurado"}
    import httpx

    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(MAKE_WEBHOOK_URL, json=payload)
        return {
            "status": "sent" if r.status_code < 300 else "failed",
            "http_status": r.status_code,
        }
    except Exception as e:
        logger.warning("Métricas: webhook Make falló: %s", e)
        return {"status": "failed", "detail": str(e)}


def _now_iso() -> str:
    from datetime import datetime, timedelta, timezone

    return datetime.now(timezone(timedelta(hours=-5))).isoformat(timespec="seconds")
