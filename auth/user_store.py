"""
auth/user_store.py — Persistent user database for Nexus AI Governance Platform.

Priority:
  1. Supabase (cloud PostgreSQL) — if SUPABASE_URL + SUPABASE_KEY configured
  2. Local JSON file (data/users.json) — local development fallback
  3. In-memory demo users (auth/roles.py) — always available

This means:
  - On Streamlit Cloud with Supabase → users persist forever
  - On local dev → users saved to data/users.json
  - Demo users (admin/compliance/auditor) always available as fallback
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.logging_config import get_logger

logger = get_logger("nexus.security.user_store")

DATA_DIR   = Path("data")
USERS_FILE = DATA_DIR / "users.json"


# ══════════════════════════════════════════════════════════════════════════════
# SMART ROUTER — Supabase first, local JSON fallback
# ══════════════════════════════════════════════════════════════════════════════

def _use_supabase() -> bool:
    """Return True if Supabase is configured and available."""
    try:
        from database.database_manager import is_configured
        return is_configured()
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════════════
# LOCAL JSON FILE (fallback)
# ══════════════════════════════════════════════════════════════════════════════

def _load_file() -> Dict[str, Any]:
    if not USERS_FILE.exists():
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.error("Failed to load users file: %s", exc)
        return {}


def _save_file(data: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as exc:
        logger.error("Failed to save users file: %s", exc)


# ══════════════════════════════════════════════════════════════════════════════
# LOAD ALL USERS
# ══════════════════════════════════════════════════════════════════════════════

def load_all_users() -> Dict[str, Any]:
    """
    Return all users: demo users + registered users.
    Registered users override demo users with same username.
    """
    from auth.roles import USERS_DB as DEMO_USERS
    merged = dict(DEMO_USERS)

    if _use_supabase():
        try:
            from database.database_manager import db_get_all_users
            db_users = db_get_all_users()
            # We need full user data including password_hash for login
            # So also fetch individually when logging in — see get_user()
            for u in db_users:
                uname = u.get("username")
                if uname:
                    merged[uname] = u
        except Exception as exc:
            logger.warning("Supabase load_all_users failed: %s", exc)
    else:
        registered = _load_file()
        merged.update(registered)

    return merged


def get_user(username: str) -> Optional[Dict[str, Any]]:
    """Get full user data including password_hash for login verification."""
    uname = username.strip().lower()

    # Try Supabase first — uses explicit select with password_hash
    if _use_supabase():
        try:
            from database.database_manager import db_get_user
            user = db_get_user(uname)
            if user:
                if not user.get("password_hash"):
                    logger.warning(
                        "User found in Supabase but no password_hash: %s", uname
                    )
                    return None
                return user
        except Exception as exc:
            logger.warning("Supabase get_user failed: %s", exc)

    # Try local file
    registered = _load_file()
    if uname in registered:
        return registered[uname]

    # Fall back to demo users
    from auth.roles import USERS_DB
    return USERS_DB.get(uname)


def user_exists(username: str) -> bool:
    uname = username.strip().lower()
    if _use_supabase():
        try:
            from database.database_manager import db_user_exists
            return db_user_exists(uname)
        except Exception:
            pass
    all_users = load_all_users()
    return uname in all_users


def email_exists(email: str) -> bool:
    if _use_supabase():
        try:
            from database.database_manager import db_email_exists
            return db_email_exists(email)
        except Exception:
            pass
    all_users = load_all_users()
    return any(
        u.get("email", "").lower() == email.strip().lower()
        for u in all_users.values()
    )


# ══════════════════════════════════════════════════════════════════════════════
# REGISTER
# ══════════════════════════════════════════════════════════════════════════════

def register_user(
    username: str,
    password_hash: str,
    full_name: str,
    email: str,
    role: str = "Compliance Officer",
    department: str = "General",
) -> tuple[bool, str]:
    """Register a new user — Supabase if available, else local JSON."""
    username = username.strip().lower()

    # Validation
    if not username:
        return False, "Username cannot be empty."
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if " " in username:
        return False, "Username cannot contain spaces."
    if user_exists(username):
        return False, f"Username '{username}' is already taken."
    if email_exists(email):
        return False, "This email address is already registered."

    # Try Supabase
    if _use_supabase():
        try:
            from database.database_manager import db_register_user
            return db_register_user(
                username=username,
                password_hash=password_hash,
                full_name=full_name,
                email=email,
                role=role,
                department=department,
            )
        except Exception as exc:
            logger.warning("Supabase register failed: %s — falling back to local.", exc)

    # Local JSON fallback
    parts  = full_name.strip().split()
    avatar = (parts[0][0] + parts[-1][0]).upper() if len(parts) >= 2 else full_name[:2].upper()

    permissions_map = {
        "Admin":              ["read", "write", "audit", "export", "admin"],
        "Developer":          ["read", "write", "audit", "export", "admin", "developer"],
        "Compliance Officer": ["read", "write", "audit", "export"],
        "Auditor":            ["read", "audit", "export"],
        "Viewer":             ["read"],
    }

    new_user = {
        "password_hash": password_hash,
        "role":          role,
        "name":          full_name.strip(),
        "email":         email.strip().lower(),
        "avatar":        avatar,
        "department":    department.strip() or "General",
        "registered_at": datetime.now().isoformat()[:19],
        "last_login":    "",
        "permissions":   permissions_map.get(role, ["read"]),
    }

    registered = _load_file()
    registered[username] = new_user
    _save_file(registered)

    logger.info("User registered locally: %s", username)
    return True, f"Account created successfully! Welcome, {full_name.strip()}."


# ══════════════════════════════════════════════════════════════════════════════
# UPDATE / DELETE
# ══════════════════════════════════════════════════════════════════════════════

def update_last_login(username: str) -> None:
    uname = username.strip().lower()
    if _use_supabase():
        try:
            from database.database_manager import db_update_last_login
            db_update_last_login(uname)
            return
        except Exception:
            pass
    # Local fallback
    registered = _load_file()
    if uname in registered:
        registered[uname]["last_login"] = datetime.now().isoformat()[:19]
        _save_file(registered)


def save_user(username: str, user_data: Dict[str, Any]) -> None:
    registered = _load_file()
    registered[username.strip().lower()] = user_data
    _save_file(registered)


def delete_user(username: str) -> bool:
    uname = username.strip().lower()
    registered = _load_file()
    if uname not in registered:
        return False
    del registered[uname]
    _save_file(registered)
    return True


def get_all_registered_users() -> List[Dict[str, Any]]:
    if _use_supabase():
        try:
            from database.database_manager import db_get_all_users
            return db_get_all_users()
        except Exception:
            pass
    registered = _load_file()
    return [
        {k: v for k, v in u.items() if k != "password_hash"} | {"username": uname}
        for uname, u in registered.items()
    ]