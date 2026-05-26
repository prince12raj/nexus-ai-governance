"""
auth/login.py — Login page renderer for Nexus AI Governance Platform.

Renders a full-screen enterprise login form with:
  - Animated gradient header
  - Username + password form
  - Failed attempt tracking with lockout
  - Demo credentials panel
  - Session initialisation on success

Usage:
    from auth.login import render_login_page
    render_login_page()
"""
from __future__ import annotations

import time
from typing import Optional

import streamlit as st

from auth.session_manager import login, is_logged_in
from config.logging_config import get_logger

logger = get_logger("nexus.security.login")

# Max failed attempts before temporary lockout
MAX_ATTEMPTS  = 5
LOCKOUT_SECS  = 30


def render_login_page() -> None:
    """
    Render the full-screen enterprise login page.

    Handles:
      - Login form submission and validation
      - Failed attempt counting and lockout
      - Session initialisation on successful auth
      - Demo credentials display
    """
    # Centre the form vertically
    st.markdown(
        '<div style="min-height:10vh;"></div>',
        unsafe_allow_html=True,
    )

    col_l, col_c, col_r = st.columns([1, 1.5, 1])
    with col_c:
        _render_logo()
        _render_form()
        _render_demo_creds()
        _render_footer()


# ══════════════════════════════════════════════════════════════════════════════
# LOGO & BRANDING
# ══════════════════════════════════════════════════════════════════════════════

def _render_logo() -> None:
    """Render the platform logo and tagline above the login card."""
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


# ══════════════════════════════════════════════════════════════════════════════
# LOGIN FORM
# ══════════════════════════════════════════════════════════════════════════════

def _render_form() -> None:
    """Render the login form card with attempt tracking."""

    # ── Lockout check ──────────────────────────────────────────────────────────
    if _is_locked_out():
        remaining = _lockout_remaining()
        st.markdown(f"""
        <div style="background:rgba(255,71,87,0.1);border:1px solid rgba(255,71,87,0.3);
                    border-radius:12px;padding:1.2rem;text-align:center;
                    margin-bottom:1rem;">
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

    # ── Form card ──────────────────────────────────────────────────────────────
    st.markdown('<div class="login-container">', unsafe_allow_html=True)

    with st.form("login_form", clear_on_submit=False):
        st.markdown(
            '<div style="text-align:center;margin-bottom:1.5rem;">'
            '<div style="font-family:\'Syne\',sans-serif;font-size:1.1rem;'
            'font-weight:700;color:#e8edf8;">Sign In to your account</div>'
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
            use_container_width=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Handle submission ──────────────────────────────────────────────────────
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
        # Reset failed attempts
        st.session_state["login_attempts"]  = 0
        st.session_state["lockout_until"]   = 0
        st.session_state["login_username"]  = username

        st.success("✅ Authenticated — loading platform…")
        logger.info("Successful login: user=%s", username)
        time.sleep(0.5)
        st.rerun()
    else:
        # Increment failed attempts
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


# ══════════════════════════════════════════════════════════════════════════════
# LOCKOUT HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _is_locked_out() -> bool:
    """Return True if the user is currently locked out."""
    lockout_until = st.session_state.get("lockout_until", 0)
    return time.time() < lockout_until


def _lockout_remaining() -> int:
    """Return seconds remaining in lockout period."""
    lockout_until = st.session_state.get("lockout_until", 0)
    return max(0, int(lockout_until - time.time()))


# ══════════════════════════════════════════════════════════════════════════════
# DEMO CREDENTIALS PANEL
# ══════════════════════════════════════════════════════════════════════════════

def _render_demo_creds() -> None:
    """Render the switch to register button."""
    st.markdown('<hr style="margin:1rem 0;">', unsafe_allow_html=True)
    st.markdown(
        '<div style="text-align:center;font-size:0.82rem;color:#4a5a78;">'
        "Don't have an account?</div>",
        unsafe_allow_html=True,
    )
    if st.button("✨ Create New Account", use_container_width=True, type="secondary",
                 key="goto_register"):
        st.session_state["auth_page"] = "register"
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════════════

def _render_footer() -> None:
    """Render the login page footer."""
    from config.constants import APP_VERSION
    st.markdown(f"""
    <div style="text-align:center;margin-top:2rem;font-size:0.72rem;
                color:#2a3a58;letter-spacing:0.04em;">
      Nexus AI Governance Platform v{APP_VERSION} &nbsp;·&nbsp;
      Enterprise Edition &nbsp;·&nbsp;
      <span style="color:#3b7ff5;">SOC 2 Compliant</span>
    </div>
    """, unsafe_allow_html=True)