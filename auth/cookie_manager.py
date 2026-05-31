"""
auth/cookie_manager.py — Browser cookie session persistence for Nexus AI Governance Platform.
"""
import hashlib
import time
from datetime import datetime, timedelta
from typing import Optional

from config.logging_config import get_logger

logger = get_logger("nexus.security.cookies")

COOKIE_NAME   = "nexus_session"
COOKIE_EXPIRY = 30  # days


# ── Singleton cookie manager ───────────────────────────────────────────────────
# extra-streamlit-components requires the SAME instance across all calls.
# We cache it in st.session_state to avoid duplicate key errors.

def _get_manager():
    """Return a single shared CookieManager instance per session."""
    try:
        import streamlit as st
        import extra_streamlit_components as stx  # type: ignore

        # Reuse existing instance stored in session_state
        if "_cookie_manager" not in st.session_state:
            st.session_state["_cookie_manager"] = stx.CookieManager(
                key="nexus_cookie_manager"
            )
        return st.session_state["_cookie_manager"]

    except ImportError:
        logger.warning("extra-streamlit-components not installed — cookies disabled.")
        return None
    except Exception as exc:
        logger.warning("Cookie manager init failed: %s", exc)
        return None


def _make_token(username: str) -> str:
    """Generate a session token — changes every hour so stale tokens auto-expire."""
    from config.settings import settings
    secret  = settings.APP_SECRET_KEY or "nexus"
    # Token is valid for the current hour window
    hour    = int(time.time() // 3600)
    payload = f"{username}:{hour}:{secret}"
    return hashlib.sha256(payload.encode()).hexdigest()[:32]


def _is_valid_token(username: str, token: str) -> bool:
    """
    Validate a stored token.
    Accepts tokens from the current hour OR the previous hour
    so a token created at 13:59 is still valid at 14:01.
    """
    from config.settings import settings
    secret = settings.APP_SECRET_KEY or "nexus"
    for offset in (0, -1):
        hour    = int(time.time() // 3600) + offset
        payload = f"{username}:{hour}:{secret}"
        expected = hashlib.sha256(payload.encode()).hexdigest()[:32]
        if token == expected:
            return True
    return False


# ── Public API ────────────────────────────────────────────────────────────────

def save_session_cookie(username: str) -> None:
    """Save session cookie after successful login."""
    manager = _get_manager()
    if not manager:
        return
    try:
        token   = _make_token(username)
        expiry  = datetime.now() + timedelta(days=COOKIE_EXPIRY)
        manager.set(COOKIE_NAME, f"{username}:{token}", expires_at=expiry)
        logger.info("Session cookie saved | user=%s", username)
    except Exception as exc:
        logger.warning("Cookie save failed: %s", exc)


def get_session_from_cookie() -> Optional[str]:
    """
    Read the session cookie and return username if valid.
    Returns None if cookie missing, expired, or invalid.
    """
    manager = _get_manager()
    if not manager:
        return None
    try:
        value = manager.get(COOKIE_NAME)
        if not value:
            return None

        parts = str(value).split(":")
        if len(parts) != 2:
            return None

        username, token = parts
        if _is_valid_token(username, token):
            return username

        logger.info("Cookie token invalid or expired for user=%s", username)
        return None
    except Exception as exc:
        logger.warning("Cookie read failed: %s", exc)
        return None


def clear_session_cookie() -> None:
    """Delete the session cookie on logout."""
    manager = _get_manager()
    if not manager:
        return
    try:
        manager.delete(COOKIE_NAME)
        logger.info("Session cookie cleared.")
    except Exception as exc:
        logger.warning("Cookie clear failed: %s", exc)