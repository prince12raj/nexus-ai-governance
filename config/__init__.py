"""
config/__init__.py — Configuration package for Nexus AI Governance Platform.

NOTE: No side-effects at import time (no setup_logging, no debug calls).
      setup_logging() is called once in app.py main() instead.
      This prevents KeyError: 'config.settings' circular import crashes.
"""

# ── Core settings ─────────────────────────────────────────────────────────────
from config.settings import settings

# ── Logger factory ────────────────────────────────────────────────────────────
from config.logging_config import get_logger, setup_logging

# ── App identity ──────────────────────────────────────────────────────────────
from config.constants import (
    APP_NAME,
    APP_VERSION,
    APP_ICON,
)

# ── Compliance frameworks & severity ─────────────────────────────────────────
from config.constants import (
    SUPPORTED_FRAMEWORKS,
    SEVERITIES,
    SEVERITY_SCORES,
    SEVERITY_COLORS,
)

# ── LLM model lists ───────────────────────────────────────────────────────────
from config.constants import (
    OPENAI_MODELS,
    LOCAL_ENGINES,
    FALLBACK_MODELS,
)

# ── RAG / chunking defaults ───────────────────────────────────────────────────
from config.constants import (
    DEFAULT_CHUNK_SIZE,
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_TOP_K,
    DEFAULT_MIN_CONFIDENCE,
)

# ── File upload limits ────────────────────────────────────────────────────────
from config.constants import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE_MB,
)

# ── UI / navigation ───────────────────────────────────────────────────────────
from config.constants import (
    NAV_PAGES,
    PLOTLY_DARK,
)

# ── NOTE: setup_logging() is intentionally NOT called here.
# Call it once in app.py main() after all imports are complete:
#
#   from config import setup_logging, settings
#   setup_logging(level=settings.LOG_LEVEL)


# ── Provider detection helper ─────────────────────────────────────────────────
def _detect_provider() -> str:
    """Quick check of which LLM provider is active."""
    if settings.OPENAI_API_KEY:
        return "openai"
    if settings.HUGGINGFACE_API_KEY:
        return "huggingface"
    return "ollama/mock"


# ── Runtime config summary ────────────────────────────────────────────────────
def get_config_summary() -> dict:
    """Return current configuration summary for Admin Settings page."""
    return {
        "app_name":             APP_NAME,
        "app_version":          APP_VERSION,
        "app_env":              settings.APP_ENV,
        "log_level":            settings.LOG_LEVEL,
        "openai_key_set":       bool(settings.OPENAI_API_KEY),
        "openai_key_preview":   _mask(settings.OPENAI_API_KEY),
        "openai_model":         settings.OPENAI_MODEL,
        "hf_key_set":           bool(settings.HUGGINGFACE_API_KEY),
        "hf_key_preview":       _mask(settings.HUGGINGFACE_API_KEY),
        "ollama_host":          settings.OLLAMA_HOST,
        "ollama_model":         settings.OLLAMA_MODEL,
        "active_provider":      _detect_provider(),
        "vector_store_backend": settings.VECTOR_STORE_BACKEND,
        "chroma_persist_dir":   settings.CHROMA_PERSIST_DIR,
        "pii_detection":        settings.ENABLE_PII_DETECTION,
        "injection_detection":  settings.ENABLE_INJECTION_DETECTION,
        "human_in_loop":        settings.ENABLE_HUMAN_IN_LOOP,
        "supported_frameworks": SUPPORTED_FRAMEWORKS,
        "severity_levels":      SEVERITIES,
        "chunk_size":           DEFAULT_CHUNK_SIZE,
        "chunk_overlap":        DEFAULT_CHUNK_OVERLAP,
        "top_k":                DEFAULT_TOP_K,
        "min_confidence":       DEFAULT_MIN_CONFIDENCE,
        "allowed_extensions":   ALLOWED_EXTENSIONS,
        "max_file_size_mb":     MAX_FILE_SIZE_MB,
    }


def _mask(key: str, show: int = 8) -> str:
    """Mask an API key for safe display."""
    if not key:
        return "not set"
    return key[:show] + "••••••••"


def validate_config() -> list:
    """Check for missing or misconfigured settings. Returns list of warnings."""
    warnings = []

    if not settings.OPENAI_API_KEY and not settings.HUGGINGFACE_API_KEY:
        warnings.append(
            "No LLM API key set. Add OPENAI_API_KEY or HUGGINGFACE_API_KEY "
            "to your .env file, or start Ollama locally."
        )
    if settings.APP_SECRET_KEY in (
        "nexus-secret-change-me",
        "change-me-in-production-use-32-char-random-string",
        "nexus-change-this-to-a-strong-32-char-secret",
    ):
        warnings.append(
            "APP_SECRET_KEY is using the default value. "
            "Set a strong secret in your .env file before deploying."
        )
    if settings.VECTOR_STORE_BACKEND not in ("memory", "faiss", "chroma"):
        warnings.append(
            f"Unknown VECTOR_STORE_BACKEND '{settings.VECTOR_STORE_BACKEND}'. "
            "Valid options: memory, faiss, chroma."
        )
    return warnings


# ── Public API ────────────────────────────────────────────────────────────────
__all__ = [
    "settings",
    "get_logger",
    "APP_NAME", "APP_VERSION", "APP_ICON",
    "SUPPORTED_FRAMEWORKS", "SEVERITIES", "SEVERITY_SCORES", "SEVERITY_COLORS",
    "OPENAI_MODELS", "LOCAL_ENGINES", "FALLBACK_MODELS",
    "DEFAULT_CHUNK_SIZE", "DEFAULT_CHUNK_OVERLAP", "DEFAULT_TOP_K", "DEFAULT_MIN_CONFIDENCE",
    "ALLOWED_EXTENSIONS", "MAX_FILE_SIZE_MB",
    "NAV_PAGES", "PLOTLY_DARK",
    "get_config_summary", "validate_config",
]