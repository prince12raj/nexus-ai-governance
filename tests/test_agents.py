"""
tests/test_agents.py — Agent and scoring pipeline tests.
"""
from compliance.scoring import calculate_compliance_score, grade_score, score_color, risk_level
from models.finding_models import Finding


def _make_finding(severity: str) -> Finding:
    return Finding(
        violated_string="test text",
        legal_reference="GDPR Art 5",
        severity=severity,
        explanation="Test explanation",
        corrected_version="Corrected version",
        confidence_score=0.9,
        department="Engineering",
        remediation_steps=["Step 1", "Step 2"],
    )


def test_perfect_score():
    assert calculate_compliance_score([]) == 100.0


def test_critical_penalty():
    score = calculate_compliance_score([_make_finding("Critical")])
    assert score == 85.0


def test_multiple_findings():
    findings = [_make_finding("Critical"), _make_finding("High"), _make_finding("Medium")]
    score    = calculate_compliance_score(findings)
    assert 0.0 <= score <= 100.0
    assert score < 85.0


def test_grade_mapping():
    assert grade_score(92) == "A"
    assert grade_score(82) == "B"
    assert grade_score(72) == "C"
    assert grade_score(62) == "D"
    assert grade_score(55) == "F"


def test_score_color_green():
    assert score_color(90) == "#00e5a0"


def test_score_color_yellow():
    assert score_color(70) == "#ffc847"


def test_score_color_red():
    assert score_color(30) == "#ff4757"


def test_risk_level():
    assert risk_level(85) == "Low Risk"
    assert risk_level(65) == "Medium Risk"
    assert risk_level(45) == "High Risk"
    assert risk_level(20) == "Critical Risk"
