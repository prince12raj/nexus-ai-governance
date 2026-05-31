"""
╔══════════════════════════════════════════════════════════════════════════════╗
║        NEXUS AI GOVERNANCE PLATFORM — Enterprise Edition v2.0               ║
║        AI Policy Governance, Compliance & Agentic Risk Intelligence         ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Run:   streamlit run app.py                                                ║
║  Docs:  https://docs.nexus-ai.enterprise                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝

Entry point for the Nexus AI Governance Platform.

Boot sequence:
  1. Streamlit page configuration
  2. Session state initialisation
  3. CSS injection
  4. Config validation warnings
  5. Vector store boot (memory / FAISS / ChromaDB)
  6. Auth gate — redirect to login if not authenticated
  7. Page permission check — block unauthorised page access
  8. Sidebar render
  9. Route to current page renderer
"""

import streamlit as st

from config import (
    APP_NAME, APP_VERSION, APP_ICON,
    validate_config, get_logger,
)

logger = get_logger("nexus.app")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE ROUTER — maps page names → render functions
# ══════════════════════════════════════════════════════════════════════════════

def _build_page_router() -> dict:
    """
    Lazily import and return the page router dict.
    Lazy imports keep startup fast and avoid circular dependency issues.
    """
    from ui.dashboard        import render_dashboard
    from ui.upload_page      import render_policy_upload
    from ui.audit_report     import render_compliance_auditor, render_audit_reports
    from ui.governance_page  import render_agentic_risk
    from ui.knowledge_base   import render_knowledge_base
    from ui.analytics        import render_analytics
    from ui.admin_settings   import render_admin_settings

    return {
        "Dashboard":          render_dashboard,
        "Policy Upload":      render_policy_upload,
        "Compliance Auditor": render_compliance_auditor,
        "Agentic Risk":       render_agentic_risk,
        "Knowledge Base":     render_knowledge_base,
        "Audit Reports":      render_audit_reports,
        "Analytics":          render_analytics,
        "Admin Settings":     render_admin_settings,
    }


# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE INITIALISATION
# ══════════════════════════════════════════════════════════════════════════════

def _init_session_state() -> None:
    """
    Initialise all session_state keys with safe defaults.
    Safe to call multiple times — only sets missing keys.
    """
    from auth.session_manager import init_session_state
    init_session_state()


# ══════════════════════════════════════════════════════════════════════════════
# VECTOR STORE BOOT
# ══════════════════════════════════════════════════════════════════════════════

def _boot_vector_store() -> None:
    """
    Initialise the vector store on first load only.
    Uses st.session_state flag to prevent re-running on every page interaction.
    """
    if st.session_state.get("vector_db_initialized"):
        return  # ← already done this session — skip

    from config.settings import settings

    with st.spinner("⚙️ Initialising knowledge base…"):
        try:
            backend = settings.VECTOR_STORE_BACKEND

            if backend == "faiss":
                from database.faiss_manager import FaissManager
                vs = FaissManager()
            elif backend == "chroma":
                from database.chroma_manager import ChromaManager
                vs = ChromaManager()
            else:
                from database.memory_store import get_memory_store
                vs = get_memory_store()

            # Seed if empty
            if vs.count() == 0:
                from rag.regulations_seed import REGULATIONS_CORPUS
                added = vs.add_documents(REGULATIONS_CORPUS)
                logger.info("Vector store seeded with %d regulations.", added)
            else:
                logger.info(
                    "Vector store loaded | backend=%s | docs=%d | frameworks=%s",
                    backend, vs.count(), vs.frameworks(),
                )

            st.session_state["vector_store"]          = vs
            st.session_state["vector_db_initialized"] = True

        except Exception as exc:
            logger.error("Vector store boot failed: %s", exc)
            # Fall back to in-memory store so the app still runs
            from database.memory_store import get_memory_store
            st.session_state["vector_store"]          = get_memory_store()
            st.session_state["vector_db_initialized"] = True
            st.warning(
                f"⚠️ Vector store init warning: {exc}. "
                "Using in-memory fallback.",
                icon="⚠️",
            )


# ══════════════════════════════════════════════════════════════════════════════
# CONFIG WARNINGS
# ══════════════════════════════════════════════════════════════════════════════

def _show_config_warnings() -> None:
    """
    Display configuration warnings only once per session
    and only to Admin / Developer users — never on the login page.
    """
    # Already shown this session — skip
    if st.session_state.get("_config_warnings_shown"):
        return

    # Don't show on login/register page
    if not st.session_state.get("authenticated"):
        return

    # Only show to Admin or Developer
    role = st.session_state.get("current_user", {}).get("role", "")
    if role not in ("Admin", "Developer"):
        st.session_state["_config_warnings_shown"] = True
        return

    warnings = validate_config()
    if warnings:
        with st.expander("⚙️ Configuration Warnings — click to dismiss", expanded=False):
            for w in warnings:
                st.warning(w, icon="⚠️")
            if st.button("✅ Dismiss", key="dismiss_warnings"):
                st.session_state["_config_warnings_shown"] = True
                st.rerun()
    else:
        st.session_state["_config_warnings_shown"] = True


