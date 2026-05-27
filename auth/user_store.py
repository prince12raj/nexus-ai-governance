"""
auth/user_store.py — Persistent JSON file user database for Nexus AI Governance Platform.

Stores registered users in data/users.json so they persist across app restarts.
Falls back to in-memory USERS_DB (demo users) if the file is missing.

Usage:
    from auth.user_store import (
        register_user, user_exists, get_user,
        load_all_users, save_user, delete_user,
    )
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.logging_config import get_logger

logger = get_logger("nexus.security.user_store")

# ── Storage path ──────────────────────────────────────────────────────────────
DATA_DIR   = Path("data")
USERS_FILE = DATA_DIR / "users.json"


# ══════════════════════════════════════════════════════════════════════════════
# FILE I/O
# ══════════════════════════════════════════════════════════════════════════════

def _load_file() -> Dict[str, Any]:
    """Load users from the JSON file. Returns empty dict if file missing."""
    if not USERS_FILE.exists():
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Failed to load users file: %s", exc)
        return {}


def _save_file(data: Dict[str, Any]) -> None:
    """Save users dict to the JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError as exc:
        logger.error("Failed to save users file: %s", exc)


# ══════════════════════════════════════════════════════════════════════════════
# LOAD ALL USERS (file + demo fallback)
# ══════════════════════════════════════════════════════════════════════════════

def load_all_users() -> Dict[str, Any]:
    """
    Return merged dict of all users:
      - Registered users from data/users.json
      - Demo users from auth/roles.py USERS_DB (always available)

    Registered users take priority over demo users with the same username.
    """
    from auth.roles import USERS_DB as DEMO_USERS
    registered = _load_file()
    # Merge: demo first, then registered (registered wins on conflict)
    merged = dict(DEMO_USERS)
    merged.update(registered)
    return merged


# ══════════════════════════════════════════════════════════════════════════════
# CRUD
# ══════════════════════════════════════════════════════════════════════════════

def user_exists(username: str) -> bool:
    """Return True if a user with this username already exists."""
    all_users = load_all_users()
    return username.strip().lower() in all_users


def email_exists(email: str) -> bool:
    """Return True if this email is already registered."""
    all_users = load_all_users()
    return any(
        u.get("email", "").lower() == email.strip().lower()
        for u in all_users.values()
    )


def get_user(username: str) -> Optional[Dict[str, Any]]:
    """Return the user dict for a given username, or None if not found."""
    return load_all_users().get(username.strip().lower())


def register_user(
    username: str,
    password_hash: str,
    full_name: str,
    email: str,
    role: str = "Compliance Officer",
    department: str = "General",
) -> tuple[bool, str]:
    """
    Register a new user and persist to data/users.json.

    Args:
        username:      Desired username (lowercase, no spaces).
        password_hash: Pre-hashed password from security.hash_password().
        full_name:     User's display name.
        email:         User's email address.
        role:          Role assigned on registration.
        department:    Department name.

    Returns:
        (success: bool, message: str)
    """
    username = username.strip().lower()

    # Validation
    if not username:
        return False, "Username cannot be empty."
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if " " in username:
        return False, "Username cannot contain spaces."
    if user_exists(username):
        return False, f"Username '{username}' is already taken. Please choose another."
    if email_exists(email):
        return False, "This email address is already registered."

    # Build avatar from initials
    parts  = full_name.strip().split()
    avatar = (parts[0][0] + parts[-1][0]).upper() if len(parts) >= 2 else full_name[:2].upper()

    # Build permission list based on role
    from auth.roles import ROLE_PERMISSIONS
    role_permissions_map = {
        "Admin":              ["read", "write", "audit", "export", "admin"],
        "Developer":          ["read", "write", "audit", "export", "admin", "developer"],
        "Compliance Officer": ["read", "write", "audit", "export"],
        "Auditor":            ["read", "audit", "export"],
        "Viewer":             ["read"],
    }

    import datetime
    new_user = {
        "password_hash": password_hash,
        "role":          role,
        "name":          full_name.strip(),
        "email":         email.strip().lower(),
        "avatar":        avatar,
        "department":    department.strip() or "General",
        "registered_at": datetime.datetime.now().isoformat()[:19],
        "last_login":    "",
        "permissions":   role_permissions_map.get(role, ["read"]),
    }

    # Load existing registered users and append
    registered = _load_file()
    registered[username] = new_user
    _save_file(registered)

    logger.info(
        "New user registered | username=%s | role=%s | email=%s",
        username, role, email,
    )
    return True, f"Account created successfully! Welcome, {full_name.strip()}."


def save_user(username: str, user_data: Dict[str, Any]) -> None:
    """Update an existing user's data in the persistent store."""
    registered = _load_file()
    registered[username.strip().lower()] = user_data
    _save_file(registered)
    logger.info("User updated | username=%s", username)


def delete_user(username: str) -> bool:
    """
    Delete a registered user. Cannot delete demo users.

    Returns:
        True if deleted, False if not found in registered users.
    """
    registered = _load_file()
    uname      = username.strip().lower()
    if uname not in registered:
        return False
    del registered[uname]
    _save_file(registered)
    logger.info("User deleted | username=%s", username)
    return True


def get_all_registered_users() -> List[Dict[str, Any]]:
    """Return all registered users (from file) as safe dicts without password hashes."""
    registered = _load_file()
    return [
        {k: v for k, v in u.items() if k != "password_hash"} | {"username": uname}
        for uname, u in registered.items()
    ]


def update_last_login(username: str) -> None:
    """Update the last_login timestamp for a user (registered users only)."""
    import datetime
    registered = _load_file()
    uname      = username.strip().lower()
    if uname in registered:
        registered[uname]["last_login"] = datetime.datetime.now().isoformat()[:19]
        _save_file(registered)