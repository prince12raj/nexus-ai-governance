"""
compliance/scoring.py — Compliance score calculation for Nexus AI Governance Platform.

Provides:
  - Overall compliance score (0–100)
  - Letter grade (A–F)
  - Risk level classification
  - Per-framework benchmarking
  - Score trend analysis
  - Detailed breakdown by severity

Usage:
    from compliance.scoring import (
        calculate_compliance_score,
        grade_score,
        score_color,
        risk_level,
        score_breakdown,
        benchmark_score,
    )
"""

from typing import Any, Dict, List, Optional

from config.constants import SEVERITY_SCORES, SEVERITY_COLORS
from config.logging_config import get_logger

logger = get_logger("nexus.compliance.scoring")


# ══════════════════════════════════════════════════════════════════════════════
# SCORING CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

# Penalty points deducted per finding at each severity
SEVERITY_PENALTIES: Dict[str, float] = {
    "Critical": 20.0,
    "High":     10.0,
    "Medium":    5.0,
    "Low":       2.0,
}

# Maximum possible penalty (caps at 0 score)
MAX_PENALTY = 100.0

# Grade thresholds
GRADE_THRESHOLDS = [
    (95, "A+"),
    (90, "A"),
    (85, "A-"),
    (80, "B+"),
    (75, "B"),
    (70, "B-"),
    (65, "C+"),
    (60, "C"),
    (55, "C-"),
    (50, "D"),
    (0,  "F"),
]

# Risk level thresholds
RISK_THRESHOLDS = [
    (85, "Low Risk",      "#00e5a0"),
    (65, "Medium Risk",   "#ffc847"),
    (40, "High Risk",     "#ff8c42"),
    (0,  "Critical Risk", "#ff4757"),
]

