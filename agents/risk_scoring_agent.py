"""
agents/risk_scoring_agent.py — AI system risk scoring agent for Nexus AI Governance Platform.

Evaluates AI systems for governance risks across:
  - Bias & Fairness
  - Transparency & Explainability
  - Privacy & Data Protection
  - Security & Robustness
  - Human Oversight & Control
  - Legal & Regulatory Compliance
  - Operational Risk

Aligned with NIST AI RMF and EU AI Act classification.

Usage:
    from agents.risk_scoring_agent import RiskScoringAgent

    agent  = RiskScoringAgent()
    result = agent.assess("We use an ML model to automate loan decisions...")
    result = agent.classify_eu_ai_act("Facial recognition system for employee access control")
"""

import json
import re
import time
from typing import Any, Dict, List, Optional

from config.logging_config import get_logger

logger = get_logger("nexus.agents.risk_scoring")

# Risk categories assessed
RISK_CATEGORIES = [
    "Bias & Fairness",
    "Transparency & Explainability",
    "Privacy & Data Protection",
    "Security & Robustness",
    "Human Oversight & Control",
    "Legal & Regulatory Compliance",
    "Operational Risk",
]

# EU AI Act risk levels
EU_AI_ACT_LEVELS = [
    "Unacceptable Risk",
    "High Risk",
    "Limited Risk",
    "Minimal Risk",
]


