"""
tests/test_rag.py — RAG / vector store tests.
"""
from database.memory_store import MockVectorStore
from rag.chunking import chunk_text, chunk_by_paragraphs
from rag.regulations_seed import REGULATIONS_CORPUS, get_by_framework


def test_regulations_corpus_not_empty():
    assert len(REGULATIONS_CORPUS) >= 10


def test_get_by_framework():
    gdpr = get_by_framework("GDPR")
    assert all(r["framework"] == "GDPR" for r in gdpr)
    assert len(gdpr) >= 3


def test_vector_store_init():
    vs = MockVectorStore()
    assert vs.count() > 0


def test_similarity_search_returns_results():
    vs      = MockVectorStore()
    results = vs.similarity_search("data retention GDPR", k=3)
    assert len(results) > 0


def test_similarity_search_framework_filter():
    vs      = MockVectorStore()
    results = vs.similarity_search("encryption", k=5, framework_filter="HIPAA")
    assert all(r["framework"] == "HIPAA" for r in results)


def test_add_document():
    vs = MockVectorStore()
    before = vs.count()
    vs.add_document({"id": "test-1", "title": "Test", "framework": "GDPR",
                      "citation": "Test", "severity": "Low",
                      "tags": ["test"], "text": "This is a test regulation."})
    assert vs.count() == before + 1


def test_chunk_text():
    text   = "A" * 2000
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    assert len(chunks) > 1
    assert all(len(c) <= 500 for c in chunks)


def test_chunk_by_paragraphs():
    text   = "Para one.\n\nPara two.\n\nPara three."
    chunks = chunk_by_paragraphs(text, max_size=200)
    assert len(chunks) >= 1
