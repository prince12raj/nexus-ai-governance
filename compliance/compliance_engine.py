"""
compliance/compliance_engine.py — Core compliance audit engine for Nexus AI Governance Platform.

Orchestrates the full audit pipeline:
  1. Retrieve relevant regulations via RAG
  2. Check for prompt injection in uploaded document
  3. Detect PII in uploaded document
  4. Call LLM via router (OpenAI → HuggingFace → Ollama → Mock)
  5. Parse and validate findings
  6. Calculate compliance score

Usage:
    from compliance.compliance_engine import run_audit, parse_findings, generate_mock_findings

    result = run_audit(policy_text="...", framework="GDPR")
    print(result["score"], result["findings"])
"""
from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, List, Optional

from config.logging_config import get_logger
from config.settings import settings
from models.finding_models import Finding

logger = get_logger("nexus.compliance.engine")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN AUDIT PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

def run_audit(
    policy_text: str,
    framework: str,
    model_name: Optional[str] = None,
    provider: Optional[str] = None,
    enable_pii_scan: bool = True,
    enable_injection_check: bool = True,
) -> Dict[str, Any]:
    """
    Run a full compliance audit on a policy document.

    Pipeline:
        1. Injection check (if enabled)
        2. PII detection (if enabled)
        3. RAG retrieval of relevant regulations
        4. LLM analysis via router
        5. Parse + validate findings
        6. Score calculation

    Args:
        policy_text:            The policy document text to audit.
        framework:              Compliance framework (e.g. "GDPR", "HIPAA").
        model_name:             Override LLM model (optional).
        provider:               Force a specific provider (optional).
        enable_pii_scan:        Run PII detection on the document.
        enable_injection_check: Check for prompt injection attempts.

    Returns:
        Dict with keys:
            findings        — List[Finding]
            score           — float (0–100)
            grade           — str ("A"–"F")
            risk_level      — str
            score_color     — str (hex)
            framework       — str
            pii_detected    — Dict[str, List[str]]
            injection_risk  — float (0–1)
            relevant_regs   — List[Dict]
            provider_used   — str
            duration_sec    — float
            error           — str | None
    """
    start_time = time.time()
    logger.info("run_audit started | framework=%s | text_len=%d", framework, len(policy_text))

    result: Dict[str, Any] = {
        "findings":       [],
        "score":          100.0,
        "grade":          "A",
        "risk_level":     "Low Risk",
        "score_color":    "#00e5a0",
        "framework":      framework,
        "pii_detected":   {},
        "injection_risk": 0.0,
        "relevant_regs":  [],
        "provider_used":  "unknown",
        "duration_sec":   0.0,
        "error":          None,
    }

    # ── 1. Injection check ────────────────────────────────────────────────────
    if enable_injection_check and settings.ENABLE_INJECTION_DETECTION:
        from compliance.injection_detector import detect_prompt_injection, injection_risk_score
        injections = detect_prompt_injection(policy_text)
        risk       = injection_risk_score(policy_text)
        result["injection_risk"] = risk

        if risk >= 0.7:
            logger.warning("High injection risk detected (score=%.2f). Blocking audit.", risk)
            result["error"] = (
                "⚠️ This document contains patterns that may be attempting prompt injection. "
                "Audit blocked for security. Please review the document and resubmit."
            )
            result["duration_sec"] = round(time.time() - start_time, 2)
            return result

        if injections:
            logger.info("Injection patterns detected (%d) but risk below threshold.", len(injections))

    # ── 2. PII detection ──────────────────────────────────────────────────────
    if enable_pii_scan and settings.ENABLE_PII_DETECTION:
        from compliance.pii_detector import detect_pii
        result["pii_detected"] = detect_pii(policy_text)
        if result["pii_detected"]:
            pii_types = list(result["pii_detected"].keys())
            logger.info("PII detected in document: %s", pii_types)

    # ── 3. RAG retrieval ──────────────────────────────────────────────────────
    try:
        from rag.retrieval_tools import retrieve_for_compliance, format_context_for_prompt
        relevant_regs = retrieve_for_compliance(policy_text, framework, k=4)
        result["relevant_regs"] = relevant_regs
        logger.info("RAG retrieved %d relevant regulations.", len(relevant_regs))
    except Exception as exc:
        logger.warning("RAG retrieval failed: %s — using empty context.", exc)
        relevant_regs = []

    # ── 4. LLM analysis ───────────────────────────────────────────────────────
    try:
        raw_json, provider_used = _call_llm(
            policy_text=policy_text,
            framework=framework,
            relevant_regs=relevant_regs,
            model_name=model_name,
            provider=provider,
        )
        result["provider_used"] = provider_used
        logger.info("LLM call complete | provider=%s", provider_used)
    except Exception as exc:
        logger.error("LLM call failed: %s — using mock findings.", exc)
        raw_json        = generate_mock_findings(policy_text, framework, relevant_regs)
        result["provider_used"] = "mock"

    # ── 5. Parse findings ─────────────────────────────────────────────────────
    findings = parse_findings(raw_json)
    result["findings"] = findings
    logger.info("Parsed %d findings.", len(findings))

    # ── 6. Scoring ────────────────────────────────────────────────────────────
    from compliance.scoring import (
        calculate_compliance_score, grade_score, score_color, risk_level
    )
    score                = calculate_compliance_score(findings)
    result["score"]      = score
    result["grade"]      = grade_score(score)
    result["risk_level"] = risk_level(score)
    result["score_color"]= score_color(score)

    result["duration_sec"] = round(time.time() - start_time, 2)
    logger.info(
        "run_audit complete | framework=%s | findings=%d | score=%.1f | time=%.2fs",
        framework, len(findings), score, result["duration_sec"]
    )
    return result


