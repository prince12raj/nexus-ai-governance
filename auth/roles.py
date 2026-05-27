"""
auth/roles.py — User database and role/permission definitions for Nexus AI Governance Platform.

In production replace USERS_DB with a real database (PostgreSQL, MongoDB, etc.)
and use bcrypt for password hashing.
"""

import hashlib
from typing import Any, Dict, List


def _hash(password: str) -> str:
    """SHA-256 hash. Replace with bcrypt in production."""
    return hashlib.sha256(password.encode()).hexdigest()


# ── Demo user database ────────────────────────────────────────────────────────
USERS_DB: Dict[str, Dict[str, Any]] = {
    "admin": {
        "password_hash": _hash("Admin@2024!"),
        "role":          "Admin",
        "name":          "Alexandra Chen",
        "email":         "admin@nexus-ai.enterprise",
        "avatar":        "AC",
        "department":    "AI Governance",
        "last_login":    "2024-01-15 09:32:14",
        "permissions":   ["read", "write", "audit", "export", "admin"],
    },
    "compliance": {
        "password_hash": _hash("Comply@2024!"),
        "role":          "Compliance Officer",
        "name":          "Marcus Williams",
        "email":         "compliance@nexus-ai.enterprise",
        "avatar":        "MW",
        "department":    "Legal & Compliance",
        "last_login":    "2024-01-15 08:15:42",
        "permissions":   ["read", "write", "audit", "export"],
    },
    "auditor": {
        "password_hash": _hash("Audit@2024!"),
        "role":          "Auditor",
        "name":          "Priya Sharma",
        "email":         "auditor@nexus-ai.enterprise",
        "avatar":        "PS",
        "department":    "Internal Audit",
        "last_login":    "2024-01-14 16:55:30",
        "permissions":   ["read", "audit", "export"],
    },
    "viewer": {
        "password_hash": _hash("View@2024!"),
        "role":          "Viewer",
        "name":          "James Mitchell",
        "email":         "viewer@nexus-ai.enterprise",
        "avatar":        "JM",
        "department":    "Operations",
        "last_login":    "2024-01-14 10:00:00",
        "permissions":   ["read"],
    },
}

# ── Role → allowed pages ──────────────────────────────────────────────────────
ROLE_PERMISSIONS: Dict[str, List[str]] = {
    "Admin": [
        "Dashboard", "Policy Upload", "Compliance Auditor",
        "Agentic Risk", "Knowledge Base", "Audit Reports",
        "Analytics", "Admin Settings",
    ],
    "Developer": [
        "Dashboard", "Policy Upload", "Compliance Auditor",
        "Agentic Risk", "Knowledge Base", "Audit Reports",
        "Analytics", "Admin Settings",
    ],
    "Compliance Officer": [
        "Dashboard", "Policy Upload", "Compliance Auditor",
        "Agentic Risk", "Knowledge Base", "Audit Reports", "Analytics",
    ],
    "Auditor": [
        "Dashboard", "Compliance Auditor",
        "Knowledge Base", "Audit Reports", "Analytics",
    ],
    "Viewer": [
        "Dashboard", "Knowledge Base", "Audit Reports",
    ],
}


def has_permission(role: str, page: str) -> bool:
    """Return True if the given role has access to the given page."""
    return page in ROLE_PERMISSIONS.get(role, [])


def get_all_users() -> List[Dict[str, Any]]:
    """Return all users as a list of safe dicts (no password hashes)."""
    return [
        {k: v for k, v in user.items() if k != "password_hash"}
        | {"username": username}
        for username, user in USERS_DB.items()
    ]