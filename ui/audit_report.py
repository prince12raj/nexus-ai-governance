"""
ui/audit_report.py — Compliance Auditor and Audit Reports pages for Nexus AI Governance Platform.
"""
from __future__ import annotations

import datetime
import time

import streamlit as st

from compliance.scoring import calculate_compliance_score, score_color, grade_score, risk_level
from config.constants import SUPPORTED_FRAMEWORKS
from ui.dashboard import render_page_header, render_kpi_card


def _f(r, field: str, default=None):
    """
    Safely read a field from either a dict (Supabase row) or an object (AuditReport/Finding).
    Handles field name aliases between DB columns and object attributes.
    """
    if isinstance(r, dict):
        return r.get(field, default)
    return getattr(r, field, default)


# ══════════════════════════════════════════════════════════════════════════════
# COMPLIANCE AUDITOR PAGE
# ══════════════════════════════════════════════════════════════════════════════

def render_compliance_auditor() -> None:
    from auth.session_manager import get_current_user
    user = get_current_user()
    render_page_header(
        "Compliance Auditor",
        "AI-powered policy compliance analysis engine",
        user.get("role", "") if user else "",
    )

    docs = st.session_state.get("uploaded_docs", [])
    if not docs:
        st.warning("⬆️ Please upload a policy document first via the **Policy Upload** page.")
        return

    # ── Controls ───────────────────────────────────────────────────────────────
    col_doc, col_fw, col_model = st.columns(3)
    with col_doc:
        doc_names    = [d.get("name", "") for d in docs]
        selected_doc = st.selectbox("Select document", doc_names)
    with col_fw:
        framework = st.selectbox("Compliance framework", SUPPORTED_FRAMEWORKS)
    with col_model:
        from config.settings import settings
        provider_hint = (
            "GPT-4o (Active)" if settings.OPENAI_API_KEY else
            "HuggingFace (Active)" if settings.HUGGINGFACE_API_KEY else
            "Ollama / Mock"
        )
        st.selectbox("LLM Provider", [provider_hint], disabled=True)

    # Resolve document text — try session first, then DB text_content,
    # then fetch full text from Supabase if still missing.
    selected = next((d for d in docs if d.get("name") == selected_doc), {})
    doc_text = (
        selected.get("text")             # session-uploaded (full text)
        or selected.get("text_content")  # already fetched from DB
        or ""
    )

    if not doc_text and selected_doc:
        # Doc was loaded from DB as metadata-only — fetch text_content now
        username = st.session_state.get("username", "")
        if username:
            with st.spinner("Loading document from database…"):
                try:
                    from database.database_manager import db_get_document_text
                    doc_text = db_get_document_text(username, selected_doc)
                    # Cache it back into session so we don't fetch again
                    if doc_text:
                        for d in docs:
                            if d.get("name") == selected_doc:
                                d["text"] = doc_text
                                break
                except Exception as exc:
                    st.error(f"Failed to load document text: {exc}")
                    return

    if not doc_text:
        st.warning(
            "⚠️ No text content found for this document. "
            "Please re-upload the file.",
            icon="⚠️",
        )
        return

    # ── Pre-scan alerts ────────────────────────────────────────────────────────
    _render_prescan_alerts(doc_text)

    # ── Run button ─────────────────────────────────────────────────────────────
    if st.button("🔍 Run Compliance Audit", type="primary", width='stretch'):
        _run_audit_ui(doc_text, selected_doc, framework)


def _render_prescan_alerts(doc_text: str) -> None:
    from compliance.pii_detector import detect_pii
    from compliance.injection_detector import detect_prompt_injection

    pii = detect_pii(doc_text)
    inj = detect_prompt_injection(doc_text)

    if pii:
        types = ", ".join(list(pii.keys())[:4])
        st.markdown(
            f'<div class="pii-alert"><div class="pii-alert-title">⚠️ PII Detected</div>'
            f'Types found: <strong>{types}</strong>. Ensure data minimisation before processing.</div>',
            unsafe_allow_html=True,
        )
    if inj:
        st.markdown(
            '<div class="injection-alert"><div class="injection-alert-title">'
            '🛡️ Potential Prompt Injection Detected</div>'
            'Adversarial patterns found. Audit will proceed with security monitoring.</div>',
            unsafe_allow_html=True,
        )