# ══════════════════════════════════════════════════════════════════════════════
# LLM DISPATCH
# ══════════════════════════════════════════════════════════════════════════════

def _call_llm(
    policy_text: str,
    framework: str,
    relevant_regs: List[Dict[str, Any]],
    model_name: Optional[str] = None,
    provider: Optional[str] = None,
) -> tuple[str, str]:
    """
    Route compliance analysis to the best available LLM provider.

    Returns:
        (raw_json_string, provider_name_used)
    """
    # Try router first
    try:
        from llm.router import route_compliance_audit
        raw = route_compliance_audit(
            policy_text=policy_text,
            framework=framework,
            relevant_regs=relevant_regs,
            provider=provider,
        )
        active = provider or _detect_provider()
        return raw, active
    except Exception as exc:
        logger.warning("Router failed: %s — trying direct provider call.", exc)

    # Direct fallback chain
    if settings.OPENAI_API_KEY:
        try:
            from llm.openai_provider import call_compliance_llm
            raw = call_compliance_llm(policy_text, framework, relevant_regs, model=model_name)
            return raw, "openai"
        except Exception as exc:
            logger.warning("OpenAI direct call failed: %s", exc)

    if settings.HUGGINGFACE_API_KEY:
        try:
            from llm.huggingface_provider import call_compliance_llm
            raw = call_compliance_llm(policy_text, framework, relevant_regs)
            return raw, "huggingface"
        except Exception as exc:
            logger.warning("HuggingFace direct call failed: %s", exc)

    try:
        from llm.ollama_provider import call_compliance_llm, is_available
        if is_available():
            raw = call_compliance_llm(policy_text, framework, relevant_regs)
            return raw, "ollama"
    except Exception as exc:
        logger.warning("Ollama direct call failed: %s", exc)

    # Final fallback
    raw = generate_mock_findings(policy_text, framework, relevant_regs)
    return raw, "mock"


def _detect_provider() -> str:
    if settings.OPENAI_API_KEY:        return "openai"
    if settings.HUGGINGFACE_API_KEY:   return "huggingface"
    return "ollama"


# ══════════════════════════════════════════════════════════════════════════════
# DIRECT LLM CALL (legacy / external use)
# ══════════════════════════════════════════════════════════════════════════════

def call_compliance_llm(
    policy_text: str,
    framework: str,
    relevant_regs: List[Dict[str, Any]],
    api_key: str = "",
    model_name: str = "GPT-4o",
) -> str:
    """
    Direct compliance LLM call (kept for backward compatibility).

    Prefer run_audit() for the full pipeline.
    Falls back to generate_mock_findings() on any error.
    """
    try:
        from llm.router import route_compliance_audit
        return route_compliance_audit(policy_text, framework, relevant_regs)
    except Exception as exc:
        logger.warning("call_compliance_llm router failed: %s — using mock.", exc)
        return generate_mock_findings(policy_text, framework, relevant_regs)


# ══════════════════════════════════════════════════════════════════════════════
# MOCK FINDINGS (deterministic, no LLM needed)
# ══════════════════════════════════════════════════════════════════════════════

