"""
models/finding_models.py — Compliance finding data model for Nexus AI Governance Platform.

The Finding model represents a single compliance violation identified
by the LLM audit engine. Used across compliance engine, agents, UI, and exports.

Usage:
    from models.finding_models import Finding, FindingSummary, FindingFilter

    finding = Finding(
        violated_string="We store data indefinitely.",
        legal_reference="GDPR Article 5(1)(e)",
        severity="Critical",
        explanation="Violates storage limitation principle.",
        corrected_version="Data shall be retained for no longer than [X months].",
        confidence_score=0.97,
        department="Engineering",
        remediation_steps=["Define retention periods", "Implement auto-deletion"],
    )
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class Finding(BaseModel):
    """
    A single compliance violation finding produced by the LLM audit engine.

    All fields map directly to the JSON schema returned by the LLM.
    Extra fields returned by the LLM are silently ignored.
    """

    # ── Core fields ───────────────────────────────────────────────────────────
    violated_string: str = Field(
        description="The exact sentence or clause from the policy that violates the regulation.",
        default="",
    )
    legal_reference: str = Field(
        description="Specific article / section / requirement being violated (e.g. 'GDPR Article 5(1)(e)').",
        default="",
    )
    severity: str = Field(
        description="Severity level: Critical | High | Medium | Low",
        default="Medium",
    )
    explanation: str = Field(
        description="Clear explanation of why this clause violates the regulation.",
        default="",
    )
    corrected_version: str = Field(
        description="A fully compliant rewrite of the violated clause.",
        default="",
    )
    confidence_score: float = Field(
        ge=0.0, le=1.0,
        description="LLM confidence in this finding (0.0–1.0).",
        default=0.75,
    )
    department: str = Field(
        description="Team responsible for remediation (e.g. 'Engineering', 'Legal').",
        default="General",
    )
    remediation_steps: List[str] = Field(
        description="Ordered list of concrete remediation actions.",
        default_factory=list,
    )

    # ── Optional enrichment fields ────────────────────────────────────────────
    framework: Optional[str] = Field(
        description="Compliance framework this finding belongs to.",
        default=None,
    )
    regulation_id: Optional[str] = Field(
        description="Internal regulation ID from the knowledge base.",
        default=None,
    )
    tags: List[str] = Field(
        description="Optional tags for filtering (e.g. ['encryption', 'consent']).",
        default_factory=list,
    )

    model_config = {"extra": "ignore", "populate_by_name": True}

    # ── Validators ────────────────────────────────────────────────────────────

    @field_validator("severity", mode="before")
    @classmethod
    def normalise_severity(cls, v: Any) -> str:
        """Normalise severity to title case and validate."""
        allowed = {"Critical", "High", "Medium", "Low"}
        if isinstance(v, str):
            title = v.strip().capitalize()
            if title in allowed:
                return title
            # Try case-insensitive match
            for a in allowed:
                if v.strip().lower() == a.lower():
                    return a
        return "Medium"

    @field_validator("confidence_score", mode="before")
    @classmethod
    def normalise_confidence(cls, v: Any) -> float:
        """Ensure confidence is a float between 0 and 1."""
        try:
            f = float(v)
            return max(0.0, min(1.0, f))
        except (TypeError, ValueError):
            return 0.75

    @field_validator("remediation_steps", mode="before")
    @classmethod
    def ensure_list(cls, v: Any) -> List[str]:
        """Accept string or list for remediation_steps."""
        if isinstance(v, str):
            return [v] if v.strip() else []
        if isinstance(v, list):
            return [str(s) for s in v if s]
        return []

    # ── Computed properties ───────────────────────────────────────────────────

    @property
    def severity_score(self) -> int:
        """Numeric severity score for sorting (4=Critical, 1=Low)."""
        return {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}.get(self.severity, 2)

    @property
    def severity_color(self) -> str:
        """Hex color for this finding's severity level."""
        return {
            "Critical": "#ff4757",
            "High":     "#ffc847",
            "Medium":   "#3b7ff5",
            "Low":      "#00e5a0",
        }.get(self.severity, "#8a9bbc")

    @property
    def severity_emoji(self) -> str:
        """Emoji for this finding's severity level."""
        return {"Critical": "🔴", "High": "🟠", "Medium": "🔵", "Low": "🟢"}.get(self.severity, "⚪")

    @property
    def is_critical_or_high(self) -> bool:
        """True if this finding requires immediate attention."""
        return self.severity in ("Critical", "High")

    @property
    def short_violation(self) -> str:
        """First 120 chars of violated_string for display."""
        return self.violated_string[:120] + ("…" if len(self.violated_string) > 120 else "")

    @property
    def short_explanation(self) -> str:
        """First 200 chars of explanation for display."""
        return self.explanation[:200] + ("…" if len(self.explanation) > 200 else "")

    # ── Utility methods ───────────────────────────────────────────────────────

    def to_display_dict(self) -> Dict[str, Any]:
        """Return a flat dict optimised for Streamlit table / dataframe display."""
        return {
            "Severity":       f"{self.severity_emoji} {self.severity}",
            "Regulation":     self.legal_reference,
            "Department":     self.department,
            "Confidence":     f"{self.confidence_score:.0%}",
            "Violation":      self.short_violation,
            "Explanation":    self.short_explanation,
        }

    def to_csv_row(self) -> Dict[str, str]:
        """Return a flat dict suitable for CSV export."""
        return {
            "severity":          self.severity,
            "legal_reference":   self.legal_reference,
            "department":        self.department,
            "confidence_score":  str(self.confidence_score),
            "violated_string":   self.violated_string[:300],
            "explanation":       self.explanation[:300],
            "corrected_version": self.corrected_version[:300],
            "remediation_steps": " | ".join(self.remediation_steps),
        }

    def __str__(self) -> str:
        return f"[{self.severity}] {self.legal_reference} (confidence={self.confidence_score:.0%})"

    def __repr__(self) -> str:
        return f"Finding(severity={self.severity!r}, ref={self.legal_reference!r})"


