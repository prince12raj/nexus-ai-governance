"""
auth/otp.py — Email one-time-code (OTP) verification for Nexus AI Governance Platform.

Used in two places:
  * Login   — after a correct password, a 6-digit code is emailed to the account's
              address; the session only starts once the code is entered.
  * Sign-up — the account is created only after the user proves they own the
              email address by entering the emailed code (= email verification).

Security notes
  * The code is never stored in plain text — only an HMAC-SHA256 of it (keyed with
    APP_SECRET_KEY) is kept in the server-side Streamlit session.
  * Codes expire (OTP_EXPIRY_MINUTES), allow OTP_MAX_ATTEMPTS wrong tries, and can be
    re-sent at most 3 times with a 30 s cooldown.
  * If SMTP is not configured (or REQUIRE_EMAIL_OTP=false) the OTP step is skipped so
    nobody gets locked out.
"""
from __future__ import annotations

import hashlib
import hmac
import html
import secrets
import time
from typing import Any, Callable, Dict, Optional, Tuple

import streamlit as st

from config.logging_config import get_logger
from config.settings import settings

logger = get_logger("nexus.security.otp")

_STATE_KEY       = "_otp"
_SENDS_KEY       = "_otp_send_times"
RESEND_COOLDOWN  = 30      # seconds between re-sends
MAX_RESENDS      = 3
SEND_WINDOW_SECS = 900     # per-session send limit window …
MAX_SENDS_WINDOW = 5       # … and how many sends are allowed in it


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def otp_enabled() -> bool:
    """OTP is active only when switched on AND email sending is configured."""
    if not settings.REQUIRE_EMAIL_OTP:
        return False
    from alerts.email_alerts import smtp_configured
    return smtp_configured()


def mask_email(email: str) -> str:
    name, _, domain = (email or "").partition("@")
    return f"{name[:2]}{'*' * max(1, len(name) - 2)}@{domain}" if domain else "your email"


def _new_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _digest(code: str, salt: str) -> str:
    key = (settings.APP_SECRET_KEY or "nexus").encode()
    return hmac.new(key, f"{salt}:{code}".encode(), hashlib.sha256).hexdigest()


def _friendly(err: str) -> str:
    """User-facing message (the technical detail goes to the log only)."""
    if "no valid email" in str(err):
        return ("There is no valid email address on this account, so a code can't be sent. "
                "Please contact an administrator.")
    return "We couldn't send the verification email. Please try again in a moment."


def get_pending() -> Optional[Dict[str, Any]]:
    return st.session_state.get(_STATE_KEY)


def clear_otp() -> None:
    st.session_state.pop(_STATE_KEY, None)


def _send_allowed() -> bool:
    now = time.time()
    times = [t for t in st.session_state.get(_SENDS_KEY, []) if now - t < SEND_WINDOW_SECS]
    st.session_state[_SENDS_KEY] = times
    return len(times) < MAX_SENDS_WINDOW


def _email_body(code: str, purpose: str) -> Tuple[str, str, str]:
    minutes = settings.OTP_EXPIRY_MINUTES
    if purpose == "register":
        subject, intro = "[Nexus] Verify your email address", "Use this code to verify your email and finish creating your account:"
    else:
        subject, intro = "[Nexus] Your login code", "Use this code to finish signing in:"
    text = (
        f"{intro}\n\n    {code}\n\nIt expires in {minutes} minutes. "
        "If you did not request it, ignore this email — your account is safe."
    )
    from alerts.email_alerts import _wrap_html
    body = (
        f"<p>{html.escape(intro)}</p>"
        f'<p style="font-size:30px;letter-spacing:8px;font-weight:700;margin:16px 0">{code}</p>'
        f"<p>It expires in {minutes} minutes. If you did not request it, ignore this email — "
        "your account is safe.</p>"
    )
    return subject, text, _wrap_html("Verification code", body)


# ══════════════════════════════════════════════════════════════════════════════
# SEND / VERIFY
# ══════════════════════════════════════════════════════════════════════════════