# ══════════════════════════════════════════════════════════════════════════════
# PAGE PERMISSION CHECK
# ══════════════════════════════════════════════════════════════════════════════

def _check_page_permission(page: str) -> bool:
    """
    Check if the current user has permission to view the requested page.
    Redirects to Dashboard if not allowed.

    Returns:
        True if allowed, False if redirected.
    """
    from auth.session_manager import has_permission, get_user_role

    role = get_user_role()

    # Admin and Developer always have full access
    if role in ("Admin", "Developer"):
        return True

    if not has_permission(page):
        logger.warning(
            "Unauthorised page access | user_role=%s | page=%s",
            role, page,
        )
        st.session_state["current_page"] = "Dashboard"
        st.warning(
            f"🔒 You don't have permission to access **{page}**. "
            f"Redirecting to Dashboard.",
            icon="🔒",
        )
        st.rerun()
        return False

    return True


# ══════════════════════════════════════════════════════════════════════════════
# ERROR BOUNDARY
# ══════════════════════════════════════════════════════════════════════════════

def _render_page_safe(renderer, page_name: str) -> None:
    """
    Render a page with an error boundary.
    Shows a friendly error card instead of crashing the app.
    """
    try:
        renderer()
    except Exception as exc:
        logger.error("Page render error | page=%s | error=%s", page_name, exc, exc_info=True)
        st.markdown(f"""
        <div style="background:rgba(255,71,87,0.08);border:1px solid rgba(255,71,87,0.3);
                    border-radius:12px;padding:2rem;margin:2rem 0;text-align:center;">
          <div style="font-size:2rem;margin-bottom:1rem;">⚠️</div>
          <div style="font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:700;
                      color:#ff4757;margin-bottom:0.5rem;">
            Page Error — {page_name}
          </div>
          <div style="color:#8a9bbc;font-size:0.85rem;margin-bottom:1rem;">
            {str(exc)[:200]}
          </div>
          <div style="font-size:0.78rem;color:#4a5a78;">
            Please check the terminal for the full traceback, or try refreshing the page.
          </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("🔧 Debug details"):
            st.exception(exc)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    """
    Main application entry point.

    Boot sequence:
      1. Streamlit page config
      2. Session state init
      3. CSS injection
      4. Config warnings
      5. Vector store boot
      6. Auth gate
      7. Permission check
      8. Sidebar + page render
    """

    # ── 1. Page configuration ──────────────────────────────────────────────────
    st.set_page_config(
        page_title=f"{APP_NAME} v{APP_VERSION}",
        page_icon=APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "Get Help":     None,
            "Report a bug": None,
            "About": (
                f"**{APP_NAME}** v{APP_VERSION}\n\n"
                "Enterprise AI Policy Governance, Compliance & Risk Intelligence.\n\n"
                "Powered by OpenAI GPT-4o, HuggingFace, and Ollama."
            ),
        },
    )

    # ── 2. Session state ───────────────────────────────────────────────────────
    _init_session_state()

    # ── 3. CSS injection ───────────────────────────────────────────────────────
    from ui.styles import ENTERPRISE_CSS
    st.markdown(ENTERPRISE_CSS, unsafe_allow_html=True)

    # ── 4. Config warnings (once per session) ──────────────────────────────────
    _show_config_warnings()

    # ── 5. Vector store boot ───────────────────────────────────────────────────
    _boot_vector_store()

    # ── 6. Restore session from cookie (handles page refresh) ─────────────────
    from auth.session_manager import restore_session_from_cookie
    restore_session_from_cookie()

    # ── 7. Auth gate ───────────────────────────────────────────────────────────
    from auth.session_manager import is_logged_in
    if not is_logged_in():
        # Route between login and register pages
        auth_page = st.session_state.get("auth_page", "login")

        if auth_page == "register":
            from auth.register import render_register_page
            render_register_page()
        else:
            # Show success message if coming from registration
            if st.session_state.get("_reg_success"):
                st.success(st.session_state.pop("_reg_success"))
            from auth.login import render_login_page
            render_login_page()
        return

    # ── 8. Build router ────────────────────────────────────────────────────────
    PAGE_ROUTER = _build_page_router()

    # ── 9. Page permission check ───────────────────────────────────────────────
    page = st.session_state.get("current_page", "Dashboard")
    if page not in PAGE_ROUTER:
        page = "Dashboard"
        st.session_state["current_page"] = "Dashboard"

    _check_page_permission(page)
    page = st.session_state.get("current_page", "Dashboard")

    # ── 9. Sidebar ─────────────────────────────────────────────────────────────
    from ui.sidebar import render_sidebar
    render_sidebar()

    # ── 10. Render page ────────────────────────────────────────────────────────
    renderer = PAGE_ROUTER.get(page, PAGE_ROUTER["Dashboard"])
    _render_page_safe(renderer, page)


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    main()