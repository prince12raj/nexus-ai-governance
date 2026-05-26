"""
ui/upload_page.py — Policy document upload page for Nexus AI Governance Platform.
"""
from __future__ import annotations

import streamlit as st

from compliance.pii_detector import detect_pii
from compliance.injection_detector import detect_prompt_injection, injection_risk_score
from ui.dashboard import render_page_header


def render_policy_upload() -> None:
    from auth.session_manager import get_current_user
    user = get_current_user()
    render_page_header(
        "Policy Upload",
        "Upload AI policy documents for compliance analysis",
        user.get("role", "") if user else "",
    )

    tab_upload, tab_paste = st.tabs(["📁 File Upload", "📝 Paste Text"])

    # ── File upload ────────────────────────────────────────────────────────────
    with tab_upload:
        st.markdown("**Supported formats:** PDF, DOCX, TXT, CSV, JSON — max 50MB each")
        uploaded = st.file_uploader(
            "Drop policy documents here",
            type=["pdf", "docx", "txt", "csv", "json"],
            accept_multiple_files=True,
            label_visibility="collapsed",
        )
        if uploaded:
            for f in uploaded:
                with st.spinner(f"Processing {f.name}…"):
                    text = _extract_text(f)
                _store_document(f.name, text)
                _show_doc_summary(f.name, text)

    # ── Paste text ─────────────────────────────────────────────────────────────
    with tab_paste:
        doc_name = st.text_input("Document name", placeholder="Privacy_Policy_v2.txt")
        pasted   = st.text_area(
            "Paste policy text here",
            height=280,
            placeholder="Paste your AI policy, terms, privacy notice, or compliance document…",
        )
        if st.button("📥 Ingest Text", type="primary", disabled=not pasted):
            name = doc_name.strip() or "Pasted_Document.txt"
            _store_document(name, pasted)
            _show_doc_summary(name, pasted)
            st.success(f"✅ '{name}' ingested successfully.")

    # ── Ingested documents list ────────────────────────────────────────────────
    docs = st.session_state.get("uploaded_docs", [])
    if docs:
        st.markdown('<div class="section-header">📂 Ingested Documents</div>',
                    unsafe_allow_html=True)
        for doc in reversed(docs):
            _render_doc_row(doc)


def _extract_text(file) -> str:
    """Extract text from an uploaded file object."""
    try:
        # Try to import parser if available
        from ingestion.parser import extract_text as _parse
        return _parse(file)
    except ImportError:
        pass

    # Fallback: read bytes and decode
    content = file.read()
    if isinstance(content, bytes):
        try:
            return content.decode("utf-8", errors="ignore")
        except Exception:
            return content.decode("latin-1", errors="ignore")
    return str(content)


def _store_document(name: str, text: str) -> None:
    """Store a document in session state."""
    docs = st.session_state.setdefault("uploaded_docs", [])
    # Remove existing doc with same name
    docs = [d for d in docs if d["name"] != name]
    docs.append({"name": name, "text": text, "length": len(text)})
    st.session_state["uploaded_docs"] = docs

    # Also ingest into vector store if available
    vs = st.session_state.get("vector_store")
    if vs:
        try:
            from rag.chunking import chunk_with_metadata
            chunks = chunk_with_metadata(text, source=name, framework="GDPR")
            vs.add_documents(chunks)
        except Exception:
            pass


def _show_doc_summary(name: str, text: str) -> None:
    """Show a brief summary card after upload."""
    pii = detect_pii(text)
    inj = injection_risk_score(text)

    pii_html = (
        f'<span style="color:#ff4757;">⚠️ PII: {len(pii)} type(s)</span>'
        if pii else
        '<span style="color:#00e5a0;">✅ No PII detected</span>'
    )
    inj_html = (
        f'<span style="color:#9b59ff;">⚠️ Injection risk: {inj:.0%}</span>'
        if inj > 0.3 else
        '<span style="color:#00e5a0;">✅ Safe</span>'
    )

    st.markdown(f"""
    <div class="reg-card" style="margin-top:0.5rem;">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <div style="font-weight:700;color:#e8edf8;">📄 {name}</div>
        <div style="font-size:0.78rem;color:#4a5a78;">{len(text):,} characters</div>
      </div>
      <div style="margin-top:0.5rem;display:flex;gap:1.5rem;font-size:0.82rem;">
        {pii_html} &nbsp; {inj_html}
      </div>
    </div>
    """, unsafe_allow_html=True)


def _render_doc_row(doc: dict) -> None:
    """Render a single document row in the ingested docs list."""
    pii = detect_pii(doc["text"])
    inj = detect_prompt_injection(doc["text"])

    col_name, col_chars, col_pii, col_inj, col_del = st.columns([3, 1, 1.2, 1.2, 0.6])
    with col_name:
        st.markdown(f"**{doc['name']}**")
    with col_chars:
        st.caption(f"{doc['length']:,} chars")
    with col_pii:
        if pii:
            st.markdown(
                f"<span style='color:#ff4757;font-size:0.8rem;'>⚠️ {len(pii)} PII type(s)</span>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<span style='color:#00e5a0;font-size:0.8rem;'>✅ No PII</span>",
                unsafe_allow_html=True,
            )
    with col_inj:
        if inj:
            st.markdown(
                "<span style='color:#9b59ff;font-size:0.8rem;'>⚠️ Injection risk</span>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<span style='color:#00e5a0;font-size:0.8rem;'>✅ Safe</span>",
                unsafe_allow_html=True,
            )
    with col_del:
        if st.button("🗑️", key=f"del_{doc['name']}", help=f"Remove {doc['name']}"):
            docs = st.session_state.get("uploaded_docs", [])
            st.session_state["uploaded_docs"] = [d for d in docs if d["name"] != doc["name"]]
            st.rerun()