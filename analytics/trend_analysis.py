"""
analytics/trend_analysis.py — Compliance trend helpers.
"""
from __future__ import annotations

import datetime
from typing import Any, Dict, List

from models.audit_models import AuditReport


def build_trend_history(reports: List[AuditReport]) -> List[Dict[str, Any]]:
    """Build a sorted list of {date, score} dicts from audit history."""
    history = [
        {"date": r.generated_timestamp[:10], "score": r.compliance_score}
        for r in reports
    ]
    history.sort(key=lambda x: x["date"])
    return history


def score_delta(reports: List[AuditReport]) -> float:
    """Return the change in compliance score from first to last audit."""
    if len(reports) < 2:
        return 0.0
    history = build_trend_history(reports)
    return round(history[-1]["score"] - history[0]["score"], 1)
