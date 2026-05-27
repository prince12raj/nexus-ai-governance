"""
compliance/injection_detector.py — Prompt injection & adversarial input detection.

Protects the platform from malicious policy documents that attempt to:
  - Override LLM instructions
  - Jailbreak the compliance analysis
  - Extract system prompts
  - Manipulate audit findings

Two detection layers:
  1. Regex pattern matching  — fast, deterministic
  2. Heuristic scoring       — context-aware risk scoring

Usage:
    from compliance.injection_detector import (
        detect_prompt_injection,
        injection_risk_score,
        injection_report,
        is_safe_to_process,
    )
"""

import re
from typing import Any, Dict, List, Tuple

from config.logging_config import get_logger

logger = get_logger("nexus.compliance.injection")


# ══════════════════════════════════════════════════════════════════════════════
# INJECTION PATTERNS
# ══════════════════════════════════════════════════════════════════════════════

# Each entry: (category, description, regex_pattern, severity_weight)
INJECTION_DEFINITIONS: List[Tuple[str, str, str, float]] = [

    # ── Direct instruction override ───────────────────────────────────────────
    ("instruction_override",
     "Ignore previous instructions",
     r'ignore\s+(?:all\s+)?(?:previous|above|prior|the\s+above|your)\s+instructions?',
     1.0),

    ("instruction_override",
     "Disregard instructions",
     r'disregard\s+(?:your\s+|all\s+|the\s+)?(?:previous\s+)?instructions?',
     1.0),

    ("instruction_override",
     "Forget instructions",
     r'forget\s+(?:your\s+|all\s+|previous\s+|the\s+above\s+)?instructions?',
     1.0),

    ("instruction_override",
     "Override safety filters",
     r'override\s+(?:your\s+|safety\s+|content\s+)?(?:filters?|guidelines?|restrictions?|rules?)',
     1.0),

    ("instruction_override",
     "New instructions injection",
     r'new\s+instructions?\s*:',
     0.9),

    ("instruction_override",
     "System prompt injection",
     r'(?:system\s+prompt|system\s+message|system\s+instruction)',
     0.9),

    # ── Role hijacking ────────────────────────────────────────────────────────
    ("role_hijacking",
     "You are now (role override)",
     r'you\s+are\s+now\s+(?:a\s+|an\s+)?(?!compliance|auditor|analyst|assistant)',
     0.9),

    ("role_hijacking",
     "Act as (jailbreak)",
     r'act\s+as\s+(?:a\s+|an\s+)?(?!compliance|auditor|analyst|review)',
     0.8),

    ("role_hijacking",
     "Pretend to be",
     r'pretend\s+(?:you\s+are|to\s+be)\s+(?!a\s+compliance|an\s+auditor)',
     0.8),

    ("role_hijacking",
     "Roleplay as",
     r'(?:roleplay|role\s+play)\s+as\s+',
     0.7),

    ("role_hijacking",
     "Simulate being",
     r'simulate\s+(?:being|you\s+are)\s+',
     0.7),

    # ── Jailbreak techniques ──────────────────────────────────────────────────
    ("jailbreak",
     "DAN mode",
     r'\bDAN\s+mode\b',
     1.0),

    ("jailbreak",
     "Jailbreak attempt",
     r'\bjailbreak\b',
     1.0),

    ("jailbreak",
     "Developer mode",
     r'\bdeveloper\s+mode\b',
     0.9),

    ("jailbreak",
     "Sudo mode",
     r'\bsudo\s+(?:mode|access|command)\b',
     0.8),

    ("jailbreak",
     "God mode",
     r'\bgod\s+mode\b',
     0.8),

    ("jailbreak",
     "Unrestricted mode",
     r'\bunrestricted\s+(?:mode|access|version)\b',
     0.9),

    ("jailbreak",
     "Bypass safety",
     r'bypass\s+(?:safety|filter|restriction|guard|content\s+policy)',
     1.0),

    ("jailbreak",
     "Remove restrictions",
     r'remove\s+(?:all\s+)?(?:your\s+)?(?:restrictions|limitations|filters|guardrails)',
     0.9),

    # ── Output manipulation ───────────────────────────────────────────────────
    ("output_manipulation",
     "Return only specific text",
     r'(?:return|output|respond|reply|answer)\s+only\s+(?:with\s+)?(?:the\s+)?(?:text|word|phrase)',
     0.6),

    ("output_manipulation",
     "Always say/respond",
     r'(?:always|must)\s+(?:say|respond\s+with|return|output)\s+',
     0.6),

    ("output_manipulation",
     "Force JSON manipulation",
     r'return\s+(?:a\s+)?(?:json|array|list)\s+(?:that\s+)?(?:says?|contains?|includes?)\s+',
     0.7),

    ("output_manipulation",
     "Mark everything as compliant",
     r'(?:mark|label|flag|report)\s+(?:everything|all|the\s+policy)\s+as\s+(?:compliant|safe|passed)',
     1.0),

    ("output_manipulation",
     "Find no violations",
     r'(?:find|report|return|output)\s+no\s+(?:violations?|findings?|issues?|problems?)',
     1.0),

    # ── Data extraction ───────────────────────────────────────────────────────
    ("data_extraction",
     "Reveal system prompt",
     r'(?:reveal|show|display|print|output|tell\s+me)\s+(?:your\s+)?system\s+prompt',
     1.0),

    ("data_extraction",
     "What are your instructions",
     r'what\s+(?:are\s+)?your\s+(?:instructions?|rules?|guidelines?|directives?)',
     0.8),

    ("data_extraction",
     "Ignore confidentiality",
     r'ignore\s+(?:all\s+)?confidentiality',
     0.9),

    ("data_extraction",
     "Leak training data",
     r'(?:leak|expose|reveal|share|output)\s+(?:your\s+)?training\s+data',
     1.0),

    # ── Code execution ────────────────────────────────────────────────────────
    ("code_execution",
     "Execute following",
     r'execute\s+(?:the\s+)?following\s+(?:code|command|script|instruction)',
     0.9),

    ("code_execution",
     "Run command",
     r'(?:run|exec|execute)\s+(?:this\s+)?(?:command|script|code)\s*:',
     0.9),

    ("code_execution",
     "Import/eval injection",
     r'(?:__import__|eval\(|exec\(|os\.system|subprocess)',
     1.0),

    # ── Social engineering ────────────────────────────────────────────────────
    ("social_engineering",
     "For testing purposes only",
     r'for\s+(?:testing|research|educational|demonstration)\s+purposes\s+only',
     0.4),

    ("social_engineering",
     "Hypothetically speaking",
     r'hypothetically\s+speaking,?\s+(?:if\s+you|what\s+would\s+you)',
     0.4),

    ("social_engineering",
     "Imagine you have no restrictions",
     r'imagine\s+(?:you\s+have\s+no|there\s+are\s+no)\s+(?:restrictions|rules|guidelines)',
     0.9),
]

