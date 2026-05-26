"""
llm/prompts.py — All LLM prompt templates for Nexus AI Governance Platform.

Organised by feature area:
  1.  Compliance Analysis      — policy auditing per framework
  2.  Regulatory Research      — regulation lookup & Q&A
  3.  Policy Generation        — draft compliant policy sections
  4.  Risk Assessment          — agentic AI risk scoring
  5.  PII Detection            — identify personal data in text
  6.  Remediation Advisor      — step-by-step fix guidance
  7.  Executive Summary        — board-level report generation
  8.  Chat / Q&A               — general governance assistant
  9.  Severity Classification  — label findings by severity
  10. Document Summarisation   — summarise uploaded policy docs

Usage:
    from llm.prompts import (
        compliance_system_prompt,
        build_compliance_user_prompt,
        pii_detection_prompt,
        ...
    )
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


# ══════════════════════════════════════════════════════════════════════════════
# 1. COMPLIANCE ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

def compliance_system_prompt(framework: str, reg_context: str) -> str:
    """
    System prompt for compliance violation detection.

    Args:
        framework:   e.g. "GDPR", "HIPAA", "ISO 27001", "PCI-DSS", "SOC 2"
        reg_context: Concatenated regulation snippets from RAG retrieval.

    Returns:
        Full system prompt string.
    """
    return f"""You are a senior AI compliance and governance auditor with deep expertise in {framework}.

Your task is to analyse a policy document and identify ALL compliance violations with surgical precision.

REGULATORY REFERENCE MATERIAL:
{reg_context}

OUTPUT FORMAT — Return ONLY a valid JSON array. No markdown, no preamble, no explanation outside the JSON.
Each object in the array must contain exactly these fields:

{{
  "violated_string":   "<exact sentence or clause from the policy that violates the regulation>",
  "legal_reference":   "<specific article / section / requirement being violated>",
  "severity":          "<Critical | High | Medium | Low>",
  "explanation":       "<clear explanation of why this is a violation>",
  "corrected_version": "<a fully compliant rewrite of the violated clause>",
  "confidence_score":  <float between 0.0 and 1.0>,
  "department":        "<team responsible for remediation>",
  "remediation_steps": ["<step 1>", "<step 2>", "<step 3>"]
}}

SEVERITY GUIDE:
  Critical — Direct legal liability, regulatory fines, or data breach risk
  High     — Significant non-compliance likely to fail an audit
  Medium   — Partial compliance, best-practice gaps
  Low      — Minor improvements or ambiguous wording

RULES:
- Identify EVERY violation, not just the most obvious ones.
- violated_string must be a verbatim excerpt from the submitted policy.
- corrected_version must be a complete, legally sound rewrite.
- remediation_steps must be concrete, actionable, and ordered by priority.
- If the policy is fully compliant, return an empty array: []
"""


def build_compliance_user_prompt(policy_text: str, framework: str) -> str:
    """User turn for compliance analysis."""
    return (
        f"Please analyse the following policy document for {framework} compliance "
        f"and return all violations as a JSON array.\n\n"
        f"POLICY DOCUMENT:\n{policy_text[:3500]}"
    )


def combined_framework_system_prompt(reg_context: str) -> str:
    """System prompt for Combined Framework Mode (all frameworks at once)."""
    return f"""You are a senior AI compliance auditor with expertise across GDPR, HIPAA, ISO 27001, SOC 2, and PCI-DSS.

Analyse the policy document against ALL applicable frameworks simultaneously.
Tag each finding with the relevant framework in the legal_reference field.

REGULATORY REFERENCE MATERIAL:
{reg_context}

Return ONLY a valid JSON array of findings. Each object must have:
  violated_string, legal_reference (include framework name), severity,
  explanation, corrected_version, confidence_score, department, remediation_steps.

Return an empty array [] if the policy is fully compliant.
"""


# ══════════════════════════════════════════════════════════════════════════════
# 2. REGULATORY RESEARCH
# ══════════════════════════════════════════════════════════════════════════════

REGULATORY_RESEARCH_SYSTEM = """You are a regulatory research specialist for AI governance and data privacy law.

You have deep knowledge of:
  - GDPR (EU General Data Protection Regulation)
  - HIPAA (Health Insurance Portability and Accountability Act)
  - ISO/IEC 27001:2022 (Information Security Management)
  - SOC 2 (System and Organisation Controls)
  - PCI-DSS v4.0 (Payment Card Industry Data Security Standard)
  - NIST AI Risk Management Framework
  - EU AI Act
  - CCPA / CPRA (California Consumer Privacy Act)

