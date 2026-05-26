"""
auth/__init__.py — Auth package for Nexus AI Governance Platform.

Note: session_manager and login require streamlit —
      import them only within page renderers, not at module level.
"""
from auth.roles import USERS_DB, ROLE_PERMISSIONS, has_permission, get_all_users
from auth.security import (
    hash_password, verify_password,
    generate_token, generate_session_id,
    is_strong_password, generate_api_key,
)
from auth.user_store import (
    load_all_users, register_user, user_exists,
    email_exists, get_user, save_user, delete_user,
    get_all_registered_users, update_last_login,
)

# Note: session_manager and login require streamlit — import only within page renderers

__all__ = [
    # Roles
    "USERS_DB",
    "ROLE_PERMISSIONS",
    "has_permission",
    "get_all_users",
    # Security
    "hash_password",
    "verify_password",
    "generate_token",
    "generate_session_id",
    "is_strong_password",
    "generate_api_key",
    # User store
    "load_all_users",
    "register_user",
    "user_exists",
    "email_exists",
    "get_user",
    "save_user",
    "delete_user",
    "get_all_registered_users",
    "update_last_login",
]