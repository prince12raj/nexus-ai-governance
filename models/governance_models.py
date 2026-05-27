"""
models/governance_models.py — Governance decision and risk models for Nexus AI Governance Platform.

Covers:
  - GovernanceDecision : human-in-the-loop approval record
  - RiskAssessment     : AI system risk scoring result
  - RiskFinding        : individual risk area from RiskScoringAgent

Usage:
    from models.governance_models import GovernanceDecision, RiskAssessment
"""

import datetime
import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class GovernanceDecision(BaseModel):
    """
    Human-in-the-loop governance decision record.

    Created when a compliance officer reviews and approves/rejects
    an audit finding or AI system risk assessment.
    """

    decision_id:         str = Field(default_factory=lambda: f"DEC-{uuid.uuid4().hex[:8].upper()}")
    report_id:           str = Field(default="", description="Associated AuditReport ID.")
    final_risk_level:    str = Field(description="Reviewer-confirmed risk level.")
    approved:            bool = Field(description="True if approved/accepted, False if rejected.")
    reviewer_notes:      str = Field(default="", description="Human reviewer comments.")
    escalation_required: bool = Field(default=False)
    reviewer_name:       str = Field(default="")
    reviewer_role:       str = Field(default="")
    decided_at:          str = Field(
        default_factory=lambda: datetime.datetime.now().isoformat()[:19]
    )
    framework:           str = Field(default="")
    action_items:        List[str] = Field(default_factory=list)

    model_config = {"extra": "ignore"}

    @field_validator("final_risk_level", mode="before")
    @classmethod
    def normalise_risk_level(cls, v: Any) -> str:
        allowed = {"Low Risk", "Medium Risk", "High Risk", "Critical Risk",
                   "Low", "Medium", "High", "Critical"}
        if isinstance(v, str) and v.strip() in allowed:
            return v.strip()
        return "Medium Risk"

    @property
    def status_label(self) -> str:
        if self.escalation_required:
            return "⚠️ Escalated"
        return "✅ Approved" if self.approved else "❌ Rejected"

    @property
    def status_color(self) -> str:
        if self.escalation_required:
            return "#ffc847"
        return "#00e5a0" if self.approved else "#ff4757"

    def to_display_dict(self) -> Dict[str, Any]:
        return {
            "Decision ID":   self.decision_id,
            "Status":        self.status_label,
            "Risk Level":    self.final_risk_level,
            "Reviewer":      self.reviewer_name,
            "Framework":     self.framework,
            "Decided At":    self.decided_at[:16],
            "Escalated":     "Yes" if self.escalation_required else "No",
        }

    def __str__(self) -> str:
        return (
            f"GovernanceDecision({self.decision_id}, "
            f"approved={self.approved}, risk={self.final_risk_level})"
        )


class RiskFinding(BaseModel):
    """
    A single risk area identified by the RiskScoringAgent.
    Maps directly to the JSON returned by the RISK_ASSESSMENT_SYSTEM prompt.
    """

    risk_category:          str   = Field(default="General Risk")
    risk_description:       str   = Field(default="")
    likelihood:             int   = Field(default=3, ge=1, le=5)
    impact:                 int   = Field(default=3, ge=1, le=5)
    risk_score:             int   = Field(default=9, ge=1, le=25)
    mitigation_strategy:    str   = Field(default="")
    eu_ai_act_classification: str = Field(default="Minimal Risk")
    nist_rmf_function:      str   = Field(default="Manage")

    model_config = {"extra": "ignore"}

    @field_validator("risk_score", mode="before")
    @classmethod
    def compute_score(cls, v: Any, info: Any) -> int:
        """Auto-compute likelihood × impact if not provided."""
        try:
            val = int(v)
            if val > 0:
                return min(25, val)
        except (TypeError, ValueError):
            pass
        try:
            data = info.data
            return int(data.get("likelihood", 3)) * int(data.get("impact", 3))
        except Exception:
            return 9

    @property
    def risk_level(self) -> str:
        if self.risk_score >= 20: return "Critical"
        if self.risk_score >= 12: return "High"
        if self.risk_score >= 6:  return "Medium"
        return "Low"

    @property
    def risk_color(self) -> str:
        colors = {
            "Critical": "#ff4757",
            "High":     "#ffc847",
            "Medium":   "#3b7ff5",
            "Low":      "#00e5a0",
        }
        return colors.get(self.risk_level, "#8a9bbc")

    def __str__(self) -> str:
        return (
            f"RiskFinding({self.risk_category!r}, "
            f"score={self.risk_score}/25, level={self.risk_level})"
        )


class RiskAssessment(BaseModel):
    """
    Full AI system risk assessment result from RiskScoringAgent.
    """

    assessment_id:   str = Field(default_factory=lambda: f"RSK-{uuid.uuid4().hex[:8].upper()}")
    system_name:     str = Field(default="AI System")
    system_description: str = Field(default="")
    overall_score:   float = Field(default=0.0, ge=0.0, le=100.0)
    risk_level:      str  = Field(default="Low")
    risk_color:      str  = Field(default="#00e5a0")
    eu_ai_act:       str  = Field(default="Minimal Risk")
    nist_rmf:        Dict[str, List[str]] = Field(default_factory=dict)
    risks:           List[RiskFinding]    = Field(default_factory=list)
    recommendations: List[str]            = Field(default_factory=list)
    summary:         str  = Field(default="")
    created_at:      str  = Field(
        default_factory=lambda: datetime.datetime.now().isoformat()[:19]
    )
    duration_sec:    float = Field(default=0.0)

    model_config = {"extra": "ignore"}

    @field_validator("risks", mode="before")
    @classmethod
    def validate_risks(cls, v: Any) -> List[RiskFinding]:
        if not isinstance(v, list):
            return []
        result = []
        for item in v:
            if isinstance(item, RiskFinding):
                result.append(item)
            elif isinstance(item, dict):
                try:
                    result.append(RiskFinding(**item))
                except Exception:
                    pass
        return result

    @property
    def is_high_risk(self) -> bool:
        return self.risk_level in ("High", "Critical")

    @property
    def eu_act_requires_conformity(self) -> bool:
        """True if EU AI Act classification requires conformity assessment."""
        return self.eu_ai_act in ("High Risk", "Unacceptable Risk")

    @property
    def top_risks(self) -> List[RiskFinding]:
        """Top 3 risks by score."""
        return sorted(self.risks, key=lambda r: r.risk_score, reverse=True)[:3]

    @property
    def risk_category_summary(self) -> Dict[str, int]:
        """Count risks per category."""
        counts: Dict[str, int] = {}
        for r in self.risks:
            counts[r.risk_category] = counts.get(r.risk_category, 0) + 1
        return counts

    def to_display_dict(self) -> Dict[str, Any]:
        return {
            "System":       self.system_name,
            "Score":        f"{self.overall_score:.0f}/100",
            "Risk Level":   self.risk_level,
            "EU AI Act":    self.eu_ai_act,
            "Risk Areas":   len(self.risks),
            "Assessed At":  self.created_at[:16],
        }

    def __str__(self) -> str:
        return (
            f"RiskAssessment({self.system_name!r}, "
            f"score={self.overall_score:.0f}, level={self.risk_level}, "
            f"eu_act={self.eu_ai_act})"
        )