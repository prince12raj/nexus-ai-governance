"""
ui/upload_page.py — Policy document upload page for Nexus AI Governance Platform.

Saves uploaded documents to:
  1. session_state  — for immediate use in current audit
  2. Supabase DB    — persists across restarts (per user)
  3. Vector store   — for RAG retrieval
"""
from __future__ import annotations

import uuid

import streamlit as st

from compliance.pii_detector import detect_pii
from compliance.injection_detector import detect_prompt_injection, injection_risk_score
from ui.dashboard import render_page_header


def render_policy_upload() -> None:
    from auth.session_manager import get_current_user
    user     = get_current_user()
    username = st.session_state.get("username", "")

    render_page_header(
        "Policy Upload",
        "Upload AI policy documents for compliance analysis",
        user.get("role", "") if user else "",
    )

    tab_upload, tab_paste, tab_list = st.tabs([
        "📁 File Upload", "📝 Paste Text", "📂 My Documents"
    ])

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
                if text:
                    _store_document(name=f.name, text=text, username=username)
                    _show_doc_summary(f.name, text)
                else:
                    st.warning(f"⚠️ Could not extract text from {f.name}")

    # ── Paste text ─────────────────────────────────────────────────────────────
    with tab_paste:
        doc_name  = st.text_input("Document name", placeholder="Privacy_Policy_v2.txt",
                                  key="paste_doc_name")
        framework = st.selectbox("Framework",
                                 ["GDPR", "HIPAA", "ISO 27001", "SOC 2", "PCI-DSS"],
                                 key="paste_framework")
        pasted    = st.text_area(
            "Paste policy text here", height=280,
            placeholder="Paste your AI policy, terms, privacy notice, or compliance document…",
            key="paste_text_area",
        )
        if st.button("📥 Ingest Text", type="primary",
                     disabled=not pasted, key="ingest_btn"):
            name = doc_name.strip() or "Pasted_Document.txt"
            _store_document(name=name, text=pasted,
                            username=username, framework=framework)
            _show_doc_summary(name, pasted)
            st.success(f"✅ '{name}' ingested and saved to database.")

    # ── My Documents ───────────────────────────────────────────────────────────
    with tab_list:
        _render_documents_tab(username)


# ══════════════════════════════════════════════════════════════════════════════
# CORE: STORE DOCUMENT
# ══════════════════════════════════════════════════════════════════════════════

def _store_document(
    name: str,
    text: str,
    username: str = "",
    framework: str = "GDPR",
) -> None:
    """
    Save document to session_state + Supabase DB + vector store.
    """
    doc_id = f"doc-{uuid.uuid4().hex[:12]}"

    pii = detect_pii(text)
    inj = injection_risk_score(text)

    doc = {
        "id":             doc_id,
        "name":           name,
        "text":           text,
        "framework":      framework,
        "length":         len(text),
        "pii_detected":   pii,
        "injection_risk": inj,
    }

    # 1. Session state
    docs = st.session_state.setdefault("uploaded_docs", [])
    docs = [d for d in docs if d.get("name") != name]   # remove duplicate
    docs.append(doc)
    st.session_state["uploaded_docs"] = docs

    # 2. Supabase DB — persists across sessions
    if username:
        try:
            from auth.db_session import save_document_to_db
            save_document_to_db(username, doc)
        except Exception as exc:
            import logging
            logging.getLogger("nexus").warning(
                "Failed to save document to DB: %s", exc
            )

    # 3. Vector store for RAG
    vs = st.session_state.get("vector_store")
    if vs:
        try:
            from rag.chunking import chunk_with_metadata
            chunks = chunk_with_metadata(text, source=name, framework=framework)
            vs.add_documents(chunks)
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# MY DOCUMENTS TAB
# ══════════════════════════════════════════════════════════════════════════════

def _render_documents_tab(username: str) -> None:
    """Show all documents for this user — merged from DB + current session."""

    # Load from DB
    db_docs: list = []
    if username:
        try:
            from auth.db_session import load_user_documents
            db_docs = load_user_documents(username)
        except Exception:
            pass

    # Merge: session docs take priority (they have full text)
    session_docs = list(st.session_state.get("uploaded_docs", []))
    session_names = {d.get("name") for d in session_docs}

    for db_doc in db_docs:
        if db_doc.get("name") not in session_names:
            session_docs.append({
                "id":             db_doc.get("doc_id", ""),
                "name":           db_doc.get("name", ""),
                "text":           "",
                "length":         db_doc.get("char_count", 0),
                "framework":      db_doc.get("framework", "GDPR"),
                "pii_detected":   db_doc.get("pii_detected", {}),
                "injection_risk": db_doc.get("injection_risk", 0),
                "uploaded_at":    str(db_doc.get("uploaded_at", ""))[:16],
            })

    if not session_docs:
        st.info(
            "📄 No documents uploaded yet. "
            "Use **File Upload** or **Paste Text** to add documents.",
            icon="ℹ️",
        )
        return

    st.markdown(
        f'<div style="font-size:0.82rem;color:#4a5a78;margin-bottom:0.8rem;">'
        f'{len(session_docs)} document(s) stored for your account</div>',
        unsafe_allow_html=True,
    )

    for doc in reversed(session_docs):
        _render_doc_row(doc)


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _extract_text(file) -> str:
    """Extract text from an uploaded file object."""
    try:
        from ingestion.parser import extract_text as _parse
        return _parse(file)
    except ImportError:
        pass
    content = file.read()
    if isinstance(content, bytes):
        try:
            return content.decode("utf-8", errors="ignore")
        except Exception:
            return content.decode("latin-1", errors="ignore")
    return str(content)


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
      <div style="margin-top:0.3rem;font-size:0.75rem;color:#00e5a0;">
        💾 Saved to database
      </div>
    </div>
    """, unsafe_allow_html=True)


def _render_doc_row(doc: dict) -> None:
    """Render a single document row."""
    text        = doc.get("text", "")
    name        = doc.get("name", "Unknown")
    length      = doc.get("length") or doc.get("char_count") or len(text)
    uploaded_at = doc.get("uploaded_at", "")

    pii = doc.get("pii_detected") or (detect_pii(text) if text else {})
    inj = doc.get("injection_risk") or (
        len(detect_prompt_injection(text)) > 0 if text else False
    )

    col_name, col_chars, col_fw, col_pii, col_inj, col_date, col_del = st.columns(
        [2.5, 0.8, 0.9, 1, 1, 1.2, 0.5]
    )
    with col_name:
        st.markdown(f"**{name}**")
    with col_chars:
        st.caption(f"{length:,} chars" if length else "—")
    with col_fw:
        st.caption(doc.get("framework", "—"))
    with col_pii:
        if pii:
            st.markdown(
                f"<span style='color:#ff4757;font-size:0.78rem;'>⚠️ {len(pii)} PII</span>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<span style='color:#00e5a0;font-size:0.78rem;'>✅ Clean</span>",
                unsafe_allow_html=True,
            )
    with col_inj:
        if inj:
            st.markdown(
                "<span style='color:#9b59ff;font-size:0.78rem;'>⚠️ Risk</span>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<span style='color:#00e5a0;font-size:0.78rem;'>✅ Safe</span>",
                unsafe_allow_html=True,
            )
    with col_date:
        st.caption(uploaded_at[:10] if uploaded_at else "This session")
    with col_del:
        if st.button("🗑️", key=f"del_{name}_{id(doc)}",
                     help=f"Remove {name}"):
            st.session_state["uploaded_docs"] = [
                d for d in st.session_state.get("uploaded_docs", [])
                if d.get("name") != name
            ]
            st.rerun()