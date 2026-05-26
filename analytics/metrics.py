"""
analytics/metrics.py — Aggregate metric calculations across audit history.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from models.audit_models import AuditReport
from models.finding_models import Finding


def aggregate_metrics(reports: List[AuditReport]) -> Dict[str, Any]:
    if not reports:
        return {
            "total_audits": 0,
            "avg_score": 0.0,
            "total_findings": 0,
            "critical_count": 0,
        }

    all_findings: List[Finding] = [f for r in reports for f in r.findings]
    return {
        "total_audits":   len(reports),
        "avg_score":      round(sum(r.compliance_score for r in reports) / len(reports), 1),
        "total_findings": sum(r.total_findings for r in reports),
        "critical_count": sum(r.critical_findings for r in reports),
        "frameworks_covered": list({r.framework_targeted for r in reports}),
        "departments_at_risk": list({f.department for f in all_findings if f.severity == "Critical"}),
    }


def top_violations(reports: List[AuditReport], n: int = 5) -> List[Dict[str, Any]]:
    """Return the N most frequently violated regulations across all reports."""
    from collections import Counter
    all_findings = [f for r in reports for f in r.findings]
    counts = Counter(f.legal_reference for f in all_findings)
    return [{"regulation": reg, "count": cnt} for reg, cnt in counts.most_common(n)]