def generate_mock_findings(
    policy_text: str,
    framework: str,
    relevant_regs: List[Dict[str, Any]],
) -> str:
    """
    Generate deterministic mock findings for demo / offline use.

    Scans for known violation keywords and returns a JSON array.
    Falls back to generic findings based on retrieved regulations.

    Returns:
        Raw JSON string — array of finding dicts.
    """
    findings: List[Dict[str, Any]] = []
    text_lower = policy_text.lower()

    # ── GDPR ──────────────────────────────────────────────────────────────────
    if framework in ("GDPR", "Combined Framework Mode"):
        if any(kw in text_lower for kw in ["indefinitely", "permanently", "forever"]):
            findings.append({
                "violated_string":   _find_sentence(policy_text, ["indefinitely", "permanently", "forever"]),
                "legal_reference":   "GDPR Article 5(1)(e) — Storage Limitation",
                "severity":          "Critical",
                "explanation":       (
                    "GDPR requires data to be kept only as long as necessary for its purpose. "
                    "Indefinite retention violates the storage limitation principle and exposes "
                    "the organisation to fines of up to €20M or 4% of global annual turnover."
                ),
                "corrected_version": (
                    "Personal data shall be retained for a maximum of [X months/years] aligned "
                    "with the documented processing purpose, then securely deleted or anonymised."
                ),
                "confidence_score":  0.97,
                "department":        "Data Engineering",
                "remediation_steps": [
                    "Define specific retention periods for each data category in your data register",
                    "Implement automated deletion workflows triggered at retention period end",
                    "Conduct quarterly data minimisation audits",
                    "Document legal basis for all processing activities",
                ],
            })

        if any(kw in text_lower for kw in ["implicit", "implicitly", "assumed consent"]):
            findings.append({
                "violated_string":   _find_sentence(policy_text, ["implicit", "implicitly"]),
                "legal_reference":   "GDPR Article 7 — Conditions for Consent",
                "severity":          "Critical",
                "explanation":       (
                    "GDPR requires consent to be freely given, specific, informed, and unambiguous. "
                    "Implied or implicit consent does not meet this standard."
                ),
                "corrected_version": (
                    "Users must provide explicit opt-in consent via a clear affirmative action. "
                    "Consent must be granular per purpose, documented, and withdrawable at any time."
                ),
                "confidence_score":  0.96,
                "department":        "Legal & Product",
                "remediation_steps": [
                    "Replace implicit consent mechanisms with explicit opt-in checkboxes",
                    "Implement consent management platform (CMP)",
                    "Build one-click consent withdrawal functionality",
                    "Maintain timestamped consent audit logs",
                ],
            })

        if any(kw in text_lower for kw in ["cannot be deleted", "cannot delete", "will not delete"]):
            findings.append({
                "violated_string":   _find_sentence(policy_text, ["cannot be deleted", "cannot delete"]),
                "legal_reference":   "GDPR Article 17 — Right to Erasure",
                "severity":          "Critical",
                "explanation":       (
                    "Blanket refusal to delete personal data violates the right to erasure (right "
                    "to be forgotten). Exceptions must be assessed individually with documented justification."
                ),
                "corrected_version": (
                    "Data subjects may request erasure of their personal data. Requests will be "
                    "assessed under Article 17 exceptions. Where no exception applies, data will be "
                    "erased within 30 days with written confirmation."
                ),
                "confidence_score":  0.95,
                "department":        "Legal & Engineering",
                "remediation_steps": [
                    "Implement a user-facing erasure request portal",
                    "Build 30-day SLA tracking and escalation workflow",
                    "Develop technical capability to delete data from all systems including backups",
                    "Train staff on handling right-to-erasure requests",
                ],
            })

        if "third party" in text_lower and "without" in text_lower:
            findings.append({
                "violated_string":   _find_sentence(policy_text, ["third party", "without"]),
                "legal_reference":   "GDPR Article 13/14 — Transparency & Third-Party Sharing",
                "severity":          "High",
                "explanation":       (
                    "Data subjects must be explicitly informed about third-party data sharing "
                    "at the point of collection. Undisclosed sharing violates GDPR transparency principles."
                ),
                "corrected_version": (
                    "The privacy notice shall clearly identify all third-party data recipients, "
                    "the legal basis for sharing, and the applicable safeguards or transfer mechanisms."
                ),
                "confidence_score":  0.88,
                "department":        "Legal",
                "remediation_steps": [
                    "Update all privacy notices with complete third-party recipient list",
                    "Implement Data Processing Agreements (DPAs) with all processors",
                    "Maintain a third-party data sharing register",
                    "Review third-party sharing annually",
                ],
            })

        if not any(kw in text_lower for kw in ["encryption", "encrypt", "tls", "ssl", "aes"]):
            findings.append({
                "violated_string":   policy_text[:150] + "...",
                "legal_reference":   "GDPR Article 32 — Security of Processing",
                "severity":          "High",
                "explanation":       (
                    "The policy does not mention encryption measures. GDPR Article 32 requires "
                    "encryption of personal data as an appropriate technical safeguard."
                ),
                "corrected_version": (
                    "All personal data shall be encrypted at rest using AES-256 and in transit "
                    "using TLS 1.3. Encryption keys shall be managed in accordance with ISO 27001."
                ),
                "confidence_score":  0.82,
                "department":        "Engineering",
                "remediation_steps": [
                    "Implement AES-256 encryption for all personal data at rest",
                    "Enforce TLS 1.3 for all data in transit",
                    "Document encryption standards in technical security policy",
                    "Conduct annual encryption audit",
                ],
            })

    # ── HIPAA ─────────────────────────────────────────────────────────────────
    if framework in ("HIPAA", "Combined Framework Mode"):
        if re.search(r'\bhttp\b(?!s)', text_lower):
            findings.append({
                "violated_string":   _find_sentence(policy_text, ["http "]),
                "legal_reference":   "HIPAA 45 CFR §164.312(e)(1) — Transmission Security",
                "severity":          "Critical",
                "explanation":       (
                    "Transmission of ePHI over unencrypted HTTP is a direct HIPAA Security "
                    "Rule violation. All ePHI must be encrypted in transit."
                ),
                "corrected_version": (
                    "All ePHI must be transmitted exclusively over TLS 1.2+ encrypted channels. "
                    "HTTP endpoints that handle ePHI must be disabled immediately."
                ),
                "confidence_score":  0.99,
                "department":        "Engineering",
                "remediation_steps": [
                    "Enforce HTTPS-only across all API endpoints and web interfaces",
                    "Configure HTTP Strict Transport Security (HSTS)",
                    "Implement TLS certificate monitoring and auto-renewal",
                    "Scan for HTTP endpoints in CI/CD pipeline",
                ],
            })

        if "shared" in text_lower and any(kw in text_lower for kw in ["account", "password", "credential"]):
            findings.append({
                "violated_string":   _find_sentence(policy_text, ["shared", "account"]),
                "legal_reference":   "HIPAA 45 CFR §164.312(a)(2)(i) — Unique User Identification",
                "severity":          "Critical",
                "explanation":       (
                    "HIPAA requires each user to have unique credentials. Shared accounts "
                    "make it impossible to maintain the individual audit trails required by the Security Rule."
                ),
                "corrected_version": (
                    "Every individual accessing ePHI must be assigned unique personal credentials. "
                    "Shared or generic accounts are prohibited in any system that processes ePHI."
                ),
                "confidence_score":  0.97,
                "department":        "IT Security",
                "remediation_steps": [
                    "Provision individual user accounts for all staff accessing ePHI",
                    "Audit and remove all shared or generic accounts",
                    "Implement Privileged Access Management (PAM) for admin accounts",
                    "Enable per-user audit logging for all ePHI access",
                ],
            })

        if "baa" not in text_lower and any(kw in text_lower for kw in ["vendor", "api", "third party", "cloud"]):
            findings.append({
                "violated_string":   _find_sentence(policy_text, ["vendor", "api", "cloud"]),
                "legal_reference":   "HIPAA 45 CFR §164.308(b) — Business Associate Agreements",
                "severity":          "Critical",
                "explanation":       (
                    "Sharing PHI with any vendor or service provider without a signed Business "
                    "Associate Agreement (BAA) is a direct HIPAA violation."
                ),
                "corrected_version": (
                    "A fully executed BAA must be in place before sharing any PHI with vendors. "
                    "BAAs must specify permissible uses, safeguards, and breach notification obligations."
                ),
                "confidence_score":  0.94,
                "department":        "Procurement & Legal",
                "remediation_steps": [
                    "Audit all vendors who process, store, or transmit PHI",
                    "Execute BAAs with all identified Business Associates before any PHI sharing",
                    "Add BAA requirement to vendor onboarding and procurement checklist",
                    "Review all BAAs annually",
                ],
            })

    # ── ISO 27001 ──────────────────────────────────────────────────────────────
    if framework in ("ISO 27001", "Combined Framework Mode"):
        if any(kw in text_lower for kw in ["md5", "sha1", "sha-1"]):
            findings.append({
                "violated_string":   _find_sentence(policy_text, ["md5", "sha1", "sha-1"]),
                "legal_reference":   "ISO 27001 A.10.1.1 — Cryptographic Controls",
                "severity":          "Critical",
                "explanation":       (
                    "MD5 and SHA-1 are cryptographically broken algorithms prohibited by "
                    "ISO 27001 and NIST guidelines. Using them for passwords or integrity checks "
                    "poses a critical security risk."
                ),
                "corrected_version": (
                    "All password hashing must use bcrypt (work factor ≥12), Argon2id, or "
                    "PBKDF2-SHA256 with ≥310,000 iterations. File integrity must use SHA-256 minimum."
                ),
                "confidence_score":  0.99,
                "department":        "Engineering",
                "remediation_steps": [
                    "Audit all cryptographic implementations across systems",
                    "Migrate all password storage to bcrypt or Argon2id immediately",
                    "Add cryptographic algorithm validation to code review checklist",
                    "Rotate all credentials stored with deprecated algorithms",
                ],
            })

        if any(kw in text_lower for kw in ["no log", "not log", "logs are not", "without logging"]):
            findings.append({
                "violated_string":   _find_sentence(policy_text, ["no log", "not log"]),
                "legal_reference":   "ISO 27001 A.12.4 — Logging & Monitoring",
                "severity":          "High",
                "explanation":       (
                    "ISO 27001 A.12.4 mandates comprehensive audit logging for all system "
                    "access, user activities, exceptions, and security events."
                ),
                "corrected_version": (
                    "All user activities, system exceptions, and security events must be logged "
                    "with timestamp, user ID, event type, and outcome. Logs retained ≥12 months."
                ),
                "confidence_score":  0.91,
                "department":        "IT Operations",
                "remediation_steps": [
                    "Deploy centralised SIEM solution",
                    "Implement log retention policy (minimum 12 months)",
                    "Enable log integrity verification via hash chaining",
                    "Configure real-time alerting for critical security events",
                ],
            })

    # ── PCI-DSS ───────────────────────────────────────────────────────────────
    if framework in ("PCI-DSS", "Combined Framework Mode"):
        if "cvv" in text_lower or ("card" in text_lower and any(
            kw in text_lower for kw in ["store", "retain", "save", "keep"]
        )):
            findings.append({
                "violated_string":   _find_sentence(policy_text, ["cvv", "card", "store"]),
                "legal_reference":   "PCI DSS v4.0, Requirement 3.2 — SAD Storage Prohibition",
                "severity":          "Critical",
                "explanation":       (
                    "Sensitive Authentication Data (SAD) including CVV/CVC must never be stored "
                    "after authorisation, even if encrypted. This is an absolute PCI-DSS prohibition."
                ),
                "corrected_version": (
                    "Sensitive authentication data must not be stored post-authorisation. "
                    "Use tokenisation and a PCI-certified payment vault for all cardholder data."
                ),
                "confidence_score":  0.98,
                "department":        "Engineering & Payments",
                "remediation_steps": [
                    "Implement tokenisation to replace PAN and CVV with non-sensitive tokens",
                    "Immediately purge any stored CVV/CVC data",
                    "Migrate to a PCI-certified payment gateway",
                    "Conduct a cardholder data environment (CDE) scoping exercise",
                ],
            })

        if "mfa" not in text_lower and "multi-factor" not in text_lower:
            findings.append({
                "violated_string":   policy_text[:150] + "...",
                "legal_reference":   "PCI DSS v4.0, Requirement 8.4 — Multi-Factor Authentication",
                "severity":          "High",
                "explanation":       (
                    "PCI DSS v4.0 mandates MFA for all access into the cardholder data environment. "
                    "The policy does not mention MFA requirements."
                ),
                "corrected_version": (
                    "Multi-factor authentication (MFA) is mandatory for all access to the "
                    "cardholder data environment (CDE) and all remote access to the network."
                ),
                "confidence_score":  0.87,
                "department":        "IT Security",
                "remediation_steps": [
                    "Deploy MFA for all CDE access using TOTP or hardware tokens",
                    "Update access control policy to explicitly require MFA",
                    "Audit all CDE access points for MFA enforcement",
                    "Train staff on MFA enrollment procedures",
                ],
            })

    # ── SOC 2 ─────────────────────────────────────────────────────────────────
    if framework in ("SOC 2", "Combined Framework Mode"):
        if "incident" not in text_lower and "breach" not in text_lower:
            findings.append({
                "violated_string":   policy_text[:150] + "...",
                "legal_reference":   "SOC 2 TSC CC7.3 — Incident Response",
                "severity":          "High",
                "explanation":       (
                    "SOC 2 CC7.3 requires documented incident response procedures. "
                    "The policy does not address security incident or breach handling."
                ),
                "corrected_version": (
                    "The organisation maintains a documented incident response plan covering: "
                    "detection, containment, eradication, recovery, and post-incident review. "
                    "All incidents must be logged and reviewed by management."
                ),
                "confidence_score":  0.85,
                "department":        "Security Operations",
                "remediation_steps": [
                    "Develop and document a formal incident response plan",
                    "Assign incident response roles and responsibilities",
                    "Conduct annual incident response tabletop exercises",
                    "Implement automated incident detection and alerting",
                ],
            })

    # ── Generic fallback if no keyword matches ────────────────────────────────
    if not findings:
        for reg in (relevant_regs[:2] or []):
            findings.append({
                "violated_string":   policy_text[:120] + "...",
                "legal_reference":   reg.get("citation", "General Compliance"),
                "severity":          reg.get("severity", "Medium"),
                "explanation":       (
                    f"The policy may not fully address requirements under "
                    f"{reg.get('title', 'this regulation')}. A detailed manual review is recommended."
                ),
                "corrected_version": (
                    f"Review and update the policy to explicitly address all requirements of "
                    f"{reg.get('citation', 'the applicable regulation')}."
                ),
                "confidence_score":  0.70,
                "department":        "Compliance",
                "remediation_steps": reg.get("remediation", [
                    "Conduct a full compliance gap analysis",
                    "Engage a qualified compliance consultant",
                    "Update policy to address all identified gaps",
                ]),
            })

    return json.dumps(findings)


