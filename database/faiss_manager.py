"""
database/faiss_manager.py — FAISS vector store for Nexus AI Governance Platform.

Provides fast semantic search over regulatory documents using
sentence-transformer embeddings and FAISS IndexFlatIP (cosine similarity).

Install:
    pip install faiss-cpu sentence-transformers numpy

Usage:
    from database.faiss_manager import FaissManager

    db = FaissManager()
    db.add_documents(docs)
    results = db.similarity_search("data retention GDPR", k=4)
"""

import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from config.logging_config import get_logger
from config.settings import settings

logger = get_logger("nexus.database.faiss")


class FaissManager:
    """
    FAISS-backed semantic search with sentence-transformer embeddings.

    Features:
      - Cosine similarity search (IndexFlatIP on normalised vectors)
      - Framework-level filtering
      - Persistent index + metadata saved to disk
      - Auto-reload from disk on startup
      - Duplicate document detection by ID
      - Document deletion
      - Full index rebuild
    """

    EMBED_DIM  = 384                          # all-MiniLM-L6-v2 output size
    MODEL_NAME = "all-MiniLM-L6-v2"

    def __init__(
        self,
        index_path: str = "",
        embed_model: str = "",
    ) -> None:
        """
        Initialise FAISS manager.

        Args:
            index_path:  Path to save/load the FAISS index.
                         Defaults to settings.FAISS_INDEX_PATH.
            embed_model: Sentence-transformer model name.
                         Defaults to settings.HUGGINGFACE_EMBED_MODEL or all-MiniLM-L6-v2.
        """
        try:
            import faiss                                      # type: ignore
            from sentence_transformers import SentenceTransformer  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "FAISS dependencies missing. Run:\n"
                "  pip install faiss-cpu sentence-transformers"
            ) from exc

        self._faiss      = faiss
        self._index_path = Path(index_path or settings.FAISS_INDEX_PATH)
        self._meta_path  = self._index_path.with_suffix(".json")

        model_name   = embed_model or settings.HUGGINGFACE_EMBED_MODEL or self.MODEL_NAME
        self._model  = SentenceTransformer(model_name)
        self._docs:  List[Dict[str, Any]] = []
        self._index: Any                  = None

        if self._index_path.exists():
            self._load()
            logger.info(
                "FaissManager loaded | vectors=%d | path=%s",
                self._index.ntotal, self._index_path
            )
        else:
            self._index = faiss.IndexFlatIP(self.EMBED_DIM)   # inner-product = cosine on normalised vecs
            logger.info("FaissManager initialised (empty index).")

    # ── Embeddings ────────────────────────────────────────────────────────────

    def _embed(self, texts: List[str]) -> np.ndarray:
        """Encode texts and L2-normalise for cosine similarity."""
        vecs = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return vecs.astype("float32")

    # ── Add documents ─────────────────────────────────────────────────────────

    def add_documents(self, docs: List[Dict[str, Any]]) -> int:
        """
        Add a list of documents to the index.

        Skips documents whose ID already exists (deduplication).

        Args:
            docs: List of dicts. Each must have at minimum:
                  { "id": str, "text": str, "title": str, "framework": str }

        Returns:
            Number of documents actually added.
        """
        existing_ids = {d["id"] for d in self._docs}
        new_docs     = [d for d in docs if d.get("id") not in existing_ids]

        if not new_docs:
            logger.info("FaissManager.add_documents: all %d docs already exist.", len(docs))
            return 0

        texts = [d["text"] for d in new_docs]
        vecs  = self._embed(texts)
        self._index.add(vecs)
        self._docs.extend(new_docs)
        self._save()

        logger.info("FaissManager: added %d docs (skipped %d duplicates).",
                    len(new_docs), len(docs) - len(new_docs))
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
        Find the most semantically similar documents to a query.

        Args:
            query:            Search query string.
            k:                Number of results to return.
            framework_filter: If set, only return docs from this framework.
            min_score:        Minimum cosine similarity score (0.0–1.0).

        Returns:
            List of matching document dicts, each with an added "_score" field.
        """
        if self._index.ntotal == 0:
            logger.warning("FaissManager: index is empty — no results.")
            return []

        vec         = self._embed([query])
        fetch_k     = min(k * 5, self._index.ntotal)    # over-fetch then filter
        scores, indices = self._index.search(vec, fetch_k)

        results: List[Dict[str, Any]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self._docs):
                continue
            if score < min_score:
                continue
            doc = dict(self._docs[idx])
            doc["_score"] = float(score)

            if framework_filter and doc.get("framework") != framework_filter:
                continue

            results.append(doc)
            if len(results) >= k:
                break

        logger.debug("FaissManager.search: query='%s' → %d results", query[:60], len(results))
        return results

    def get_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a document by its ID."""
        for doc in self._docs:
            if doc.get("id") == doc_id:
                return dict(doc)
        return None

    def get_all_by_framework(self, framework: str) -> List[Dict[str, Any]]:
        """Return all documents for a specific compliance framework."""
        return [dict(d) for d in self._docs if d.get("framework") == framework]

    # ── Delete ────────────────────────────────────────────────────────────────

    def delete_document(self, doc_id: str) -> bool:
        """
        Remove a document by ID and rebuild the index.

        Args:
            doc_id: Document ID to remove.

        Returns:
            True if found and removed, False if not found.
        """
        before = len(self._docs)
        self._docs = [d for d in self._docs if d.get("id") != doc_id]

        if len(self._docs) == before:
            return False

        self._rebuild_index()
        self._save()
        logger.info("FaissManager: deleted doc id=%s, rebuilt index.", doc_id)
        return True

    def _rebuild_index(self) -> None:
        """Rebuild the FAISS index from current _docs list."""
        self._index = self._faiss.IndexFlatIP(self.EMBED_DIM)
        if self._docs:
            texts = [d["text"] for d in self._docs]
            vecs  = self._embed(texts)
            self._index.add(vecs)

    # ── Persistence ───────────────────────────────────────────────────────────

    def _save(self) -> None:
        """Persist the FAISS index and metadata to disk."""
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        self._faiss.write_index(self._index, str(self._index_path))
        self._meta_path.write_text(
            json.dumps(self._docs, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.debug("FaissManager: saved index (%d vectors).", self._index.ntotal)

    def _load(self) -> None:
        """Load the FAISS index and metadata from disk."""
        self._index = self._faiss.read_index(str(self._index_path))
        if self._meta_path.exists():
            self._docs = json.loads(self._meta_path.read_text(encoding="utf-8"))

    def clear(self) -> None:
        """Wipe the index and all stored documents."""
        self._docs  = []
        self._index = self._faiss.IndexFlatIP(self.EMBED_DIM)
        if self._index_path.exists():
            self._index_path.unlink()
        if self._meta_path.exists():
            self._meta_path.unlink()
        logger.info("FaissManager: index cleared.")

    # ── Stats ─────────────────────────────────────────────────────────────────

    def count(self) -> int:
        """Total number of indexed documents."""
        return len(self._docs)

    def frameworks(self) -> List[str]:
        """List of unique framework names in the index."""
        return sorted({d.get("framework", "Unknown") for d in self._docs})

    def stats(self) -> Dict[str, Any]:
        """Return a summary of index statistics."""
        framework_counts: Dict[str, int] = {}
        for doc in self._docs:
            fw = doc.get("framework", "Unknown")
            framework_counts[fw] = framework_counts.get(fw, 0) + 1

        return {
            "total_documents": self.count(),
            "index_vectors":   self._index.ntotal,
            "frameworks":      framework_counts,
            "index_path":      str(self._index_path),
            "index_exists":    self._index_path.exists(),
            "embed_model":     self.MODEL_NAME,
            "embed_dim":       self.EMBED_DIM,
        }

    def __repr__(self) -> str:
        return f"FaissManager(docs={self.count()}, path={self._index_path})"