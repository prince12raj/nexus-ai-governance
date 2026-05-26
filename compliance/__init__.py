"""
compliance/__init__.py — Compliance package for Nexus AI Governance Platform.

Single import point for all compliance operations.

Usage:
    from compliance import run_audit, detect_pii, injection_report
    from compliance import calculate_compliance_score, grade_score
"""
from compliance.compliance_engine import (
    run_audit,
    call_compliance_llm,
    generate_mock_findings,
    parse_findings,
)
from compliance.pii_detector import (
    detect_pii,
    detect_pii_detailed,
    detect_pii_with_llm,
    redact_pii,
    mask_pii,
    pii_risk_summary,
    PII_PATTERNS,
    PII_META,
)
from compliance.injection_detector import (
    detect_prompt_injection,
    detect_injection_detailed,
    injection_risk_score,
    is_safe_to_process,
    injection_report,
    INJECTION_PATTERNS,
)
from compliance.scoring import (
    calculate_compliance_score,
    calculate_weighted_score,
    grade_score,
    score_color,
    risk_level,
    risk_emoji,
    is_passing,
    score_breakdown,
    benchmark_score,
    score_trend,
    generate_certificate_data,
    SEVERITY_PENALTIES,
    FRAMEWORK_BENCHMARKS,
)

__all__ = [
    # Engine
    "run_audit",
    "call_compliance_llm",
    "generate_mock_findings",
    "parse_findings",
    # PII
    "detect_pii",
    "detect_pii_detailed",
    "detect_pii_with_llm",
    "redact_pii",
    "mask_pii",
    "pii_risk_summary",
    "PII_PATTERNS",
    "PII_META",
    # Injection
    "detect_prompt_injection",
    "detect_injection_detailed",
    "injection_risk_score",
    "is_safe_to_process",
    "injection_report",
    "INJECTION_PATTERNS",
    # Scoring
    "calculate_compliance_score",
    "calculate_weighted_score",
    "grade_score",
    "score_color",
    "risk_level",
    "risk_emoji",
    "is_passing",
    "score_breakdown",
    "benchmark_score",
    "score_trend",
    "generate_certificate_data",
    "SEVERITY_PENALTIES",
    "FRAMEWORK_BENCHMARKS",
]