# Industry benchmark scores per framework (approximate)
FRAMEWORK_BENCHMARKS: Dict[str, Dict[str, float]] = {
    "GDPR": {
        "industry_average": 72.0,
        "top_quartile":     88.0,
        "minimum_passing":  60.0,
    },
    "HIPAA": {
        "industry_average": 75.0,
        "top_quartile":     90.0,
        "minimum_passing":  65.0,
    },
    "ISO 27001": {
        "industry_average": 70.0,
        "top_quartile":     85.0,
        "minimum_passing":  60.0,
    },
    "SOC 2": {
        "industry_average": 78.0,
        "top_quartile":     92.0,
        "minimum_passing":  70.0,
    },
    "PCI-DSS": {
        "industry_average": 68.0,
        "top_quartile":     85.0,
        "minimum_passing":  60.0,
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# CORE SCORING
# ══════════════════════════════════════════════════════════════════════════════

def calculate_compliance_score(findings: List[Any]) -> float:
    """
    Calculate a 0–100 compliance score from a list of findings.

    Algorithm:
      - Start at 100
      - Deduct SEVERITY_PENALTIES per finding
      - Apply diminishing returns for many findings of same severity
        (prevents unrealistic negative scores for policy-heavy documents)
      - Floor at 0.0

    Args:
        findings: List of Finding objects (must have .severity attribute).

    Returns:
        Float compliance score between 0.0 and 100.0.
    """
    if not findings:
        return 100.0

    # Count findings per severity
    counts: Dict[str, int] = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for f in findings:
        sev = getattr(f, "severity", "Medium")
        sev = sev.capitalize() if isinstance(sev, str) else "Medium"
        counts[sev] = counts.get(sev, 0) + 1

    total_penalty = 0.0
    for severity, count in counts.items():
        if count == 0:
            continue
        penalty     = SEVERITY_PENALTIES.get(severity, 5.0)
        # Diminishing returns: 1st finding = full penalty, subsequent = 60%
        first_hit   = penalty
        extra_hits  = penalty * 0.60 * (count - 1)
        total_penalty += first_hit + extra_hits

    score = max(0.0, 100.0 - total_penalty)
    return round(score, 1)


def calculate_weighted_score(
    findings: List[Any],
    confidence_weight: bool = True,
) -> float:
    """
    Weighted compliance score that factors in LLM confidence.

    Lower-confidence findings contribute less to the penalty.

    Args:
        findings:          List of Finding objects.
        confidence_weight: If True, weight penalties by confidence_score.

    Returns:
        Weighted compliance score (0–100).
    """
    if not findings:
        return 100.0

    total_penalty = 0.0

    for f in findings:
        sev        = getattr(f, "severity", "Medium").capitalize()
        confidence = getattr(f, "confidence_score", 1.0) if confidence_weight else 1.0
        penalty    = SEVERITY_PENALTIES.get(sev, 5.0) * float(confidence)
        total_penalty += penalty

    score = max(0.0, 100.0 - total_penalty)
    return round(score, 1)


# ══════════════════════════════════════════════════════════════════════════════
# GRADE & CLASSIFICATION
# ══════════════════════════════════════════════════════════════════════════════

def grade_score(score: float) -> str:
    """
    Convert a compliance score to a letter grade (A+ to F).

    Args:
        score: Compliance score (0–100).

    Returns:
        Grade string: "A+", "A", "A-", "B+", "B", ..., "F"
    """
    for threshold, grade in GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "F"


def score_color(score: float) -> str:
    """
    Return a hex color code for a compliance score.

    Green  (#00e5a0) → High compliance
    Yellow (#ffc847) → Medium compliance
    Orange (#ff8c42) → Low compliance
    Red    (#ff4757) → Critical non-compliance

    Args:
        score: Compliance score (0–100).

    Returns:
        Hex color string.
    """
    for threshold, _, color in RISK_THRESHOLDS:
        if score >= threshold:
            return color
    return "#ff4757"


def risk_level(score: float) -> str:
    """
    Return a human-readable risk level for a compliance score.

    Args:
        score: Compliance score (0–100).

    Returns:
        One of: "Low Risk", "Medium Risk", "High Risk", "Critical Risk"
    """
    for threshold, label, _ in RISK_THRESHOLDS:
        if score >= threshold:
            return label
    return "Critical Risk"


def risk_emoji(score: float) -> str:
    """Return an emoji representing the risk level."""
    level = risk_level(score)
    emojis = {
        "Low Risk":      "✅",
        "Medium Risk":   "⚠️",
        "High Risk":     "🔶",
        "Critical Risk": "🔴",
    }
    return emojis.get(level, "❓")


def is_passing(score: float, framework: str = "") -> bool:
    """
    Return True if score meets the minimum passing threshold for the framework.

    Args:
        score:     Compliance score.
        framework: Optional framework name for framework-specific thresholds.

    Returns:
        True if passing.
    """
    benchmark = FRAMEWORK_BENCHMARKS.get(framework, {})
    threshold = benchmark.get("minimum_passing", 60.0)
    return score >= threshold


# ══════════════════════════════════════════════════════════════════════════════
# BREAKDOWN & ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

def score_breakdown(findings: List[Any]) -> Dict[str, Any]:
    """
    Produce a detailed scoring breakdown by severity.

    Args:
        findings: List of Finding objects.

    Returns:
        Dict with overall score, grade, risk_level, counts, penalties, breakdown.
    """
    counts: Dict[str, int]   = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    penalties: Dict[str, float] = {}

    for f in findings:
        sev = getattr(f, "severity", "Medium").capitalize()
        counts[sev] = counts.get(sev, 0) + 1

    total_penalty = 0.0
    for severity, count in counts.items():
        if count == 0:
            penalties[severity] = 0.0
            continue
        base     = SEVERITY_PENALTIES.get(severity, 5.0)
        pen      = base + base * 0.60 * (count - 1)
        penalties[severity] = round(pen, 1)
        total_penalty      += pen

    score = max(0.0, round(100.0 - total_penalty, 1))

    return {
        "score":         score,
        "grade":         grade_score(score),
        "risk_level":    risk_level(score),
        "score_color":   score_color(score),
        "risk_emoji":    risk_emoji(score),
        "total_findings":len(findings),
        "counts":        counts,
        "penalties":     penalties,
        "total_penalty": round(total_penalty, 1),
        "breakdown": [
            {
                "severity":    sev,
                "count":       counts[sev],
                "penalty":     penalties[sev],
                "color":       SEVERITY_COLORS.get(sev, "#8a9bbc"),
            }
            for sev in ["Critical", "High", "Medium", "Low"]
            if counts[sev] > 0
        ],
    }


def benchmark_score(score: float, framework: str) -> Dict[str, Any]:
    """
    Compare a score against industry benchmarks for the framework.

    Args:
        score:     Compliance score to benchmark.
        framework: Compliance framework name.

    Returns:
        Dict with benchmark comparison data.
    """
    bench = FRAMEWORK_BENCHMARKS.get(framework, {
        "industry_average": 70.0,
        "top_quartile":     85.0,
        "minimum_passing":  60.0,
    })

    avg    = bench["industry_average"]
    top_q  = bench["top_quartile"]
    min_p  = bench["minimum_passing"]

    if score >= top_q:
        position = "Top Quartile"
        vs_avg   = f"+{round(score - avg, 1)} above industry average"
    elif score >= avg:
        position = "Above Average"
        vs_avg   = f"+{round(score - avg, 1)} above industry average"
    elif score >= min_p:
        position = "Below Average"
        vs_avg   = f"{round(score - avg, 1)} below industry average"
    else:
        position = "Failing"
        vs_avg   = f"{round(score - avg, 1)} below industry average"

    return {
        "score":            score,
        "framework":        framework,
        "industry_average": avg,
        "top_quartile":     top_q,
        "minimum_passing":  min_p,
        "position":         position,
        "vs_average":       vs_avg,
        "gap_to_top":       max(0.0, round(top_q - score, 1)),
        "gap_to_passing":   max(0.0, round(min_p - score, 1)),
        "is_passing":       score >= min_p,
        "is_top_quartile":  score >= top_q,
    }


def score_trend(scores: List[float]) -> Dict[str, Any]:
    """
    Analyse a series of compliance scores over time.

    Args:
        scores: List of scores in chronological order (oldest first).

    Returns:
        Dict with trend direction, change, average, best, worst.
    """
    if not scores:
        return {"trend": "no_data", "change": 0.0, "average": 0.0}

    if len(scores) == 1:
        return {
            "trend":   "stable",
            "change":  0.0,
            "average": scores[0],
            "best":    scores[0],
            "worst":   scores[0],
        }

    change   = round(scores[-1] - scores[-2], 1)
    trend    = "improving" if change > 1.0 else "declining" if change < -1.0 else "stable"
    average  = round(sum(scores) / len(scores), 1)

    return {
        "trend":           trend,
        "trend_emoji":     "📈" if trend == "improving" else "📉" if trend == "declining" else "➡️",
        "change":          change,
        "change_str":      f"+{change}" if change > 0 else str(change),
        "average":         average,
        "best":            max(scores),
        "worst":           min(scores),
        "total_audits":    len(scores),
        "recent_score":    scores[-1],
    }


# ══════════════════════════════════════════════════════════════════════════════
# COMPLIANCE CERTIFICATE
# ══════════════════════════════════════════════════════════════════════════════

def generate_certificate_data(
    score: float,
    framework: str,
    policy_name: str,
    findings_count: int,
    org_name: str = "Organisation",
) -> Dict[str, Any]:
    """
    Generate data for a compliance certificate / audit summary card.

    Used by the UI to render the post-audit certificate panel.

    Returns:
        Dict with all data needed to render the certificate.
    """
    from datetime import datetime

    bench   = benchmark_score(score, framework)
    passing = is_passing(score, framework)

    return {
        "org_name":        org_name,
        "policy_name":     policy_name,
        "framework":       framework,
        "score":           score,
        "grade":           grade_score(score),
        "risk_level":      risk_level(score),
        "score_color":     score_color(score),
        "risk_emoji":      risk_emoji(score),
        "is_passing":      passing,
        "status":          "PASSED" if passing else "NEEDS REMEDIATION",
        "findings_count":  findings_count,
        "benchmark":       bench,
        "audit_date":      datetime.now().strftime("%d %B %Y"),
        "valid_until":     datetime.now().replace(year=datetime.now().year + 1).strftime("%d %B %Y"),
        "certificate_id":  f"NXS-{framework[:4].upper()}-{datetime.now().strftime('%Y%m%d')}-{score:.0f}",
    }