class RiskScoringAgent:
    """
    AI governance risk scoring agent aligned with NIST AI RMF and EU AI Act.

    Workflow:
        1. Send system description to LLM with RISK_ASSESSMENT_SYSTEM prompt
        2. Parse JSON risk findings
        3. Calculate aggregate risk score
        4. Classify under EU AI Act
        5. Return structured risk report
    """

    def __init__(self, provider: Optional[str] = None) -> None:
        self.provider = provider
        logger.info("RiskScoringAgent initialised | provider=%s", provider or "auto")

    # ── Main assessment ───────────────────────────────────────────────────────

    def assess(
        self,
        system_description: str,
        system_name: str = "AI System",
    ) -> Dict[str, Any]:
        """
        Perform a full AI governance risk assessment.

        Args:
            system_description: Description of the AI system to assess.
            system_name:        Name of the system (for reporting).

        Returns:
            Dict with:
                risks           — List[Dict] (individual risk findings)
                overall_score   — float (0–100, higher = more risk)
                risk_level      — str (Low/Medium/High/Critical)
                risk_color      — str (hex)
                eu_ai_act       — str (EU AI Act classification)
                nist_rmf        — Dict (NIST RMF function mapping)
                summary         — str (LLM-generated narrative)
                recommendations — List[str]
                duration        — float
        """
        start = time.time()
        logger.info("RiskScoringAgent.assess | system='%s'", system_name)

        result: Dict[str, Any] = {
            "system_name":     system_name,
            "risks":           [],
            "overall_score":   0.0,
            "risk_level":      "Low",
            "risk_color":      "#00e5a0",
            "eu_ai_act":       "Minimal Risk",
            "nist_rmf":        {},
            "summary":         "",
            "recommendations": [],
            "duration":        0.0,
        }

        try:
            # Call LLM for risk assessment
            from llm.router import route
            raw = route(
                task="risk_assessment",
                payload={"system_description": system_description},
                provider=self.provider,
            )

            # Parse risks
            risks = self._parse_risks(raw)
            result["risks"] = risks

            # Score and classify
            score              = self._calculate_risk_score(risks)
            result["overall_score"] = score
            result["risk_level"]    = self._risk_level(score)
            result["risk_color"]    = self._risk_color(score)
            result["eu_ai_act"]     = self.classify_eu_ai_act(system_description)
            result["nist_rmf"]      = self._nist_rmf_mapping(risks)
            result["recommendations"] = self._top_recommendations(risks)
            result["summary"]       = self._generate_summary(risks, score, result["eu_ai_act"])

        except Exception as exc:
            logger.error("RiskScoringAgent.assess failed: %s", exc)
            result["summary"] = f"Risk assessment encountered an error: {exc}"

        result["duration"] = round(time.time() - start, 2)
        return result

    # ── EU AI Act classification ───────────────────────────────────────────────

    def classify_eu_ai_act(self, system_description: str) -> str:
        """
        Classify an AI system under the EU AI Act risk tiers.

        Args:
            system_description: Description of the AI system.

        Returns:
            One of: "Unacceptable Risk", "High Risk", "Limited Risk", "Minimal Risk"
        """
        desc = system_description.lower()

        # Unacceptable risk — prohibited systems
        unacceptable_keywords = [
            "social scoring", "mass surveillance", "subliminal manipulation",
            "exploit vulnerabilities", "real-time biometric surveillance",
            "emotion recognition workplace", "untargeted facial scraping",
        ]
        if any(kw in desc for kw in unacceptable_keywords):
            return "Unacceptable Risk"

        # High risk — regulated sectors
        high_risk_keywords = [
            "credit scoring", "loan decision", "hiring", "recruitment",
            "criminal justice", "law enforcement", "border control",
            "medical diagnosis", "clinical decision", "safety critical",
            "critical infrastructure", "biometric", "educational assessment",
            "employment decision", "benefits", "insurance underwriting",
        ]
        if any(kw in desc for kw in high_risk_keywords):
            return "High Risk"

        # Limited risk — transparency obligations
        limited_risk_keywords = [
            "chatbot", "deepfake", "emotion recognition", "content generation",
            "recommendation system", "advertising", "synthetic content",
        ]
        if any(kw in desc for kw in limited_risk_keywords):
            return "Limited Risk"

        return "Minimal Risk"

    # ── Parsers ───────────────────────────────────────────────────────────────

    def _parse_risks(self, raw: str) -> List[Dict[str, Any]]:
        """Parse LLM JSON output into risk finding dicts."""
        try:
            cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`")
            data    = json.loads(cleaned)

            if isinstance(data, dict):
                for key in ("risks", "findings", "results", "items"):
                    if key in data and isinstance(data[key], list):
                        data = data[key]
                        break

            if not isinstance(data, list):
                return self._mock_risks()

            return data

        except (json.JSONDecodeError, Exception) as exc:
            logger.warning("Risk JSON parse failed: %s — using mock risks.", exc)
            return self._mock_risks()

    def _mock_risks(self) -> List[Dict[str, Any]]:
        """Return deterministic mock risks when LLM is unavailable."""
        return [
            {
                "risk_category":        "Bias & Fairness",
                "risk_description":     "Model may exhibit bias if training data is not representative of all demographic groups.",
                "likelihood":           3,
                "impact":               4,
                "risk_score":           12,
                "mitigation_strategy":  "Conduct bias audits, use diverse training data, implement fairness metrics.",
                "eu_ai_act_classification": "High Risk",
                "nist_rmf_function":    "Measure",
            },
            {
                "risk_category":        "Transparency & Explainability",
                "risk_description":     "Decisions may not be explainable to affected individuals as required by GDPR Art. 22.",
                "likelihood":           3,
                "impact":               3,
                "risk_score":           9,
                "mitigation_strategy":  "Implement LIME/SHAP explainability. Provide human review for high-stakes decisions.",
                "eu_ai_act_classification": "High Risk",
                "nist_rmf_function":    "Govern",
            },
            {
                "risk_category":        "Human Oversight & Control",
                "risk_description":     "Insufficient human-in-the-loop controls for high-stakes automated decisions.",
                "likelihood":           2,
                "impact":               4,
                "risk_score":           8,
                "mitigation_strategy":  "Implement mandatory human review for decisions above risk threshold.",
                "eu_ai_act_classification": "High Risk",
                "nist_rmf_function":    "Manage",
            },
        ]

    # ── Scoring ───────────────────────────────────────────────────────────────

    def _calculate_risk_score(self, risks: List[Dict[str, Any]]) -> float:
        """
        Calculate aggregate risk score (0–100).
        Based on average of individual risk scores (likelihood × impact, max 25).
        """
        if not risks:
            return 0.0

        scores = []
        for r in risks:
            score = r.get("risk_score", r.get("likelihood", 1) * r.get("impact", 1))
            scores.append(float(score))

        # Normalise to 0–100 (individual max = 25)
        avg_score = sum(scores) / len(scores)
        return round(min(100.0, (avg_score / 25.0) * 100.0), 1)

    def _risk_level(self, score: float) -> str:
        if score >= 75: return "Critical"
        if score >= 50: return "High"
        if score >= 25: return "Medium"
        return "Low"

    def _risk_color(self, score: float) -> str:
        if score >= 75: return "#ff4757"
        if score >= 50: return "#ff8c42"
        if score >= 25: return "#ffc847"
        return "#00e5a0"

    def _nist_rmf_mapping(self, risks: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Map risks to NIST AI RMF functions."""
        mapping: Dict[str, List[str]] = {
            "Govern": [], "Map": [], "Measure": [], "Manage": []
        }
        for r in risks:
            fn  = r.get("nist_rmf_function", "Manage")
            cat = r.get("risk_category", "General Risk")
            if fn in mapping:
                mapping[fn].append(cat)
        return {k: v for k, v in mapping.items() if v}

    def _top_recommendations(self, risks: List[Dict[str, Any]]) -> List[str]:
        """Extract top mitigation strategies sorted by risk score."""
        sorted_risks = sorted(risks, key=lambda r: r.get("risk_score", 0), reverse=True)
        return [r["mitigation_strategy"] for r in sorted_risks[:5] if r.get("mitigation_strategy")]

    def _generate_summary(self, risks: List[Dict[str, Any]], score: float, eu_act: str) -> str:
        """Generate a narrative summary of the risk assessment."""
        level = self._risk_level(score)
        cats  = [r.get("risk_category", "") for r in risks]
        return (
            f"Risk Assessment Summary: {level} overall risk (score: {score}/100). "
            f"EU AI Act Classification: {eu_act}. "
            f"{len(risks)} risk area(s) identified: {', '.join(cats[:4])}. "
            "See individual findings for detailed mitigation strategies."
        )