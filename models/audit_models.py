"""
models/audit_models.py — Audit report data models for Nexus AI Governance Platform.

Covers:
  - AuditReport     : full compliance audit result (stored in session history)
  - AuditSummary    : lightweight version for list display
  - AuditComparison : diff between two audit reports
  - RemediationPlan : structured remediation roadmap from RemediationAgent

Usage:
    from models.audit_models import AuditReport, AuditSummary

    report = AuditReport(
        compliance_score=72.5,
        executive_summary="...",
        framework_targeted="GDPR",
        total_findings=8,
        critical_findings=2,
        generated_timestamp="2024-01-15T09:41:22",
        findings=[...],
    )
    print(report.grade)          # "B-"
    print(report.risk_level)     # "Medium Risk"
    print(report.is_passing)     # True
"""

import datetime
import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from models.finding_models import Finding, count_by_severity, sort_findings_by_severity


class AuditReport(BaseModel):
    """
    A complete compliance audit report produced by compliance_engine.run_audit().

    Stored in st.session_state["audit_history"] as a list.
    All findings are validated Finding objects.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    report_id:           str = Field(default_factory=lambda: f"RPT-{uuid.uuid4().hex[:8].upper()}")
    framework_targeted:  str = Field(description="Compliance framework audited.")
    document_name:       str = Field(default="Unknown Document")
    generated_timestamp: str = Field(
        default_factory=lambda: datetime.datetime.now().isoformat()[:19]
    )

    # ── Score ─────────────────────────────────────────────────────────────────
    compliance_score:  float = Field(ge=0.0, le=100.0, description="0–100 compliance score.")
    executive_summary: str   = Field(default="", description="Board-level summary text.")

    # ── Finding counts ────────────────────────────────────────────────────────
    total_findings:    int = Field(default=0, ge=0)
    critical_findings: int = Field(default=0, ge=0)
    high_findings:     int = Field(default=0, ge=0)
    medium_findings:   int = Field(default=0, ge=0)
    low_findings:      int = Field(default=0, ge=0)

    # ── Findings ──────────────────────────────────────────────────────────────
    findings: List[Finding] = Field(default_factory=list)

    # ── Security scan results ─────────────────────────────────────────────────
    pii_detected:    Dict[str, List[str]] = Field(default_factory=dict)
    injection_risk:  float = Field(default=0.0, ge=0.0, le=1.0)

    # ── Run metadata ──────────────────────────────────────────────────────────
    provider_used:  str   = Field(default="unknown", description="LLM provider used.")
    duration_sec:   float = Field(default=0.0, ge=0.0)
    relevant_regs:  List[Dict[str, Any]] = Field(default_factory=list)
    error:          Optional[str] = Field(default=None)

    model_config = {"extra": "ignore"}

    # ── Validators ────────────────────────────────────────────────────────────

    @field_validator("findings", mode="before")
    @classmethod
    def validate_findings(cls, v: Any) -> List[Finding]:
        """Accept list of Finding objects, dicts, or mixed."""
        if not isinstance(v, list):
            return []
        result = []
        for item in v:
            if isinstance(item, Finding):
                result.append(item)
            elif isinstance(item, dict):
                try:
                    result.append(Finding(**item))
                except Exception:
                    pass
        return result

    @field_validator("compliance_score", mode="before")
    @classmethod
    def round_score(cls, v: Any) -> float:
        try:
            return round(max(0.0, min(100.0, float(v))), 1)
        except (TypeError, ValueError):
            return 0.0

    @field_validator("total_findings", mode="before")
    @classmethod
    def compute_total(cls, v: Any, info: Any) -> int:
        """Auto-compute from findings list if not provided."""
        if v and int(v) > 0:
            return int(v)
        try:
            return len(info.data.get("findings", []))
        except Exception:
            return int(v) if v else 0

    @field_validator("critical_findings", mode="before")
    @classmethod
    def compute_critical(cls, v: Any, info: Any) -> int:
        if v and int(v) > 0:
            return int(v)
        try:
            findings = info.data.get("findings", [])
            return sum(1 for f in findings if getattr(f, "severity", "") == "Critical")
        except Exception:
            return int(v) if v else 0

    # ── Computed properties ───────────────────────────────────────────────────

    @property
    def grade(self) -> str:
        """Letter grade for this audit (A+–F)."""
        from compliance.scoring import grade_score
        return grade_score(self.compliance_score)

    @property
    def risk_level(self) -> str:
        """Risk level string (Low/Medium/High/Critical Risk)."""
        from compliance.scoring import risk_level
        return risk_level(self.compliance_score)

    @property
    def score_color(self) -> str:
        """Hex color for this score."""
        from compliance.scoring import score_color
        return score_color(self.compliance_score)

    @property
    def is_passing(self) -> bool:
        """True if score meets minimum passing threshold for framework."""
        from compliance.scoring import is_passing
        return is_passing(self.compliance_score, self.framework_targeted)

    @property
    def severity_counts(self) -> Dict[str, int]:
        """Count of findings per severity level."""
        return count_by_severity(self.findings)

    @property
    def critical_and_high(self) -> List[Finding]:
        """Return only Critical and High severity findings."""
        return [f for f in self.findings if f.severity in ("Critical", "High")]

    @property
    def sorted_findings(self) -> List[Finding]:
        """Findings sorted by severity (Critical first)."""
        return sort_findings_by_severity(self.findings)

    @property
    def date(self) -> str:
        """Date portion of generated_timestamp (YYYY-MM-DD)."""
        return self.generated_timestamp[:10]

    @property
    def time(self) -> str:
        """Time portion of generated_timestamp (HH:MM:SS)."""
        return self.generated_timestamp[11:19] if len(self.generated_timestamp) > 10 else ""

    @property
    def has_pii(self) -> bool:
        return bool(self.pii_detected)

    @property
    def has_injection_risk(self) -> bool:
        return self.injection_risk >= 0.3

    @property
    def short_id(self) -> str:
        """Last 8 chars of report_id for display."""
        return self.report_id[-8:]

    # ── Utility methods ───────────────────────────────────────────────────────

    def to_summary(self) -> "AuditSummary":
        """Return a lightweight AuditSummary for list display."""
        return AuditSummary(
            report_id=self.report_id,
            framework=self.framework_targeted,
            document_name=self.document_name,
            score=self.compliance_score,
            grade=self.grade,
            risk_level=self.risk_level,
            total_findings=self.total_findings,
            critical_findings=self.critical_findings,
            generated_at=self.generated_timestamp[:16],
            is_passing=self.is_passing,
        )

    def to_export_dict(self) -> Dict[str, Any]:
        """Return a dict suitable for JSON/CSV export."""
        d = self.model_dump()
        # Flatten findings to list of dicts
        d["findings"] = [f.model_dump() for f in self.findings]
        d["grade"]    = self.grade
        d["risk_level"] = self.risk_level
        return d

    def benchmark(self) -> Dict[str, Any]:
        """Compare score against industry benchmarks."""
        from compliance.scoring import benchmark_score
        return benchmark_score(self.compliance_score, self.framework_targeted)

    def __str__(self) -> str:
        return (
            f"AuditReport({self.report_id}, {self.framework_targeted}, "
            f"score={self.compliance_score:.1f}%, {self.total_findings} findings)"
        )

    def __repr__(self) -> str:
        return (
            f"AuditReport(id={self.report_id!r}, framework={self.framework_targeted!r}, "
            f"score={self.compliance_score}, grade={self.grade!r})"
        )


# ══════════════════════════════════════════════════════════════════════════════
# AUDIT SUMMARY (lightweight, for list display)
# ══════════════════════════════════════════════════════════════════════════════

class AuditSummary(BaseModel):
    """
    Lightweight audit summary for display in reports list / analytics tables.
    Does not carry the full findings list.
    """
    report_id:        str
    framework:        str
    document_name:    str
    score:            float
    grade:            str
    risk_level:       str
    total_findings:   int
    critical_findings:int
    generated_at:     str
    is_passing:       bool

    model_config = {"extra": "ignore"}

    def to_table_row(self) -> Dict[str, Any]:
        """Return a flat dict for Streamlit dataframe display."""
        status = "✅ Pass" if self.is_passing else "❌ Fail"
        return {
            "Report ID":  self.report_id[-8:],
            "Framework":  self.framework,
            "Document":   self.document_name[:40],
            "Score":      f"{self.score:.0f}%",
            "Grade":      self.grade,
            "Risk":       self.risk_level,
            "Findings":   self.total_findings,
            "Critical":   self.critical_findings,
            "Date":       self.generated_at[:10],
            "Status":     status,
        }


# ══════════════════════════════════════════════════════════════════════════════
# AUDIT COMPARISON
# ══════════════════════════════════════════════════════════════════════════════

class AuditComparison(BaseModel):
    """
    Comparison between two audit reports on the same framework.
    Generated by the analytics module for trend analysis.
    """
    framework:        str
    old_report_id:    str
    new_report_id:    str
    old_score:        float
    new_score:        float
    score_delta:      float
    old_findings:     int
    new_findings:     int
    findings_delta:   int
    old_critical:     int
    new_critical:     int
    improved:         bool
    summary:          str = ""

    model_config = {"extra": "ignore"}

    @classmethod
    def from_reports(cls, old: AuditReport, new: AuditReport) -> "AuditComparison":
        """Create a comparison from two AuditReport objects."""
        score_delta   = round(new.compliance_score - old.compliance_score, 1)
        findings_delta= new.total_findings - old.total_findings

        if score_delta > 2:
            summary = f"Score improved by {score_delta:+.1f}% — compliance is trending positively."
        elif score_delta < -2:
            summary = f"Score declined by {abs(score_delta):.1f}% — review recent policy changes."
        else:
            summary = f"Score is stable (change: {score_delta:+.1f}%)."

        return cls(
            framework=new.framework_targeted,
            old_report_id=old.report_id,
            new_report_id=new.report_id,
            old_score=old.compliance_score,
            new_score=new.compliance_score,
            score_delta=score_delta,
            old_findings=old.total_findings,
            new_findings=new.total_findings,
            findings_delta=findings_delta,
            old_critical=old.critical_findings,
            new_critical=new.critical_findings,
            improved=score_delta > 0,
            summary=summary,
        )

    def __str__(self) -> str:
        direction = "↑" if self.improved else "↓"
        return (
            f"AuditComparison({self.framework}: "
            f"{self.old_score:.0f}% → {self.new_score:.0f}% "
            f"{direction}{abs(self.score_delta):.1f}%)"
        )


# ══════════════════════════════════════════════════════════════════════════════
# REMEDIATION PLAN MODEL
# ══════════════════════════════════════════════════════════════════════════════

class RemediationPlan(BaseModel):
    """
    A structured remediation plan produced by RemediationAgent.
    """
    framework:    str
    document_name:str = ""
    total_items:  int = 0
    critical_items:int = 0
    roadmap:      str = Field(default="", description="Full roadmap text from LLM.")
    phases: Dict[str, List[str]] = Field(
        default_factory=lambda: {
            "quick_wins":  [],
            "short_term":  [],
            "long_term":   [],
        },
        description="Time-horizon phases: quick_wins, short_term, long_term.",
    )
    plans:        List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Individual remediation plans per finding.",
    )
    created_at:   str = Field(
        default_factory=lambda: datetime.datetime.now().isoformat()[:19]
    )

    model_config = {"extra": "ignore"}

    @property
    def has_critical(self) -> bool:
        return self.critical_items > 0

    @property
    def estimated_effort(self) -> str:
        if self.critical_items >= 3:
            return "High"
        if self.critical_items >= 1 or self.total_items >= 5:
            return "Medium"
        return "Low"

    def __str__(self) -> str:
        return (
            f"RemediationPlan({self.framework}, {self.total_items} items, "
            f"{self.critical_items} critical, effort={self.estimated_effort})"
        )


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def audit_reports_to_dataframe(reports: List[AuditReport]):
    """Convert a list of AuditReports to a pandas DataFrame."""
    try:
        import pandas as pd
        rows = [r.to_summary().to_table_row() for r in reports]
        return pd.DataFrame(rows)
    except ImportError:
        return [r.to_summary().to_table_row() for r in reports]


def latest_report(reports: List[AuditReport]) -> Optional[AuditReport]:
    """Return the most recent audit report."""
    if not reports:
        return None
    return sorted(reports, key=lambda r: r.generated_timestamp)[-1]


def reports_for_framework(
    reports: List[AuditReport],
    framework: str,
) -> List[AuditReport]:
    """Return all reports for a specific framework."""
    return [r for r in reports if r.framework_targeted == framework]