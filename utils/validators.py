"""
utils/validators.py — Input validation helpers.
"""
import re
from pathlib import Path

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".csv", ".json"}


def is_valid_email(email: str) -> bool:
    return bool(re.match(r'^[^@]+@[^@]+\.[^@]+$', email))


def is_allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def is_valid_api_key(key: str) -> bool:
    return key.startswith("sk-") and len(key) > 20


def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))
