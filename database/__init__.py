"""
database/__init__.py — Vector store factory for Nexus AI Governance Platform.

Auto-selects the correct backend based on VECTOR_STORE_BACKEND in .env:
    memory  → MemoryVectorStore  (default, no install needed)
    faiss   → FaissManager       (pip install faiss-cpu sentence-transformers)
    chroma  → ChromaManager      (pip install chromadb)

Usage anywhere in the project:
    from database import get_vector_store

    store   = get_vector_store()
    results = store.similarity_search("GDPR data retention", k=4)
    store.add_documents(docs)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from config.logging_config import get_logger
from config.settings import settings

logger = get_logger("nexus.database")

# Type alias for all three store types
VectorStore = Any


# ── Factory ───────────────────────────────────────────────────────────────────

_store_instance: Optional[VectorStore] = None


def get_vector_store(backend: str = "") -> VectorStore:
    """
    Return the active vector store instance based on .env settings.

    Args:
        backend: Override the backend: "memory" | "faiss" | "chroma".
                 Defaults to settings.VECTOR_STORE_BACKEND.

    Returns:
        One of: MemoryVectorStore | FaissManager | ChromaManager

    All three share the same interface:
        .similarity_search(query, k, framework_filter) → List[Dict]
        .add_documents(docs)                           → int
        .add_document(doc)                             → bool
        .get_by_id(doc_id)                             → Dict | None
        .get_all_by_framework(framework)               → List[Dict]
        .delete_document(doc_id)                       → bool
        .count()                                       → int
        .frameworks()                                  → List[str]
        .stats()                                       → Dict
        .clear()                                       → None
    """
    global _store_instance

    if _store_instance is not None:
        return _store_instance

    chosen = (backend or settings.VECTOR_STORE_BACKEND or "memory").lower()

    if chosen == "faiss":
        logger.info("VectorStore: using FAISS backend.")
        from database.faiss_manager import FaissManager
        _store_instance = FaissManager()

    elif chosen == "chroma":
        logger.info("VectorStore: using ChromaDB backend.")
        from database.chroma_manager import ChromaManager
        _store_instance = ChromaManager()

    else:
        if chosen not in ("memory", "mock"):
            logger.warning(
                "Unknown VECTOR_STORE_BACKEND '%s' — falling back to memory.", chosen
            )
        logger.info("VectorStore: using in-memory backend.")
        from database.memory_store import MemoryVectorStore
        _store_instance = MemoryVectorStore(preload=True)

    return _store_instance


def reset_vector_store() -> None:
    """
    Clear the cached store instance so the next call to get_vector_store()
    creates a fresh one. Useful for testing.
    """
    global _store_instance
    _store_instance = None
    logger.info("VectorStore: singleton reset.")


# ── Named exports ─────────────────────────────────────────────────────────────
from database.memory_store import MemoryVectorStore, get_memory_store
from database.faiss_manager import FaissManager
from database.chroma_manager import ChromaManager

__all__ = [
    "get_vector_store",
    "reset_vector_store",
    "MemoryVectorStore",
    "FaissManager",
    "ChromaManager",
    "get_memory_store",
]