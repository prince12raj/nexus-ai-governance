"""
rag/retrieval_tools.py — High-level retrieval tools for Nexus AI Governance Platform.

These functions are called by compliance_engine.py, agents, and UI pages
to fetch relevant regulations before passing them to the LLM.

Usage:
    from rag.retrieval_tools import (
        retrieve_for_compliance,
        retrieve_for_question,
        retrieve_pii_regulations,
        format_context_for_prompt,
    )
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from config.logging_config import get_logger

logger = get_logger("nexus.rag.retrieval")


# ── Core retrieval ────────────────────────────────────────────────────────────

def retrieve_for_compliance(
    policy_text: str,
    framework: str,
    k: int = 4,
) -> List[Dict[str, Any]]:
    """
    Retrieve the most relevant regulations for a compliance audit.

    Called by compliance_engine.py before every LLM audit call.

    Args:
        policy_text: Policy document text.
        framework:   Compliance framework (e.g. "GDPR", "HIPAA").
        k:           Number of regulation docs to retrieve.

    Returns:
        List of regulation dicts with title, text, citation, severity fields.
    """
    from rag.vector_store import search_for_compliance

    if framework == "Combined Framework Mode":
        # Retrieve top-k from ALL frameworks
        return retrieve_all_frameworks(policy_text, k_per_framework=2)

    results = search_for_compliance(policy_text, framework, k=k)
    logger.info(
        "retrieve_for_compliance: framework=%s | retrieved=%d", framework, len(results)
    )
    return results


def retrieve_for_question(
    question: str,
    framework: Optional[str] = None,
    k: int = 4,
) -> List[Dict[str, Any]]:
    """
    Retrieve relevant regulations for a user question (regulatory Q&A).

    Called by governance chat and regulatory research agent.

    Args:
        question:  The user's question.
        framework: Optional framework filter.
        k:         Number of results to return.

    Returns:
        List of relevant regulation dicts.
    """
    from rag.vector_store import search

    results = search(query=question, framework=framework, k=k)
    logger.info(
        "retrieve_for_question: query='%s' | framework=%s | retrieved=%d",
        question[:60], framework, len(results)
    )
    return results


def retrieve_all_frameworks(
    query: str,
    k_per_framework: int = 2,
) -> List[Dict[str, Any]]:
    """
    Retrieve top results from every supported framework.

    Used for Combined Framework Mode audits.

    Args:
        query:             Search query.
        k_per_framework:   Results per framework.

    Returns:
        Combined list of regulation dicts from all frameworks.
    """
    from config.constants import SUPPORTED_FRAMEWORKS
    from rag.vector_store import search

    all_results: List[Dict[str, Any]] = []
    frameworks  = [f for f in SUPPORTED_FRAMEWORKS if f != "Combined Framework Mode"]

    for fw in frameworks:
        results = search(query=query, framework=fw, k=k_per_framework)
        all_results.extend(results)

    logger.info(
        "retrieve_all_frameworks: %d frameworks × %d = %d docs retrieved",
        len(frameworks), k_per_framework, len(all_results)
    )
    return all_results


def retrieve_pii_regulations(k: int = 4) -> List[Dict[str, Any]]:
    """
    Retrieve PII-specific regulations for the PII detection engine.

    Returns:
        List of regulation dicts related to personal data handling.
    """
    from rag.vector_store import search

    pii_query = "personal data PII privacy sensitive information protection"
    results   = search(query=pii_query, k=k)
    return results


def retrieve_by_ids(doc_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Retrieve specific documents by their IDs.

    Args:
        doc_ids: List of document IDs to retrieve.

    Returns:
        List of document dicts (skips IDs not found).
    """
    from rag.vector_store import get_store

    store   = get_store()
    results = []
    for doc_id in doc_ids:
        doc = store.get_by_id(doc_id)
        if doc:
            results.append(doc)
    return results


# ── Context formatting ────────────────────────────────────────────────────────

def format_context_for_prompt(
    docs: List[Dict[str, Any]],
    max_chars: int = 3000,
) -> str:
    """
    Format retrieved regulation docs into a prompt-ready context string.

    Args:
        docs:      List of regulation dicts from retrieval.
        max_chars: Maximum total characters in the output string.

    Returns:
        Formatted context string for injection into system prompts.

    Example output:
        [GDPR Article 5 — Regulation (EU) 2016/679, Article 5]
        Personal data shall be collected for specified purposes...

        [HIPAA Security Rule — 45 CFR §164.312]
        Covered entities must implement technical safeguards...
    """
    if not docs:
        return "No relevant regulatory context found."

    parts: List[str] = []
    total = 0

    for doc in docs:
        title    = doc.get("title", "Unknown Regulation")
        citation = doc.get("citation", "")
        text     = doc.get("text", "")

        header  = f"[{title} — {citation}]" if citation else f"[{title}]"
        section = f"{header}\n{text}"

        if total + len(section) > max_chars:
            remaining = max_chars - total
            if remaining > 100:
                section = section[:remaining] + "..."
                parts.append(section)
            break

        parts.append(section)
        total += len(section) + 2   # +2 for \n\n separator

    return "\n\n".join(parts)


def format_context_as_list(docs: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Format retrieved docs as a clean list of {citation, title, summary} dicts.

    Used by UI pages to display sources alongside AI responses.

    Returns:
        List of simplified dicts for display.
    """
    return [
        {
            "citation":  doc.get("citation", ""),
            "title":     doc.get("title", ""),
            "framework": doc.get("framework", ""),
            "severity":  doc.get("severity", ""),
            "summary":   doc.get("text", "")[:200] + "...",
        }
        for doc in docs
    ]


# ── Knowledge base browsing ───────────────────────────────────────────────────

def get_all_regulations(framework: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Return all regulations in the knowledge base.

    Args:
        framework: Optional filter by framework name.

    Returns:
        List of all regulation dicts.
    """
    from rag.vector_store import get_store

    store = get_store()

    if framework:
        return store.get_all_by_framework(framework)

    if hasattr(store, "get_all"):
        return store.get_all()

    # Fallback for backends without get_all
    from rag.regulations_seed import REGULATIONS_CORPUS
    if framework:
        return [r for r in REGULATIONS_CORPUS if r["framework"] == framework]
    return list(REGULATIONS_CORPUS)


def get_knowledge_base_stats() -> Dict[str, Any]:
    """
    Return knowledge base statistics for the Admin Settings page.

    Returns:
        Dict with total docs, frameworks, and per-framework counts.
    """
    from rag.vector_store import get_store_stats
    return get_store_stats()