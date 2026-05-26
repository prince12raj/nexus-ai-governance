"""
ui/governance_page.py — Agentic Risk Intelligence page for Nexus AI Governance Platform.
"""
from __future__ import annotations

import time

import streamlit as st

from compliance.scoring import risk_level, score_color
from ui.dashboard import render_page_header, render_kpi_card


def render_agentic_risk() -> None:
    from auth.session_manager import get_current_user
    user = get_current_user()
    render_page_header(
        "Agentic Risk Intelligence",
        "Multi-agent AI system risk assessment with EU AI Act and NIST RMF alignment",
        user.get("role", "") if user else "",
    )

    tab_risk, tab_chat, tab_policy = st.tabs([
        "🤖 AI System Risk", "💬 Governance Chat", "📝 Policy Generator"
    ])

    # ── AI System Risk ─────────────────────────────────────────────────────────
    with tab_risk:
        st.markdown("**Describe your AI system to receive a governance risk assessment.**")
        system_name = st.text_input("AI System Name", placeholder="e.g. LoanBot v3, HR Screening Tool")
        system_desc = st.text_area(
            "System Description",
            height=180,
            placeholder=(
                "Describe: purpose, data inputs, decision outputs, affected users, "
                "deployment context, and any known limitations…"
            ),
        )

        if st.button("🤖 Run Risk Assessment", type="primary", use_container_width=True,
                     disabled=not system_desc):
            _run_risk_assessment(system_desc, system_name or "AI System")

    # ── Governance Chat ────────────────────────────────────────────────────────
    with tab_chat:
        _render_governance_chat()

    # ── Policy Generator ───────────────────────────────────────────────────────
    with tab_policy:
        _render_policy_generator()


def _run_risk_assessment(system_desc: str, system_name: str) -> None:
    with st.spinner("Multi-agent risk assessment running…"):
        from agents.risk_scoring_agent import RiskScoringAgent
        agent  = RiskScoringAgent()
        result = agent.assess(system_desc, system_name=system_name)

    score  = result.get("overall_score", 0)
    level  = result.get("risk_level", "Low")
    eu_act = result.get("eu_ai_act", "Minimal Risk")
    risks  = result.get("risks", [])
    recs   = result.get("recommendations", [])
    color  = result.get("risk_color", "#00e5a0")

    # Score banner
    st.markdown(f"""
    <div class="score-banner">
      <div class="score-number" style="color:{color};">{score:.0f}</div>
      <div style="font-family:'Syne',sans-serif;font-size:1.4rem;font-weight:700;color:{color};">{level} Risk</div>
      <div class="score-label">EU AI Act: {eu_act} · {len(risks)} risk area(s) identified</div>
    </div>
    """, unsafe_allow_html=True)

    # KPIs
    nist = result.get("nist_rmf", {})
    c1, c2, c3, c4 = st.columns(4)
    with c1: render_kpi_card("Risk Score", f"{score:.0f}/100", level, "neutral", "⚠️", "red" if score > 50 else "green")
    with c2: render_kpi_card("EU AI Act", eu_act.split()[0], eu_act, "neutral", "🇪🇺", "blue")
    with c3: render_kpi_card("Risk Areas", str(len(risks)), "Identified", "neutral", "🔍", "yellow")
    with c4: render_kpi_card("NIST Functions", str(len(nist)), "Mapped", "neutral", "🗺️", "green")

    # Risk findings
    if risks:
        st.markdown('<div class="section-header">⚠️ Risk Findings</div>', unsafe_allow_html=True)
        for r in risks:
            cat   = r.get("risk_category", "General Risk")
            desc  = r.get("risk_description", "")
            rscore= r.get("risk_score", 0)
            mit   = r.get("mitigation_strategy", "")
            nist_fn = r.get("nist_rmf_function", "")

            st.markdown(f"""
            <div class="governance-card">
              <div style="display:flex;justify-content:space-between;margin-bottom:0.6rem;">
                <strong style="color:#e8edf8;">{cat}</strong>
                <span style="font-size:0.75rem;color:#4a5a78;">
                  Risk Score: {rscore}/25 · NIST: {nist_fn}
                </span>
              </div>
              <div style="font-size:0.84rem;color:#8a9bbc;margin-bottom:0.6rem;">{desc}</div>
              <div style="font-size:0.8rem;color:#00e5a0;">🔧 {mit}</div>
            </div>
            """, unsafe_allow_html=True)

    # Recommendations
    if recs:
        st.markdown('<div class="section-header">💡 Top Recommendations</div>', unsafe_allow_html=True)
        for i, rec in enumerate(recs[:5], 1):
            st.markdown(f"**{i}.** {rec}")


def _render_governance_chat() -> None:
    """Render the governance chat interface."""
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    history = st.session_state["chat_history"]

    # Display history
    for msg in history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input
    if prompt := st.chat_input("Ask about GDPR, HIPAA, ISO 27001, risk governance…"):
        st.session_state["chat_history"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                from agents.governance_agent import GovernanceAgent
                agent  = GovernanceAgent()
                result = agent.run(
                    query=prompt,
                    context={"framework": st.session_state.get("chat_framework", "GDPR")},
                )
                reply = result.get("response", "I couldn't process that request.")

            st.markdown(reply)
            st.session_state["chat_history"].append({"role": "assistant", "content": reply})

            sources = result.get("sources", [])
            if sources:
                with st.expander("📚 Sources", expanded=False):
                    for s in sources[:3]:
                        st.markdown(
                            f"- **{s.get('title', '')}** — {s.get('citation', '')}"
                        )

    if history and st.button("🗑️ Clear Chat", type="secondary"):
        st.session_state["chat_history"] = []
        st.rerun()


def _render_policy_generator() -> None:
    """Render the policy section generator."""
    from config.constants import SUPPORTED_FRAMEWORKS

    col1, col2 = st.columns(2)
    with col1:
        section_title = st.text_input(
            "Policy Section Title",
            placeholder="e.g. Data Retention Policy, Consent Management Policy",
        )
    with col2:
        framework = st.selectbox("Framework", [f for f in SUPPORTED_FRAMEWORKS if f != "Combined Framework Mode"])

    org_context = st.text_area(
        "Organisation Context (optional)",
        placeholder="e.g. Healthcare SaaS company, 200 employees, processes EU patient data…",
        height=80,
    )

    if st.button("✍️ Generate Policy Section", type="primary",
                 use_container_width=True, disabled=not section_title):
        with st.spinner("Drafting compliant policy section…"):
            from agents.policy_analysis_agent import PolicyAnalysisAgent
            agent  = PolicyAnalysisAgent()
            result = agent.generate_section(
                section_title=section_title,
                framework=framework,
                org_context=org_context,
            )

        st.markdown(f"""
        <div class="exec-summary">
          <div class="exec-summary-title">📄 {section_title} — {framework}</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(result["content"])

        st.download_button(
            "💾 Download as .txt",
            data=result["content"],
            file_name=f"{section_title.replace(' ', '_')}_{framework}.txt",
            mime="text/plain",
        )