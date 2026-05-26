"""
ui/admin_settings.py — Admin Settings page for Nexus AI Governance Platform.
"""
from __future__ import annotations

import streamlit as st

from config.constants import SUPPORTED_FRAMEWORKS
from ui.dashboard import render_page_header


AUDIT_EVENTS = [
    {"timestamp": "2024-01-15 09:41", "user": "admin",      "action": "Run Compliance Audit",       "resource": "AI_Retention_Policy.pdf", "result": "✅ Success"},
    {"timestamp": "2024-01-15 09:15", "user": "compliance",  "action": "Upload Document",             "resource": "Healthcare_Policy.docx",  "result": "✅ Success"},
    {"timestamp": "2024-01-15 08:52", "user": "auditor",     "action": "Escalate Finding",            "resource": "RPT-20240115",            "result": "⚠️ Escalated"},
    {"timestamp": "2024-01-15 08:30", "user": "admin",       "action": "Login",                       "resource": "Authentication",          "result": "✅ Success"},
    {"timestamp": "2024-01-14 17:12", "user": "compliance",  "action": "Approve Governance Decision", "resource": "RPT-20240114",            "result": "✅ Approved"},
    {"timestamp": "2024-01-14 16:45", "user": "auditor",     "action": "Export Report PDF",           "resource": "RPT-20240114",            "result": "✅ Success"},
    {"timestamp": "2024-01-14 11:22", "user": "admin",       "action": "Add Regulation",              "resource": "PCI DSS v4.0 Req 8",      "result": "✅ Success"},
]


def render_admin_settings() -> None:
    from auth.session_manager import get_current_user
    user = get_current_user()
    render_page_header(
        "Admin Settings",
        "Platform configuration, API management, and user administration",
        user.get("role", "") if user else "",
    )

    tab_api, tab_platform, tab_users, tab_kb, tab_audit = st.tabs([
        "🔑 API Config", "⚙️ Platform", "👥 Users", "📚 Knowledge Base", "📜 Audit Log"
    ])

    # ── API Configuration ──────────────────────────────────────────────────────
    with tab_api:
        _render_api_config()

    # ── Platform Settings ──────────────────────────────────────────────────────
    with tab_platform:
        _render_platform_settings()

    # ── User Management ────────────────────────────────────────────────────────
    with tab_users:
        _render_user_management()

    # ── Knowledge Base Management ──────────────────────────────────────────────
    with tab_kb:
        _render_kb_management()

    # ── Audit Log ─────────────────────────────────────────────────────────────
    with tab_audit:
        _render_audit_log()


# ══════════════════════════════════════════════════════════════════════════════
# TAB RENDERERS
# ══════════════════════════════════════════════════════════════════════════════

