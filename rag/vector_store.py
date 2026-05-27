"""
rag/vector_store.py — RAG vector store interface for Nexus AI Governance Platform.

Thin wrapper around database/ backends that adds:
  - Document ingestion pipeline (chunk → embed → store)
  - Seeding from REGULATIONS_CORPUS on first run
  - Streamlit session_state caching
  - Unified search across all backends

Usage:
    from rag.vector_store import get_store, ingest_document, search

    store   = get_store()
    results = search("GDPR data retention", framework="GDPR", k=4)
    ingest_document(text, source="policy.pdf", framework="GDPR")
"""

from typing import Any, Dict, List, Optional

from config.logging_config import get_logger
from config.settings import settings

logger = get_logger("nexus.rag.vector_store")


# ── Store accessor ────────────────────────────────────────────────────────────

def get_store() -> Any:
    """
    Return the active vector store based on VECTOR_STORE_BACKEND in .env.

    Seeded with REGULATIONS_CORPUS on first call if store is empty.

    Returns:
        MemoryVectorStore | FaissManager | ChromaManager
    """
    from database import get_vector_store
    store = get_vector_store()

    # Seed on first use if empty
    if store.count() == 0:
        logger.info("Vector store is empty — seeding regulations corpus.")
        _seed_regulations(store)

    return store


def _seed_regulations(store: Any) -> None:
    """Load REGULATIONS_CORPUS into the vector store."""
    from rag.regulations_seed import REGULATIONS_CORPUS
    added = store.add_documents(REGULATIONS_CORPUS)
    logger.info("Seeded %d regulations into vector store.", added)


# ── Ingest pipeline ───────────────────────────────────────────────────────────

def ingest_document(
    text: str,
    source: str = "uploaded_document",
    framework: str = "GDPR",
    strategy: str = "auto",
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> int:
    """
    Full ingestion pipeline: chunk → create doc dicts → add to store.

    Args:
        text:           Raw document text.
        source:         Document name (e.g. "privacy_policy.pdf").
        framework:      Compliance framework label.
        strategy:       Chunking strategy ("auto"|"fixed"|"paragraphs"|"sentences"|"sections").
        extra_metadata: Additional fields to attach to each chunk.

    Returns:
        Number of chunks added to the store.
    """
    from rag.chunking import chunk_with_metadata

    if not text or not text.strip():
        logger.warning("ingest_document: empty text provided for source='%s'.", source)
        return 0

    docs  = chunk_with_metadata(
        text=text,
        source=source,
        framework=framework,
        strategy=strategy,
        extra_metadata=extra_metadata,
    )
    if not docs:
        return 0

    store = get_store()
    added = store.add_documents(docs)

    logger.info(
        "ingest_document: source='%s' | framework=%s | chunks=%d | added=%d",
        source, framework, len(docs), added
    )
    return added


# ── Search ────────────────────────────────────────────────────────────────────

def search(
    query: str,
    framework: Optional[str] = None,
    k: int = 4,
    min_score: float = 0.0,
) -> List[Dict[str, Any]]:
    """
    Search the vector store for documents relevant to a query.

    Args:
        query:     Search query string.
        framework: Optional framework filter (e.g. "GDPR").
        k:         Number of results to return.
        min_score: Minimum relevance score (0.0 = return anything).

    Returns:
        List of matching document dicts with "_score" field.
    """
    store   = get_store()
    results = store.similarity_search(
        query=query,
        k=k,
        framework_filter=framework,
        min_score=min_score,
    )
    logger.debug("rag.search: query='%s' framework=%s → %d results", query[:60], framework, len(results))
    return results


def search_for_compliance(
    policy_text: str,
    framework: str,
    k: int = 4,
) -> List[Dict[str, Any]]:
    """
    Retrieve the most relevant regulations for a compliance audit.

    Builds a concise query from the policy text and searches for
    matching regulations in the specified framework.

    Args:
        policy_text: Policy document text (first 500 chars used as query).
        framework:   Compliance framework to filter by.
        k:           Number of regulation chunks to retrieve.

    Returns:
        List of regulation dicts for injection into the LLM prompt.
    """
    # Use first 500 chars as query — captures the topic of the policy
    query = f"{framework} compliance requirements {policy_text[:300]}"
    return search(query=query, framework=framework, k=k)


# ── Store management ──────────────────────────────────────────────────────────

def get_store_stats() -> Dict[str, Any]:
    """Return statistics about the current vector store."""
    store = get_store()
    return store.stats()


def clear_user_documents(source_prefix: str = "uploaded") -> int:
    """
    Remove all user-uploaded documents from the store (keeps regulations corpus).

    Args:
        source_prefix: Documents whose source starts with this prefix are removed.

    Returns:
        Number of documents removed.
    """
    store  = get_store()
    all_docs = store.get_all() if hasattr(store, "get_all") else []
    removed  = 0

    for doc in all_docs:
        if doc.get("source", "").startswith(source_prefix):
            if store.delete_document(doc["id"]):
                removed += 1

    logger.info("clear_user_documents: removed %d docs with prefix='%s'.", removed, source_prefix)
    return removed


def reset_to_corpus() -> None:
    """
    Clear everything and re-seed from REGULATIONS_CORPUS.
    Used by Admin Settings → Reset Knowledge Base.
    """
    store = get_store()
    store.clear()
    _seed_regulations(store)
    logger.info("Vector store reset to regulations corpus.")