def start_otp(purpose: str, email: str, payload: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Email a fresh code and remember the pending step in the session.

    Args:
        purpose: "login" or "register".
        email:   where the code is sent.
        payload: data needed to finish afterwards (e.g. {"username": ...}).
    Returns:
        (ok, error_message)
    """
    if not _send_allowed():
        return False, "Too many codes requested. Please wait a few minutes and try again."

    code = _new_code()
    ok, err = _deliver(email, code, purpose)
    if not ok:
        logger.error("OTP email failed | purpose=%s | to=%s | %s", purpose, mask_email(email), err)
        return False, _friendly(err)

    salt = secrets.token_hex(8)
    st.session_state[_STATE_KEY] = {
        "purpose":    purpose,
        "email":      email,
        "payload":    payload,
        "salt":       salt,
        "code_hash":  _digest(code, salt),
        "expires":    time.time() + settings.OTP_EXPIRY_MINUTES * 60,
        "attempts":   0,
        "sent_at":    time.time(),
        "resends":    0,
    }
    return True, ""


def _deliver(email: str, code: str, purpose: str) -> Tuple[bool, str]:
    from alerts.email_alerts import _send, parse_recipients
    rcpt = parse_recipients(email)
    if not rcpt:
        return False, "no valid email address on this account"
    subject, text, html_body = _email_body(code, purpose)
    ok, err = _send(rcpt, subject, text, html_body)
    if ok:
        st.session_state.setdefault(_SENDS_KEY, []).append(time.time())
        logger.info("OTP sent | purpose=%s | to=%s", purpose, mask_email(email))
    return ok, err


def resend_otp() -> Tuple[bool, str]:
    st_ = get_pending()
    if not st_:
        return False, "Start again."
    wait = RESEND_COOLDOWN - (time.time() - st_["sent_at"])
    if wait > 0:
        return False, f"Please wait {int(wait) + 1}s before requesting another code."
    if st_["resends"] >= MAX_RESENDS:
        return False, "Resend limit reached. Go back and start again."
    if not _send_allowed():
        return False, "Too many codes requested. Please wait a few minutes."
    code = _new_code()
    ok, err = _deliver(st_["email"], code, st_["purpose"])
    if not ok:
        logger.error("OTP resend failed | %s", err)
        return False, _friendly(err)
    st_.update({
        "code_hash": _digest(code, st_["salt"]),
        "expires":   time.time() + settings.OTP_EXPIRY_MINUTES * 60,
        "attempts":  0,
        "sent_at":   time.time(),
        "resends":   st_["resends"] + 1,
    })
    return True, "A new code has been sent."


def verify_code(entered: str) -> Tuple[bool, str]:
    """Check an entered code. On success the pending step is kept (caller clears it)."""
    st_ = get_pending()
    if not st_:
        return False, "Your session expired. Please start again."
    if time.time() > st_["expires"]:
        clear_otp()
        return False, "That code has expired. Please start again."
    entered = (entered or "").strip().replace(" ", "")
    if not (entered.isdigit() and len(entered) == 6):
        return False, "Enter the 6-digit code from your email."

    st_["attempts"] += 1
    if hmac.compare_digest(_digest(entered, st_["salt"]), st_["code_hash"]):
        return True, ""
    left = settings.OTP_MAX_ATTEMPTS - st_["attempts"]
    if left <= 0:
        clear_otp()
        logger.warning("OTP locked after too many wrong codes")
        return False, "Too many wrong codes. Please start again."
    return False, f"Wrong code. {left} attempt(s) left."


# ══════════════════════════════════════════════════════════════════════════════
# UI
# ══════════════════════════════════════════════════════════════════════════════

def render_otp_step(
    on_verified: Callable[[Dict[str, Any]], None],
    heading: str = "Enter your verification code",
) -> None:
    """Show the code-entry form for the pending OTP step."""
    pending = get_pending()
    if not pending:
        return

    st.markdown(
        f'<div style="text-align:center;margin-bottom:1rem;">'
        f'<div style="font-family:\'Syne\',sans-serif;font-size:1.1rem;font-weight:700;'
        f'color:#e8edf8;">{html.escape(heading)}</div>'
        f'<div style="color:#8a9bbc;font-size:0.85rem;margin-top:6px;">'
        f'We emailed a 6-digit code to <b>{html.escape(mask_email(pending["email"]))}</b>. '
        f'It expires in {settings.OTP_EXPIRY_MINUTES} minutes.</div></div>',
        unsafe_allow_html=True,
    )

    with st.form("otp_form", clear_on_submit=True):
        code = st.text_input("6-digit code", max_chars=6, placeholder="123456",
                             autocomplete="one-time-code")
        verify = st.form_submit_button("Verify →", type="primary", width="stretch")

    c1, c2 = st.columns(2)
    with c1:
        resend = st.button("📧 Resend code", width="stretch")
    with c2:
        back = st.button("← Back", width="stretch")

    if verify:
        ok, msg = verify_code(code)
        if ok:
            payload = dict(pending["payload"])
            clear_otp()
            on_verified(payload)
        else:
            st.error(f"❌ {msg}")
            if not get_pending():          # locked / expired → leave the step
                st.rerun()
    elif resend:
        ok, msg = resend_otp()
        (st.success if ok else st.error)(("✅ " if ok else "❌ ") + msg)
    elif back:
        clear_otp()
        st.rerun()