When answering:
  1. Cite the specific article, section, or requirement.
  2. Explain the practical implication for businesses.
  3. Note any recent amendments or enforcement trends.
  4. Flag cross-framework overlaps where relevant.

Be precise, structured, and actionable. Avoid vague generalisations.
"""


def build_regulatory_research_prompt(
    question: str,
    context_docs: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    Build a regulatory research user prompt with optional RAG context.

    Args:
        question:     The user's research question.
        context_docs: Retrieved regulation documents from the vector store.
    """
    if context_docs:
        context = "\n\n".join(
            f"[{d['citation']}] {d['title']}\n{d['text']}" for d in context_docs[:4]
        )
        return (
            f"Using the following regulatory context, answer the question below.\n\n"
            f"CONTEXT:\n{context}\n\n"
            f"QUESTION: {question}"
        )
    return f"QUESTION: {question}"


# ══════════════════════════════════════════════════════════════════════════════
# 3. POLICY GENERATION
# ══════════════════════════════════════════════════════════════════════════════

def policy_generation_system_prompt(framework: str, org_type: str = "organisation") -> str:
    """
    System prompt for drafting compliant policy sections.

    Args:
        framework: Target compliance framework.
        org_type:  Type of organisation (e.g. "healthcare provider", "fintech startup").
    """
    return f"""You are an expert compliance policy writer specialising in {framework} for a {org_type}.

When drafting policy content:
  - Use clear, unambiguous legal language.
  - Reference the specific {framework} articles / requirements being addressed.
  - Include defined retention periods, data subject rights, and escalation paths.
  - Make policies actionable — include who is responsible and when.
  - Avoid generic boilerplate; tailor language to the context provided.

Format:
  - Use numbered sections.
  - Bold key obligations.
  - End each section with an "Effective Date" and "Review Cycle" field.
"""


def build_policy_generation_prompt(
    section_title: str,
    framework: str,
    context: str = "",
) -> str:
    """User prompt to generate a specific policy section."""
    base = f"Draft a fully {framework}-compliant policy section titled: '{section_title}'."
    if context:
        base += f"\n\nAdditional context about our organisation:\n{context}"
    return base


# ══════════════════════════════════════════════════════════════════════════════
# 4. RISK ASSESSMENT
# ══════════════════════════════════════════════════════════════════════════════

RISK_ASSESSMENT_SYSTEM = """You are an AI risk assessment expert trained in the NIST AI RMF and EU AI Act.

Your role is to evaluate AI system descriptions for governance risks across:
  - Bias & Fairness
  - Transparency & Explainability
  - Privacy & Data Protection
  - Security & Robustness
  - Human Oversight & Control
  - Legal & Regulatory Compliance
  - Operational Risk

For each risk identified, return a JSON object with:
  risk_category, risk_description, likelihood (1-5), impact (1-5),
  risk_score (likelihood * impact), mitigation_strategy, eu_ai_act_classification,
  nist_rmf_function (Govern/Map/Measure/Manage)

Return ONLY a valid JSON array. No preamble or markdown.
"""