# ══════════════════════════════════════════════════════════════════════════════
# FINDING SUMMARY (lightweight, for display tables)
# ══════════════════════════════════════════════════════════════════════════════

class FindingSummary(BaseModel):
    """
    Lightweight summary of a Finding for display in tables and lists.
    Avoids carrying the full text fields.
    """
    severity:        str
    legal_reference: str
    department:      str
    confidence_score:float
    severity_color:  str = ""
    severity_emoji:  str = ""

    @classmethod
    def from_finding(cls, f: Finding) -> "FindingSummary":
        return cls(
            severity=f.severity,
            legal_reference=f.legal_reference,
            department=f.department,
            confidence_score=f.confidence_score,
            severity_color=f.severity_color,
            severity_emoji=f.severity_emoji,
        )


# ══════════════════════════════════════════════════════════════════════════════
# FINDING FILTER (for querying findings lists)
# ══════════════════════════════════════════════════════════════════════════════

class FindingFilter(BaseModel):
    """
    Filter criteria for querying a list of findings.

    Usage:
        filt    = FindingFilter(severity=["Critical", "High"], department="Engineering")
        results = filt.apply(findings)
    """
    severity:         Optional[List[str]] = None
    department:       Optional[str]       = None
    framework:        Optional[str]       = None
    min_confidence:   float               = 0.0
    legal_reference:  Optional[str]       = None

    def apply(self, findings: List[Finding]) -> List[Finding]:
        """Apply this filter to a list of findings."""
        result = findings

        if self.severity:
            result = [f for f in result if f.severity in self.severity]
        if self.department:
            result = [f for f in result if self.department.lower() in f.department.lower()]
        if self.framework:
            result = [f for f in result if f.framework == self.framework]
        if self.min_confidence > 0:
            result = [f for f in result if f.confidence_score >= self.min_confidence]
        if self.legal_reference:
            result = [f for f in result
                      if self.legal_reference.lower() in f.legal_reference.lower()]

        return result


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def sort_findings_by_severity(findings: List[Finding]) -> List[Finding]:
    """Sort findings from Critical → Low by severity score."""
    return sorted(findings, key=lambda f: f.severity_score, reverse=True)


def filter_by_severity(findings: List[Finding], severity: str) -> List[Finding]:
    """Return only findings of a specific severity."""
    return [f for f in findings if f.severity == severity]


def count_by_severity(findings: List[Finding]) -> Dict[str, int]:
    """Return a dict of severity → count."""
    counts: Dict[str, int] = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    return counts


def findings_to_dataframe(findings: List[Finding]):
    """Convert a list of findings to a pandas DataFrame for display."""
    try:
        import pandas as pd
        return pd.DataFrame([f.to_display_dict() for f in findings])
    except ImportError:
        return [f.to_display_dict() for f in findings]