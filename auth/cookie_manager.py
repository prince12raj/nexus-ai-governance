"""
auth/cookie_manager.py — Browser cookie-based session persistence.

Saves a session token to the browser cookie on login.
On page refresh, reads the cookie and auto-restores the session.

Requires: pip install extra-streamlit-components
"""
import hashlib
import time
from typing import Optional

from config.logging_config import get_logger

logger = get_logger("nexus.security.cookies")

COOKIE_NAME    = "nexus_session"
COOKIE_EXPIRY  = 30   # days


def _get_manager():
    """Get the cookie manager instance."""
    try:
        import extra_streamlit_components as stx  # type: ignore
        return stx.CookieManager(key="nexus_cookie_manager")
    except ImportError:
        logger.warning("extra-streamlit-components not installed — cookies disabled.")
        return None


def _make_token(username: str, secret: str = "nexus") -> str:
    """Generate a session token from username + timestamp."""
    payload = f"{username}:{int(time.time() // 3600)}:{secret}"
    return hashlib.sha256(payload.encode()).hexdigest()[:32]


def save_session_cookie(username: str) -> None:
    """
    Save a session cookie after successful login.
    The cookie stores the username and a token — no password ever stored.
    """
    manager = _get_manager()
    if not manager:
        return
    try:
        token = _make_token(username)
        manager.set(
            COOKIE_NAME,
            f"{username}:{token}",
            expires_at=_expiry_date(),
            key=f"set_{COOKIE_NAME}",
        )
        logger.info("Session cookie saved for user=%s", username)
    except Exception as exc:
        logger.warning("Failed to save session cookie: %s", exc)


def get_session_from_cookie() -> Optional[str]:
    """
    Read the session cookie and return the username if valid.
    Returns None if cookie is missing, expired, or invalid.
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

        username, stored_token = parts
        expected = _make_token(username)

        if stored_token == expected:
            return username
        return None
    except Exception as exc:
        logger.warning("Failed to read session cookie: %s", exc)
        return None


def clear_session_cookie() -> None:
    """Delete the session cookie on logout."""
    manager = _get_manager()
    if not manager:
        return
    try:
        manager.delete(COOKIE_NAME, key=f"del_{COOKIE_NAME}")
        logger.info("Session cookie cleared.")
    except Exception as exc:
        logger.warning("Failed to clear session cookie: %s", exc)


def _expiry_date():
    """Return expiry datetime for the cookie."""
    from datetime import datetime, timedelta
    return datetime.now() + timedelta(days=COOKIE_EXPIRY)