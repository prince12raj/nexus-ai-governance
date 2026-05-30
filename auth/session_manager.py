"""
auth/session_manager.py — Session management for Nexus AI Governance Platform.

Handles:
  - Authentication state in Streamlit session_state
  - Login / logout lifecycle
  - Current user retrieval
  - Permission checking
  - Session timeout enforcement
  - Activity tracking

Usage:
    from auth.session_manager import (
        login, logout, is_logged_in,
        get_current_user, require_auth,
        has_permission, get_session_info,
    )
"""

import time
from typing import Any, Dict, List, Optional

import streamlit as st

from config.logging_config import get_logger
from config.settings import settings

logger = get_logger("nexus.security.session")


# ══════════════════════════════════════════════════════════════════════════════
# CORE AUTH FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def login(username: str, password: str) -> bool:
    """
    Authenticate a user and initialise their session.

    Args:
        username: The submitted username.
        password: The submitted plain-text password.

    Returns:
        True if credentials are valid, False otherwise.
    """
    from auth.user_store import load_all_users, update_last_login
    from auth.security import verify_password

    all_users  = load_all_users()
    uname      = username.strip().lower()
    user       = all_users.get(uname)

    if not user:
        logger.warning("Login failed — unknown user: %s", username)
        return False

    # Block demo-only accounts (those without a registered_at timestamp)
    # Only users who registered via the registration page can log in
    if not user.get("registered_at"):
        logger.warning("Login blocked — demo account not allowed: %s", username)
        return False

    if not verify_password(password, user["password_hash"]):
        logger.warning("Login failed — wrong password: user=%s", uname)
        return False

    # Initialise session
    now = time.time()
    st.session_state.update({
        "authenticated":    True,
        "username":         uname,
        "current_user":     user,
        "login_time":       now,
        "last_activity":    now,
        "login_attempts":   0,
        "lockout_until":    0,
    })

    # Load this user's own audit history from DB (never another user's data)
    try:
        from auth.db_session import load_user_audits, load_user_documents
        db_audits = load_user_audits(uname)
        if db_audits:
            st.session_state["audit_history"] = db_audits
            logger.info("Loaded %d audits for user=%s", len(db_audits), uname)

        db_docs = load_user_documents(uname)
        if db_docs:
            st.session_state["uploaded_docs"] = db_docs
            logger.info("Loaded %d documents for user=%s", len(db_docs), uname)
    except Exception as exc:
        logger.warning("Failed to load user data from DB: %s", exc)

    # Update last login timestamp
    try:
        update_last_login(uname)
    except Exception:
        pass

    logger.info(
        "Login success | user=%s | role=%s | ip=client",
        uname, user.get("role", "unknown"),
    )
    return True


def logout() -> None:
    """
    Log out the current user and clear their session state.

    Preserves non-auth keys like audit_history and uploaded_docs
    so the session data is not lost on accidental logout.
    """
    username = st.session_state.get("username", "unknown")
    logger.info("Logout | user=%s", username)

    # Keys to clear on logout
    auth_keys = [
        "authenticated", "username", "current_user",
        "login_time", "last_activity",
        "login_attempts", "lockout_until",
        "_config_warnings_shown",
    ]
    for key in auth_keys:
        st.session_state.pop(key, None)


def is_logged_in() -> bool:
    """
    Return True if the current session has a valid authenticated user.

    Also checks session timeout — automatically logs out expired sessions.
    """
    if not st.session_state.get("authenticated"):
        return False

    # Check session timeout
    if _is_session_expired():
        logger.info(
            "Session expired | user=%s",
            st.session_state.get("username", "unknown"),
        )
        logout()
        return False

    # Update last activity time
    st.session_state["last_activity"] = time.time()
    return True


def require_auth() -> bool:
    """
    Guard function for pages that require authentication.

    Call at the top of any page renderer.

    Returns:
        True if authenticated, False if not (caller should return early).

    Usage:
        def render_my_page():
            if not require_auth():
                return
            # ... page content
    """
    if not is_logged_in():
        st.warning("🔒 Please sign in to access this page.")
        return False
    return True


# ══════════════════════════════════════════════════════════════════════════════
# USER INFO
# ══════════════════════════════════════════════════════════════════════════════

def get_current_user() -> Optional[Dict[str, Any]]:
    """
    Return the current authenticated user's profile dict.

    Returns:
        User dict with keys: name, role, email, avatar, department, etc.
        None if not authenticated.
    """
    # Try cached current_user first (fastest)
    cached = st.session_state.get("current_user")
    if cached:
        return cached

    # Fallback: look up from USERS_DB
    username = st.session_state.get("username")
    if username:
        from auth.user_store import load_all_users
        all_users = load_all_users()
        user = all_users.get(username)
        if user:
            st.session_state["current_user"] = user
            return user

    return None


def get_username() -> Optional[str]:
    """Return the current authenticated username."""
    return st.session_state.get("username")


def get_user_role() -> str:
    """Return the current user's role string, or 'Guest' if not authenticated."""
    user = get_current_user()
    return user.get("role", "Guest") if user else "Guest"


def get_user_name() -> str:
    """Return the current user's display name."""
    user = get_current_user()
    return user.get("name", "Unknown User") if user else "Guest"


def get_user_avatar() -> str:
    """Return the current user's avatar initials."""
    user = get_current_user()
    return user.get("avatar", "?") if user else "?"