def _run_audit_ui(doc_text: str, doc_name: str, framework: str) -> None:
    """Run the compliance audit with animated agent progress display."""

    agents = [
        ("📚", "Regulatory Research Agent",  "Retrieving relevant regulations…"),
        ("🔍", "Policy Analysis Agent",       "Analysing policy for violations…"),
        ("⚖️",  "Risk Scoring Agent",          "Scoring severity and confidence…"),
        ("🔧", "Remediation Agent",           "Generating remediation guidance…"),
        ("✅", "Governance Agent",            "Compiling audit report…"),
    ]

    progress_ph = st.empty()
    bar_ph      = st.empty()

    for idx in range(len(agents) + 1):
        rows = ""
        for i, (icon, name, status) in enumerate(agents):
            if i < idx:
                dot, txt = "done", "✓ Complete"
            elif i == idx:
                dot, txt = "running", status
            else:
                dot, txt = "idle", "Waiting…"
            rows += (
                f'<div class="agent-row">'
                f'<div class="agent-dot {dot}"></div>'
                f'<span class="agent-name">{icon} {name}</span>'
                f'<span class="agent-status-text">{txt}</span>'
                f'</div>'
            )

        progress_ph.markdown(
            f'<div style="background:#111827;border:1px solid rgba(59,127,245,0.12);'
            f'border-radius:12px;padding:1rem;">{rows}</div>',
            unsafe_allow_html=True,
        )
        bar_ph.progress(min(idx / len(agents), 1.0))
        time.sleep(0.4)

    progress_ph.empty()
    bar_ph.empty()

    # ── Actual audit ───────────────────────────────────────────────────────────
    with st.spinner("Finalising audit report…"):
        from compliance.compliance_engine import run_audit
        result = run_audit(policy_text=doc_text, framework=framework)

    if result.get("error"):
        st.error(result["error"])
        return

    findings = result.get("findings", [])
    score    = result.get("score", 0.0)

    _save_audit_report(doc_name, framework, findings, score)
    _render_audit_results(findings, score, framework, result)


