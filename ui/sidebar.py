"""
ui/sidebar.py — Sidebar navigation and user profile for Nexus AI Governance Platform.
"""
from __future__ import annotations

import streamlit as st

from config.constants import NAV_PAGES


def render_sidebar() -> None:
    """Render the full sidebar with logo, user profile, navigation, and system status."""
    from auth.session_manager import get_current_user, logout

    user = get_current_user()

    with st.sidebar:
        # ── Logo ───────────────────────────────────────────────────────────────
        st.markdown("""
        <div style="padding:1.2rem 1rem 0.8rem;">
          <div style="font-family:'Syne',sans-serif;font-size:1.3rem;font-weight:800;color:#e8edf8;">
            ⚖️ <span style="color:#3b7ff5;">Nexus</span> AI
          </div>
          <div style="font-size:0.7rem;color:#4a5a78;letter-spacing:0.08em;text-transform:uppercase;margin-top:2px;">
            Governance Platform v2.0
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<hr style="margin:0.5rem 0 1rem;">', unsafe_allow_html=True)

        # ── User profile card ──────────────────────────────────────────────────
        if user:
            st.markdown(f"""
            <div class="profile-card">
              <div class="avatar-circle">{user.get('avatar', '?')}</div>
              <div class="profile-name">{user.get('name', 'Unknown')}</div>
              <div class="profile-role">{user.get('role', '')}</div>
              <div class="profile-dept">{user.get('department', '')}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(
            '<div style="margin:0.8rem 0 0.4rem;padding:0 1rem;font-size:0.7rem;'
            'letter-spacing:0.1em;text-transform:uppercase;color:#4a5a78;">Navigation</div>',
            unsafe_allow_html=True,
        )

        # ── Navigation buttons ─────────────────────────────────────────────────
        current = st.session_state.get("current_page", "Dashboard")
        for icon, page in NAV_PAGES:
            is_active = current == page
            if st.button(
                f"{icon}  {page}",
                key=f"nav_{page}",
                width='stretch',
                type="primary" if is_active else "secondary",
            ):
                st.session_state["current_page"] = page
                st.rerun()

        st.markdown('<hr style="margin:1rem 0;">', unsafe_allow_html=True)

        # ── System status ──────────────────────────────────────────────────────
        _render_system_status()

        st.markdown('<hr style="margin:1rem 0;">', unsafe_allow_html=True)

        # ── Logout ─────────────────────────────────────────────────────────────
        if st.button("🚪  Sign Out", width='stretch', type="secondary"):
            logout()
            st.rerun()


def _render_system_status() -> None:
    """Render the system status chips in the sidebar."""
    from config.settings import settings

    # LLM status
    if settings.OPENAI_API_KEY:
        llm_status, llm_label = "online", "LLM: GPT-4o"
    elif settings.HUGGINGFACE_API_KEY:
        llm_status, llm_label = "online", "LLM: HuggingFace"
    else:
        llm_status, llm_label = "warning", "LLM: Mock Mode"

    # Vector store doc count
    vs = st.session_state.get("vector_store")
    vdb_count = vs.count() if vs and hasattr(vs, "count") else 0

    # Active page
    page = st.session_state.get("current_page", "Dashboard")

    st.markdown(f"""
    <div style="padding:0 0.5rem">
      <div style="font-size:0.7rem;letter-spacing:0.1em;text-transform:uppercase;
                  color:#4a5a78;margin-bottom:0.5rem;">System Status</div>
      <div style="display:flex;flex-direction:column;gap:6px">
        <span class="status-chip {llm_status}">● {llm_label}</span>
        <span class="status-chip online">● Vector DB: {vdb_count} docs</span>
        <span class="status-chip online">● Agents: Ready</span>
        <span class="status-chip online">● Page: {page}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)