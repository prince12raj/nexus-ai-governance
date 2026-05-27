"""
rag/embeddings.py — Embedding generation for Nexus AI Governance Platform.

Provides a unified embed() interface that routes to the active LLM provider:
    OpenAI      → text-embedding-3-small
    HuggingFace → sentence-transformers/all-MiniLM-L6-v2
    Ollama      → nomic-embed-text
    Local       → sentence-transformers (offline, no API key)

Usage:
    from rag.embeddings import embed, embed_single, get_embedder

    vectors = embed(["GDPR Article 5", "data retention policy"])
    vector  = embed_single("What is data minimisation?")
"""

from typing import List, Optional

from config.logging_config import get_logger
from config.settings import settings

logger = get_logger("nexus.rag.embeddings")


# ── Unified embed interface ───────────────────────────────────────────────────

def embed(
    texts: List[str],
    provider: Optional[str] = None,
) -> List[List[float]]:
    """
    Generate embeddings for a list of texts using the active provider.

    Args:
        texts:    List of strings to embed.
        provider: Force a provider: "openai"|"huggingface"|"ollama"|"local".
                  Auto-detected from .env if not specified.

    Returns:
        List of embedding vectors (list of floats), one per input text.
    """
    if not texts:
        return []

    p = provider or _detect_provider()
    logger.info("rag.embed | provider=%s | texts=%d", p, len(texts))

    if p == "openai":
        from llm.openai_provider import embed as oai_embed
        return oai_embed(texts)

    if p == "huggingface":
        from llm.huggingface_provider import embed as hf_embed
        return hf_embed(texts)

    if p == "ollama":
        from llm.ollama_provider import embed as ol_embed
        return ol_embed(texts)

    # Local sentence-transformers (offline fallback)
    return _embed_local(texts)


def embed_single(
    text: str,
    provider: Optional[str] = None,
) -> List[float]:
    """
    Embed a single string and return its vector.

    Args:
        text:     String to embed.
        provider: Force a provider (optional).

    Returns:
        Embedding vector as a list of floats.
    """
    results = embed([text], provider=provider)
    return results[0] if results else []


def embed_documents(
    docs: list,
    text_field: str = "text",
    provider: Optional[str] = None,
) -> list:
    """
    Add embedding vectors to a list of document dicts in-place.

    Args:
        docs:       List of document dicts (must have a text_field key).
        text_field: Key in each dict containing the text to embed.
        provider:   Force a provider (optional).

    Returns:
        Same docs list with "_embedding" key added to each dict.
    """
    if not docs:
        return docs

    texts   = [d.get(text_field, "") for d in docs]
    vectors = embed(texts, provider=provider)

    for doc, vec in zip(docs, vectors):
        doc["_embedding"] = vec

    logger.info("rag.embed_documents: embedded %d documents.", len(docs))
    return docs


# ── Local fallback (no API key needed) ───────────────────────────────────────

def _embed_local(texts: List[str], model_name: str = "all-MiniLM-L6-v2") -> List[List[float]]:
    """
    Generate embeddings locally using sentence-transformers.
    Used when no cloud provider is available.

    Requires: pip install sentence-transformers
    """
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
        model   = SentenceTransformer(model_name)
        vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return vectors.tolist()
    except ImportError:
        logger.warning(
            "sentence-transformers not installed — returning zero vectors. "
            "Run: pip install sentence-transformers"
        )
        return [[0.0] * 384 for _ in texts]
    except Exception as exc:
        logger.error("Local embedding failed: %s", exc)
        return [[0.0] * 384 for _ in texts]


# ── Provider detection ────────────────────────────────────────────────────────

def _detect_provider() -> str:
    """Detect the active embedding provider from settings."""
    if settings.OPENAI_API_KEY:
        return "openai"
    if settings.HUGGINGFACE_API_KEY:
        return "huggingface"
    try:
        from llm.ollama_provider import is_available
        if is_available():
            return "ollama"
    except Exception:
        pass
    return "local"


def get_embedder() -> str:
    """Return the name of the active embedding provider."""
    return _detect_provider()


def get_embedding_dim() -> int:
    """
    Return the embedding dimension for the active provider.
    Used when initialising FAISS indexes.
    """
    dims = {
        "openai":       1536,   # text-embedding-3-small
        "huggingface":  384,    # all-MiniLM-L6-v2
        "ollama":       768,    # nomic-embed-text
        "local":        384,    # all-MiniLM-L6-v2
    }
    return dims.get(_detect_provider(), 384)