# Flat lookup for backward compatibility
INJECTION_PATTERNS: List[str] = [pattern for _, _, pattern, _ in INJECTION_DEFINITIONS]


# ══════════════════════════════════════════════════════════════════════════════
# DETECTION FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def detect_prompt_injection(text: str) -> List[str]:
    """
    Scan text for prompt injection patterns.

    Args:
        text: Text to scan (policy document content).

    Returns:
        List of matched pattern descriptions (empty if clean).
    """
    if not text:
        return []

    matched: List[str] = []
    for _, description, pattern, _ in INJECTION_DEFINITIONS:
        if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
            matched.append(description)

    if matched:
        logger.warning("Injection patterns detected: %s", matched)

    return matched


def detect_injection_detailed(text: str) -> List[Dict[str, Any]]:
    """
    Detailed injection detection — returns full metadata per match.

    Returns:
        List of dicts with: category, description, matched_text, severity_weight
    """
    if not text:
        return []

    results: List[Dict[str, Any]] = []

    for category, description, pattern, weight in INJECTION_DEFINITIONS:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            results.append({
                "category":       category,
                "description":    description,
                "matched_text":   match.group()[:100],
                "severity_weight":weight,
                "position":       match.start(),
            })

    # Sort by severity weight descending
    results.sort(key=lambda x: x["severity_weight"], reverse=True)
    return results


def injection_risk_score(text: str) -> float:
    """
    Calculate a 0.0–1.0 injection risk score.

    Algorithm:
      - Sum severity weights of all matched patterns
      - Normalise to 0–1 range (cap at 1.0)
      - Partial credit for near-threshold patterns

    Args:
        text: Text to evaluate.

    Returns:
        Float between 0.0 (no risk) and 1.0 (certain injection attempt).
    """
    if not text:
        return 0.0

    total_weight = 0.0
    matches      = 0

    for _, _, pattern, weight in INJECTION_DEFINITIONS:
        if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
            total_weight += weight
            matches      += 1

    if matches == 0:
        return 0.0

    # Normalise: 3+ critical patterns = score 1.0
    score = min(1.0, total_weight / 3.0)
    return round(score, 3)


def is_safe_to_process(text: str, threshold: float = 0.5) -> bool:
    """
    Return True if the document is safe to process (injection risk below threshold).

    Args:
        text:      Document text to check.
        threshold: Risk score threshold (0.0–1.0). Default 0.5.

    Returns:
        True if safe, False if injection risk is too high.
    """
    score = injection_risk_score(text)
    safe  = score < threshold

    if not safe:
        logger.warning(
            "Document blocked — injection risk score=%.3f (threshold=%.2f)",
            score, threshold
        )
    return safe


# ══════════════════════════════════════════════════════════════════════════════
# FULL REPORT
# ══════════════════════════════════════════════════════════════════════════════

def injection_report(text: str) -> Dict[str, Any]:
    """
    Generate a complete injection analysis report for a document.

    Returns:
        Dict with:
            risk_score      — float (0–1)
            risk_level      — str (None/Low/Medium/High/Critical)
            is_safe         — bool
            matches         — List[Dict] (detailed match info)
            categories      — List[str] (unique categories matched)
            recommendation  — str
    """
    score   = injection_risk_score(text)
    matches = detect_injection_detailed(text)
    cats    = sorted({m["category"] for m in matches})

    if score == 0.0:
        level = "None"
        rec   = "Document appears safe to process. No injection patterns detected."
    elif score < 0.3:
        level = "Low"
        rec   = (
            "Low-level patterns detected. Review flagged sections manually before processing. "
            "May be false positives from policy language."
        )
    elif score < 0.6:
        level = "Medium"
        rec   = (
            "Moderate injection risk. Manual review strongly recommended before processing. "
            "Consider rejecting and requesting document resubmission."
        )
    elif score < 0.85:
        level = "High"
        rec   = (
            "High injection risk detected. Do not process without manual security review. "
            "Document likely contains adversarial content."
        )
    else:
        level = "Critical"
        rec   = (
            "Critical injection risk. Document BLOCKED. This document appears to be a deliberate "
            "prompt injection attack. Log this incident and escalate to the security team."
        )

    return {
        "risk_score":     score,
        "risk_level":     level,
        "is_safe":        score < 0.5,
        "matches":        matches,
        "match_count":    len(matches),
        "categories":     cats,
        "recommendation": rec,
    }