"""
auth/login.py — Login page for Nexus AI Governance Platform.
"""
from __future__ import annotations

import time

import streamlit as st

from auth.session_manager import login
from config.logging_config import get_logger

logger = get_logger("nexus.security.login")

MAX_ATTEMPTS = 5
LOCKOUT_SECS = 30


def render_login_page() -> None:
    """Render the full-screen login page."""
    st.markdown('<div style="min-height:10vh;"></div>', unsafe_allow_html=True)

    col_l, col_c, col_r = st.columns([1, 1.5, 1])
    with col_c:
        _render_logo()
        _render_form()
        _render_register_link()
        _render_footer()


# ── Logo ───────────────────────────────────────────────────────────────────────

def _render_logo() -> None:
    st.markdown("""
    <div style="text-align:center;margin-bottom:2rem;">
      <div style="font-family:'Syne',sans-serif;font-size:2.2rem;
                  font-weight:800;color:#e8edf8;letter-spacing:-0.02em;">
        ⚖️ <span style="color:#3b7ff5;">Nexus</span> AI
      </div>
      <div style="font-size:0.8rem;color:#4a5a78;letter-spacing:0.1em;
                  text-transform:uppercase;margin-top:4px;">
        Enterprise AI Governance Platform
      </div>
    </div>
    """, unsafe_allow_html=True)


# ── Login form ─────────────────────────────────────────────────────────────────

def _render_form() -> None:
    """Render the login form with lockout protection."""

    # Lockout check
    if _is_locked_out():
        remaining = _lockout_remaining()
        st.markdown(f"""
        <div style="background:rgba(255,71,87,0.1);border:1px solid rgba(255,71,87,0.3);
                    border-radius:12px;padding:1.2rem;text-align:center;margin-bottom:1rem;">
          <div style="color:#ff4757;font-weight:700;margin-bottom:0.3rem;">
            🔒 Account Temporarily Locked
          </div>
          <div style="color:#8a9bbc;font-size:0.85rem;">
            Too many failed attempts. Try again in {remaining}s.
          </div>
        </div>
        """, unsafe_allow_html=True)
        time.sleep(1)
        st.rerun()
        return

    st.markdown('<div class="login-container">', unsafe_allow_html=True)

    with st.form("login_form", clear_on_submit=False):
        st.markdown(
            '<div style="text-align:center;margin-bottom:1.5rem;">'
            '<div style="font-family:\'Syne\',sans-serif;font-size:1.1rem;'
            'font-weight:700;color:#e8edf8;">Sign in to your account</div>'
            '</div>',
            unsafe_allow_html=True,
        )

        username = st.text_input(
            "Username",
            placeholder="Enter your username",
            autocomplete="username",
        )
        password = st.text_input(
            "Password",
            type="password",
            placeholder="••••••••",
            autocomplete="current-password",
        )

        # Failed attempts warning
        attempts = st.session_state.get("login_attempts", 0)
        if attempts > 0:
            remaining_attempts = MAX_ATTEMPTS - attempts
            st.markdown(
                f'<div style="color:#ffc847;font-size:0.78rem;margin-top:-0.5rem;">'
                f'⚠️ {attempts} failed attempt(s). {remaining_attempts} remaining before lockout.'
                f'</div>',
                unsafe_allow_html=True,
            )

        submitted = st.form_submit_button(
            "Sign In →",
            type="primary",
            width='stretch',
        )

    st.markdown("</div>", unsafe_allow_html=True)

    if submitted:
        _handle_login(username.strip(), password)


def _handle_login(username: str, password: str) -> None:
    """Validate credentials and handle login outcome."""
    if not username or not password:
        st.error("Please enter both username and password.")
        return

    with st.spinner("Authenticating…"):
        success = login(username, password)

    if success:
        st.session_state["login_attempts"] = 0
        st.session_state["lockout_until"]  = 0
        st.success("✅ Authenticated — loading platform…")
        logger.info("Successful login: user=%s", username)
        time.sleep(0.5)
        st.rerun()
    else:
        attempts = st.session_state.get("login_attempts", 0) + 1
        st.session_state["login_attempts"] = attempts
        logger.warning("Failed login attempt %d: user=%s", attempts, username)

        if attempts >= MAX_ATTEMPTS:
            st.session_state["lockout_until"] = time.time() + LOCKOUT_SECS
            st.error(
                f"🔒 Account locked for {LOCKOUT_SECS} seconds after "
                f"{MAX_ATTEMPTS} failed attempts."
            )
        else:
            remaining = MAX_ATTEMPTS - attempts
            st.error(
                f"❌ Invalid username or password. "
                f"{remaining} attempt(s) remaining."
            )


# ── Lockout helpers ────────────────────────────────────────────────────────────

def _is_locked_out() -> bool:
    return time.time() < st.session_state.get("lockout_until", 0)


def _lockout_remaining() -> int:
    return max(0, int(st.session_state.get("lockout_until", 0) - time.time()))


# ── Register link ──────────────────────────────────────────────────────────────

def _render_register_link() -> None:
    """Render the Create New Account link."""
    st.markdown('<hr style="margin:1rem 0;">', unsafe_allow_html=True)
    st.markdown(
        '<div style="text-align:center;font-size:0.82rem;color:#4a5a78;">'
        "Don't have an account?</div>",
        unsafe_allow_html=True,
    )
    if st.button("✨ Create New Account", width='stretch',
                 type="secondary", key="goto_register"):
        st.session_state["auth_page"] = "register"
        st.rerun()


# ── Footer ─────────────────────────────────────────────────────────────────────

def _render_footer() -> None:
    st.markdown("""
    <div style="text-align:center;margin-top:2rem;font-size:0.72rem;
                color:#2a3a58;letter-spacing:0.04em;">
      Nexus AI Governance Platform &nbsp;·&nbsp; Enterprise Edition
    </div>
    """, unsafe_allow_html=True)