# ══════════════════════════════════════════════════════════════════════════════
# PARSE & VALIDATE FINDINGS
# ══════════════════════════════════════════════════════════════════════════════

def parse_findings(raw_json: str) -> List[Finding]:
    """
    Parse raw LLM JSON output into validated Finding objects.

    Handles:
      - Markdown code fences (```json ... ```)
      - Wrapped objects ({"findings": [...]})
      - Malformed individual finding objects (skipped with warning)

    Args:
        raw_json: Raw string from LLM or generate_mock_findings().

    Returns:
        List of validated Finding objects. Empty list on parse failure.
    """
    if not raw_json or not raw_json.strip():
        return []

    try:
        # Strip markdown fences
        cleaned = re.sub(r"```(?:json)?", "", raw_json).strip().rstrip("`").strip()

        data = json.loads(cleaned)

        # Unwrap common dict wrappers
        if isinstance(data, dict):
            for key in ("findings", "results", "violations", "items", "data"):
                if key in data and isinstance(data[key], list):
                    data = data[key]
                    break
            else:
                data = [data]

        if not isinstance(data, list):
            logger.error("parse_findings: expected list, got %s", type(data))
            return []

        results: List[Finding] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            try:
                # Normalise severity capitalisation
                if "severity" in item:
                    item["severity"] = item["severity"].capitalize()
                results.append(Finding(**item))
            except Exception as exc:
                logger.warning("Skipping malformed finding: %s | item=%s", exc, str(item)[:100])

        return results

    except json.JSONDecodeError as exc:
        logger.error("JSON parse error in findings: %s | raw=%s", exc, raw_json[:200])

        # Last resort: try to extract JSON array with regex
        match = re.search(r"\[.*\]", raw_json, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
                return [Finding(**item) for item in data if isinstance(item, dict)]
            except Exception:
                pass

        return []


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _find_sentence(text: str, keywords: List[str]) -> str:
    """Extract the first sentence containing any of the keywords."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    for kw in keywords:
        for sent in sentences:
            if kw.lower() in sent.lower():
                return sent[:250]
    return text[:250]