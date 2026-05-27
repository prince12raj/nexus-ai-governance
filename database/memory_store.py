"""
database/memory_store.py — In-memory vector store for Nexus AI Governance Platform.

No dependencies required — works out of the box.
Used as the default backend (VECTOR_STORE_BACKEND=memory in .env).

Features:
  - Keyword + TF-IDF style scoring for semantic-like retrieval
  - Framework filtering
  - Full CRUD (add, update, delete)
  - Pre-loaded with REGULATIONS_CORPUS on startup
  - Singleton pattern for Streamlit session reuse

Switch to FAISS or ChromaDB for production by changing .env:
    VECTOR_STORE_BACKEND=faiss    → uses FaissManager
    VECTOR_STORE_BACKEND=chroma   → uses ChromaManager
    VECTOR_STORE_BACKEND=memory   → uses this file (default)
"""

import math
import re
from collections import Counter
from typing import Any, Dict, List, Optional

from config.logging_config import get_logger
from rag.regulations_seed import REGULATIONS_CORPUS

logger = get_logger("nexus.database.memory")


class MemoryVectorStore:
    """
    In-memory keyword-scored document store.

    Scoring algorithm:
      - TF-IDF style word matching across title, text, tags, framework
      - Title matches weighted 3x, tag matches 2x, text matches 1x
      - Stopwords filtered out
      - Results sorted by score descending

    Good enough for development and demos.
    For production semantic search use FaissManager or ChromaManager.
    """

    # Common English stopwords to ignore during scoring
    STOPWORDS = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
        "for", "of", "with", "by", "from", "as", "is", "are", "was",
        "were", "be", "been", "being", "have", "has", "had", "do", "does",
        "did", "will", "would", "shall", "should", "may", "might", "must",
        "can", "could", "not", "no", "nor", "so", "yet", "both", "either",
        "that", "this", "these", "those", "it", "its", "their", "they",
        "data", "shall", "must", "all", "any", "each", "every", "more",
    }

    def __init__(self, preload: bool = True) -> None:
        """
        Initialise the in-memory store.

        Args:
            preload: If True, load REGULATIONS_CORPUS on startup.
        """
        self._docs: List[Dict[str, Any]] = []

        if preload:
            self._docs = [dict(d) for d in REGULATIONS_CORPUS]
            logger.info(
                "MemoryVectorStore initialised | docs=%d | frameworks=%s",
                len(self._docs), self.frameworks()
            )
        else:
            logger.info("MemoryVectorStore initialised (empty).")

    # ── Add ───────────────────────────────────────────────────────────────────

    def add_documents(self, docs: List[Dict[str, Any]]) -> int:
        """
        Add a list of documents to the store.

        Skips duplicates by ID.

        Args:
            docs: List of document dicts with at least:
                  { "id": str, "text": str, "title": str, "framework": str }

        Returns:
            Number of documents actually added.
        """
        existing_ids = {d["id"] for d in self._docs}
        new_docs     = [d for d in docs if d.get("id") not in existing_ids]

        for doc in new_docs:
            self._docs.append(dict(doc))

        if new_docs:
            logger.info(
                "MemoryVectorStore: added %d docs (skipped %d duplicates).",
                len(new_docs), len(docs) - len(new_docs)
            )
        return len(new_docs)

    def add_document(self, doc: Dict[str, Any]) -> bool:
        """Add a single document. Returns True if added, False if duplicate."""
        return self.add_documents([doc]) == 1

    # ── Search ────────────────────────────────────────────────────────────────

    def similarity_search(
        self,
        query: str,
        k: int = 4,
        framework_filter: Optional[str] = None,
        min_score: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        Search for documents matching the query using keyword scoring.

        Args:
            query:            Search query string.
            k:                Number of results to return.
            framework_filter: If set, only return docs matching this framework.
            min_score:        Minimum score threshold (0.0 = return anything).

        Returns:
            List of matching document dicts, each with a "_score" field added.
        """
        query_words = self._tokenise(query)

        if not query_words:
            # No meaningful words — return top-k for the framework
            pool = [
                d for d in self._docs
                if not framework_filter or d.get("framework") == framework_filter
            ]
            return [dict(d) for d in pool[:k]]

        scored: List[tuple[float, Dict[str, Any]]] = []

        for doc in self._docs:
            if framework_filter and doc.get("framework") != framework_filter:
                continue

            score = self._score(query_words, doc)
            if score >= min_score:
                scored.append((score, doc))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, doc in scored[:k]:
            d           = dict(doc)
            d["_score"] = round(score, 4)
            results.append(d)

        # If nothing scored above 0, return top-k anyway (fallback)
        if not results and not min_score:
            pool = [
                d for d in self._docs
                if not framework_filter or d.get("framework") == framework_filter
            ]
            results = [dict(d) for d in pool[:k]]

        logger.debug(
            "MemoryVectorStore.search: query='%s' → %d results",
            query[:60], len(results)
        )
        return results

    def _tokenise(self, text: str) -> List[str]:
        """Lowercase, split, remove stopwords and short tokens."""
        words = re.findall(r"[a-zA-Z0-9]+", text.lower())
        return [w for w in words if len(w) > 2 and w not in self.STOPWORDS]

    def _score(self, query_words: List[str], doc: Dict[str, Any]) -> float:
        """
        Score a document against query words.

        Weights:
          title match  → 3.0 per word
          tag match    → 2.0 per word
          text match   → 1.0 per word (capped to avoid long-doc bias)
          framework    → 1.0 per word
        """
        score = 0.0

        title_words     = self._tokenise(doc.get("title", ""))
        text_words      = self._tokenise(doc.get("text", ""))
        tag_words       = self._tokenise(" ".join(doc.get("tags", [])))
        framework_words = self._tokenise(doc.get("framework", ""))

        title_counts     = Counter(title_words)
        text_counts      = Counter(text_words)
        tag_counts       = Counter(tag_words)
        framework_counts = Counter(framework_words)

        for word in query_words:
            if title_counts[word]:
                score += 3.0 * math.log1p(title_counts[word])
            if tag_counts[word]:
                score += 2.0 * math.log1p(tag_counts[word])
            if text_counts[word]:
                score += 1.0 * math.log1p(text_counts[word])
            if framework_counts[word]:
                score += 1.0

        return score

    # ── Get ───────────────────────────────────────────────────────────────────

    def get_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a document by its ID."""
        for doc in self._docs:
            if doc.get("id") == doc_id:
                return dict(doc)
        return None

    def get_all_by_framework(self, framework: str) -> List[Dict[str, Any]]:
        """Return all documents for a specific compliance framework."""
        return [dict(d) for d in self._docs if d.get("framework") == framework]

    def get_all(self) -> List[Dict[str, Any]]:
        """Return all documents in the store."""
        return [dict(d) for d in self._docs]

    # ── Update & Delete ───────────────────────────────────────────────────────

    def update_document(self, doc: Dict[str, Any]) -> bool:
        """
        Update an existing document by ID.

        Args:
            doc: Document dict with "id" field and updated values.

        Returns:
            True if found and updated, False if not found.
        """
        doc_id = doc.get("id")
        for i, existing in enumerate(self._docs):
            if existing.get("id") == doc_id:
                self._docs[i] = dict(doc)
                logger.info("MemoryVectorStore: updated doc id=%s", doc_id)
                return True
        return False

    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document by ID.

        Args:
            doc_id: Document ID to remove.

        Returns:
            True if found and deleted, False if not found.
        """
        before = len(self._docs)
        self._docs = [d for d in self._docs if d.get("id") != doc_id]

        if len(self._docs) < before:
            logger.info("MemoryVectorStore: deleted doc id=%s", doc_id)
            return True
        return False

    def clear(self) -> None:
        """Remove all documents from the store."""
        count       = len(self._docs)
        self._docs  = []
        logger.info("MemoryVectorStore: cleared %d documents.", count)

    def reload_corpus(self) -> None:
        """Reload the default REGULATIONS_CORPUS (resets any custom additions)."""
        self._docs = [dict(d) for d in REGULATIONS_CORPUS]
        logger.info("MemoryVectorStore: reloaded corpus (%d docs).", len(self._docs))

    # ── Stats ─────────────────────────────────────────────────────────────────

    def count(self) -> int:
        """Total number of documents in the store."""
        return len(self._docs)

    def frameworks(self) -> List[str]:
        """List of unique framework names in the store."""
        return sorted({d.get("framework", "Unknown") for d in self._docs})

    def stats(self) -> Dict[str, Any]:
        """Return a summary of store statistics."""
        framework_counts: Dict[str, int] = {}
        for doc in self._docs:
            fw = doc.get("framework", "Unknown")
            framework_counts[fw] = framework_counts.get(fw, 0) + 1

        return {
            "total_documents": self.count(),
            "frameworks":      framework_counts,
            "backend":         "memory",
            "persistent":      False,
            "search_type":     "keyword (TF-IDF style)",
        }

    def __repr__(self) -> str:
        return f"MemoryVectorStore(docs={self.count()}, frameworks={self.frameworks()})"


# ══════════════════════════════════════════════════════════════════════════════
# SINGLETON ACCESSOR
# ══════════════════════════════════════════════════════════════════════════════

_store: Optional[MemoryVectorStore] = None


def get_memory_store() -> MemoryVectorStore:
    """
    Return the singleton MemoryVectorStore instance.

    Creates it on first call. Subsequent calls return the same instance.
    This is the correct way to access the store in Streamlit pages and agents.

    Usage:
        from database.memory_store import get_memory_store
        store = get_memory_store()
        results = store.similarity_search("GDPR data retention", k=4)
    """
    global _store
    if _store is None:
        _store = MemoryVectorStore(preload=True)
    return _store


def reset_memory_store() -> MemoryVectorStore:
    """
    Reset and return a fresh MemoryVectorStore singleton.

    Useful for testing or when you need a clean state.
    """
    global _store
    _store = MemoryVectorStore(preload=True)
    return _store