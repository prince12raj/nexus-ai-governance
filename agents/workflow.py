"""
agents/workflow.py — Agent workflow orchestrator for Nexus AI Governance Platform.

Defines multi-step workflows that chain agents together:

  1. full_compliance_workflow  — Upload → PII scan → Injection check → Audit → Remediate → Report
  2. risk_governance_workflow  — AI system description → Risk score → Remediation → EU AI Act
  3. policy_review_workflow    — Policy text → Gap analysis → Generate fixes → Summary
  4. research_workflow         — Question → RAG retrieval → Answer → Sources

Usage:
    from agents.workflow import run_workflow

    result = run_workflow("full_compliance", payload={
        "policy_text": text,
        "framework":   "GDPR",
    })
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from config.logging_config import get_logger

logger = get_logger("nexus.agents.workflow")


# ══════════════════════════════════════════════════════════════════════════════
# WORKFLOW DISPATCHER
# ══════════════════════════════════════════════════════════════════════════════

def run_workflow(
    workflow_name: str,
    payload: Dict[str, Any],
    provider: Optional[str] = None,
    progress_callback: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Run a named multi-agent workflow.

    Args:
        workflow_name:      One of: "full_compliance", "risk_governance",
                            "policy_review", "research"
        payload:            Workflow-specific input data dict.
        provider:           Force LLM provider (optional).
        progress_callback:  Optional callable(step: str, pct: int) for UI progress.

    Returns:
        Workflow result dict (structure varies by workflow).

    Raises:
        ValueError: If workflow_name is not recognised.
    """
    workflows = {
        "full_compliance": full_compliance_workflow,
        "risk_governance": risk_governance_workflow,
        "policy_review":   policy_review_workflow,
        "research":        research_workflow,
    }

    fn = workflows.get(workflow_name)
    if fn is None:
        raise ValueError(
            f"Unknown workflow '{workflow_name}'. "
            f"Valid workflows: {list(workflows.keys())}"
        )

    logger.info("run_workflow | name=%s | provider=%s", workflow_name, provider or "auto")
    return fn(payload=payload, provider=provider, progress_callback=progress_callback)


# ══════════════════════════════════════════════════════════════════════════════
# WORKFLOW 1: FULL COMPLIANCE
# ══════════════════════════════════════════════════════════════════════════════