def _render_audit_results(findings, score, framework, result):
    """Render the full audit results panel."""
    color = score_color(score)
    grade = grade_score(score)
    level = risk_level(score)

    st.markdown("---")
    st.markdown(f"""
    <div class="score-banner">
      <div class="score-number" style="color:{color};">{score:.0f}</div>
      <div style="font-family:'Syne',sans-serif;font-size:2rem;font-weight:700;color:{color};">{grade}</div>
      <div class="score-label">{level} · {framework} Compliance Score · {len(findings)} finding(s)</div>
    </div>
    """, unsafe_allow_html=True)

    from collections import Counter
    # findings may be dicts or objects
    sev_counts = Counter(_f(f, "severity", "Medium") for f in findings)

    c1, c2, c3, c4 = st.columns(4)
    with c1: render_kpi_card("Score",       f"{score:.0f}%", grade, "neutral", "🛡️", "blue")
    with c2: render_kpi_card("Critical",    str(sev_counts.get("Critical", 0)), "findings", "down" if sev_counts.get("Critical") else "up", "🔴", "red")
    with c3: render_kpi_card("High",        str(sev_counts.get("High", 0)),     "findings", "neutral", "🟠", "yellow")
    with c4: render_kpi_card("Medium/Low",  str(sev_counts.get("Medium", 0) + sev_counts.get("Low", 0)), "findings", "neutral", "🔵", "green")

    if not findings:
        st.success("🎉 No compliance violations found. This policy appears to be fully compliant.")
        return

    st.markdown('<div class="section-header">📋 Compliance Findings</div>', unsafe_allow_html=True)

    for i, f in enumerate(findings):
        sev         = (_f(f, "severity",          "Medium") or "Medium").lower()
        legal_ref   = _f(f, "legal_reference",    "") or ""
        violated    = _f(f, "violated_string",    "") or ""
        explanation = _f(f, "explanation",        "") or ""
        corrected   = _f(f, "corrected_version",  "") or ""
        dept        = _f(f, "department",         "") or ""
        confidence  = _f(f, "confidence_score",   0)  or 0
        steps       = _f(f, "remediation_steps",  []) or []

        icon = (
            "🔴" if sev == "critical" else
            "🟠" if sev == "high" else
            "🔵" if sev == "medium" else "🟢"
        )

        with st.expander(f"{icon} [{sev.upper()}] {legal_ref}", expanded=(i == 0)):
            st.markdown(f"""
            <div class="finding-card {sev}">
              <div style="display:flex;justify-content:space-between;margin-bottom:0.8rem;">
                <span class="severity-badge {sev}">{sev.upper()}</span>
                <span style="font-size:0.75rem;color:#4a5a78;">
                  Confidence: {confidence:.0%} · Dept: {dept}
                </span>
              </div>
              <div style="background:rgba(255,71,87,0.06);border-radius:6px;padding:0.7rem;
                          margin-bottom:0.8rem;font-family:'DM Mono',monospace;
                          font-size:0.78rem;color:#8a9bbc;line-height:1.5;">
                "{violated[:300]}"
              </div>
              <div style="font-size:0.85rem;color:#8a9bbc;line-height:1.6;margin-bottom:0.8rem;">
                {explanation}
              </div>
            </div>
            """, unsafe_allow_html=True)

            if corrected:
                st.markdown(f"""
                <div class="fix-card">
                  <div class="fix-card-title">✅ Corrected Version</div>
                  <div class="fix-card-text">{corrected}</div>
                </div>
                """, unsafe_allow_html=True)

            if steps:
                st.markdown("**🔧 Remediation Steps:**")
                for j, step in enumerate(steps, 1):
                    st.markdown(f"{j}. {step}")

    if st.button("📊 Generate Executive Summary", type="secondary"):
        with st.spinner("Generating board-level summary…"):
            from llm.router import route_executive_summary
            findings_dicts = []
            for f in findings:
                if isinstance(f, dict):
                    findings_dicts.append(f)
                elif hasattr(f, "model_dump"):
                    findings_dicts.append(f.model_dump())
                elif hasattr(f, "dict"):
                    findings_dicts.append(f.dict())
                else:
                    findings_dicts.append({"severity": _f(f, "severity", "")})
            summary = route_executive_summary(findings_dicts, framework, "Policy Document")
        st.markdown(f"""
        <div class="exec-summary">
          <div class="exec-summary-title">📋 Executive Summary</div>
          <div class="exec-summary-text">{summary}</div>
        </div>
        """, unsafe_allow_html=True)


def _save_audit_report(doc_name, framework, findings, score):
    """Save audit report to session history AND Supabase DB."""
    try:
        from models.audit_models import AuditReport

        critical = sum(1 for f in findings if _f(f, "severity", "") == "Critical")
        high     = sum(1 for f in findings if _f(f, "severity", "") == "High")
        medium   = sum(1 for f in findings if _f(f, "severity", "") == "Medium")
        low      = sum(1 for f in findings if _f(f, "severity", "") == "Low")

        report = AuditReport(
            compliance_score     = score,
            executive_summary    = "",
            framework_targeted   = framework,
            document_name        = doc_name,
            total_findings       = len(findings),
            critical_findings    = critical,
            high_findings        = high,
            medium_findings      = medium,
            low_findings         = low,
            generated_timestamp  = datetime.datetime.now().isoformat(),
            findings             = findings,
        )

        history = st.session_state.setdefault("audit_history", [])
        history.append(report)
        st.session_state["current_report"] = report

        username = st.session_state.get("username", "")
        if username:
            from auth.db_session import save_audit_to_db
            save_audit_to_db(username, report)

    except Exception as exc:
        import logging
        logging.getLogger("nexus").warning("_save_audit_report error: %s", exc)