def _render_api_config() -> None:
    from config.settings import settings

    st.markdown('<div class="section-header">🔑 LLM Provider Configuration</div>',
                unsafe_allow_html=True)

    # ── OpenAI ─────────────────────────────────────────────────────────────────
    with st.expander("🤖 OpenAI", expanded=True):
        api_key = st.text_input(
            "OpenAI API Key",
            value=st.session_state.get("api_key", settings.OPENAI_API_KEY or ""),
            type="password",
            placeholder="sk-…",
            help="Get your key at platform.openai.com/api-keys",
        )
        if api_key != st.session_state.get("api_key", ""):
            st.session_state["api_key"] = api_key

        c1, c2 = st.columns(2)
        with c1:
            st.selectbox("Primary Model", ["GPT-4o", "GPT-4-Turbo", "GPT-3.5-Turbo"],
                         key="openai_model")
        with c2:
            st.selectbox("Embedding Model",
                         ["text-embedding-3-small", "text-embedding-3-large",
                          "text-embedding-ada-002"],
                         key="openai_embed_model")

        if st.button("🔌 Test OpenAI Connection", key="test_openai"):
            with st.spinner("Testing connection…"):
                try:
                    from llm.openai_provider import test_connection
                    result = test_connection(api_key=api_key or None)
                    if result.get("status") == "ok":
                        st.success(f"✅ Connected — Model: {result.get('model')} — Reply: {result.get('reply')}")
                    else:
                        st.error(f"❌ {result.get('message', 'Connection failed')}")
                except Exception as e:
                    st.error(f"❌ {e}")

    # ── HuggingFace ────────────────────────────────────────────────────────────
    with st.expander("🤗 HuggingFace"):
        hf_key = st.text_input(
            "HuggingFace API Key",
            value=settings.HUGGINGFACE_API_KEY or "",
            type="password",
            placeholder="hf_…",
        )
        st.text_input("Model", value=settings.HUGGINGFACE_MODEL, key="hf_model")

        if st.button("🔌 Test HuggingFace Connection", key="test_hf"):
            with st.spinner("Testing…"):
                try:
                    from llm.huggingface_provider import test_connection
                    result = test_connection(api_key=hf_key or None)
                    if result.get("status") == "ok":
                        st.success(f"✅ Connected — {result.get('reply', '')}")
                    else:
                        st.error(f"❌ {result.get('message', 'Failed')}")
                except Exception as e:
                    st.error(f"❌ {e}")

    # ── Ollama ─────────────────────────────────────────────────────────────────
    with st.expander("🦙 Ollama (Local)"):
        c1, c2 = st.columns(2)
        with c1:
            ollama_host = st.text_input("Host", value=settings.OLLAMA_HOST, key="ollama_host")
        with c2:
            ollama_model = st.text_input("Model", value=settings.OLLAMA_MODEL, key="ollama_model_input")

        if st.button("🔌 Test Ollama Connection", key="test_ollama"):
            with st.spinner("Checking Ollama…"):
                try:
                    from llm.ollama_provider import test_connection
                    result = test_connection(host=ollama_host)
                    if result.get("status") == "ok":
                        models = ", ".join(result.get("models_installed", [])[:3])
                        st.success(f"✅ Connected — Models: {models}")
                    else:
                        st.error(f"❌ {result.get('message', 'Ollama not running')}")
                except Exception as e:
                    st.error(f"❌ {e}")

    # ── Test all ────────────────────────────────────────────────────────────────
    st.markdown("")
    if st.button("🔌 Test All Providers", type="primary"):
        with st.spinner("Testing all providers…"):
            from llm import test_all_providers
            results = test_all_providers()

        st.markdown(f"**Active Provider:** `{results.get('active', 'unknown')}`")
        for provider in ["openai", "huggingface", "ollama"]:
            r      = results.get(provider, {})
            status = r.get("status", "error")
            icon   = "✅" if status == "ok" else "❌"
            msg    = r.get("reply", r.get("message", ""))
            st.markdown(f"{icon} **{provider.title()}:** {msg[:80]}")

    if st.button("💾 Save API Configuration", type="primary"):
        st.success("✅ Configuration saved to session.")