def full_compliance_workflow(
    payload: Dict[str, Any],
    provider: Optional[str] = None,
    progress_callback: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Full compliance audit workflow.

    Steps:
        1. Injection check        (5%)
        2. PII detection          (15%)
        3. RAG retrieval          (30%)
        4. Compliance audit       (60%)
        5. Remediation planning   (80%)
        6. Executive summary      (95%)
        7. Assemble report        (100%)

    Payload keys:
        policy_text   — str (required)
        framework     — str (default "GDPR")
        policy_name   — str (default "Policy Document")
        org_name      — str (default "Organisation")
        auto_remediate— bool (default True)
        auto_summary  — bool (default True)

    Returns:
        Dict with: audit_result, remediation, executive_summary, duration_sec
    """
    start         = time.time()
    policy_text   = payload.get("policy_text", "")
    framework     = payload.get("framework", "GDPR")
    policy_name   = payload.get("policy_name", "Policy Document")
    org_name      = payload.get("org_name", "Organisation")
    auto_remediate= payload.get("auto_remediate", True)
    auto_summary  = payload.get("auto_summary", True)

    result: Dict[str, Any] = {
        "workflow":          "full_compliance",
        "framework":         framework,
        "policy_name":       policy_name,
        "audit_result":      None,
        "remediation":       None,
        "executive_summary": "",
        "steps_completed":   [],
        "duration_sec":      0.0,
        "error":             None,
    }

    def _progress(step: str, pct: int) -> None:
        result["steps_completed"].append({"step": step, "pct": pct})
        if progress_callback:
            try:
                progress_callback(step, pct)
            except Exception:
                pass
        logger.info("Workflow [full_compliance] | step=%s | %d%%", step, pct)

    try:
        # ── Step 1–4: Core audit ──────────────────────────────────────────────
        _progress("Running compliance audit", 10)
        from compliance.compliance_engine import run_audit
        audit = run_audit(
            policy_text=policy_text,
            framework=framework,
            provider=provider,
            enable_pii_scan=True,
            enable_injection_check=True,
        )
        result["audit_result"] = audit
        _progress("Audit complete", 60)

        # Abort if injection blocked
        if audit.get("error") and "injection" in audit.get("error", "").lower():
            result["error"] = audit["error"]
            result["duration_sec"] = round(time.time() - start, 2)
            return result

        findings = audit.get("findings", [])

        # ── Step 5: Remediation ───────────────────────────────────────────────
        if auto_remediate and findings:
            _progress("Building remediation plan", 70)
            from agents.remediation_agent import RemediationAgent
            rem_agent = RemediationAgent(provider=provider)
            remediation = rem_agent.build_batch_plan(
                findings=findings,
                framework=framework,
            )
            result["remediation"] = remediation
            _progress("Remediation plan ready", 85)

        # ── Step 6: Executive summary ─────────────────────────────────────────
        if auto_summary and findings:
            _progress("Generating executive summary", 90)
            from llm.router import route_executive_summary
            summary = route_executive_summary(
                findings=[
                    f.model_dump() if hasattr(f, "model_dump") else f.dict()
                    for f in findings
                ],
                framework=framework,
                policy_name=policy_name,
                org_name=org_name,
                provider=provider,
            )
            result["executive_summary"] = summary
            _progress("Executive summary ready", 97)

        _progress("Complete", 100)

    except Exception as exc:
        logger.error("full_compliance_workflow failed: %s", exc)
        result["error"] = str(exc)

    result["duration_sec"] = round(time.time() - start, 2)
    return result


# ══════════════════════════════════════════════════════════════════════════════
# WORKFLOW 2: RISK GOVERNANCE
# ══════════════════════════════════════════════════════════════════════════════

def risk_governance_workflow(
    payload: Dict[str, Any],
    provider: Optional[str] = None,
    progress_callback: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    AI system risk governance workflow.

    Steps:
        1. Risk assessment        (30%)
        2. EU AI Act classification(50%)
        3. NIST RMF mapping       (70%)
        4. Mitigation planning    (90%)
        5. Governance report      (100%)

    Payload keys:
        system_description — str (required)
        system_name        — str (default "AI System")

    Returns:
        Dict with: risk_result, eu_ai_act, nist_rmf, governance_report
    """
    start              = time.time()
    system_description = payload.get("system_description", "")
    system_name        = payload.get("system_name", "AI System")

    result: Dict[str, Any] = {
        "workflow":          "risk_governance",
        "system_name":       system_name,
        "risk_result":       None,
        "governance_report": "",
        "steps_completed":   [],
        "duration_sec":      0.0,
        "error":             None,
    }

    def _progress(step: str, pct: int) -> None:
        result["steps_completed"].append({"step": step, "pct": pct})
        if progress_callback:
            try:
                progress_callback(step, pct)
            except Exception:
                pass
        logger.info("Workflow [risk_governance] | step=%s | %d%%", step, pct)

    try:
        _progress("Assessing AI governance risks", 20)
        from agents.risk_scoring_agent import RiskScoringAgent
        agent       = RiskScoringAgent(provider=provider)
        risk_result = agent.assess(system_description, system_name=system_name)
        result["risk_result"] = risk_result
        _progress("Risk assessment complete", 60)

        _progress("Building governance report", 80)
        result["governance_report"] = _build_governance_report(risk_result, system_name)
        _progress("Complete", 100)

    except Exception as exc:
        logger.error("risk_governance_workflow failed: %s", exc)
        result["error"] = str(exc)

    result["duration_sec"] = round(time.time() - start, 2)
    return result


# ══════════════════════════════════════════════════════════════════════════════
# WORKFLOW 3: POLICY REVIEW
# ══════════════════════════════════════════════════════════════════════════════

def policy_review_workflow(
    payload: Dict[str, Any],
    provider: Optional[str] = None,
    progress_callback: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Policy document review and improvement workflow.

    Steps:
        1. Summarise document     (20%)
        2. Gap analysis           (50%)
        3. Generate missing sections (80%)
        4. Readability report     (100%)

    Payload keys:
        policy_text   — str (required)
        framework     — str (default "GDPR")
        doc_name      — str (default "Policy Document")
        generate_gaps — bool (default True)

    Returns:
        Dict with: summary, gap_analysis, generated_sections, readability
    """
    start         = time.time()
    policy_text   = payload.get("policy_text", "")
    framework     = payload.get("framework", "GDPR")
    doc_name      = payload.get("doc_name", "Policy Document")
    generate_gaps = payload.get("generate_gaps", True)

    result: Dict[str, Any] = {
        "workflow":          "policy_review",
        "framework":         framework,
        "summary":           None,
        "gap_analysis":      None,
        "generated_sections":[],
        "steps_completed":   [],
        "duration_sec":      0.0,
        "error":             None,
    }

    def _progress(step: str, pct: int) -> None:
        result["steps_completed"].append({"step": step, "pct": pct})
        if progress_callback:
            try:
                progress_callback(step, pct)
            except Exception:
                pass

    try:
        from agents.policy_analysis_agent import PolicyAnalysisAgent
        agent = PolicyAnalysisAgent(provider=provider)

        _progress("Summarising document", 15)
        result["summary"] = agent.summarise(policy_text, doc_name=doc_name)
        _progress("Document summarised", 30)

        _progress("Running gap analysis", 40)
        gap = agent.gap_analysis(policy_text, framework=framework)
        result["gap_analysis"] = gap
        _progress("Gap analysis complete", 60)

        if generate_gaps and gap.get("missing_elements"):
            _progress("Generating missing policy sections", 65)
            generated: List[Dict[str, Any]] = []
            for missing_name in gap["missing_elements"][:3]:    # cap at 3
                section = agent.generate_section(
                    section_title=missing_name,
                    framework=framework,
                )
                generated.append(section)
            result["generated_sections"] = generated
            _progress("Sections generated", 90)

        _progress("Complete", 100)

    except Exception as exc:
        logger.error("policy_review_workflow failed: %s", exc)
        result["error"] = str(exc)

    result["duration_sec"] = round(time.time() - start, 2)
    return result


# ══════════════════════════════════════════════════════════════════════════════
# WORKFLOW 4: RESEARCH
# ══════════════════════════════════════════════════════════════════════════════

def research_workflow(
    payload: Dict[str, Any],
    provider: Optional[str] = None,
    progress_callback: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Regulatory research workflow.

    Steps:
        1. RAG retrieval          (40%)
        2. LLM answer generation  (80%)
        3. Source formatting      (100%)

    Payload keys:
        question  — str (required)
        framework — str | None (optional filter)
        k         — int (number of sources, default 4)

    Returns:
        Dict with: answer, sources, question, framework
    """
    start     = time.time()
    question  = payload.get("question", "")
    framework = payload.get("framework")
    k         = payload.get("k", 4)

    result: Dict[str, Any] = {
        "workflow":      "research",
        "answer":        "",
        "sources":       [],
        "question":      question,
        "framework":     framework,
        "steps_completed":[],
        "duration_sec":  0.0,
        "error":         None,
    }

    def _progress(step: str, pct: int) -> None:
        result["steps_completed"].append({"step": step, "pct": pct})
        if progress_callback:
            try:
                progress_callback(step, pct)
            except Exception:
                pass

    try:
        _progress("Searching knowledge base", 30)
        from agents.regulatory_research_agent import RegulatoryResearchAgent
        agent    = RegulatoryResearchAgent(provider=provider)
        research = agent.answer(question=question, framework=framework, k=k)

        result["answer"]  = research["answer"]
        result["sources"] = research["sources"]
        _progress("Complete", 100)

    except Exception as exc:
        logger.error("research_workflow failed: %s", exc)
        result["error"] = str(exc)

    result["duration_sec"] = round(time.time() - start, 2)
    return result


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _build_governance_report(risk_result: Dict[str, Any], system_name: str) -> str:
    """Build a governance report string from risk assessment results."""
    score   = risk_result.get("overall_score", 0)
    level   = risk_result.get("risk_level", "Unknown")
    eu_act  = risk_result.get("eu_ai_act", "Unknown")
    risks   = risk_result.get("risks", [])
    recs    = risk_result.get("recommendations", [])

    lines = [
        f"AI GOVERNANCE REPORT — {system_name}",
        f"Overall Risk Score: {score}/100 | Risk Level: {level}",
        f"EU AI Act Classification: {eu_act}",
        "",
        f"Risk Areas Identified ({len(risks)}):",
    ]
    for r in risks[:5]:
        lines.append(
            f"  [{r.get('risk_category','?')}] Score: {r.get('risk_score','?')} — "
            f"{r.get('risk_description','')[:80]}"
        )

    lines += ["", "Top Recommendations:"]
    for i, rec in enumerate(recs[:4], 1):
        lines.append(f"  {i}. {rec}")

    return "\n".join(lines)