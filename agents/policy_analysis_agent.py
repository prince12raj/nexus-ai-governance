"""
agents/policy_analysis_agent.py — Policy analysis and generation agent for Nexus AI Governance Platform.

Handles:
  - Policy document summarisation
  - Gap analysis against a framework
  - Compliant policy section generation
  - Policy comparison (old vs new)
  - Readability scoring

Usage:
    from agents.policy_analysis_agent import PolicyAnalysisAgent

    agent   = PolicyAnalysisAgent()
    summary = agent.summarise("path/to/policy.txt", text=policy_text)
    gap     = agent.gap_analysis(policy_text, framework="GDPR")
    draft   = agent.generate_section("Data Retention Policy", framework="GDPR")
"""
from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional

from config.logging_config import get_logger

logger = get_logger("nexus.agents.policy_analysis")


class PolicyAnalysisAgent:
    """
    Policy analysis and generation agent.

    Capabilities:
        summarise()        — Summarise an uploaded policy document
        gap_analysis()     — Identify what the policy is missing for a framework
        generate_section() — Draft a fully compliant policy section
        compare()          — Compare two versions of a policy
        readability()      — Score readability and plain-language compliance
    """

    def __init__(self, provider: Optional[str] = None) -> None:
        self.provider = provider
        logger.info("PolicyAnalysisAgent initialised | provider=%s", provider or "auto")

    # ── Summarise ─────────────────────────────────────────────────────────────

    def summarise(
        self,
        text: str,
        doc_name: str = "Policy Document",
    ) -> Dict[str, Any]:
        """
        Summarise a policy document.

        Args:
            text:     Full document text.
            doc_name: Document name for reference.

        Returns:
            Dict with summary, key_points, word_count, readability_score.
        """
        start = time.time()
        logger.info("PolicyAnalysisAgent.summarise | doc='%s' | len=%d", doc_name, len(text))

        try:
            from llm.router import route
            summary = route(
                task="document_summary",
                payload={"document_text": text, "doc_name": doc_name},
                provider=self.provider,
            )
        except Exception as exc:
            logger.warning("Summarise LLM call failed: %s", exc)
            summary = self._extractive_summary(text)

        return {
            "summary":          summary,
            "doc_name":         doc_name,
            "word_count":       len(text.split()),
            "char_count":       len(text),
            "readability_score":self._readability_score(text),
            "key_sections":     self._extract_sections(text),
            "duration":         round(time.time() - start, 2),
        }

    # ── Gap analysis ──────────────────────────────────────────────────────────

    def gap_analysis(
        self,
        policy_text: str,
        framework: str = "GDPR",
    ) -> Dict[str, Any]:
        """
        Identify gaps in a policy document against a compliance framework.

        Args:
            policy_text: Policy document text.
            framework:   Framework to check against.

        Returns:
            Dict with gaps, present_elements, missing_elements, coverage_score.
        """
        start = time.time()
        logger.info("PolicyAnalysisAgent.gap_analysis | framework=%s | len=%d", framework, len(policy_text))

        # Get required elements for this framework
        required = self._required_elements(framework)

        # Check what's present
        present  = []
        missing  = []
        text_low = policy_text.lower()

        for element in required:
            keywords = element.get("keywords", [])
            if any(kw in text_low for kw in keywords):
                present.append(element["name"])
            else:
                missing.append(element)

        coverage_score = round((len(present) / len(required)) * 100, 1) if required else 100.0

        # Ask LLM for detailed gap analysis
        try:
            from llm.router import route
            gap_prompt = (
                f"Analyse this {framework} policy for compliance gaps. "
                f"Known missing elements: {[m['name'] for m in missing]}. "
                f"Provide specific recommendations for each gap.\n\n"
                f"POLICY:\n{policy_text[:2500]}"
            )
            analysis = route(
                task="regulatory_qa",
                payload={"question": gap_prompt},
                provider=self.provider,
            )
        except Exception as exc:
            logger.warning("Gap analysis LLM call failed: %s", exc)
            analysis = self._format_gap_summary(missing, framework)

        return {
            "framework":       framework,
            "coverage_score":  coverage_score,
            "present_elements":present,
            "missing_elements":[m["name"] for m in missing],
            "missing_details": missing,
            "analysis":        analysis,
            "recommendation":  f"Policy covers {coverage_score}% of {framework} requirements. "
                               f"{len(missing)} element(s) need attention.",
            "duration":        round(time.time() - start, 2),
        }

    # ── Generate policy section ───────────────────────────────────────────────

    def generate_section(
        self,
        section_title: str,
        framework: str = "GDPR",
        org_context: str = "",
        org_type: str = "organisation",
    ) -> Dict[str, Any]:
        """
        Draft a fully compliant policy section.

        Args:
            section_title: Title of the section to generate (e.g. "Data Retention Policy").
            framework:     Target compliance framework.
            org_context:   Optional context about the organisation.
            org_type:      Type of organisation (e.g. "healthcare provider").

        Returns:
            Dict with content, word_count, framework, section_title.
        """
        start = time.time()
        logger.info(
            "PolicyAnalysisAgent.generate_section | section='%s' | framework=%s",
            section_title, framework
        )

        try:
            from llm.router import route
            content = route(
                task="policy_generation",
                payload={
                    "section_title": section_title,
                    "framework":     framework,
                    "context":       org_context,
                    "org_type":      org_type,
                },
                provider=self.provider,
            )
        except Exception as exc:
            logger.warning("Generate section LLM call failed: %s", exc)
            content = self._fallback_section(section_title, framework)

        return {
            "content":       content,
            "section_title": section_title,
            "framework":     framework,
            "word_count":    len(content.split()),
            "duration":      round(time.time() - start, 2),
        }

    # ── Compare policy versions ───────────────────────────────────────────────

    def compare(
        self,
        old_text: str,
        new_text: str,
        framework: str = "GDPR",
    ) -> Dict[str, Any]:
        """
        Compare two versions of a policy document.

        Args:
            old_text:  Previous version text.
            new_text:  Updated version text.
            framework: Framework for compliance context.

        Returns:
            Dict with improvements, regressions, unchanged, overall_assessment.
        """
        start = time.time()
        logger.info("PolicyAnalysisAgent.compare | framework=%s", framework)

        old_sections = set(self._extract_sections(old_text))
        new_sections = set(self._extract_sections(new_text))
        added        = new_sections - old_sections
        removed      = old_sections - new_sections

        try:
            from llm.router import route
            comparison_prompt = (
                f"Compare these two versions of a {framework} policy document. "
                "Identify: (1) compliance improvements, (2) potential regressions, "
                "(3) sections that need further attention.\n\n"
                f"OLD VERSION (first 1000 chars):\n{old_text[:1000]}\n\n"
                f"NEW VERSION (first 1000 chars):\n{new_text[:1000]}"
            )
            assessment = route(
                task="regulatory_qa",
                payload={"question": comparison_prompt},
                provider=self.provider,
            )
        except Exception as exc:
            logger.warning("Compare LLM call failed: %s", exc)
            assessment = "Automated comparison unavailable. Please review changes manually."

        return {
            "sections_added":   list(added),
            "sections_removed": list(removed),
            "old_word_count":   len(old_text.split()),
            "new_word_count":   len(new_text.split()),
            "overall_assessment":assessment,
            "framework":        framework,
            "duration":         round(time.time() - start, 2),
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _extractive_summary(self, text: str, sentences: int = 5) -> str:
        """Simple extractive summary — first N sentences."""
        parts = re.split(r"(?<=[.!?])\s+", text)
        return " ".join(parts[:sentences]) if parts else text[:500]

    def _readability_score(self, text: str) -> Dict[str, Any]:
        """Simple readability metrics."""
        words     = text.split()
        sentences = re.split(r"[.!?]+", text)
        sentences = [s for s in sentences if s.strip()]

        avg_words_per_sentence = len(words) / len(sentences) if sentences else 0
        avg_word_length        = sum(len(w) for w in words) / len(words) if words else 0

        # Simple score: lower avg sentence length and word length = more readable
        readability = max(0, min(100, 100 - (avg_words_per_sentence - 15) * 2))

        return {
            "score":                    round(readability, 1),
            "avg_words_per_sentence":   round(avg_words_per_sentence, 1),
            "avg_word_length":          round(avg_word_length, 1),
            "total_words":              len(words),
            "total_sentences":          len(sentences),
            "plain_language_rating":    "Good" if readability >= 70 else "Needs Improvement",
        }

    def _extract_sections(self, text: str) -> List[str]:
        """Extract section headings from document."""
        patterns = [
            r"(?m)^#{1,3}\s+(.+)$",                          # Markdown headers
            r"(?m)^(\d+\.?\d*\.?\s+[A-Z][^\n]{5,60})$",      # Numbered sections
            r"(?m)^([A-Z][A-Z\s]{4,40})$",                   # ALL CAPS headings
        ]
        sections = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            sections.extend(matches)

        return list(dict.fromkeys(sections))[:20]   # deduplicate, cap at 20

    def _required_elements(self, framework: str) -> List[Dict[str, Any]]:
        """Return required policy elements for a framework."""
        elements = {
            "GDPR": [
                {"name": "Data Controller Identity",      "keywords": ["controller", "data controller", "company name"]},
                {"name": "Lawful Basis for Processing",   "keywords": ["lawful basis", "legal basis", "consent", "legitimate interest"]},
                {"name": "Data Minimisation Statement",   "keywords": ["minimisation", "minimization", "necessary", "adequate, relevant"]},
                {"name": "Retention Periods",             "keywords": ["retention", "retain", "delete after", "kept for"]},
                {"name": "Data Subject Rights",           "keywords": ["right to access", "right to erasure", "data subject rights", "right to rectification"]},
                {"name": "Third Party Sharing",           "keywords": ["third party", "data sharing", "recipients", "processors"]},
                {"name": "International Transfers",       "keywords": ["transfer", "international", "third country", "adequacy decision"]},
                {"name": "Security Measures",             "keywords": ["encryption", "security", "technical measures", "safeguards"]},
                {"name": "DPO Contact Details",           "keywords": ["dpo", "data protection officer", "privacy contact"]},
                {"name": "Breach Notification",           "keywords": ["breach", "notification", "72 hours", "incident"]},
            ],
            "HIPAA": [
                {"name": "PHI Definition",                "keywords": ["phi", "protected health information", "health information"]},
                {"name": "Minimum Necessary Standard",    "keywords": ["minimum necessary", "least privilege", "need to know"]},
                {"name": "Access Controls",               "keywords": ["access control", "unique user", "authentication"]},
                {"name": "Encryption Requirements",       "keywords": ["encryption", "encrypt", "tls", "aes"]},
                {"name": "Breach Notification",           "keywords": ["breach", "notification", "hhs", "60 days"]},
                {"name": "BAA Requirements",              "keywords": ["business associate", "baa", "vendor agreement"]},
                {"name": "Patient Rights",                "keywords": ["patient rights", "access request", "amendment"]},
                {"name": "Audit Controls",                "keywords": ["audit", "logging", "access log", "monitoring"]},
            ],
            "ISO 27001": [
                {"name": "Information Security Policy",   "keywords": ["information security policy", "isms", "security objectives"]},
                {"name": "Asset Classification",          "keywords": ["asset classification", "data classification", "confidential", "restricted"]},
                {"name": "Access Control Policy",         "keywords": ["access control", "rbac", "least privilege", "user access"]},
                {"name": "Cryptographic Policy",          "keywords": ["encryption", "cryptographic", "key management", "aes"]},
                {"name": "Incident Response",             "keywords": ["incident", "response", "security event", "escalation"]},
                {"name": "Business Continuity",           "keywords": ["business continuity", "disaster recovery", "rto", "rpo"]},
                {"name": "Supplier Security",             "keywords": ["supplier", "vendor", "third party", "supply chain"]},
                {"name": "Compliance Monitoring",         "keywords": ["compliance", "audit", "review", "monitoring"]},
            ],
            "SOC 2": [
                {"name": "Security Commitments",          "keywords": ["security", "safeguards", "controls"]},
                {"name": "Availability Commitments",      "keywords": ["availability", "uptime", "sla", "99."]},
                {"name": "Confidentiality Statement",     "keywords": ["confidential", "confidentiality", "nda"]},
                {"name": "Incident Response",             "keywords": ["incident", "breach", "response"]},
                {"name": "Change Management",             "keywords": ["change management", "change control", "release"]},
                {"name": "Vendor Management",             "keywords": ["vendor", "supplier", "third party"]},
            ],
            "PCI-DSS": [
                {"name": "Cardholder Data Scope",         "keywords": ["cardholder", "cde", "pan", "payment card"]},
                {"name": "Encryption Requirements",       "keywords": ["encryption", "tls", "aes", "tokenisation"]},
                {"name": "Access Control",                "keywords": ["access control", "mfa", "least privilege", "unique user"]},
                {"name": "Vulnerability Management",      "keywords": ["vulnerability", "patch", "scan", "penetration"]},
                {"name": "Logging and Monitoring",        "keywords": ["logging", "monitoring", "audit trail", "siem"]},
                {"name": "Incident Response",             "keywords": ["incident", "breach", "response", "forensics"]},
            ],
        }
        return elements.get(framework, [])

    def _format_gap_summary(self, missing: List[Dict[str, Any]], framework: str) -> str:
        """Format a text summary of missing policy elements."""
        if not missing:
            return f"The policy appears to cover the key {framework} requirements."
        lines = [f"The following {framework} required elements were not found in the policy:"]
        for m in missing:
            lines.append(f"  • {m['name']}")
        lines.append("\nRecommendation: Update the policy to explicitly address each missing element.")
        return "\n".join(lines)

    def _fallback_section(self, section_title: str, framework: str) -> str:
        """Return a generic policy section template."""
        return (
            f"# {section_title}\n\n"
            f"**Effective Date:** [DATE] | **Review Cycle:** Annual | "
            f"**Owner:** Compliance Team | **Framework:** {framework}\n\n"
            f"## Purpose\n"
            f"This policy establishes requirements for {section_title.lower()} "
            f"in compliance with {framework} obligations.\n\n"
            f"## Scope\n"
            f"This policy applies to all employees, contractors, and third parties who "
            f"process or have access to [ORGANISATION] data systems.\n\n"
            f"## Policy Statement\n"
            f"[ORGANISATION] shall implement and maintain controls to ensure compliance "
            f"with {framework} requirements relating to {section_title.lower()}.\n\n"
            f"## Responsibilities\n"
            f"- **Data Protection Officer:** Oversees policy implementation and compliance.\n"
            f"- **IT Security Team:** Implements and maintains technical controls.\n"
            f"- **All Staff:** Adhere to this policy and report violations immediately.\n\n"
            f"## Review and Updates\n"
            f"This policy shall be reviewed annually or when significant changes occur "
            f"to {framework} requirements or organisational operations."
        )