# ══════════════════════════════════════════════════════════════════════════════
# PERMISSIONS
# ══════════════════════════════════════════════════════════════════════════════

def has_permission(page_or_action: str) -> bool:
    """
    Check if the current user has permission for a given page or action.

    Args:
        page_or_action: Page name (e.g. "Admin Settings") or action string.

    Returns:
        True if the user's role has permission, False otherwise.
        Returns False if not authenticated.
    """
    role = get_user_role()
    if role == "Guest":
        return False

    from auth.roles import has_permission as _role_has_permission
    return _role_has_permission(role, page_or_action)


def get_allowed_pages() -> List[str]:
    """
    Return the list of pages the current user is allowed to access.

    Returns:
        List of page name strings.
    """
    role = get_user_role()
    from auth.roles import ROLE_PERMISSIONS
    return ROLE_PERMISSIONS.get(role, [])


def require_role(required_role: str) -> bool:
    """
    Require a specific role or higher.

    Hierarchy: Admin > Compliance Officer > Auditor > Viewer

    Args:
        required_role: Minimum role required.

    Returns:
        True if the user meets the requirement.
    """
    role_hierarchy = {
        "Admin":              4,
        "Developer":          4,
        "Compliance Officer": 3,
        "Auditor":            2,
        "Viewer":             1,
        "Guest":              0,
    }
    current_level  = role_hierarchy.get(get_user_role(), 0)
    required_level = role_hierarchy.get(required_role, 4)
    return current_level >= required_level


# ══════════════════════════════════════════════════════════════════════════════
# SESSION INFO
# ══════════════════════════════════════════════════════════════════════════════

def get_session_info() -> Dict[str, Any]:
    """
    Return a summary of the current session state.

    Used by Admin Settings and sidebar status panel.

    Returns:
        Dict with username, role, login_time, session_age_min, etc.
    """
    user      = get_current_user()
    login_ts  = st.session_state.get("login_time", 0)
    last_act  = st.session_state.get("last_activity", 0)
    now       = time.time()

    session_age_min   = round((now - login_ts) / 60, 1) if login_ts else 0
    idle_min          = round((now - last_act) / 60, 1)  if last_act else 0
    timeout_remaining = max(0, settings.SESSION_TIMEOUT_MINUTES - idle_min)

    return {
        "username":           st.session_state.get("username", ""),
        "name":               user.get("name", "") if user else "",
        "role":               user.get("role", "") if user else "",
        "department":         user.get("department", "") if user else "",
        "avatar":             user.get("avatar", "?") if user else "?",
        "authenticated":      is_logged_in(),
        "session_age_min":    session_age_min,
        "idle_min":           idle_min,
        "timeout_remaining":  timeout_remaining,
        "login_time":         _format_time(login_ts),
        "allowed_pages":      get_allowed_pages(),
        "audit_count":        len(st.session_state.get("audit_history", [])),
        "doc_count":          len(st.session_state.get("uploaded_docs", [])),
    }


def get_session_age_minutes() -> float:
    """Return how long the current session has been active (minutes)."""
    login_ts = st.session_state.get("login_time", time.time())
    return round((time.time() - login_ts) / 60, 1)


def get_idle_minutes() -> float:
    """Return how many minutes since the last user activity."""
    last_act = st.session_state.get("last_activity", time.time())
    return round((time.time() - last_act) / 60, 1)


# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE INITIALISATION
# ══════════════════════════════════════════════════════════════════════════════

def init_session_state() -> None:
    """
    Initialise all required session_state keys with safe defaults.

    Call once at app startup (in app.py main()).
    Safe to call multiple times — only sets missing keys.
    """
    defaults: Dict[str, Any] = {
        # Auth
        "authenticated":            False,
        "username":                 None,
        "current_user":             None,
        "login_time":               0.0,
        "last_activity":            0.0,
        "login_attempts":           0,
        "lockout_until":            0.0,
        "auth_page":                "login",
        # UI state
        "_config_warnings_shown":   False,
        # Navigation
        "current_page":          "Dashboard",
        # LLM
        "api_key":               "",
        "selected_llm":          "GPT-4o",
        # Data
        "vector_store":          None,
        "vector_db_initialized": False,
        "audit_history":         [],
        "uploaded_docs":         [],
        "governance_decisions":  [],
        "current_report":        None,
        # Chat
        "chat_history":          [],
        "chat_framework":        "GDPR",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def clear_session_data() -> None:
    """
    Clear all user-generated session data (audits, docs, chat).
    Preserves auth state. Used by Admin Settings → Reset Session.
    """
    data_keys = [
        "audit_history", "uploaded_docs", "governance_decisions",
        "current_report", "chat_history",
    ]
    for key in data_keys:
        if key in st.session_state:
            st.session_state[key] = [] if isinstance(
                st.session_state[key], list
            ) else None

    logger.info("Session data cleared | user=%s", get_username())


# ══════════════════════════════════════════════════════════════════════════════
# PRIVATE HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _is_session_expired() -> bool:
    """Return True if the session has exceeded the timeout limit."""
    last_activity = st.session_state.get("last_activity", 0)
    if not last_activity:
        return False
    idle_minutes = (time.time() - last_activity) / 60
    return idle_minutes > settings.SESSION_TIMEOUT_MINUTES


def _format_time(ts: float) -> str:
    """Format a Unix timestamp as 'HH:MM:SS'."""
    if not ts:
        return ""
    import datetime
    return datetime.datetime.fromtimestamp(ts).strftime("%H:%M:%S")