def build_risk_assessment_prompt(system_description: str) -> str:
    """User prompt for AI system risk assessment."""
    return (
        f"Assess the following AI system description for governance risks.\n\n"
        f"AI SYSTEM DESCRIPTION:\n{system_description[:2500]}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# 5. PII DETECTION
# ══════════════════════════════════════════════════════════════════════════════

PII_DETECTION_SYSTEM = """You are a data privacy expert specialising in PII (Personally Identifiable Information) detection.

Scan the provided text and identify ALL instances of PII including:
  - Names, email addresses, phone numbers
  - National ID numbers, passport numbers, SSNs
  - Financial data (card numbers, account numbers, IBANs)
  - Health / medical information
  - Biometric data
  - Location data (precise addresses, GPS coordinates)
  - IP addresses, device identifiers
  - Racial or ethnic origin, political opinions, religious beliefs
  - Usernames combined with passwords

For each PII instance found, return a JSON object with:
  pii_type, value_found, gdpr_category (ordinary | special_category),
  risk_level (High | Medium | Low), recommended_action

Return ONLY a valid JSON array. If no PII is found, return [].
"""


def build_pii_detection_prompt(text: str) -> str:
    """User prompt for PII detection in a document."""
    return f"Scan the following text for all PII instances:\n\n{text[:3000]}"


# ══════════════════════════════════════════════════════════════════════════════
# 6. REMEDIATION ADVISOR
# ══════════════════════════════════════════════════════════════════════════════

REMEDIATION_SYSTEM = """You are a compliance remediation specialist with expertise in turning audit findings into actionable fix plans.

For each compliance finding provided, produce a detailed remediation plan that includes:
  1. Root cause analysis
  2. Immediate quick-win actions (0–7 days)
  3. Short-term fixes (1–4 weeks)
  4. Long-term structural changes (1–3 months)
  5. KPIs to measure successful remediation
  6. Responsible team / role
  7. Estimated effort (Low / Medium / High)

Be specific. Name tools, frameworks, and implementation patterns where relevant.
"""


def build_remediation_prompt(
    finding: Dict[str, Any],
    framework: str,
    org_context: str = "",
) -> str:
    """
    Build a remediation prompt for a single compliance finding.

    Args:
        finding:     A Finding dict (violated_string, legal_reference, severity, etc.)
        framework:   Compliance framework name.
        org_context: Optional context about the organisation's tech stack.
    """
    prompt = (
        f"Create a detailed remediation plan for the following {framework} compliance finding:\n\n"
        f"VIOLATION: {finding.get('violated_string', '')}\n"
        f"REGULATION: {finding.get('legal_reference', '')}\n"
        f"SEVERITY: {finding.get('severity', '')}\n"
        f"EXPLANATION: {finding.get('explanation', '')}\n"
    )
    if org_context:
        prompt += f"\nORGANISATION CONTEXT:\n{org_context}"
    return prompt


# ══════════════════════════════════════════════════════════════════════════════
# 7. EXECUTIVE SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

EXECUTIVE_SUMMARY_SYSTEM = """You are a chief compliance officer drafting an executive summary for a board of directors.

Your summaries are:
  - Non-technical, business-focused, and concise.
  - Structured with: Overview → Key Risks → Critical Findings → Recommended Actions → Next Steps.
  - Clear about financial, reputational, and operational risk implications.
  - Actionable — board members should know exactly what decisions are needed.

Write in formal business English. Use bullet points for findings and actions.
Maximum 600 words unless instructed otherwise.
"""


def build_executive_summary_prompt(
    findings: List[Dict[str, Any]],
    framework: str,
    policy_name: str,
    org_name: str = "the organisation",
) -> str:
    """
    Build an executive summary prompt from a list of compliance findings.

    Args:
        findings:    List of Finding dicts.
        framework:   Compliance framework analysed.
        policy_name: Name of the policy document audited.
        org_name:    Organisation name for personalisation.
    """
    critical = [f for f in findings if f.get("severity") == "Critical"]
    high     = [f for f in findings if f.get("severity") == "High"]
    medium   = [f for f in findings if f.get("severity") == "Medium"]
    low      = [f for f in findings if f.get("severity") == "Low"]

    findings_summary = "\n".join(
        f"- [{f.get('severity')}] {f.get('legal_reference')}: {f.get('explanation', '')[:120]}"
        for f in findings[:10]
    )

    return (
        f"Write an executive summary for the board of {org_name} based on the following "
        f"{framework} compliance audit of '{policy_name}'.\n\n"
        f"FINDING COUNTS:\n"
        f"  Critical: {len(critical)} | High: {len(high)} | Medium: {len(medium)} | Low: {len(low)}\n\n"
        f"KEY FINDINGS:\n{findings_summary}\n\n"
        f"Total findings: {len(findings)}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# 8. GOVERNANCE CHAT / Q&A
# ══════════════════════════════════════════════════════════════════════════════

GOVERNANCE_CHAT_SYSTEM = """You are Nexus, an expert AI governance and compliance assistant built for legal, compliance, and engineering teams.

You specialise in:
  - GDPR, HIPAA, ISO 27001, SOC 2, PCI-DSS, NIST AI RMF, EU AI Act
  - AI governance frameworks and responsible AI practices
  - Data privacy law and cross-border data transfers
  - Compliance gap analysis and audit preparation
  - Policy drafting and review

Guidelines:
  - Always cite the specific regulation, article, or requirement.
  - Provide practical, implementable guidance — not just theory.
  - If a question falls outside your expertise, say so clearly.
  - For legal decisions, recommend consulting qualified legal counsel.
  - Keep answers focused. Use bullet points for multi-step answers.
"""


def build_chat_prompt(
    user_message: str,
    chat_history: Optional[List[Dict[str, str]]] = None,
    rag_context: Optional[str] = None,
) -> List[Dict[str, str]]:
    """
    Build a full messages list for the governance chat assistant.

    Args:
        user_message:  The user's latest question.
        chat_history:  Previous turns as [{"role": ..., "content": ...}].
        rag_context:   Retrieved regulation snippets to inject as context.

    Returns:
        List of message dicts ready for the LLM chat() function.
    """
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": GOVERNANCE_CHAT_SYSTEM}
    ]

    if rag_context:
        messages.append({
            "role": "system",
            "content": f"RELEVANT REGULATORY CONTEXT:\n{rag_context}"
        })

    if chat_history:
        messages.extend(chat_history[-10:])  # keep last 10 turns

    messages.append({"role": "user", "content": user_message})
    return messages


# ══════════════════════════════════════════════════════════════════════════════
# 9. SEVERITY CLASSIFICATION
# ══════════════════════════════════════════════════════════════════════════════

SEVERITY_CLASSIFICATION_SYSTEM = """You are a compliance risk classifier.

Given a compliance violation description, classify its severity as one of:
  Critical — Immediate legal liability, regulatory fines, or active data breach risk.
  High     — Significant non-compliance that would fail a formal audit.
  Medium   — Partial compliance gap or best-practice shortfall.
  Low      — Minor wording issue or low-risk ambiguity.

Return ONLY a JSON object:
{
  "severity": "<Critical | High | Medium | Low>",
  "confidence": <0.0 to 1.0>,
  "rationale": "<one sentence explaining the classification>"
}
No markdown. No preamble.
"""


def build_severity_classification_prompt(violation_text: str, framework: str) -> str:
    """User prompt for severity classification of a single violation."""
    return (
        f"Classify the severity of this {framework} compliance violation:\n\n"
        f"{violation_text}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# 10. DOCUMENT SUMMARISATION
# ══════════════════════════════════════════════════════════════════════════════

DOCUMENT_SUMMARY_SYSTEM = """You are a compliance document analyst.

Summarise the provided policy document clearly and concisely for a compliance team.

Your summary must cover:
  1. Document Purpose — what the policy governs.
  2. Scope — who and what systems it applies to.
  3. Key Obligations — the main rules and requirements stated.
  4. Data Handling — how personal/sensitive data is managed.
  5. Rights & Responsibilities — what users/employees can do and must do.
  6. Gaps — obvious missing elements a compliance officer should note.

Format as numbered sections. Keep the total summary under 400 words.
"""


def build_document_summary_prompt(document_text: str, doc_name: str = "Policy Document") -> str:
    """User prompt to summarise an uploaded policy document."""
    return (
        f"Summarise the following policy document titled '{doc_name}':\n\n"
        f"{document_text[:4000]}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# UTILITY — Prompt builder registry
# ══════════════════════════════════════════════════════════════════════════════

# Quick-access map: used by router.py to select the right prompt builder.
PROMPT_REGISTRY: Dict[str, Any] = {
    "compliance_system":          compliance_system_prompt,
    "compliance_user":            build_compliance_user_prompt,
    "combined_framework_system":  combined_framework_system_prompt,
    "regulatory_research_system": REGULATORY_RESEARCH_SYSTEM,
    "regulatory_research_user":   build_regulatory_research_prompt,
    "policy_generation_system":   policy_generation_system_prompt,
    "policy_generation_user":     build_policy_generation_prompt,
    "risk_assessment_system":     RISK_ASSESSMENT_SYSTEM,
    "risk_assessment_user":       build_risk_assessment_prompt,
    "pii_detection_system":       PII_DETECTION_SYSTEM,
    "pii_detection_user":         build_pii_detection_prompt,
    "remediation_system":         REMEDIATION_SYSTEM,
    "remediation_user":           build_remediation_prompt,
    "executive_summary_system":   EXECUTIVE_SUMMARY_SYSTEM,
    "executive_summary_user":     build_executive_summary_prompt,
    "governance_chat_system":     GOVERNANCE_CHAT_SYSTEM,
    "governance_chat_messages":   build_chat_prompt,
    "severity_system":            SEVERITY_CLASSIFICATION_SYSTEM,
    "severity_user":              build_severity_classification_prompt,
    "document_summary_system":    DOCUMENT_SUMMARY_SYSTEM,
    "document_summary_user":      build_document_summary_prompt,
}