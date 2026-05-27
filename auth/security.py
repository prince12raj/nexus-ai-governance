"""
auth/security.py — Password hashing and token utilities for Nexus AI Governance Platform.

Uses SHA-256 for demo simplicity.
In production swap hash_password/verify_password for bcrypt:
    pip install bcrypt
    hash_password   = lambda p: bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
    verify_password = lambda p, h: bcrypt.checkpw(p.encode(), h.encode())
"""

import hashlib
import hmac
import secrets
import time
from typing import Optional


def hash_password(password: str) -> str:
    """Return SHA-256 hash of password. Replace with bcrypt in production."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """Constant-time comparison to prevent timing attacks."""
    return hmac.compare_digest(
        hash_password(password),
        password_hash,
    )


def generate_token(length: int = 32) -> str:
    """Generate a cryptographically secure random hex token."""
    return secrets.token_hex(length)


def generate_session_id() -> str:
    """Generate a unique session identifier."""
    return secrets.token_urlsafe(32)


def is_strong_password(password: str) -> tuple[bool, str]:
    """
    Validate password strength.

    Returns:
        (is_valid: bool, message: str)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter."
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter."
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit."
    if not any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in password):
        return False, "Password must contain at least one special character."
    return True, "Password meets requirements."


def generate_api_key(prefix: str = "nxs") -> str:
    """Generate a prefixed API key for programmatic access."""
    return f"{prefix}_{secrets.token_urlsafe(32)}"