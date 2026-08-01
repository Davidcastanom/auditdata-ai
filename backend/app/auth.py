"""Supabase authentication helpers for AuditData AI backend."""

import os
import logging
from typing import Any
from supabase import create_client, Client

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")


def get_supabase_client() -> Client:
    """Create a Supabase client with the service key (for backend operations)."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def verify_token(token: str) -> dict[str, Any] | None:
    """Verify a Supabase JWT token and return the user payload."""
    if not SUPABASE_ANON_KEY:
        logger.warning("SUPABASE_ANON_KEY not configured, skipping auth")
        return None

    try:
        client = get_supabase_client()
        user = client.auth.get_user(token)
        if user and user.user:
            metadata = user.user.user_metadata or {}
            return {
                "id": user.user.id,
                "email": user.user.email,
                "full_name": metadata.get("full_name", "")
                or metadata.get("name", ""),
                "avatar_url": metadata.get("avatar_url", "")
                or metadata.get("picture", ""),
                "user_metadata": metadata,
                "app_metadata": user.user.app_metadata or {},
            }
        return None
    except Exception as e:
        logger.warning("Token verification failed: %s", e)
        return None
