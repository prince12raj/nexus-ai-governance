"""
ui/knowledge_base.py — Regulatory Knowledge Base browser for Nexus AI Governance Platform.
"""
from __future__ import annotations

import streamlit as st

from config.constants import SUPPORTED_FRAMEWORKS
from ui.dashboard import render_page_header


def render_knowledge_base() -> None:
    from auth.session_manager import get_current_user
    user = get_current_user()
    render_page_header(
        "Knowledge Base",
        "Browse and search the regulatory corpus: GDPR, ISO 27001, HIPAA, SOC 2, PCI-DSS",
        user.get("role", "") if user else "",
    )

    # ── Stats bar ──────────────────────────────────────────────────────────────
    from rag.regulations_seed import get_corpus_stats
    stats = get_corpus_stats()
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total Regulations", stats["total"])
    with c2:
        st.metric("Frameworks Covered", len(stats["frameworks"]))
    with c3:
        critical_count = stats.get("by_severity", {}).get("Critical", 0)
        st.metric("Critical Requirements", critical_count)

    st.markdown("")

    # ── Search + filter ────────────────────────────────────────────────────────
    col_s, col_fw, col_sev = st.columns([2, 1, 1])
    with col_s:
        query = st.text_input(
            "🔍 Search regulations",
            placeholder="e.g. data retention, encryption, consent, breach notification…",
        )
    with col_fw:
        fw_options = ["All"] + [f for f in SUPPORTED_FRAMEWORKS if f != "Combined Framework Mode"]
        fw_filter  = st.selectbox("Framework", fw_options)
    with col_sev:
        sev_filter = st.selectbox("Severity", ["All", "Critical", "High", "Medium", "Low"])

    # ── Retrieve results ───────────────────────────────────────────────────────
    results = _get_regulations(query, fw_filter, sev_filter)

    st.markdown(
        f'<div style="font-size:0.82rem;color:#4a5a78;margin-bottom:0.8rem;">'
        f'{len(results)} regulation(s) found</div>',
        unsafe_allow_html=True,
    )

    if not results:
        st.info("No regulations found matching your search criteria.")
        return

    # ── Regulation cards ───────────────────────────────────────────────────────
    sev_colors = {
        "Critical": "#ff4757", "High": "#ffc847",
        "Medium": "#3b7ff5", "Low": "#00e5a0",
    }

    for reg in results:
        sev   = reg.get("severity", "Medium")
        color = sev_colors.get(sev, "#3b7ff5")
        tags  = " ".join(
            f'<span style="background:rgba(59,127,245,0.1);color:#3b7ff5;'
            f'font-size:0.68rem;padding:2px 7px;border-radius:10px;margin-right:4px;">{t}</span>'
            for t in reg.get("tags", [])[:5]
        )

        with st.expander(f"📜 {reg['title']}", expanded=False):
            st.markdown(f"""
            <div class="reg-card">
              <div style="display:flex;justify-content:space-between;
                          align-items:center;margin-bottom:0.6rem;">
                <div class="reg-citation">{reg.get('citation', '')}</div>
                <span class="severity-badge {sev.lower()}">{sev}</span>
              </div>
              <div style="font-size:0.75rem;color:#4a5a78;margin-bottom:0.5rem;">
                Framework: <strong style="color:#3b7ff5;">{reg.get('framework', '')}</strong>
              </div>
              <div class="reg-text">{reg.get('text', '')}</div>
              <div style="margin-top:0.8rem;">{tags}</div>
            </div>
            """, unsafe_allow_html=True)

            remediation = reg.get("remediation", [])
            if remediation:
                st.markdown("**🔧 Remediation Guidance:**")
                for step in remediation:
                    st.markdown(f"- {step}")

            # Ask AI about this regulation
            if st.button(f"💬 Ask AI about this", key=f"ask_{reg.get('id', '')}"):
                with st.spinner("Generating explanation…"):
                    from llm.router import route
                    answer = route(
                        task="regulatory_qa",
                        payload={
                            "question": f"Explain {reg.get('title', '')} and its practical implications for businesses.",
                            "context_docs": [reg],
                        },
                    )
                st.markdown(f"""
                <div class="exec-summary">
                  <div class="exec-summary-title">💡 AI Explanation</div>
                  <div class="exec-summary-text">{answer}</div>
                </div>
                """, unsafe_allow_html=True)

    # ── Add custom regulation ──────────────────────────────────────────────────
    with st.expander("➕ Add Custom Regulation to Knowledge Base"):
        _render_add_regulation_form()


def _get_regulations(query: str, fw_filter: str, sev_filter: str) -> list:
    """Retrieve regulations based on search criteria."""
    from rag.regulations_seed import REGULATIONS_CORPUS

    # Try vector store search if query provided
    if query:
        vs = st.session_state.get("vector_store")
        if vs:
            filt    = None if fw_filter == "All" else fw_filter
            results = vs.similarity_search(query, k=8, framework_filter=filt)
        else:
            results = [r for r in REGULATIONS_CORPUS
                       if query.lower() in r.get("text", "").lower()
                       or query.lower() in r.get("title", "").lower()]
    else:
        results = list(REGULATIONS_CORPUS)

    # Apply filters
    if fw_filter != "All":
        results = [r for r in results if r.get("framework") == fw_filter]
    if sev_filter != "All":
        results = [r for r in results if r.get("severity") == sev_filter]

    return results


def _render_add_regulation_form() -> None:
    """Form to add a custom regulation to the knowledge base."""
    from config.constants import SUPPORTED_FRAMEWORKS

    c1, c2 = st.columns(2)
    with c1:
        new_title    = st.text_input("Title", key="new_reg_title")
        new_framework= st.selectbox("Framework", [f for f in SUPPORTED_FRAMEWORKS if f != "Combined Framework Mode"], key="new_reg_fw")
    with c2:
        new_citation = st.text_input("Citation / Reference", key="new_reg_citation")
        new_severity = st.selectbox("Severity", ["Critical", "High", "Medium", "Low"], key="new_reg_sev")

    new_text = st.text_area("Regulation Text", height=100, key="new_reg_text")

    if st.button("➕ Add to Knowledge Base", type="primary",
                 disabled=not (new_title and new_text)):
        import uuid
        new_doc = {
            "id":        f"custom-{uuid.uuid4().hex[:8]}",
            "title":     new_title,
            "framework": new_framework,
            "citation":  new_citation,
            "severity":  new_severity,
            "text":      new_text,
            "tags":      ["custom"],
        }
        vs = st.session_state.get("vector_store")
        if vs:
            vs.add_document(new_doc)
            st.success(f"✅ '{new_title}' added to the knowledge base.")
        else:
            st.warning("Vector store not initialised. Please restart the app.")