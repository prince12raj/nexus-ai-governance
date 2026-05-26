"""
rag/__init__.py — RAG package for Nexus AI Governance Platform.

Single import point for all RAG operations.

Usage:
    from rag import search, ingest_document, retrieve_for_compliance
    from rag import REGULATIONS_CORPUS, get_by_framework
"""
from rag.regulations_seed import (
    REGULATIONS_CORPUS,
    get_all_regulations,
    get_by_framework,
    get_by_id,
    get_by_severity,
    get_frameworks,
    get_corpus_stats,
)
from rag.chunking import (
    chunk_text,
    chunk_by_paragraphs,
    chunk_by_sentences,
    chunk_by_sections,
    chunk_document,
    chunk_with_metadata,
    estimate_token_count,
)
from rag.embeddings import (
    embed,
    embed_single,
    embed_documents,
    get_embedder,
    get_embedding_dim,
)
from rag.vector_store import (
    get_store,
    ingest_document,
    search,
    search_for_compliance,
    get_store_stats,
    reset_to_corpus,
    clear_user_documents,
)
from rag.retrieval_tools import (
    retrieve_for_compliance,
    retrieve_for_question,
    retrieve_all_frameworks,
    retrieve_pii_regulations,
    retrieve_by_ids,
    format_context_for_prompt,
    format_context_as_list,
    get_all_regulations as get_kb_regulations,
    get_knowledge_base_stats,
)

__all__ = [
    # Corpus
    "REGULATIONS_CORPUS",
    "get_all_regulations",
    "get_by_framework",
    "get_by_id",
    "get_by_severity",
    "get_frameworks",
    "get_corpus_stats",
    # Chunking
    "chunk_text",
    "chunk_by_paragraphs",
    "chunk_by_sentences",
    "chunk_by_sections",
    "chunk_document",
    "chunk_with_metadata",
    "estimate_token_count",
    # Embeddings
    "embed",
    "embed_single",
    "embed_documents",
    "get_embedder",
    "get_embedding_dim",
    # Vector store
    "get_store",
    "ingest_document",
    "search",
    "search_for_compliance",
    "get_store_stats",
    "reset_to_corpus",
    "clear_user_documents",
    # Retrieval
    "retrieve_for_compliance",
    "retrieve_for_question",
    "retrieve_all_frameworks",
    "retrieve_pii_regulations",
    "retrieve_by_ids",
    "format_context_for_prompt",
    "format_context_as_list",
    "get_kb_regulations",
    "get_knowledge_base_stats",
]