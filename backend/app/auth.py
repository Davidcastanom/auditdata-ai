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
    """Verify a Supabase JWT token and return the user payload.

    Supabase JWTs are signed with the JWT secret from the project settings.
    We decode them using PyJWT with the secret.
    """
    if not SUPABASE_ANON_KEY:
        logger.warning("SUPABASE_ANON_KEY not configured, skipping auth")
        return None

    try:
        # Supabase uses the JWT secret from project settings
        # The anon key itself IS a JWT, and the JWT secret is used to sign user tokens
        # We need to get the JWT secret from the project settings
        # For now, we'll use the Supabase client to verify
        client = get_supabase_client()
        # Use Supabase auth to get user from token
        user = client.auth.get_user(token)
        if user and user.user:
            return {
                "id": user.user.id,
                "email": user.user.email,
                "full_name": user.user.user_metadata.get("full_name", "")
                or user.user.user_metadata.get("name", ""),
                "avatar_url": user.user.user_metadata.get("avatar_url", "")
                or user.user.user_metadata.get("picture", ""),
            }
        return None
    except Exception as e:
        logger.warning("Token verification failed: %s", e)
        return None


def get_user_datasets(user_id: str) -> list[dict[str, Any]]:
    """Fetch all datasets for a user."""
    client = get_supabase_client()
    result = client.table("datasets").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
    return result.data or []


def save_dataset(user_id: str, filename: str, content_base64: str, row_count: int, column_count: int) -> dict[str, Any]:
    """Save a dataset to Supabase."""
    client = get_supabase_client()
    result = client.table("datasets").insert({
        "user_id": user_id,
        "filename": filename,
        "content_base64": content_base64,
        "row_count": row_count,
        "column_count": column_count,
    }).execute()
    return result.data[0] if result.data else {}


def save_analysis(dataset_id: str, user_id: str, analysis_json: dict, row_meaning: str = "", analysis_objective: str = "") -> dict[str, Any]:
    """Save an analysis to Supabase."""
    client = get_supabase_client()
    result = client.table("analyses").insert({
        "dataset_id": dataset_id,
        "user_id": user_id,
        "analysis_json": analysis_json,
        "row_meaning": row_meaning,
        "analysis_objective": analysis_objective,
    }).execute()
    return result.data[0] if result.data else {}


def save_cleaning_session(
    dataset_id: str,
    user_id: str,
    actions_json: list,
    before_json: dict | None = None,
    after_json: dict | None = None,
    changelog_json: list | None = None,
    analyst: str = "",
    version: str = "v1.0",
) -> dict[str, Any]:
    """Save a cleaning session to Supabase."""
    client = get_supabase_client()
    result = client.table("cleaning_sessions").insert({
        "dataset_id": dataset_id,
        "user_id": user_id,
        "actions_json": actions_json,
        "before_json": before_json,
        "after_json": after_json,
        "changelog_json": changelog_json or [],
        "analyst": analyst,
        "version": version,
    }).execute()
    return result.data[0] if result.data else {}


def get_user_history(user_id: str) -> list[dict[str, Any]]:
    """Fetch cleaning session history for a user."""
    client = get_supabase_client()
    result = (
        client.table("cleaning_sessions")
        .select("*, datasets!inner(filename, row_count, column_count)")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    return result.data or []
