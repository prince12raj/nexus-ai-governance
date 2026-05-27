"""
rag/chunking.py — Text chunking utilities for Nexus AI Governance Platform.

Splits large policy documents into smaller chunks before embedding and
storing in the vector store. Good chunking = better RAG retrieval.

Strategies:
  chunk_text()           — fixed-size with overlap (default)
  chunk_by_paragraphs()  — paragraph-boundary aware
  chunk_by_sentences()   — sentence-boundary aware
  chunk_document()       — smart chunker: picks best strategy per doc type
  chunk_with_metadata()  — returns dicts with chunk + source metadata

Usage:
    from rag.chunking import chunk_document, chunk_with_metadata

    chunks = chunk_document(text, strategy="paragraphs")
    docs   = chunk_with_metadata(text, source="privacy_policy.pdf", framework="GDPR")
"""

import re
import uuid
from typing import Any, Dict, List, Optional

from config.constants import DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP
from config.logging_config import get_logger

logger = get_logger("nexus.rag.chunking")


# ══════════════════════════════════════════════════════════════════════════════
# CORE CHUNKING STRATEGIES
# ══════════════════════════════════════════════════════════════════════════════

def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[str]:
    """
    Split text into fixed-size overlapping chunks (character-based).

    Best for: dense legal text, PDFs, plain text files.

    Args:
        text:       Input text to split.
        chunk_size: Maximum characters per chunk.
        overlap:    Characters of overlap between consecutive chunks.

    Returns:
        List of text chunk strings.
    """
    if not text or not text.strip():
        return []

    text   = _clean_text(text)
    chunks: List[str] = []
    start  = 0

    while start < len(text):
        end   = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap

    logger.debug("chunk_text: %d chars → %d chunks (size=%d, overlap=%d)",
                 len(text), len(chunks), chunk_size, overlap)
    return chunks


def chunk_by_paragraphs(
    text: str,
    max_size: int = DEFAULT_CHUNK_SIZE,
    min_size: int = 50,
) -> List[str]:
    """
    Split text at paragraph boundaries, merging short paragraphs.

    Best for: structured policy documents, Word docs, HTML content.

    Args:
        text:     Input text to split.
        max_size: Maximum characters per chunk.
        min_size: Minimum characters — shorter paragraphs are merged.

    Returns:
        List of text chunk strings.
    """
    if not text or not text.strip():
        return []

    text       = _clean_text(text)
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    chunks:    List[str] = []
    buffer     = ""

    for para in paragraphs:
        if len(para) < min_size and buffer:
            # Merge short paragraph into buffer
            buffer = (buffer + " " + para).strip()
        elif len(buffer) + len(para) + 2 <= max_size:
            buffer = (buffer + "\n\n" + para).strip() if buffer else para
        else:
            if buffer:
                chunks.append(buffer)
            # If single paragraph is too long, split it further
            if len(para) > max_size:
                chunks.extend(chunk_text(para, chunk_size=max_size))
                buffer = ""
            else:
                buffer = para

    if buffer:
        chunks.append(buffer)

    logger.debug("chunk_by_paragraphs: %d paragraphs → %d chunks", len(paragraphs), len(chunks))
    return chunks


def chunk_by_sentences(
    text: str,
    max_size: int = DEFAULT_CHUNK_SIZE,
    overlap_sentences: int = 1,
) -> List[str]:
    """
    Split text at sentence boundaries, grouping sentences up to max_size.

    Best for: regulatory text, compliance clauses, Q&A content.

    Args:
        text:               Input text to split.
        max_size:           Maximum characters per chunk.
        overlap_sentences:  Number of sentences to repeat at start of next chunk.

    Returns:
        List of text chunk strings.
    """
    if not text or not text.strip():
        return []

    text      = _clean_text(text)
    sentences = _split_sentences(text)
    chunks:   List[str] = []
    current:  List[str] = []
    current_len = 0

    for sent in sentences:
        sent_len = len(sent)

        if current_len + sent_len + 1 > max_size and current:
            chunks.append(" ".join(current))
            # Keep overlap sentences for context continuity
            current     = current[-overlap_sentences:] if overlap_sentences else []
            current_len = sum(len(s) + 1 for s in current)

        current.append(sent)
        current_len += sent_len + 1

    if current:
        chunks.append(" ".join(current))

    logger.debug("chunk_by_sentences: %d sentences → %d chunks", len(sentences), len(chunks))
    return chunks


def chunk_by_sections(
    text: str,
    max_size: int = DEFAULT_CHUNK_SIZE,
) -> List[str]:
    """
    Split text at heading/section boundaries (numbered sections, ARTICLE, etc.).

    Best for: legal documents, compliance frameworks with numbered sections.

    Args:
        text:     Input text to split.
        max_size: Maximum characters per chunk. Long sections are further split.

    Returns:
        List of text chunk strings.
    """
    if not text or not text.strip():
        return []

    text = _clean_text(text)

    # Detect section headers: "1.", "1.1", "Article 5", "Section 3", "A.9.4.3"
    section_pattern = re.compile(
        r"(?m)^(?:(?:Article|Section|Clause|Annex|Requirement|Control)\s+[\d.]+|[\d]+\.[\d.]*\s+\w|\([a-z]\))\s*",
        re.IGNORECASE
    )

    parts   = section_pattern.split(text)
    headers = section_pattern.findall(text)
    chunks: List[str] = []

    for i, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue
        header   = headers[i - 1].strip() if i > 0 and i - 1 < len(headers) else ""
        combined = f"{header}\n{part}".strip() if header else part

        if len(combined) > max_size:
            chunks.extend(chunk_by_paragraphs(combined, max_size=max_size))
        else:
            chunks.append(combined)

    logger.debug("chunk_by_sections: %d sections → %d chunks", len(parts), len(chunks))
    return chunks


