"""
agents/regulatory_research_agent.py — Regulatory research agent for Nexus AI Governance Platform.

Answers deep regulation questions by combining RAG retrieval
with LLM reasoning. Provides cited, framework-specific answers.

Usage:
    from agents.regulatory_research_agent import RegulatoryResearchAgent

    agent  = RegulatoryResearchAgent()
    result = agent.answer("What are the GDPR requirements for data breach notification?")
    result = agent.search_regulations("encryption requirements", framework="HIPAA")
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from config.logging_config import get_logger

logger = get_logger("nexus.agents.regulatory_research")


class RegulatoryResearchAgent:
    """
    Regulatory research agent — answers regulation questions with cited sources.

    Workflow:
        1. Retrieve top-k relevant regulations via RAG
        2. Format as context string
        3. Call LLM with REGULATORY_RESEARCH_SYSTEM prompt
        4. Return answer + source citations
    """

    def __init__(self, provider: Optional[str] = None) -> None:
        self.provider = provider
        logger.info("RegulatoryResearchAgent initialised | provider=%s", provider or "auto")

    # ── Main answer function ──────────────────────────────────────────────────

    def answer(
        self,
        question: str,
        framework: Optional[str] = None,
        k: int = 4,
    ) -> Dict[str, Any]:
        """
        Answer a regulatory question using RAG + LLM.

        Args:
            question:  The regulation question to answer.
            framework: Optional framework filter (e.g. "GDPR").
            k:         Number of regulation documents to retrieve.

        Returns:
            Dict with:
                answer   — str (LLM-generated answer with citations)
                sources  — List[Dict] (retrieved regulation docs)
                question — str
                framework— str | None
                duration — float
        """
        start = time.time()
        logger.info("RegulatoryResearchAgent.answer | framework=%s | q='%s'", framework, question[:80])

        # Retrieve relevant regulations
        sources = self._retrieve(question, framework=framework, k=k)

        # Build LLM prompt
        from llm.router import route
        answer = route(
            task="regulatory_qa",
            payload={
                "question":     question,
                "context_docs": sources,
            },
            provider=self.provider,
        )

        return {
            "answer":    answer,
            "sources":   self._format_sources(sources),
            "question":  question,
            "framework": framework,
            "duration":  round(time.time() - start, 2),
        }

    # ── Regulation search ─────────────────────────────────────────────────────

    def search_regulations(
        self,
        query: str,
        framework: Optional[str] = None,
        k: int = 6,
    ) -> List[Dict[str, Any]]:
        """
        Search the regulatory knowledge base directly.

        Args:
            query:     Search query.
            framework: Optional framework filter.
            k:         Number of results.

        Returns:
            List of matching regulation dicts.
        """
        logger.info("RegulatoryResearchAgent.search | framework=%s | q='%s'", framework, query[:60])
        return self._retrieve(query, framework=framework, k=k)

    def get_all_for_framework(self, framework: str) -> List[Dict[str, Any]]:
        """
        Return all regulations for a specific framework.

        Args:
            framework: Framework name (e.g. "GDPR").

        Returns:
            List of all regulation dicts for that framework.
        """
        from rag.retrieval_tools import get_all_regulations
        all_regs = get_all_regulations(framework=framework)
        logger.info("RegulatoryResearchAgent.get_all | framework=%s | count=%d", framework, len(all_regs))
        return all_regs

    def compare_frameworks(
        self,
        topic: str,
        frameworks: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Compare requirements across multiple frameworks on a given topic.

        Args:
            topic:      Topic to compare (e.g. "data encryption").
            frameworks: List of frameworks to compare. Defaults to all.

        Returns:
            Dict mapping framework → relevant regulations.
        """
        from config.constants import SUPPORTED_FRAMEWORKS
        from rag.vector_store import search

        fws     = frameworks or [f for f in SUPPORTED_FRAMEWORKS if f != "Combined Framework Mode"]
        results: Dict[str, List[Dict[str, Any]]] = {}

        for fw in fws:
            regs = search(query=topic, framework=fw, k=2)
            if regs:
                results[fw] = regs

        # Ask LLM to synthesise comparison
        from llm.router import route

        context_parts = []
        for fw, regs in results.items():
            for r in regs:
                context_parts.append(f"[{fw}] {r.get('title', '')}: {r.get('text', '')[:200]}")

        context = "\n\n".join(context_parts)
        prompt  = (
            f"Compare the requirements for '{topic}' across the following frameworks "
            f"({', '.join(results.keys())}). Highlight key differences and similarities.\n\n"
            f"CONTEXT:\n{context}"
        )

        comparison = route(
            task="regulatory_qa",
            payload={"question": prompt, "context_docs": []},
            provider=self.provider,
        )

        return {
            "topic":       topic,
            "frameworks":  list(results.keys()),
            "sources":     results,
            "comparison":  comparison,
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _retrieve(
        self,
        query: str,
        framework: Optional[str] = None,
        k: int = 4,
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant regulations from the vector store."""
        from rag.retrieval_tools import retrieve_for_question
        return retrieve_for_question(query=query, framework=framework, k=k)

    def _format_sources(self, docs: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Format retrieved docs as clean source citations."""
        from rag.retrieval_tools import format_context_as_list
        return format_context_as_list(docs)