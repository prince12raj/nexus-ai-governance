"""
config/settings.py — Environment-driven settings for Nexus AI Governance Platform.

All values are read from .env via python-dotenv.
Access anywhere in the project:
    from config.settings import settings
    print(settings.OPENAI_API_KEY)

Never import os.getenv() directly in other modules — always use settings.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load .env from the project root (works from any working directory)
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=False)


class Settings:
    """
    Central configuration object for the entire Nexus platform.

    All attributes are read from environment variables.
    Defaults are provided for every setting so the app
    always starts — even with an empty .env file.

    Sections:
        1. OpenAI
        2. HuggingFace
        3. Ollama
        4. Application
        5. Vector Store / Database
        6. RAG
        7. Feature Flags
        8. Auth & Security
        9. File Upload
        10. Logging
    """

    # ── 1. OpenAI ─────────────────────────────────────────────────────────────
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL:   str = os.getenv("OPENAI_MODEL", "gpt-4o")
    OPENAI_ORG_ID:  str = os.getenv("OPENAI_ORG_ID", "")        # optional org ID

    # ── 2. HuggingFace ────────────────────────────────────────────────────────
    HUGGINGFACE_API_KEY:    str = os.getenv("HUGGINGFACE_API_KEY", "")
    HUGGINGFACE_MODEL:      str = os.getenv(
        "HUGGINGFACE_MODEL", "mistralai/Mistral-7B-Instruct-v0.2"
    )
    HUGGINGFACE_EMBED_MODEL: str = os.getenv(
        "HUGGINGFACE_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
    )

    # ── 3. Ollama ─────────────────────────────────────────────────────────────
    OLLAMA_HOST:        str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL:       str = os.getenv("OLLAMA_MODEL", "llama3")
    OLLAMA_EMBED_MODEL: str = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

    # ── 4. Application ────────────────────────────────────────────────────────
    APP_ENV:        str = os.getenv("APP_ENV", "development")   # development | staging | production
    APP_NAME:       str = os.getenv("APP_NAME", "Nexus AI Governance Platform")
    APP_VERSION:    str = os.getenv("APP_VERSION", "2.0.0")
    APP_SECRET_KEY: str = os.getenv("APP_SECRET_KEY", "nexus-secret-change-me")
    APP_HOST:       str = os.getenv("APP_HOST", "localhost")
    APP_PORT:       int = int(os.getenv("APP_PORT", "8501"))
    DEBUG:          bool = os.getenv("DEBUG", "false").lower() == "true"

    # ── 5. Vector Store / Database ────────────────────────────────────────────
    VECTOR_STORE_BACKEND: str = os.getenv(
        "VECTOR_STORE_BACKEND", "memory"
    )                                               # memory | faiss | chroma
    CHROMA_PERSIST_DIR:   str = os.getenv("CHROMA_PERSIST_DIR", "./data/vector_cache")
    FAISS_INDEX_PATH:     str = os.getenv("FAISS_INDEX_PATH", "./data/vector_cache/faiss.index")
    DATA_DIR:             str = os.getenv("DATA_DIR", "./data")

    # ── 6. RAG ────────────────────────────────────────────────────────────────
    RAG_CHUNK_SIZE:     int   = int(os.getenv("RAG_CHUNK_SIZE", "800"))
    RAG_CHUNK_OVERLAP:  int   = int(os.getenv("RAG_CHUNK_OVERLAP", "100"))
    RAG_TOP_K:          int   = int(os.getenv("RAG_TOP_K", "4"))
    RAG_MIN_CONFIDENCE: float = float(os.getenv("RAG_MIN_CONFIDENCE", "0.70"))

    # ── 7. Feature Flags ──────────────────────────────────────────────────────
    ENABLE_PII_DETECTION:       bool = os.getenv("ENABLE_PII_DETECTION",       "true").lower()  == "true"
    ENABLE_INJECTION_DETECTION: bool = os.getenv("ENABLE_INJECTION_DETECTION", "true").lower()  == "true"
    ENABLE_HUMAN_IN_LOOP:       bool = os.getenv("ENABLE_HUMAN_IN_LOOP",       "false").lower() == "true"
    ENABLE_AUDIT_LOGGING:       bool = os.getenv("ENABLE_AUDIT_LOGGING",       "true").lower()  == "true"
    ENABLE_STREAMING:           bool = os.getenv("ENABLE_STREAMING",           "true").lower()  == "true"
    ENABLE_RAG:                 bool = os.getenv("ENABLE_RAG",                 "true").lower()  == "true"

    # ── 8. Auth & Security ────────────────────────────────────────────────────
    SESSION_TIMEOUT_MINUTES: int  = int(os.getenv("SESSION_TIMEOUT_MINUTES", "60"))
    MAX_LOGIN_ATTEMPTS:      int  = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
    BCRYPT_ROUNDS:           int  = int(os.getenv("BCRYPT_ROUNDS", "12"))

    # ── 9. File Upload ────────────────────────────────────────────────────────
    MAX_FILE_SIZE_MB:    int  = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
    UPLOAD_DIR:          str  = os.getenv("UPLOAD_DIR", "./data/uploads")
    ALLOWED_EXTENSIONS:  str  = os.getenv(
        "ALLOWED_EXTENSIONS", ".pdf,.docx,.txt,.csv,.json"
    )

    # ── 10. Logging ───────────────────────────────────────────────────────────
    LOG_LEVEL:    str = os.getenv("LOG_LEVEL", "INFO")   # DEBUG | INFO | WARNING | ERROR
    LOG_DIR:      str = os.getenv("LOG_DIR", "./logs")
    LOG_TO_FILE:  bool = os.getenv("LOG_TO_FILE", "true").lower() == "true"

    # ── Derived helpers ───────────────────────────────────────────────────────

    @property
    def is_production(self) -> bool:
        """True when running in production mode."""
        return self.APP_ENV.lower() == "production"

    @property
    def is_development(self) -> bool:
        """True when running in development mode."""
        return self.APP_ENV.lower() == "development"

    @property
    def allowed_extensions_list(self) -> list[str]:
        """Return ALLOWED_EXTENSIONS as a Python list."""
        return [ext.strip() for ext in self.ALLOWED_EXTENSIONS.split(",")]

    @property
    def active_llm_provider(self) -> str:
        """
        Return the name of the active LLM provider based on what keys are set.
        Priority: openai → huggingface → ollama → mock
        """
        if self.OPENAI_API_KEY:
            return "openai"
        if self.HUGGINGFACE_API_KEY:
            return "huggingface"
        return "ollama"

    @property
    def openai_configured(self) -> bool:
        """True if OpenAI API key is set and non-empty."""
        return bool(self.OPENAI_API_KEY)

    @property
    def huggingface_configured(self) -> bool:
        """True if HuggingFace API key is set and non-empty."""
        return bool(self.HUGGINGFACE_API_KEY)

    def masked_key(self, key: str, show: int = 8) -> str:
        """
        Return a masked version of an API key for safe display in the UI.

        Example:
            settings.masked_key(settings.OPENAI_API_KEY)
            → "sk-proj-a••••••••"
        """
        if not key:
            return "not set"
        return key[:show] + "••••••••"

    def as_dict(self, mask_secrets: bool = True) -> dict:
        """
        Return all settings as a dictionary.

        Args:
            mask_secrets: If True, API keys and secret key are masked.
                          Set to False only in trusted internal contexts.

        Returns:
            Dict of all setting names and values.
        """
        raw = {
            # OpenAI
            "OPENAI_API_KEY":            self.OPENAI_API_KEY,
            "OPENAI_MODEL":              self.OPENAI_MODEL,
            "OPENAI_ORG_ID":             self.OPENAI_ORG_ID,
            # HuggingFace
            "HUGGINGFACE_API_KEY":       self.HUGGINGFACE_API_KEY,
            "HUGGINGFACE_MODEL":         self.HUGGINGFACE_MODEL,
            "HUGGINGFACE_EMBED_MODEL":   self.HUGGINGFACE_EMBED_MODEL,
            # Ollama
            "OLLAMA_HOST":               self.OLLAMA_HOST,
            "OLLAMA_MODEL":              self.OLLAMA_MODEL,
            "OLLAMA_EMBED_MODEL":        self.OLLAMA_EMBED_MODEL,
            # App
            "APP_ENV":                   self.APP_ENV,
            "APP_NAME":                  self.APP_NAME,
            "APP_VERSION":               self.APP_VERSION,
            "APP_SECRET_KEY":            self.APP_SECRET_KEY,
            "APP_HOST":                  self.APP_HOST,
            "APP_PORT":                  self.APP_PORT,
            "DEBUG":                     self.DEBUG,
            # Vector store
            "VECTOR_STORE_BACKEND":      self.VECTOR_STORE_BACKEND,
            "CHROMA_PERSIST_DIR":        self.CHROMA_PERSIST_DIR,
            "FAISS_INDEX_PATH":          self.FAISS_INDEX_PATH,
            "DATA_DIR":                  self.DATA_DIR,
            # RAG
            "RAG_CHUNK_SIZE":            self.RAG_CHUNK_SIZE,
            "RAG_CHUNK_OVERLAP":         self.RAG_CHUNK_OVERLAP,
            "RAG_TOP_K":                 self.RAG_TOP_K,
            "RAG_MIN_CONFIDENCE":        self.RAG_MIN_CONFIDENCE,
            # Feature flags
            "ENABLE_PII_DETECTION":      self.ENABLE_PII_DETECTION,
            "ENABLE_INJECTION_DETECTION":self.ENABLE_INJECTION_DETECTION,
            "ENABLE_HUMAN_IN_LOOP":      self.ENABLE_HUMAN_IN_LOOP,
            "ENABLE_AUDIT_LOGGING":      self.ENABLE_AUDIT_LOGGING,
            "ENABLE_STREAMING":          self.ENABLE_STREAMING,
            "ENABLE_RAG":                self.ENABLE_RAG,
            # Auth
            "SESSION_TIMEOUT_MINUTES":   self.SESSION_TIMEOUT_MINUTES,
            "MAX_LOGIN_ATTEMPTS":        self.MAX_LOGIN_ATTEMPTS,
            "BCRYPT_ROUNDS":             self.BCRYPT_ROUNDS,
            # Upload
            "MAX_FILE_SIZE_MB":          self.MAX_FILE_SIZE_MB,
            "UPLOAD_DIR":                self.UPLOAD_DIR,
            "ALLOWED_EXTENSIONS":        self.ALLOWED_EXTENSIONS,
            # Logging
            "LOG_LEVEL":                 self.LOG_LEVEL,
            "LOG_DIR":                   self.LOG_DIR,
            "LOG_TO_FILE":               self.LOG_TO_FILE,
        }

        if mask_secrets:
            raw["OPENAI_API_KEY"]      = self.masked_key(self.OPENAI_API_KEY)
            raw["HUGGINGFACE_API_KEY"] = self.masked_key(self.HUGGINGFACE_API_KEY)
            raw["APP_SECRET_KEY"]      = self.masked_key(self.APP_SECRET_KEY)

        return raw

    def validate(self) -> list[str]:
        """
        Validate settings and return a list of warning messages.

        Returns:
            List of warning strings. Empty list = all good.

        Used by app.py on startup to show config warnings in the UI.
        """
        warnings: list[str] = []

        if not self.OPENAI_API_KEY and not self.HUGGINGFACE_API_KEY:
            warnings.append(
                "⚠️ No LLM API key configured. "
                "Set OPENAI_API_KEY or HUGGINGFACE_API_KEY in .env, "
                "or run Ollama locally."
            )

        if self.APP_SECRET_KEY in ("nexus-secret-change-me", "change-me-in-production-use-32-char-random-string"):
            warnings.append(
                "⚠️ APP_SECRET_KEY is using the default value. "
                "Set a strong 32-character random secret in .env before deploying."
            )

        if self.VECTOR_STORE_BACKEND not in ("memory", "faiss", "chroma"):
            warnings.append(
                f"⚠️ Unknown VECTOR_STORE_BACKEND '{self.VECTOR_STORE_BACKEND}'. "
                "Valid options: memory | faiss | chroma."
            )

        if self.is_production and self.DEBUG:
            warnings.append(
                "⚠️ DEBUG=true in production mode. "
                "Set DEBUG=false in .env for production."
            )

        if self.is_production and not self.OPENAI_API_KEY:
            warnings.append(
                "⚠️ Running in production without OPENAI_API_KEY. "
                "Compliance audit quality will be limited."
            )

        if self.RAG_TOP_K < 1 or self.RAG_TOP_K > 20:
            warnings.append(
                f"⚠️ RAG_TOP_K={self.RAG_TOP_K} is outside recommended range (1–20)."
            )

        return warnings

    def __repr__(self) -> str:
        return (
            f"Settings(env={self.APP_ENV}, provider={self.active_llm_provider}, "
            f"vector_store={self.VECTOR_STORE_BACKEND}, "
            f"pii={self.ENABLE_PII_DETECTION}, rag={self.ENABLE_RAG})"
        )


# ── Singleton instance ────────────────────────────────────────────────────────
# Import this everywhere:  from config.settings import settings
settings = Settings()