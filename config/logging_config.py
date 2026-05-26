"""
config/logging_config.py — Centralised logging for Nexus AI Governance Platform.

Log files created:
    logs/app.log        — all application logs
    logs/security.log   — login, auth, access events  (nexus.security)
    logs/compliance.log — audit runs, findings         (nexus.compliance)
    logs/llm.log        — every LLM call               (nexus.llm)
    logs/rag.log        — vector store / retrieval     (nexus.rag)

Usage anywhere in the project:
    from config.logging_config import get_logger
    logger = get_logger("nexus.compliance")
    logger.info("Audit started | framework=%s", framework)
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path


# ── Log directory ─────────────────────────────────────────────────────────────
LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ── Format ────────────────────────────────────────────────────────────────────
_FMT     = "%(asctime)s [%(levelname)-8s] %(name)s — %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"

# ── Dedicated log files per subsystem ────────────────────────────────────────
_SUBSYSTEM_LOGS = {
    "nexus.security":   LOG_DIR / "security.log",
    "nexus.compliance": LOG_DIR / "compliance.log",
    "nexus.llm":        LOG_DIR / "llm.log",
    "nexus.rag":        LOG_DIR / "rag.log",
}

_setup_done = False


def setup_logging(level: str = "INFO") -> None:
    """
    Initialise the root logger and all subsystem loggers.

    Safe to call multiple times — only runs once.

    Args:
        level: Log level string: DEBUG | INFO | WARNING | ERROR | CRITICAL
    """
    global _setup_done
    if _setup_done:
        return
    _setup_done = True

    numeric = getattr(logging, level.upper(), logging.INFO)
    formatter = logging.Formatter(_FMT, datefmt=_DATEFMT)

    # ── Root / app logger ─────────────────────────────────────────────────────
    root = logging.getLogger()
    root.setLevel(numeric)

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(numeric)
    console.setFormatter(formatter)

    # Main app.log handler
    app_fh = logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8")
    app_fh.setLevel(numeric)
    app_fh.setFormatter(formatter)

    # Avoid duplicate handlers if called again
    if not root.handlers:
        root.addHandler(console)
        root.addHandler(app_fh)

    # ── Subsystem dedicated log files ─────────────────────────────────────────
    for logger_name, log_file in _SUBSYSTEM_LOGS.items():
        lg = logging.getLogger(logger_name)
        # Only add handler if not already present
        if not any(isinstance(h, logging.FileHandler) and
                   getattr(h, "baseFilename", "") == str(log_file.resolve())
                   for h in lg.handlers):
            fh = logging.FileHandler(log_file, encoding="utf-8")
            fh.setLevel(numeric)
            fh.setFormatter(formatter)
            lg.addHandler(fh)
        lg.propagate = True

    # ── Silence noisy third-party libraries ───────────────────────────────────
    for noisy in ("httpx", "httpcore", "openai", "chromadb", "faiss"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger.

    Args:
        name: Logger name, e.g. "nexus.llm.openai_provider"

    Returns:
        logging.Logger instance.

    Convention:
        nexus.llm.*        — LLM provider calls
        nexus.compliance.* — Audit engine events
        nexus.rag.*        — RAG / vector store events
        nexus.security.*   — Auth / login / access events
        nexus.database.*   — DB operations
        nexus.agents.*     — Agent workflow events
        nexus.ui.*         — Streamlit page events
    """
    return logging.getLogger(name)


def get_security_logger() -> logging.Logger:
    """Shortcut for the security logger — logs to security.log."""
    return logging.getLogger("nexus.security")


def get_compliance_logger() -> logging.Logger:
    """Shortcut for the compliance logger — logs to compliance.log."""
    return logging.getLogger("nexus.compliance")


def get_llm_logger() -> logging.Logger:
    """Shortcut for the LLM logger — logs to llm.log."""
    return logging.getLogger("nexus.llm")


def get_rag_logger() -> logging.Logger:
    """Shortcut for the RAG logger — logs to rag.log."""
    return logging.getLogger("nexus.rag")


# ── Auto-setup on import ──────────────────────────────────────────────────────
# Called here with default level; config/__init__.py calls it again with
# the level from settings.LOG_LEVEL once settings are loaded.
setup_logging()