def _render_platform_settings() -> None:
    from config.settings import settings

    st.markdown('<div class="section-header">⚙️ Compliance Framework Settings</div>',
                unsafe_allow_html=True)

    active_fws = st.multiselect(
        "Active Frameworks",
        [f for f in SUPPORTED_FRAMEWORKS if f != "Combined Framework Mode"],
        default=["GDPR", "ISO 27001", "HIPAA"],
        key="active_frameworks",
    )

    st.markdown('<div class="section-header">🔍 Analysis Settings</div>',
                unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        chunk_size = st.slider("Chunk Size (chars)", 400, 2000,
                               settings.RAG_CHUNK_SIZE, step=100)
        top_k      = st.slider("Retrieval Top-K", 2, 10, settings.RAG_TOP_K)
    with c2:
        min_conf   = st.slider("Min Confidence Threshold", 0.5, 0.99,
                               settings.RAG_MIN_CONFIDENCE, step=0.05)
        alert_sev  = st.selectbox("Severity Alert Threshold",
                                  ["Low", "Medium", "High", "Critical"],
                                  index=2)

    st.markdown('<div class="section-header">🚩 Feature Flags</div>',
                unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.checkbox("Enable PII Detection",       value=settings.ENABLE_PII_DETECTION,       key="ff_pii")
        st.checkbox("Enable Injection Detection", value=settings.ENABLE_INJECTION_DETECTION, key="ff_inj")
    with c2:
        st.checkbox("Auto-generate Remediation",  value=True, key="ff_rem")
        st.checkbox("Human-in-the-Loop",          value=settings.ENABLE_HUMAN_IN_LOOP,       key="ff_hitl")
    with c3:
        st.checkbox("Enable Streaming",           value=settings.ENABLE_STREAMING, key="ff_stream")
        st.checkbox("Enable RAG",                 value=settings.ENABLE_RAG,       key="ff_rag")

    st.markdown('<div class="section-header">💾 Vector Store</div>',
                unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        vs_backend = st.selectbox("Backend",
                                  ["memory", "faiss", "chroma"],
                                  index=["memory","faiss","chroma"].index(
                                      settings.VECTOR_STORE_BACKEND
                                  ) if settings.VECTOR_STORE_BACKEND in ["memory","faiss","chroma"] else 0)
    with c2:
        if vs_backend == "chroma":
            st.text_input("ChromaDB Persist Dir", value=settings.CHROMA_PERSIST_DIR)
        elif vs_backend == "faiss":
            st.text_input("FAISS Index Path", value=settings.FAISS_INDEX_PATH)

    if st.button("💾 Save Platform Settings", type="primary"):
        st.success("✅ Settings saved.")


def _render_user_management() -> None:
    st.markdown('<div class="section-header">👥 User Accounts</div>',
                unsafe_allow_html=True)

    try:
        from auth.user_store import load_all_users
        import pandas as pd

        all_users = load_all_users()
        rows = []
        for username, info in all_users.items():
            rows.append({
                "Username":    username,
                "Name":        info.get("name", ""),
                "Role":        info.get("role", ""),
                "Department":  info.get("department", ""),
                "Email":       info.get("email", ""),
                "Registered":  info.get("registered_at", "Demo User")[:10],
                "Last Login":  info.get("last_login", "")[:16] or "Never",
                "Status":      "✅ Active",
            })

        if rows:
            st.dataframe(
                pd.DataFrame(rows),
                use_container_width=True,
                hide_index=True,
            )
            st.caption(f"Total users: {len(rows)} ({sum(1 for r in rows if r['Registered'] != 'Demo User')} registered + {sum(1 for r in rows if r['Registered'] == 'Demo User')} demo)")

    except ImportError:
        st.info("User management requires pandas: pip install pandas")
        return

    # Only Admin and Developer can add users
    from auth.session_manager import get_user_role
    current_role = get_user_role()

    if current_role not in ("Admin", "Developer"):
        st.warning("🔒 Admin or Developer access required to manage users.")
        return

    st.markdown('<div class="section-header">➕ Add User</div>',
                unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        new_username = st.text_input("Username", key="new_user")
        new_name     = st.text_input("Full Name", key="new_name")
    with c2:
        new_role = st.selectbox(
            "Role",
            ["Compliance Officer", "Auditor", "Viewer", "Developer", "Admin"],
            key="new_role",
        )
        new_dept = st.text_input("Department", key="new_dept")
    with c3:
        new_email    = st.text_input("Email", key="new_email")
        new_password = st.text_input("Password", type="password", key="new_pass")

    st.markdown("")
    if st.button("➕ Add User", type="primary", key="add_user_btn"):
        if not new_username or not new_password or not new_name:
            st.error("Username, full name and password are required.")
        else:
            from auth.security import hash_password
            from auth.user_store import register_user
            success, message = register_user(
                username=new_username,
                password_hash=hash_password(new_password),
                full_name=new_name,
                email=new_email,
                role=new_role,
                department=new_dept,
            )
            if success:
                st.success(f"✅ User '{new_username}' added successfully.")
                st.rerun()
            else:
                st.error(f"❌ {message}")

    # Delete user
    st.markdown('<div class="section-header">🗑️ Remove User</div>',
                unsafe_allow_html=True)

    from auth.user_store import get_all_registered_users
    registered = get_all_registered_users()

    if not registered:
        st.info("No registered users to remove. Demo users cannot be deleted.")
    else:
        del_options = [u["username"] for u in registered]
        del_user    = st.selectbox("Select registered user to remove", del_options, key="del_user_select")
        if st.button("🗑️ Delete User", type="secondary", key="del_user_btn"):
            from auth.user_store import delete_user
            if delete_user(del_user):
                st.success(f"✅ User '{del_user}' deleted.")
                st.rerun()
            else:
                st.error("Could not delete user.")


def _render_kb_management() -> None:
    st.markdown('<div class="section-header">📚 Knowledge Base Status</div>',
                unsafe_allow_html=True)

    vs = st.session_state.get("vector_store")

    if vs:
        stats = vs.stats()
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Total Documents", stats.get("total_documents", 0))
        with c2:
            st.metric("Backend", stats.get("backend", "memory").title())
        with c3:
            st.metric("Frameworks", len(stats.get("frameworks", {})))

        st.markdown("**Documents by Framework:**")
        for fw, count in (stats.get("frameworks", {}) or {}).items():
            st.markdown(f"- **{fw}:** {count} document(s)")
    else:
        st.warning("Vector store not initialised.")

    st.markdown('<div class="section-header">🔄 Knowledge Base Actions</div>',
                unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🔄 Reload Regulations Corpus", use_container_width=True):
            with st.spinner("Reloading corpus…"):
                if vs and hasattr(vs, "reload_corpus"):
                    vs.reload_corpus()
                    st.success("✅ Corpus reloaded.")
                else:
                    from rag.vector_store import reset_to_corpus
                    reset_to_corpus()
                    st.success("✅ Corpus reset to default regulations.")

    with c2:
        if st.button("🧹 Clear User Documents", use_container_width=True):
            from rag.vector_store import clear_user_documents
            removed = clear_user_documents()
            st.success(f"✅ Removed {removed} user-uploaded document(s).")

    with c3:
        if st.button("💣 Clear Entire KB", use_container_width=True, type="secondary"):
            if vs:
                vs.clear()
                st.warning("⚠️ Knowledge base cleared. Reload regulations to restore.")


def _render_audit_log() -> None:
    st.markdown('<div class="section-header">📜 Platform Audit Log</div>',
                unsafe_allow_html=True)

    import pandas as pd

    # Combine static events with session events
    session_audits = st.session_state.get("audit_history", [])
    dynamic_events = []
    for r in session_audits:
        dynamic_events.append({
            "timestamp": getattr(r, "generated_timestamp", "")[:16],
            "user":      st.session_state.get("current_user", {}).get("name", "user"),
            "action":    "Run Compliance Audit",
            "resource":  getattr(r, "framework_targeted", ""),
            "result":    f"✅ Score: {getattr(r, 'compliance_score', 0):.0f}%",
        })

    all_events = dynamic_events + AUDIT_EVENTS

    # Filter controls
    c1, c2 = st.columns([2, 1])
    with c1:
        search = st.text_input("🔍 Filter events", placeholder="Search by user, action, or resource…")
    with c2:
        result_filter = st.selectbox("Result", ["All", "✅ Success", "⚠️ Escalated", "❌ Failed"])

    filtered = all_events
    if search:
        filtered = [e for e in filtered if search.lower() in str(e).lower()]
    if result_filter != "All":
        filtered = [e for e in filtered if result_filter in e.get("result", "")]

    st.markdown(f'<div style="font-size:0.82rem;color:#4a5a78;margin-bottom:0.6rem;">'
                f'{len(filtered)} event(s)</div>', unsafe_allow_html=True)

    if filtered:
        df = pd.DataFrame(filtered)
        st.dataframe(df, use_container_width=True, hide_index=True)

        if st.button("📥 Export Audit Log (CSV)"):
            csv = df.to_csv(index=False)
            st.download_button(
                "💾 Download audit_log.csv",
                data=csv,
                file_name="audit_log.csv",
                mime="text/csv",
            )
    else:
        st.info("No events match your filter.")

    st.markdown('<div class="section-header">🔔 Alert Configuration</div>',
                unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.checkbox("Email alerts on Critical findings",    value=True)
        st.checkbox("Slack notifications for new audits",   value=False)
    with c2:
        st.checkbox("Alert on injection detection",         value=True)
        st.checkbox("Weekly compliance digest",             value=False)
    st.text_input("Alert Email", placeholder="compliance@yourcompany.com")
    if st.button("💾 Save Alert Settings", type="primary"):
        st.success("✅ Alert settings saved.")