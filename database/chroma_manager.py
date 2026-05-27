"""
database/chroma_manager.py — ChromaDB vector store for Nexus AI Governance Platform.

Provides persistent semantic search over regulatory documents using
ChromaDB's built-in embeddings or a custom sentence-transformer model.

Install:
    pip install chromadb

Usage:
    from database.chroma_manager import ChromaManager

    db = ChromaManager()
    db.add_documents(docs)
    results = db.similarity_search("data retention GDPR", k=4)
"""

from typing import Any, Dict, List, Optional

from config.logging_config import get_logger
from config.settings import settings

logger = get_logger("nexus.database.chroma")

# ChromaDB collection name
COLLECTION_NAME = "nexus_regulations"


class ChromaManager:
    """
    ChromaDB-backed persistent vector store for regulatory documents.

    Features:
      - Persistent storage to disk (survives restarts)
      - Framework-level metadata filtering
      - Duplicate document detection by ID
      - Document update and deletion
      - Collection stats and inspection
      - Auto-creates collection on first run
    """

    def __init__(
        self,
        persist_dir: str = "",
        collection_name: str = COLLECTION_NAME,
    ) -> None:
        """
        Initialise ChromaDB manager.

        Args:
            persist_dir:     Directory to store the ChromaDB files.
                             Defaults to settings.CHROMA_PERSIST_DIR.
            collection_name: Name of the ChromaDB collection to use.
        """
        try:
            import chromadb                                   # type: ignore
            from chromadb.config import Settings as ChromaSettings  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "ChromaDB is not installed. Run:\n"
                "  pip install chromadb"
            ) from exc

        dir_path = persist_dir or settings.CHROMA_PERSIST_DIR

        self._client = chromadb.PersistentClient(
            path=dir_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._col = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},              # cosine similarity
        )

        logger.info(
            "ChromaManager initialised | collection=%s | docs=%d | path=%s",
            collection_name, self._col.count(), dir_path
        )

    # ── Add documents ─────────────────────────────────────────────────────────

    def add_documents(self, docs: List[Dict[str, Any]]) -> int:
        """
        Add a list of documents to the ChromaDB collection.

        Skips documents whose ID already exists (deduplication).

        Args:
            docs: List of dicts. Each must have at minimum:
                  { "id": str, "text": str, "title": str, "framework": str }

        Returns:
            Number of documents actually added.
        """
        if not docs:
            return 0

        # Fetch existing IDs to skip duplicates
        existing = self._col.get(ids=[d["id"] for d in docs if "id" in d])
        existing_ids = set(existing["ids"]) if existing["ids"] else set()

        new_docs = [d for d in docs if d.get("id") not in existing_ids]
        if not new_docs:
            logger.info("ChromaManager: all %d docs already exist.", len(docs))
            return 0

        ids      = [d["id"]   for d in new_docs]
        texts    = [d["text"] for d in new_docs]
        metadatas = [
            {k: str(v) if not isinstance(v, (str, int, float, bool)) else v
             for k, v in d.items() if k != "text"}
            for d in new_docs
        ]

        self._col.add(ids=ids, documents=texts, metadatas=metadatas)

        logger.info(
            "ChromaManager: added %d docs (skipped %d duplicates).",
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
        Find the most semantically similar documents to a query.

        Args:
            query:            Search query string.
            k:                Number of results to return.
            framework_filter: If set, only return docs from this framework.
            min_score:        Minimum similarity score (0.0–1.0).
                              ChromaDB returns distance; converted to score = 1 - distance.

        Returns:
            List of matching document dicts, each with an added "_score" field.
        """
        if self._col.count() == 0:
            logger.warning("ChromaManager: collection is empty — no results.")
            return []

        where = {"framework": framework_filter} if framework_filter else None

        try:
            results = self._col.query(
                query_texts=[query],
                n_results=min(k, self._col.count()),
                where=where,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            logger.error("ChromaDB query failed: %s", exc)
            return []

        docs: List[Dict[str, Any]] = []
        for meta, text, distance in zip(
            results["metadatas"][0],
            results["documents"][0],
            results["distances"][0],
        ):
            score = 1.0 - float(distance)       # convert cosine distance → similarity
            if score < min_score:
                continue
            doc          = dict(meta)
            doc["text"]  = text
            doc["_score"] = round(score, 4)
            docs.append(doc)

        logger.debug("ChromaManager.search: query='%s' → %d results", query[:60], len(docs))
        return docs

    def get_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a document by its ID."""
        try:
            result = self._col.get(ids=[doc_id], include=["documents", "metadatas"])
            if result["ids"]:
                doc         = dict(result["metadatas"][0])
                doc["text"] = result["documents"][0]
                return doc
        except Exception as exc:
            logger.error("ChromaManager.get_by_id failed: %s", exc)
        return None

    def get_all_by_framework(self, framework: str) -> List[Dict[str, Any]]:
        """Return all documents for a specific compliance framework."""
        try:
            result = self._col.get(
                where={"framework": framework},
                include=["documents", "metadatas"],
            )
            docs = []
            for meta, text in zip(result["metadatas"], result["documents"]):
                doc         = dict(meta)
                doc["text"] = text
                docs.append(doc)
            return docs
        except Exception as exc:
            logger.error("ChromaManager.get_all_by_framework failed: %s", exc)
            return []

    # ── Update & Delete ───────────────────────────────────────────────────────

    def update_document(self, doc: Dict[str, Any]) -> bool:
        """
        Update an existing document by ID.

        Args:
            doc: Document dict with "id" and updated fields.

        Returns:
            True if updated, False if ID not found.
        """
        doc_id = doc.get("id")
        if not doc_id:
            return False

        existing = self.get_by_id(doc_id)
        if not existing:
            return False

        text      = doc.get("text", existing.get("text", ""))
        metadata  = {
            k: str(v) if not isinstance(v, (str, int, float, bool)) else v
            for k, v in doc.items() if k != "text"
        }

        try:
            self._col.update(ids=[doc_id], documents=[text], metadatas=[metadata])
            logger.info("ChromaManager: updated doc id=%s", doc_id)
            return True
        except Exception as exc:
            logger.error("ChromaManager.update failed: %s", exc)
            return False

    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document by ID.

        Args:
            doc_id: Document ID to remove.

        Returns:
            True if deleted, False if not found.
        """
        existing = self.get_by_id(doc_id)
        if not existing:
            return False

        try:
            self._col.delete(ids=[doc_id])
            logger.info("ChromaManager: deleted doc id=%s", doc_id)
            return True
        except Exception as exc:
            logger.error("ChromaManager.delete failed: %s", exc)
            return False

    def clear(self) -> None:
        """Delete all documents from the collection."""
        try:
            all_ids = self._col.get()["ids"]
            if all_ids:
                self._col.delete(ids=all_ids)
            logger.info("ChromaManager: collection cleared (%d docs removed).", len(all_ids))
        except Exception as exc:
            logger.error("ChromaManager.clear failed: %s", exc)

    # ── Stats ─────────────────────────────────────────────────────────────────

    def count(self) -> int:
        """Total number of documents in the collection."""
        return self._col.count()

    def frameworks(self) -> List[str]:
        """List of unique framework names in the collection."""
        try:
            result = self._col.get(include=["metadatas"])
            return sorted({
                m.get("framework", "Unknown")
                for m in result["metadatas"]
            })
        except Exception:
            return []

    def stats(self) -> Dict[str, Any]:
        """Return a summary of collection statistics."""
        framework_counts: Dict[str, int] = {}
        try:
            result = self._col.get(include=["metadatas"])
            for meta in result["metadatas"]:
                fw = meta.get("framework", "Unknown")
                framework_counts[fw] = framework_counts.get(fw, 0) + 1
        except Exception:
            pass

        return {
            "total_documents": self.count(),
            "frameworks":      framework_counts,
            "collection_name": self._col.name,
            "persist_dir":     settings.CHROMA_PERSIST_DIR,
            "backend":         "chromadb",
        }

    def __repr__(self) -> str:
        return f"ChromaManager(collection={self._col.name}, docs={self.count()})"