# ══════════════════════════════════════════════════════════════════════════════
# SMART CHUNKER
# ══════════════════════════════════════════════════════════════════════════════

def chunk_document(
    text: str,
    strategy: str = "auto",
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[str]:
    """
    Smart document chunker — picks the best strategy automatically.

    Args:
        text:       Input document text.
        strategy:   "auto"|"fixed"|"paragraphs"|"sentences"|"sections"
                    "auto" detects the best strategy from content structure.
        chunk_size: Max characters per chunk.
        overlap:    Overlap characters (for fixed strategy).

    Returns:
        List of text chunk strings.
    """
    if not text or not text.strip():
        return []

    if strategy == "auto":
        strategy = _detect_strategy(text)
        logger.debug("chunk_document: auto-detected strategy=%s", strategy)

    if strategy == "sections":
        return chunk_by_sections(text, max_size=chunk_size)
    if strategy == "paragraphs":
        return chunk_by_paragraphs(text, max_size=chunk_size)
    if strategy == "sentences":
        return chunk_by_sentences(text, max_size=chunk_size)

    # Default: fixed
    return chunk_text(text, chunk_size=chunk_size, overlap=overlap)


def _detect_strategy(text: str) -> str:
    """Auto-detect the best chunking strategy from text structure."""
    # Many numbered sections → section chunking
    section_matches = len(re.findall(
        r"(?m)^(?:Article|Section|Clause|Requirement|Control)\s+\d", text, re.IGNORECASE
    ))
    if section_matches >= 3:
        return "sections"

    # Many paragraph breaks → paragraph chunking
    para_breaks = text.count("\n\n")
    if para_breaks >= 5:
        return "paragraphs"

    # Long text with sentences → sentence chunking
    if len(text) > 2000:
        return "sentences"

    return "fixed"


# ══════════════════════════════════════════════════════════════════════════════
# CHUNK WITH METADATA
# ══════════════════════════════════════════════════════════════════════════════

def chunk_with_metadata(
    text: str,
    source: str = "unknown",
    framework: str = "GDPR",
    strategy: str = "auto",
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Chunk a document and return a list of dicts ready for vector store ingestion.

    Each dict has the structure expected by FaissManager, ChromaManager, MemoryVectorStore:
    {
        "id":        str,   unique chunk ID
        "text":      str,   chunk content
        "title":     str,   source + chunk index
        "framework": str,   compliance framework
        "source":    str,   original document name
        "chunk_idx": int,   position in document
        "citation":  str,   source citation string
        ...extra_metadata
    }

    Args:
        text:           Full document text.
        source:         Document name/path (e.g. "privacy_policy.pdf").
        framework:      Compliance framework (e.g. "GDPR").
        strategy:       Chunking strategy ("auto"|"fixed"|"paragraphs"|"sentences"|"sections").
        chunk_size:     Max characters per chunk.
        overlap:        Overlap characters (fixed strategy).
        extra_metadata: Additional metadata to include in each chunk dict.

    Returns:
        List of document dicts ready for vector store add_documents().
    """
    chunks = chunk_document(text, strategy=strategy, chunk_size=chunk_size, overlap=overlap)

    if not chunks:
        return []

    docs: List[Dict[str, Any]] = []
    base_id = str(uuid.uuid4())[:8]

    for i, chunk in enumerate(chunks):
        doc: Dict[str, Any] = {
            "id":        f"{base_id}-chunk-{i:04d}",
            "text":      chunk,
            "title":     f"{source} — Chunk {i + 1}/{len(chunks)}",
            "framework": framework,
            "source":    source,
            "chunk_idx": i,
            "citation":  f"{source}, chunk {i + 1}",
            "tags":      [framework.lower(), "user-document"],
        }
        if extra_metadata:
            doc.update(extra_metadata)
        docs.append(doc)

    logger.info(
        "chunk_with_metadata: source='%s' | strategy=%s | %d chunks",
        source, strategy, len(docs)
    )
    return docs


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _clean_text(text: str) -> str:
    """Remove null bytes, excessive whitespace, and normalise line endings."""
    text = text.replace("\x00", "")              # null bytes
    text = re.sub(r"\r\n", "\n", text)           # Windows line endings
    text = re.sub(r"\r", "\n", text)             # old Mac line endings
    text = re.sub(r"[ \t]+", " ", text)          # multiple spaces/tabs
    text = re.sub(r"\n{4,}", "\n\n\n", text)     # excessive blank lines
    return text.strip()


def _split_sentences(text: str) -> List[str]:
    """
    Split text into sentences using regex.
    Handles abbreviations, decimal numbers, and common edge cases.
    """
    # Split on sentence-ending punctuation followed by whitespace + capital
    sentence_endings = re.compile(
        r"(?<=[.!?])\s+(?=[A-Z\"\(])"
    )
    sentences = sentence_endings.split(text)
    return [s.strip() for s in sentences if s.strip()]


def estimate_token_count(text: str) -> int:
    """
    Rough token count estimate (1 token ≈ 4 chars for English).
    Used to check if a chunk fits in a model's context window.
    """
    return len(text) // 4