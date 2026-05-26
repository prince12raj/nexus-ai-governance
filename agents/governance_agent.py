"""
agents/governance_agent.py — Master governance agent for Nexus AI Governance Platform.

The GovernanceAgent is the top-level orchestrator. It:
  - Accepts a governance query or task
  - Decides which sub-agents to invoke
  - Combines results into a structured response
  - Manages session context across multi-turn conversations

Usage:
    from agents.governance_agent import GovernanceAgent

    agent    = GovernanceAgent()
    response = agent.run("What are the GDPR requirements for data retention?")
    response = agent.run("Assess this AI system for governance risks", context={"system": "..."})
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from config.logging_config import get_logger
from config.settings import settings

logger = get_logger("nexus.agents.governance")


class GovernanceAgent:
    """
    Master governance agent that routes tasks to the appropriate sub-agent.

    Supported task types:
        regulatory_qa       — Answer regulation questions
        risk_assessment     — Score an AI system for governance risks
        policy_generation   — Draft a compliant policy section
        remediation         — Build a fix plan for a finding
        compliance_chat     — General governance Q&A with RAG context
        pii_scan            — Detect PII in a document
        executive_summary   — Generate board-level audit summary
    """

    def __init__(self, provider: Optional[str] = None) -> None:
        self.provider    = provider
        self.history:    List[Dict[str, str]] = []
        self.session_ctx: Dict[str, Any]      = {}
        logger.info("GovernanceAgent initialised | provider=%s", provider or "auto")

    # ── Main entry point ──────────────────────────────────────────────────────

    def run(
        self,
        query: str,
        task_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """
        Process a governance query and return a structured response.

        Args:
            query:     The user's question or instruction.
            task_type: Force a task type (optional — auto-detected if not set).
            context:   Additional context dict (e.g. findings, system description).
            stream:    If True, return a generator for streaming chat responses.

        Returns:
            Dict with keys:
                response    — str or Generator (if stream=True)
                task_type   — str (detected or provided)
                sources     — List[Dict] (retrieved regulation sources)
                duration_sec— float
                error       — str | None
        """
        start   = time.time()
        context = context or {}
        self.session_ctx.update(context)

        result: Dict[str, Any] = {
            "response":    "",
            "task_type":   task_type or "",
            "sources":     [],
            "duration_sec":0.0,
            "error":       None,
        }

        try:
            # Auto-detect task type
            detected_task = task_type or self._detect_task(query, context)
            result["task_type"] = detected_task
            logger.info("GovernanceAgent.run | task=%s | query='%s'", detected_task, query[:80])

            # Route to sub-agent
            if detected_task == "regulatory_qa":
                from agents.regulatory_research_agent import RegulatoryResearchAgent
                sub  = RegulatoryResearchAgent(provider=self.provider)
                resp = sub.answer(query, framework=context.get("framework"))
                result["response"] = resp["answer"]
                result["sources"]  = resp.get("sources", [])

            elif detected_task == "risk_assessment":
                from agents.risk_scoring_agent import RiskScoringAgent
                sub  = RiskScoringAgent(provider=self.provider)
                resp = sub.assess(
                    system_description=context.get("system_description", query)
                )
                result["response"] = resp["summary"]
                result["sources"]  = []

            elif detected_task == "policy_generation":
                from agents.policy_analysis_agent import PolicyAnalysisAgent
                sub  = PolicyAnalysisAgent(provider=self.provider)
                resp = sub.generate_section(
                    section_title=context.get("section_title", query),
                    framework=context.get("framework", "GDPR"),
                    org_context=context.get("org_context", ""),
                )
                result["response"] = resp["content"]

            elif detected_task == "remediation":
                from agents.remediation_agent import RemediationAgent
                sub  = RemediationAgent(provider=self.provider)
                resp = sub.build_plan(
                    finding=context.get("finding", {}),
                    framework=context.get("framework", "GDPR"),
                    org_context=context.get("org_context", ""),
                )
                result["response"] = resp["plan"]

            elif detected_task == "pii_scan":
                from compliance.pii_detector import detect_pii, pii_risk_summary
                text    = context.get("text", query)
                found   = detect_pii(text)
                summary = pii_risk_summary(found)
                result["response"] = self._format_pii_response(found, summary)

            elif detected_task == "executive_summary":
                from llm.router import route_executive_summary
                result["response"] = route_executive_summary(
                    findings=context.get("findings", []),
                    framework=context.get("framework", "GDPR"),
                    policy_name=context.get("policy_name", "Policy Document"),
                    org_name=context.get("org_name", "the organisation"),
                    provider=self.provider,
                )

            else:
                # Default: governance chat with RAG
                response = self._chat(query, stream=stream)
                result["response"] = response

            # Update conversation history
            self.history.append({"role": "user",      "content": query})
            self.history.append({"role": "assistant",  "content": str(result["response"])[:500]})

        except Exception as exc:
            logger.error("GovernanceAgent.run failed: %s", exc)
            result["error"]    = str(exc)
            result["response"] = (
                f"I encountered an error processing your request: {exc}. "
                "Please check your configuration and try again."
            )

        result["duration_sec"] = round(time.time() - start, 2)
        return result

    # ── Chat ──────────────────────────────────────────────────────────────────

    def _chat(self, query: str, stream: bool = False) -> Any:
        """Run a governance chat turn with RAG context injection."""
        from llm.router import route_chat
        from rag.retrieval_tools import retrieve_for_question, format_context_for_prompt

        # Retrieve relevant regulations
        framework = self.session_ctx.get("framework")
        regs      = retrieve_for_question(query, framework=framework, k=3)
        context   = format_context_for_prompt(regs) if regs else None

        # Build messages with history
        messages = self._build_messages(query)

        return route_chat(
            messages=messages,
            rag_context=context,
            provider=self.provider,
            stream=stream,
        )

    def _build_messages(self, query: str) -> List[Dict[str, str]]:
        """Build message list with recent history for context."""
        from llm.prompts import GOVERNANCE_CHAT_SYSTEM
        messages = [{"role": "system", "content": GOVERNANCE_CHAT_SYSTEM}]
        # Include last 6 turns of history
        messages.extend(self.history[-6:])
        messages.append({"role": "user", "content": query})
        return messages

    # ── Task detection ────────────────────────────────────────────────────────

    def _detect_task(self, query: str, context: Dict[str, Any]) -> str:
        """Detect the appropriate task type from query and context."""
        q = query.lower()

        if context.get("finding") or any(kw in q for kw in ["fix", "remediate", "remediation", "how to fix", "resolve"]):
            return "remediation"
        if context.get("system_description") or any(kw in q for kw in ["risk", "assess", "score", "ai system"]):
            return "risk_assessment"
        if context.get("findings") and any(kw in q for kw in ["summary", "executive", "board", "report"]):
            return "executive_summary"
        if any(kw in q for kw in ["draft", "write policy", "generate policy", "create policy", "policy section"]):
            return "policy_generation"
        if context.get("text") and any(kw in q for kw in ["pii", "personal data", "scan", "detect"]):
            return "pii_scan"
        if any(kw in q for kw in ["article", "regulation", "requirement", "what does", "explain", "define", "gdpr", "hipaa", "iso", "pci", "soc 2"]):
            return "regulatory_qa"

        return "compliance_chat"

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _format_pii_response(
        self,
        found: Dict[str, List[str]],
        summary: Dict[str, Any],
    ) -> str:
        if not found:
            return "✅ No PII detected in the provided text."

        lines = [
            f"🔍 PII Detection Report",
            f"Overall Risk: {summary.get('overall_risk', 'Unknown')}",
            f"Total Types Found: {summary.get('total_types', 0)}",
            f"Total Instances: {summary.get('total_instances', 0)}",
            "",
            "Detected PII Types:",
        ]
        for pii_type, values in found.items():
            lines.append(f"  • {pii_type}: {len(values)} instance(s)")

        lines.append("\nRecommendations:")
        for rec in summary.get("recommendations", [])[:3]:
            lines.append(f"  • {rec}")

        return "\n".join(lines)

    def clear_history(self) -> None:
        """Clear conversation history and session context."""
        self.history      = []
        self.session_ctx  = {}
        logger.info("GovernanceAgent: history cleared.")

    def get_history(self) -> List[Dict[str, str]]:
        """Return the full conversation history."""
        return list(self.history)