# ══════════════════════════════════════════════════════════════════════════════
# AUDIT REPORTS PAGE
# ══════════════════════════════════════════════════════════════════════════════

def render_audit_reports() -> None:
    from auth.session_manager import get_current_user
    user = get_current_user()
    render_page_header(
        "Audit Reports",
        "View, export and manage compliance audit history",
        user.get("role", "") if user else "",
    )

    reports = st.session_state.get("audit_history", [])

    if not reports:
        st.info("📋 No audit reports yet. Run a compliance audit to generate reports.", icon="ℹ️")
        if st.button("🔍 Go to Compliance Auditor", type="primary"):
            st.session_state["current_page"] = "Compliance Auditor"
            st.rerun()
        return

    # ── Summary KPIs ───────────────────────────────────────────────────────────
    avg_score = round(
        sum(_f(r, "compliance_score", 0) or 0 for r in reports) / len(reports), 1
    )
    frameworks_used = {
        _f(r, "framework_targeted") or _f(r, "framework") or ""
        for r in reports
    }
    c1, c2, c3, c4 = st.columns(4)
    with c1: render_kpi_card("Total Reports",    str(len(reports)),          "All time",        "neutral", "📋", "blue")
    with c2: render_kpi_card("Avg Score",        f"{avg_score}%",            "Across all",      "neutral", "📊", "green")
    with c3: render_kpi_card("Frameworks",       str(len(frameworks_used)),  "Covered",         "neutral", "🎯", "yellow")
    with c4: render_kpi_card("Critical Findings",str(sum(_f(r, "critical_findings", 0) or 0 for r in reports)), "Total", "neutral", "🚨", "red")

    st.markdown("")
    st.markdown('<div class="section-header">📑 Report History</div>', unsafe_allow_html=True)

    for i, r in enumerate(reversed(reports)):
        score = _f(r, "compliance_score", 0) or 0
        fw    = _f(r, "framework_targeted") or _f(r, "framework") or ""
        ts    = str(_f(r, "generated_timestamp") or _f(r, "created_at") or "")[:19]
        total = _f(r, "total_findings", 0) or 0
        crit  = _f(r, "critical_findings", 0) or 0
        grade = grade_score(score)

        with st.expander(
            f"📋 {fw} Audit — Score: {score:.0f}% ({grade}) — {ts}",
            expanded=(i == 0),
        ):
            c_score, c_fw, c_total, c_crit = st.columns(4)
            with c_score: st.metric("Score",     f"{score:.0f}%")
            with c_fw:    st.metric("Framework", fw)
            with c_total: st.metric("Findings",  total)
            with c_crit:  st.metric("Critical",  crit)

            findings = _f(r, "findings") or _f(r, "findings_json") or []
            if findings:
                st.markdown("**Top Findings:**")
                for f in findings[:3]:
                    sev = _f(f, "severity", "") or ""
                    ref = _f(f, "legal_reference", "") or ""
                    st.markdown(
                        f"- <span class='severity-badge {sev.lower()}'>{sev}</span> {ref}",
                        unsafe_allow_html=True,
                    )

            col_ex, _ = st.columns([1, 4])
            with col_ex:
                if st.button("📥 Export JSON", key=f"export_{i}"):
                    import json
                    try:
                        if isinstance(r, dict):
                            data = r
                        elif hasattr(r, "model_dump"):
                            data = r.model_dump()
                        elif hasattr(r, "dict"):
                            data = r.dict()
                        else:
                            data = {}
                        st.download_button(
                            "💾 Download",
                            data=json.dumps(data, indent=2, default=str),
                            file_name=f"audit_{fw}_{ts[:10]}.json",
                            mime="application/json",
                            key=f"dl_{i}",
                        )
                    except Exception:
                        st.info("Export unavailable.")