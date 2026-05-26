"""
agents/remediation_agent.py — Compliance remediation planning agent for Nexus AI Governance Platform.

Generates detailed, actionable fix plans for compliance findings.
Prioritises by severity and organises steps by time horizon.

Usage:
    from agents.remediation_agent import RemediationAgent

    agent  = RemediationAgent()
    result = agent.build_plan(finding=finding_dict, framework="GDPR")
    result = agent.build_batch_plan(findings=findings_list, framework="GDPR")
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from config.logging_config import get_logger

logger = get_logger("nexus.agents.remediation")


class RemediationAgent:
    """
    Remediation planning agent — turns audit findings into actionable fix plans.

    Workflow:
        1. Accept a Finding (or list of Findings)
        2. Call LLM with REMEDIATION_SYSTEM prompt
        3. Structure output into time-horizon phases
        4. Assign owners and effort estimates
        5. Return prioritised remediation roadmap
    """

    def __init__(self, provider: Optional[str] = None) -> None:
        self.provider = provider
        logger.info("RemediationAgent initialised | provider=%s", provider or "auto")

    # ── Single finding plan ───────────────────────────────────────────────────

    def build_plan(
        self,
        finding: Any,
        framework: str = "GDPR",
        org_context: str = "",
    ) -> Dict[str, Any]:
        """
        Generate a remediation plan for a single compliance finding.

        Args:
            finding:     Finding object or dict with violation details.
            framework:   Compliance framework (e.g. "GDPR").
            org_context: Optional organisation context (tech stack, team structure).

        Returns:
            Dict with:
                plan        — str (full remediation plan)
                phases      — Dict (quick_wins, short_term, long_term)
                owner       — str (recommended responsible team)
                effort      — str (Low/Medium/High)
                priority    — int (1 = highest)
                finding_ref — str (legal reference)
                duration    — float
        """
        start = time.time()

        # Normalise finding to dict
        finding_dict = self._normalise_finding(finding)
        logger.info(
            "RemediationAgent.build_plan | framework=%s | severity=%s | ref=%s",
            framework,
            finding_dict.get("severity", "?"),
            finding_dict.get("legal_reference", "?")[:60],
        )

        try:
            from llm.router import route
            plan = route(
                task="remediation",
                payload={
                    "finding":     finding_dict,
                    "framework":   framework,
                    "org_context": org_context,
                },
                provider=self.provider,
            )
        except Exception as exc:
            logger.warning("RemediationAgent LLM call failed: %s — using structured fallback.", exc)
            plan = self._fallback_plan(finding_dict, framework)

        phases = self._extract_phases(plan, finding_dict)

        return {
            "plan":        plan,
            "phases":      phases,
            "owner":       finding_dict.get("department", "Compliance Team"),
            "effort":      self._estimate_effort(finding_dict),
            "priority":    self._priority_score(finding_dict),
            "finding_ref": finding_dict.get("legal_reference", ""),
            "severity":    finding_dict.get("severity", "Medium"),
            "duration":    round(time.time() - start, 2),
        }

    # ── Batch plan ────────────────────────────────────────────────────────────

    def build_batch_plan(
        self,
        findings: List[Any],
        framework: str = "GDPR",
        org_context: str = "",
    ) -> Dict[str, Any]:
        """
        Generate a prioritised remediation roadmap for multiple findings.

        Findings are sorted by severity before planning.
        Returns an ordered list of individual plans plus an executive roadmap.

        Args:
            findings:    List of Finding objects or dicts.
            framework:   Compliance framework.
            org_context: Optional organisation context.

        Returns:
            Dict with:
                plans       — List[Dict] (individual plans, sorted by priority)
                roadmap     — str (LLM-generated overall remediation roadmap)
                total       — int
                critical    — int
                duration    — float
        """
        start = time.time()
        logger.info("RemediationAgent.build_batch_plan | framework=%s | count=%d", framework, len(findings))

        # Sort by severity
        severity_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
        sorted_findings = sorted(
            findings,
            key=lambda f: severity_order.get(
                getattr(f, "severity", f.get("severity", "Low") if isinstance(f, dict) else "Low"),
                3,
            ),
        )

        plans: List[Dict[str, Any]] = []
        for i, finding in enumerate(sorted_findings[:10]):    # cap at 10 per batch
            plan = self.build_plan(finding, framework=framework, org_context=org_context)
            plan["priority"] = i + 1
            plans.append(plan)

        # Generate overall roadmap
        roadmap = self._generate_roadmap(plans, framework)

        return {
            "plans":    plans,
            "roadmap":  roadmap,
            "total":    len(findings),
            "critical": sum(
                1 for f in findings
                if getattr(f, "severity", getattr(f, "get", lambda k, d=None: d)("severity", "")) == "Critical"
            ),
            "duration": round(time.time() - start, 2),
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _normalise_finding(self, finding: Any) -> Dict[str, Any]:
        """Convert Finding object or dict to plain dict."""
        if isinstance(finding, dict):
            return finding
        # Pydantic model or object with attributes
        try:
            return finding.model_dump() if hasattr(finding, "model_dump") else finding.dict()
        except Exception:
            return {
                "violated_string":   getattr(finding, "violated_string",   ""),
                "legal_reference":   getattr(finding, "legal_reference",   ""),
                "severity":          getattr(finding, "severity",          "Medium"),
                "explanation":       getattr(finding, "explanation",        ""),
                "corrected_version": getattr(finding, "corrected_version",  ""),
                "department":        getattr(finding, "department",         "Compliance"),
                "remediation_steps": getattr(finding, "remediation_steps",  []),
            }

    def _fallback_plan(self, finding: Dict[str, Any], framework: str) -> str:
        """Generate a structured fallback plan from finding metadata."""
        steps = finding.get("remediation_steps", [])
        ref   = finding.get("legal_reference", "applicable regulation")
        sev   = finding.get("severity", "Medium")
        dept  = finding.get("department", "Compliance Team")

        lines = [
            f"Remediation Plan — {ref}",
            f"Severity: {sev} | Owner: {dept} | Framework: {framework}",
            "",
            "IMMEDIATE ACTIONS (0–7 days):",
        ]
        for i, step in enumerate(steps[:2], 1):
            lines.append(f"  {i}. {step}")

        lines += [
            "",
            "SHORT-TERM (1–4 weeks):",
        ]
        for i, step in enumerate(steps[2:4], 1):
            lines.append(f"  {i}. {step}")

        lines += [
            "",
            "LONG-TERM (1–3 months):",
        ]
        for i, step in enumerate(steps[4:], 1):
            lines.append(f"  {i}. {step}")
        if not steps[4:]:
            lines.append("  1. Schedule a full compliance review and update all related policies.")

        lines += [
            "",
            f"KPIs: Zero recurrence in next audit. Full {framework} compliance sign-off.",
        ]

        return "\n".join(lines)

    def _extract_phases(
        self,
        plan_text: str,
        finding: Dict[str, Any],
    ) -> Dict[str, List[str]]:
        """Extract time-horizon phases from plan text."""
        steps = finding.get("remediation_steps", [])

        # Simple split by position if we have steps
        if steps:
            return {
                "quick_wins":   steps[:2],
                "short_term":   steps[2:4],
                "long_term":    steps[4:] or ["Schedule annual review and policy update"],
            }

        # Parse from text
        quick: List[str]  = []
        short: List[str]  = []
        long_:  List[str] = []

        current = quick
        for line in plan_text.split("\n"):
            l = line.strip()
            if not l:
                continue
            if any(kw in l.lower() for kw in ["immediate", "0–7", "quick", "today", "now"]):
                current = quick
            elif any(kw in l.lower() for kw in ["short", "1–4 week", "month"]):
                current = short
            elif any(kw in l.lower() for kw in ["long", "strategic", "3 month", "quarter"]):
                current = long_
            elif l.startswith(("-", "•", "*")) or (len(l) > 3 and l[0].isdigit()):
                current.append(l.lstrip("-•*0123456789. "))

        return {
            "quick_wins": quick[:3] or ["Review and assess current state"],
            "short_term": short[:3] or ["Implement primary control changes"],
            "long_term":  long_[:3] or ["Establish ongoing monitoring and review cycle"],
        }

    def _estimate_effort(self, finding: Dict[str, Any]) -> str:
        """Estimate remediation effort based on severity and department."""
        sev  = finding.get("severity", "Medium")
        dept = finding.get("department", "")

        if sev == "Critical":
            return "High"
        if sev == "High" or "Engineering" in dept:
            return "Medium"
        return "Low"

    def _priority_score(self, finding: Dict[str, Any]) -> int:
        """Return a numeric priority (1 = highest)."""
        order = {"Critical": 1, "High": 2, "Medium": 3, "Low": 4}
        return order.get(finding.get("severity", "Medium"), 3)

    def _generate_roadmap(self, plans: List[Dict[str, Any]], framework: str) -> str:
        """Generate a high-level remediation roadmap summary."""
        if not plans:
            return "No findings to remediate."

        critical = [p for p in plans if p.get("severity") == "Critical"]
        high     = [p for p in plans if p.get("severity") == "High"]

        lines = [
            f"REMEDIATION ROADMAP — {framework}",
            f"Total findings: {len(plans)} | Critical: {len(critical)} | High: {len(high)}",
            "",
            "PHASE 1 — IMMEDIATE (Week 1):",
        ]
        for p in plans[:2]:
            lines.append(f"  • [{p.get('severity')}] {p.get('finding_ref', '')} — Owner: {p.get('owner', '')}")

        if len(plans) > 2:
            lines += ["", "PHASE 2 — SHORT-TERM (Weeks 2–4):"]
            for p in plans[2:5]:
                lines.append(f"  • [{p.get('severity')}] {p.get('finding_ref', '')} — Effort: {p.get('effort', '')}")

        if len(plans) > 5:
            lines += ["", "PHASE 3 — LONG-TERM (Month 2–3):"]
            for p in plans[5:]:
                lines.append(f"  • [{p.get('severity')}] {p.get('finding_ref', '')}")

        lines += [
            "",
            "SUCCESS CRITERIA:",
            f"  • All Critical and High findings resolved within 30 days",
            f"  • Full {framework} compliance audit passed",
            "  • Zero recurrence in next quarterly review",
        ]

        return "\n".join(lines)