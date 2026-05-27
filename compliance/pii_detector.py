"""
compliance/pii_detector.py — PII detection engine for Nexus AI Governance Platform.

Two detection layers:
  1. Regex patterns  — fast, deterministic, no API needed
  2. LLM scan        — deeper contextual detection via OpenAI/HF/Ollama (optional)

Usage:
    from compliance.pii_detector import detect_pii, redact_pii, pii_risk_summary

    found   = detect_pii(text)
    redacted = redact_pii(text)
    summary  = pii_risk_summary(found)
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from config.logging_config import get_logger

logger = get_logger("nexus.compliance.pii")


# ══════════════════════════════════════════════════════════════════════════════
# PII PATTERNS
# ══════════════════════════════════════════════════════════════════════════════

# Each entry: (display_name, regex_pattern, gdpr_category, risk_level)
PII_DEFINITIONS: List[Tuple[str, str, str, str]] = [
    # ── Identity ──────────────────────────────────────────────────────────────
    ("Email Address",
     r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b',
     "ordinary", "Medium"),

    ("Phone Number (International)",
     r'\b(\+\d{1,3}[\s.\-])?\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}\b',
     "ordinary", "Medium"),

    ("Date of Birth",
     r'\b(?:DOB|Date\s+of\s+Birth|Born\s+on):?\s*\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\b',
     "ordinary", "High"),

    ("Full Name (Formal)",
     r'\b(?:Mr|Mrs|Ms|Dr|Prof)\.?\s+[A-Z][a-z]+(?: [A-Z][a-z]+)+\b',
     "ordinary", "Medium"),

    # ── Government IDs ────────────────────────────────────────────────────────
    ("SSN (US)",
     r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b',
     "ordinary", "Critical"),

    ("NI Number (UK)",
     r'\b[A-CEGHJ-PR-TW-Z]{2}\s?\d{2}\s?\d{2}\s?\d{2}\s?[A-D]\b',
     "ordinary", "Critical"),

    ("Passport Number",
     r'\b[A-Z]{1,2}\d{6,9}\b',
     "ordinary", "High"),

    ("Driver Licence (UK)",
     r'\b[A-Z]{5}\d{6}[A-Z]{2}\d{2}\b',
     "ordinary", "High"),

    # ── Financial ─────────────────────────────────────────────────────────────
    ("Credit/Debit Card Number",
     r'\b(?:\d{4}[\s\-]){3}\d{4}\b',
     "ordinary", "Critical"),

    ("IBAN",
     r'\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}(?:[A-Z0-9]{0,16})?\b',
     "ordinary", "Critical"),

    ("Sort Code (UK)",
     r'\b\d{2}[-\s]?\d{2}[-\s]?\d{2}\b',
     "ordinary", "High"),

    ("Bank Account Number",
     r'\b(?:account\s*(?:number|no\.?|#)\s*:?\s*)\d{6,12}\b',
     "ordinary", "Critical"),

    # ── Network / Technical ───────────────────────────────────────────────────
    ("IP Address (IPv4)",
     r'\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b',
     "ordinary", "Low"),

    ("IP Address (IPv6)",
     r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b',
     "ordinary", "Low"),

    ("MAC Address",
     r'\b([0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}\b',
     "ordinary", "Low"),

    # ── Health ────────────────────────────────────────────────────────────────
    ("NHS Number (UK)",
     r'\b\d{3}\s\d{3}\s\d{4}\b',
     "special_category", "Critical"),

    ("Medical Record Number",
     r'\b(?:MRN|Patient\s+ID|Record\s+No\.?)\s*:?\s*\d{6,10}\b',
     "special_category", "Critical"),

    # ── Location ──────────────────────────────────────────────────────────────
    ("UK Postcode",
     r'\b[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}\b',
     "ordinary", "Low"),

    ("GPS Coordinates",
     r'\b[-+]?([1-8]?\d(\.\d+)?|90(\.0+)?),\s*[-+]?(180(\.0+)?|((1[0-7]\d)|([1-9]?\d))(\.\d+)?)\b',
     "ordinary", "Medium"),

    # ── Credentials (security critical) ──────────────────────────────────────
    ("API Key / Secret",
     r'\b(?:api[_\-]?key|secret[_\-]?key|access[_\-]?token)\s*[:=]\s*[A-Za-z0-9+/\-_]{20,}\b',
     "ordinary", "Critical"),

    ("JWT Token",
     r'\beyJ[A-Za-z0-9+/\-_]+\.[A-Za-z0-9+/\-_]+\.[A-Za-z0-9+/\-_]+\b',
     "ordinary", "Critical"),

    ("Password in Text",
     r'\b(?:password|passwd|pwd)\s*[:=]\s*\S{6,}\b',
     "ordinary", "Critical"),
]

# Quick lookup dict: name → (pattern, gdpr_category, risk_level)
PII_PATTERNS: Dict[str, str] = {name: pattern for name, pattern, _, _ in PII_DEFINITIONS}

# Risk metadata lookup
PII_META: Dict[str, Dict[str, str]] = {
    name: {"gdpr_category": cat, "risk_level": risk}
    for name, _, cat, risk in PII_DEFINITIONS
}

# Risk ordering for sorting
_RISK_ORDER = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}


# ══════════════════════════════════════════════════════════════════════════════
# CORE DETECTION
# ══════════════════════════════════════════════════════════════════════════════

def detect_pii(text: str, max_matches: int = 5) -> Dict[str, List[str]]:
    """
    Scan text for PII using regex patterns.

    Args:
        text:        Text to scan.
        max_matches: Maximum number of matches to return per PII type.

    Returns:
        Dict mapping PII type name → list of matched values.
        Example: {"Email Address": ["user@example.com"], "SSN (US)": ["123-45-6789"]}
    """
    if not text:
        return {}

    found: Dict[str, List[str]] = {}

    for name, pattern, _, _ in PII_DEFINITIONS:
        try:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Flatten tuple groups from grouping patterns
                flat = [m if isinstance(m, str) else m[0] for m in matches]
                # Deduplicate while preserving order
                seen:  List[str] = []
                dedup: List[str] = []
                for m in flat:
                    if m not in seen:
                        seen.append(m)
                        dedup.append(m)
                found[name] = dedup[:max_matches]
        except re.error as exc:
            logger.warning("Regex error for pattern '%s': %s", name, exc)

    if found:
        logger.info("PII detected: %s", list(found.keys()))

    return found


def detect_pii_detailed(text: str) -> List[Dict[str, Any]]:
    """
    Detailed PII detection — returns full metadata per finding.

    Returns:
        List of dicts with keys:
            pii_type, value_found, gdpr_category, risk_level,
            recommended_action, count
    """
    raw = detect_pii(text)
    results: List[Dict[str, Any]] = []

    for pii_type, values in raw.items():
        meta = PII_META.get(pii_type, {"gdpr_category": "ordinary", "risk_level": "Medium"})
        results.append({
            "pii_type":           pii_type,
            "value_found":        values[0] if values else "",
            "all_values":         values,
            "count":              len(values),
            "gdpr_category":      meta["gdpr_category"],
            "risk_level":         meta["risk_level"],
            "recommended_action": _recommended_action(pii_type, meta["gdpr_category"]),
        })

    # Sort by risk level descending
    results.sort(key=lambda x: _RISK_ORDER.get(x["risk_level"], 0), reverse=True)
    return results


def _recommended_action(pii_type: str, gdpr_category: str) -> str:
    """Return recommended action for a detected PII type."""
    if gdpr_category == "special_category":
        return "Immediate review required — special category data needs explicit legal basis under GDPR Art. 9"
    if any(kw in pii_type.lower() for kw in ["ssn", "card", "iban", "api key", "password", "jwt"]):
        return "Critical: Remove or encrypt immediately — high risk of identity theft or system compromise"
    if any(kw in pii_type.lower() for kw in ["passport", "ni number", "account"]):
        return "High risk: Ensure this data is necessary, encrypted at rest, and access-controlled"
    if "email" in pii_type.lower() or "phone" in pii_type.lower():
        return "Verify consent is documented and data is covered by your privacy notice"
    return "Review necessity — ensure processing has a documented legal basis under GDPR Art. 6"


# ══════════════════════════════════════════════════════════════════════════════
# REDACTION
# ══════════════════════════════════════════════════════════════════════════════

def redact_pii(
    text: str,
    replacement: str = "[REDACTED]",
    types_to_redact: Optional[List[str]] = None,
) -> str:
    """
    Redact PII from text by replacing matches with a placeholder.

    Args:
        text:             Input text.
        replacement:      Replacement string (default "[REDACTED]").
        types_to_redact:  List of PII type names to redact. If None, redacts all.

    Returns:
        Redacted text string.
    """
    if not text:
        return text

    redacted_count = 0
    for name, pattern, _, _ in PII_DEFINITIONS:
        if types_to_redact and name not in types_to_redact:
            continue
        new_text, n = re.subn(pattern, replacement, text, flags=re.IGNORECASE)
        text          = new_text
        redacted_count += n

    if redacted_count:
        logger.info("redact_pii: replaced %d PII instances.", redacted_count)

    return text


def mask_pii(text: str) -> str:
    """
    Partially mask PII — shows first and last character with asterisks in between.
    Less aggressive than full redaction. Good for audit logs.

    Example: "john@example.com" → "j***@example.com"
    """
    def _mask(match: re.Match) -> str:
        val = match.group()
        if len(val) <= 2:
            return "*" * len(val)
        return val[0] + "*" * (len(val) - 2) + val[-1]

    masked = text
    for _, pattern, _, _ in PII_DEFINITIONS:
        try:
            masked = re.sub(pattern, _mask, masked, flags=re.IGNORECASE)
        except re.error:
            pass
    return masked


# ══════════════════════════════════════════════════════════════════════════════
# RISK SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

def pii_risk_summary(detected: Dict[str, List[str]]) -> Dict[str, Any]:
    """
    Summarise PII detection results into a risk report.

    Args:
        detected: Output from detect_pii().

    Returns:
        Dict with overall_risk, total_instances, by_risk_level, gdpr_implications, recommendations.
    """
    if not detected:
        return {
            "overall_risk":     "None",
            "total_types":      0,
            "total_instances":  0,
            "by_risk_level":    {},
            "special_category": [],
            "gdpr_implications":[],
            "recommendations":  ["No PII detected in document."],
        }

    by_risk: Dict[str, List[str]] = {"Critical": [], "High": [], "Medium": [], "Low": []}
    special: List[str]            = []
    total_instances               = 0

    for pii_type, values in detected.items():
        meta     = PII_META.get(pii_type, {"gdpr_category": "ordinary", "risk_level": "Medium"})
        risk     = meta["risk_level"]
        total_instances += len(values)
        by_risk.setdefault(risk, []).append(pii_type)
        if meta["gdpr_category"] == "special_category":
            special.append(pii_type)

    # Overall risk = highest risk level present
    overall = "Low"
    for level in ["Critical", "High", "Medium", "Low"]:
        if by_risk.get(level):
            overall = level
            break

    implications = _gdpr_implications(detected, special)
    recs         = _build_recommendations(by_risk, special)

    return {
        "overall_risk":      overall,
        "total_types":       len(detected),
        "total_instances":   total_instances,
        "by_risk_level":     {k: v for k, v in by_risk.items() if v},
        "special_category":  special,
        "gdpr_implications": implications,
        "recommendations":   recs,
    }


def _gdpr_implications(
    detected: Dict[str, List[str]],
    special: List[str],
) -> List[str]:
    """Generate GDPR implications based on detected PII types."""
    implications = []

    if detected:
        implications.append(
            "GDPR Art. 5: Verify data minimisation — only collect PII strictly necessary for purpose."
        )
        implications.append(
            "GDPR Art. 13/14: Ensure all detected PII types are disclosed in your privacy notice."
        )

    if special:
        implications.append(
            f"GDPR Art. 9: Special category data detected ({', '.join(special)}). "
            "Explicit consent or another Art. 9(2) condition must be documented."
        )

    if "Credit/Debit Card Number" in detected or "IBAN" in detected:
        implications.append(
            "PCI-DSS Requirement 3: Financial card data must be tokenised — never stored in plain text."
        )

    if "SSN (US)" in detected or "NI Number (UK)" in detected:
        implications.append(
            "Government IDs detected — high re-identification risk. Justify necessity and encrypt."
        )

    return implications


def _build_recommendations(
    by_risk: Dict[str, List[str]],
    special: List[str],
) -> List[str]:
    """Build prioritised recommendations from risk breakdown."""
    recs = []

    if by_risk.get("Critical"):
        recs.append(
            f"🔴 CRITICAL: Immediately review {', '.join(by_risk['Critical'])} — "
            "encrypt, tokenise, or remove as appropriate."
        )
    if by_risk.get("High"):
        recs.append(
            f"🟠 HIGH: Ensure {', '.join(by_risk['High'])} has documented legal basis, "
            "is encrypted at rest, and access-controlled."
        )
    if special:
        recs.append(
            f"⚠️ SPECIAL CATEGORY: {', '.join(special)} requires Art. 9 explicit consent "
            "and a Data Protection Impact Assessment (DPIA)."
        )
    if by_risk.get("Medium"):
        recs.append(
            "🔵 MEDIUM: Verify consent documentation and privacy notice coverage for "
            f"{', '.join(by_risk['Medium'])}."
        )

    recs.append("Conduct a full Data Protection Impact Assessment (DPIA) if processing at scale.")
    return recs


# ══════════════════════════════════════════════════════════════════════════════
# LLM-POWERED DEEP SCAN (optional)
# ══════════════════════════════════════════════════════════════════════════════

def detect_pii_with_llm(
    text: str,
    provider: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Deep PII detection using LLM for contextual understanding.

    Catches PII that regex misses (e.g. names not preceded by titles,
    implicit personal info, sensitive context).

    Falls back to regex detection if LLM is unavailable.

    Args:
        text:     Text to scan.
        provider: Force LLM provider (optional).

    Returns:
        List of detailed PII finding dicts.
    """
    # First run regex scan
    regex_results = detect_pii_detailed(text)

    try:
        from llm.router import route
        raw = route(
            task="pii_detection",
            payload={"text": text[:3000]},
            provider=provider,
        )
        import json, re as _re
        cleaned = _re.sub(r"```(?:json)?", "", raw).strip().rstrip("`")
        llm_results = json.loads(cleaned)

        if isinstance(llm_results, list):
            # Merge regex and LLM results, deduplicating by pii_type
            existing_types = {r["pii_type"] for r in regex_results}
            for llm_item in llm_results:
                if llm_item.get("pii_type") not in existing_types:
                    regex_results.append(llm_item)

    except Exception as exc:
        logger.debug("LLM PII scan skipped: %s", exc)

    return regex_results