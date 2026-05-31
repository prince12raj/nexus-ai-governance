"""
config/__init__.py — Configuration package for Nexus AI Governance Platform.

This file is the single import point for all config across the project.
Every module imports from here instead of from individual config files.

Usage anywhere in the project:
    from config import settings, APP_NAME, APP_VERSION, get_logger
    from config import SUPPORTED_FRAMEWORKS, SEVERITY_COLORS, PLOTLY_DARK
    from config import OPENAI_MODELS, DEFAULT_CHUNK_SIZE, ALLOWED_EXTENSIONS
"""

# ── Core settings (env-driven) ────────────────────────────────────────────────
from config.settings import settings

# ── Logger factory ────────────────────────────────────────────────────────────
from config.logging_config import get_logger

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

# ── Initialise logging immediately on import ──────────────────────────────────
from config.logging_config import setup_logging
setup_logging(level=settings.LOG_LEVEL)

_logger = get_logger("nexus.config")
_logger.debug(
    "Config loaded | app=%s v%s | env=%s | llm_provider=%s",
    APP_NAME,
    APP_VERSION,
    settings.APP_ENV,
    _detect_provider(),
)


# ── Provider detection helper (used for startup log) ─────────────────────────
def _detect_provider() -> str:
    """Quick check of which LLM provider is active — used only for startup logging."""
    if settings.OPENAI_API_KEY:
        return "openai"
    if settings.HUGGINGFACE_API_KEY:
        return "huggingface"
    return "ollama/mock"


# ── Runtime config summary (useful for Admin Settings page) ──────────────────
def get_config_summary() -> dict:
    """
    Return a human-readable summary of current configuration.

    Used by ui/admin_settings.py to display the system status panel.

    Returns:
        Dict with all key config values (API keys masked).
    """
    return {
        # App
        "app_name":             APP_NAME,
        "app_version":          APP_VERSION,
        "app_env":              settings.APP_ENV,
        "log_level":            settings.LOG_LEVEL,

        # LLM
        "openai_key_set":       bool(settings.OPENAI_API_KEY),
        "openai_key_preview":   _mask(settings.OPENAI_API_KEY),
        "openai_model":         settings.OPENAI_MODEL,
        "hf_key_set":           bool(settings.HUGGINGFACE_API_KEY),
        "hf_key_preview":       _mask(settings.HUGGINGFACE_API_KEY),
        "ollama_host":          settings.OLLAMA_HOST,
        "ollama_model":         settings.OLLAMA_MODEL,
        "active_provider":      _detect_provider(),

        # Vector store
        "vector_store_backend": settings.VECTOR_STORE_BACKEND,
        "chroma_persist_dir":   settings.CHROMA_PERSIST_DIR,

        # Feature flags
        "pii_detection":        settings.ENABLE_PII_DETECTION,
        "injection_detection":  settings.ENABLE_INJECTION_DETECTION,
        "human_in_loop":        settings.ENABLE_HUMAN_IN_LOOP,

        # Compliance
        "supported_frameworks": SUPPORTED_FRAMEWORKS,
        "severity_levels":      SEVERITIES,

        # RAG
        "chunk_size":           DEFAULT_CHUNK_SIZE,
        "chunk_overlap":        DEFAULT_CHUNK_OVERLAP,
        "top_k":                DEFAULT_TOP_K,
        "min_confidence":       DEFAULT_MIN_CONFIDENCE,

        # Upload
        "allowed_extensions":   ALLOWED_EXTENSIONS,
        "max_file_size_mb":     MAX_FILE_SIZE_MB,
    }


def _mask(key: str, show: int = 8) -> str:
    """Mask an API key for safe display — shows first N chars only."""
    if not key:
        return "not set"
    return key[:show] + "••••••••"


# ── Validate critical settings on startup ────────────────────────────────────
def validate_config() -> list[str]:
    """
    Check for missing or misconfigured settings.

    Returns:
        List of warning strings. Empty list means all good.

    Used by app.py on startup to show configuration warnings in the UI.
    """
    warnings: list[str] = []

    if not settings.OPENAI_API_KEY and not settings.HUGGINGFACE_API_KEY:
        warnings.append(
            "No LLM API key set. Add OPENAI_API_KEY or HUGGINGFACE_API_KEY "
            "to your .env file, or start Ollama locally."
        )

    if settings.APP_SECRET_KEY == "nexus-secret-change-me":
        warnings.append(
            "APP_SECRET_KEY is using the default value. "
            "Set a strong secret in your .env file before deploying."
        )

    if settings.VECTOR_STORE_BACKEND not in ("memory", "faiss", "chroma"):
        warnings.append(
            f"Unknown VECTOR_STORE_BACKEND '{settings.VECTOR_STORE_BACKEND}'. "
            "Valid options: memory, faiss, chroma."
        )

    if settings.APP_ENV == "production" and not settings.OPENAI_API_KEY:
        warnings.append(
            "Running in production mode without OPENAI_API_KEY. "
            "Compliance analysis quality will be limited."
        )

    return warnings


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Settings instance
    "settings",

    # Logger
    "get_logger",

    # App identity
    "APP_NAME",
    "APP_VERSION",
    "APP_ICON",

    # Compliance
    "SUPPORTED_FRAMEWORKS",
    "SEVERITIES",
    "SEVERITY_SCORES",
    "SEVERITY_COLORS",

    # LLM
    "OPENAI_MODELS",
    "LOCAL_ENGINES",
    "FALLBACK_MODELS",

    # RAG
    "DEFAULT_CHUNK_SIZE",
    "DEFAULT_CHUNK_OVERLAP",
    "DEFAULT_TOP_K",
    "DEFAULT_MIN_CONFIDENCE",

    # File upload
    "ALLOWED_EXTENSIONS",
    "MAX_FILE_SIZE_MB",

    # UI
    "NAV_PAGES",
    "PLOTLY_DARK",

    # Utilities
    "get_config_summary",
    "validate_config",
]