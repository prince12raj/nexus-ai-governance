"""
auth/register.py — Registration page for Nexus AI Governance Platform.

New users register here. Credentials are saved to data/users.json
and are immediately usable for login — no restart required.

Usage:
    from auth.register import render_register_page
    render_register_page()
"""
from __future__ import annotations

import streamlit as st

from config.logging_config import get_logger

logger = get_logger("nexus.security.register")


def render_register_page() -> None:
    """
    Render the full registration page.

    Shows:
      - Brand logo
      - Registration form (name, email, username, password, role, dept)
      - Password strength meter
      - Switch to Login link
    """
    st.markdown('<div style="min-height:5vh;"></div>', unsafe_allow_html=True)

    col_l, col_c, col_r = st.columns([1, 1.5, 1])
    with col_c:
        _render_logo()
        _render_form()
        _render_switch_to_login()
        _render_footer()


# ══════════════════════════════════════════════════════════════════════════════
# LOGO
# ══════════════════════════════════════════════════════════════════════════════

def _render_logo() -> None:
    st.markdown("""
    <div style="text-align:center;margin-bottom:1.5rem;">
      <div style="font-family:'Syne',sans-serif;font-size:2.2rem;
                  font-weight:800;color:#e8edf8;letter-spacing:-0.02em;">
        ⚖️ <span style="color:#3b7ff5;">Nexus</span> AI
      </div>
      <div style="font-size:0.8rem;color:#4a5a78;letter-spacing:0.1em;
                  text-transform:uppercase;margin-top:4px;">
        Create your account
      </div>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# REGISTRATION FORM
# ══════════════════════════════════════════════════════════════════════════════

def _render_form() -> None:
    """Render the registration card with form fields."""

    # Show success message if registration just succeeded
    if st.session_state.get("_reg_success"):
        st.success(st.session_state["_reg_success"])
        st.info("👉 Click **Go to Login** below to sign in with your new account.")
        st.session_state["_reg_success"] = ""
        return

    st.markdown('<div class="login-container">', unsafe_allow_html=True)

    with st.form("register_form", clear_on_submit=False):
        st.markdown(
            '<div style="text-align:center;margin-bottom:1.2rem;">'
            '<div style="font-family:\'Syne\',sans-serif;font-size:1.05rem;'
            'font-weight:700;color:#e8edf8;">Create your Nexus account</div>'
            '</div>',
            unsafe_allow_html=True,
        )

        # ── Row 1: Full name + Email ───────────────────────────────────────────
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input(
                "Full Name *",
                placeholder="Alexandra Chen",
                key="reg_name",
            )
        with col2:
            email = st.text_input(
                "Email Address *",
                placeholder="you@company.com",
                key="reg_email",
            )

        # ── Row 2: Username + Department ──────────────────────────────────────
        col3, col4 = st.columns(2)
        with col3:
            username = st.text_input(
                "Username *",
                placeholder="alex.chen",
                key="reg_username",
                help="Lowercase letters, numbers, dots and underscores only. Min 3 chars.",
            )
        with col4:
            department = st.text_input(
                "Department",
                placeholder="e.g. Legal & Compliance",
                key="reg_dept",
            )

        # ── Row 3: Role ───────────────────────────────────────────────────────
        role = st.selectbox(
            "Role *",
            ["Compliance Officer", "Auditor", "Viewer", "Developer", "Admin"],
            key="reg_role",
            help=(
                "Compliance Officer — full audit access. "
                "Auditor — read + audit. "
                "Viewer — read only. "
                "Developer — full access (requires secret key). "
                "Admin — full access + user management (requires secret key)."
            ),
        )

        # ── Developer / Admin secret key ──────────────────────────────────────
        dev_key = ""
        if role == "Developer":
            st.markdown(
                '<div style="background:rgba(155,89,255,0.08);border:1px solid '
                'rgba(155,89,255,0.25);border-radius:8px;padding:0.8rem 1rem;'
                'margin:0.3rem 0 0.5rem;">'
                '<div style="color:#9b59ff;font-weight:700;font-size:0.82rem;'
                'margin-bottom:0.3rem;">🔐 Developer Access Required</div>'
                '<div style="color:#8a9bbc;font-size:0.76rem;">Contact your '
                'system administrator for the Developer secret key.</div>'
                '</div>',
                unsafe_allow_html=True,
            )
            dev_key = st.text_input(
                "Developer Secret Key *",
                type="password",
                placeholder="Enter 6-digit secret key",
                key="reg_dev_key",
            )

        elif role == "Admin":
            st.markdown(
                '<div style="background:rgba(59,127,245,0.08);border:1px solid '
                'rgba(59,127,245,0.25);border-radius:8px;padding:0.8rem 1rem;'
                'margin:0.3rem 0 0.5rem;">'
                '<div style="color:#3b7ff5;font-weight:700;font-size:0.82rem;'
                'margin-bottom:0.3rem;">🛡️ Admin Access Required</div>'
                '<div style="color:#8a9bbc;font-size:0.76rem;">Admin accounts '
                'have full platform access including user management. '
                'Contact your platform owner for the Admin secret key.</div>'
                '</div>',
                unsafe_allow_html=True,
            )
            dev_key = st.text_input(
                "Admin Secret Key *",
                type="password",
                placeholder="Enter 5-digit secret key",
                key="reg_dev_key",
            )

        # ── Row 4: Passwords ──────────────────────────────────────────────────
        col5, col6 = st.columns(2)
        with col5:
            password = st.text_input(
                "Password *",
                type="password",
                placeholder="••••••••",
                key="reg_pass",
                help="Min 8 chars, uppercase, lowercase, digit, special character.",
            )
        with col6:
            confirm = st.text_input(
                "Confirm Password *",
                type="password",
                placeholder="••••••••",
                key="reg_confirm",
            )

        # ── Live password strength ────────────────────────────────────────────
        if password:
            _show_password_strength(password)

        # ── Terms checkbox ────────────────────────────────────────────────────
        agreed = st.checkbox(
            "I agree to the Terms of Service and Privacy Policy",
            key="reg_agreed",
        )

        submitted = st.form_submit_button(
            "Create Account →",
            type="primary",
            width='stretch',
        )

    st.markdown("</div>", unsafe_allow_html=True)

    if submitted:
        _handle_registration(
            full_name=full_name,
            email=email,
            username=username,
            department=department,
            role=role,
            password=password,
            confirm=confirm,
            agreed=agreed,
            dev_key=dev_key,
        )


# ══════════════════════════════════════════════════════════════════════════════
# FORM HANDLER
# ══════════════════════════════════════════════════════════════════════════════

def _handle_registration(
    full_name: str,
    email: str,
    username: str,
    department: str,
    role: str,
    password: str,
    confirm: str,
    agreed: bool,
    dev_key: str = "",
) -> None:
    """Validate inputs and register the user."""

    # ── Client-side validation ────────────────────────────────────────────────
    errors = []

    if not full_name.strip():
        errors.append("Full name is required.")
    if not email.strip() or "@" not in email:
        errors.append("A valid email address is required.")
    if not username.strip():
        errors.append("Username is required.")
    elif len(username.strip()) < 3:
        errors.append("Username must be at least 3 characters.")
    elif " " in username:
        errors.append("Username cannot contain spaces.")
    if not password:
        errors.append("Password is required.")
    elif password != confirm:
        errors.append("Passwords do not match.")
    else:
        from auth.security import is_strong_password
        valid, msg = is_strong_password(password)
        if not valid:
            errors.append(f"Weak password: {msg}")
    if not agreed:
        errors.append("You must agree to the Terms of Service.")

    # Developer and Admin secret key check
    DEVELOPER_SECRET = "844502"
    ADMIN_SECRET     = "73520"

    if role == "Developer":
        if not dev_key.strip():
            errors.append("Developer Secret Key is required for the Developer role.")
        elif dev_key.strip() != DEVELOPER_SECRET:
            errors.append("❌ Invalid Developer Secret Key. Access denied.")

    elif role == "Admin":
        if not dev_key.strip():
            errors.append("Admin Secret Key is required for the Admin role.")
        elif dev_key.strip() != ADMIN_SECRET:
            errors.append("❌ Invalid Admin Secret Key. Access denied.")

    if errors:
        for err in errors:
            st.error(f"❌ {err}")
        return

    # ── Register ──────────────────────────────────────────────────────────────
    from auth.security import hash_password
    from auth.user_store import register_user

    hashed   = hash_password(password)
    success, message = register_user(
        username=username.strip().lower(),
        password_hash=hashed,
        full_name=full_name.strip(),
        email=email.strip().lower(),
        role=role,
        department=department.strip(),
    )

    if success:
        st.session_state["_reg_success"] = (
            f"✅ {message} Your username is: **{username.strip().lower()}**"
        )
        # Auto-switch to login page after short delay
        st.session_state["auth_page"] = "login"
        st.rerun()
    else:
        st.error(f"❌ {message}")


# ══════════════════════════════════════════════════════════════════════════════
# PASSWORD STRENGTH METER
# ══════════════════════════════════════════════════════════════════════════════

def _show_password_strength(password: str) -> None:
    """Render a visual password strength meter below the password field."""
    checks = {
        "8+ characters":     len(password) >= 8,
        "Uppercase letter":  any(c.isupper() for c in password),
        "Lowercase letter":  any(c.islower() for c in password),
        "Number":            any(c.isdigit() for c in password),
        "Special character": any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in password),
    }

    passed = sum(checks.values())
    total  = len(checks)
    pct    = int((passed / total) * 100)

    # Color based on strength
    if passed <= 2:
        color, label = "#ff4757", "Weak"
    elif passed <= 3:
        color, label = "#ffc847", "Fair"
    elif passed == 4:
        color, label = "#3b7ff5", "Good"
    else:
        color, label = "#00e5a0", "Strong"

    # Progress bar
    st.markdown(f"""
    <div style="margin:-0.5rem 0 0.5rem;">
      <div style="display:flex;justify-content:space-between;
                  font-size:0.72rem;color:#4a5a78;margin-bottom:3px;">
        <span>Password Strength</span>
        <span style="color:{color};font-weight:700;">{label}</span>
      </div>
      <div style="background:#1a2540;border-radius:4px;height:4px;">
        <div style="width:{pct}%;background:{color};height:4px;
                    border-radius:4px;transition:width 0.3s;"></div>
      </div>
      <div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:6px;">
        {''.join(
            f'<span style="font-size:0.68rem;color:{"#00e5a0" if ok else "#2a3a58"};">'
            f'{"✓" if ok else "○"} {label_}</span>'
            for label_, ok in checks.items()
        )}
      </div>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SWITCH TO LOGIN
# ══════════════════════════════════════════════════════════════════════════════

def _render_switch_to_login() -> None:
    """Render the 'Already have an account? Sign in' button."""
    st.markdown("")
    st.markdown(
        '<div style="text-align:center;font-size:0.82rem;color:#4a5a78;">'
        'Already have an account?</div>',
        unsafe_allow_html=True,
    )
    if st.button("← Go to Login", width='stretch', type="secondary"):
        st.session_state["auth_page"] = "login"
        st.rerun()


def _render_footer() -> None:
    from config.constants import APP_VERSION
    st.markdown(f"""
    <div style="text-align:center;margin-top:1.5rem;font-size:0.72rem;
                color:#2a3a58;letter-spacing:0.04em;">
      Nexus AI Governance Platform v{APP_VERSION} &nbsp;·&nbsp; Enterprise Edition
    </div>
    """, unsafe_allow_html=True)