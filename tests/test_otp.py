"""
tests/test_otp.py — Email OTP for login and sign-up (runs the real Streamlit screens).

A fake SMTP server captures the emailed codes, so no real email is sent.
"""
import json
import re
import shutil
import smtplib
import time
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from config.settings import settings

ROOT = Path(__file__).resolve().parent.parent
USERS = ROOT / "data" / "users.json"
SENT: list = []


class FakeSMTP:
    def __init__(self, *a, **k): pass
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def starttls(self, context=None): pass
    def login(self, u, p): pass
    def send_message(self, m):
        body = m.get_body(("plain",)).get_content()
        SENT.append({"to": m["To"], "subject": m["Subject"], "code": (re.search(r"\b(\d{6})\b", body) or [None, None])[1]})


@pytest.fixture(autouse=True)
def env(monkeypatch):
    backup = USERS.read_text() if USERS.exists() else None
    SENT.clear()
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.test")
    monkeypatch.setattr(settings, "SMTP_USER", "u@test.com")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "pw")
    monkeypatch.setattr(settings, "REQUIRE_EMAIL_OTP", True)
    from auth.security import hash_password
    users = json.loads(backup) if backup else {}
    users["otpuser"] = {"username": "otpuser", "password_hash": hash_password("Str0ng!Pass1"),
                        "full_name": "Otp User", "email": "otp.user@example.com", "role": "Analyst",
                        "department": "QA", "registered_at": "2026-10-01T10:00:00"}
    USERS.parent.mkdir(exist_ok=True)
    USERS.write_text(json.dumps(users))
    yield
    if backup is None:
        USERS.unlink(missing_ok=True)
    else:
        USERS.write_text(backup)


def login_app():
    def script():
        from auth.login import render_login_page
        render_login_page()
    at = AppTest.from_function(script, default_timeout=30)
    at.run()
    return at


def submit_password(at, user="otpuser", pw="Str0ng!Pass1"):
    at.text_input[0].set_value(user)
    at.text_input[1].set_value(pw)
    at.button[0].click()
    at.run()
    return at


def enter_code(at, code):
    box = [t for t in at.text_input if t.label == "6-digit code"][0]
    box.set_value(code)
    [b for b in at.button if "Verify" in b.label][0].click()
    at.run()
    return at


def on_otp_screen(at):
    return any(t.label == "6-digit code" for t in at.text_input)


# ── Login ──────────────────────────────────────────────────────────────────────

def test_correct_password_asks_for_code_and_does_not_log_in():
    at = submit_password(login_app())
    assert on_otp_screen(at)
    assert not at.session_state["authenticated"] if "authenticated" in at.session_state else True
    assert len(SENT) == 1 and SENT[0]["to"] == "otp.user@example.com"
    assert re.fullmatch(r"\d{6}", SENT[0]["code"])


def test_correct_code_logs_in():
    at = submit_password(login_app())
    enter_code(at, SENT[0]["code"])
    assert at.session_state["authenticated"] is True
    assert at.session_state["username"] == "otpuser"


def test_wrong_code_is_rejected_then_right_code_works():
    at = submit_password(login_app())
    real = SENT[0]["code"]
    wrong = "000000" if real != "000000" else "111111"
    enter_code(at, wrong)
    assert any("Wrong code" in e.value for e in at.error)
    assert "authenticated" not in at.session_state or not at.session_state["authenticated"]
    enter_code(at, real)
    assert at.session_state["authenticated"] is True


def test_wrong_password_sends_no_email():
    at = submit_password(login_app(), pw="WrongPass1!")
    assert SENT == []
    assert not on_otp_screen(at)
    assert any("Invalid username or password" in e.value for e in at.error)


def test_too_many_wrong_codes_resets_to_password_form():
    at = submit_password(login_app())
    real = SENT[0]["code"]
    wrong = "000000" if real != "000000" else "111111"
    for _ in range(settings.OTP_MAX_ATTEMPTS):
        if not on_otp_screen(at):
            break
        enter_code(at, wrong)
    assert not on_otp_screen(at)               # code invalidated → back to password
    assert "authenticated" not in at.session_state or not at.session_state["authenticated"]


def test_expired_code_is_rejected():
    at = submit_password(login_app())
    at.session_state["_otp"]["expires"] = time.time() - 1
    enter_code(at, SENT[0]["code"])
    assert "authenticated" not in at.session_state or not at.session_state["authenticated"]


def test_resend_has_a_cooldown():
    at = submit_password(login_app())
    [b for b in at.button if "Resend" in b.label][0].click()
    at.run()
    assert any("wait" in e.value.lower() for e in at.error)
    assert len(SENT) == 1
    at.session_state["_otp"]["sent_at"] -= 60          # cooldown passed
    [b for b in at.button if "Resend" in b.label][0].click()
    at.run()
    assert len(SENT) == 2
    enter_code(at, SENT[1]["code"])                    # new code works
    assert at.session_state["authenticated"] is True


def test_old_code_stops_working_after_resend():
    at = submit_password(login_app())
    first = SENT[0]["code"]
    at.session_state["_otp"]["sent_at"] -= 60
    [b for b in at.button if "Resend" in b.label][0].click()
    at.run()
    if SENT[1]["code"] != first:
        enter_code(at, first)
        assert "authenticated" not in at.session_state or not at.session_state["authenticated"]


def test_code_is_not_stored_in_plain_text():
    at = submit_password(login_app())
    state = json.dumps(at.session_state["_otp"], default=str)
    assert SENT[0]["code"] not in state.replace(at.session_state["_otp"]["code_hash"], "")


def test_without_smtp_login_skips_otp(monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    at = submit_password(login_app())
    assert at.session_state["authenticated"] is True
    assert SENT == []


def test_otp_can_be_switched_off(monkeypatch):
    monkeypatch.setattr(settings, "REQUIRE_EMAIL_OTP", False)
    at = submit_password(login_app())
    assert at.session_state["authenticated"] is True


# ── Sign-up ────────────────────────────────────────────────────────────────────

def register_app():
    def script():
        import streamlit as st
        from auth import register
        if not st.session_state.get("_started"):
            st.session_state["_started"] = True
            register._handle_registration(
                full_name="New Person", email="new.person@example.com", username="newperson",
                department="IT", role="Analyst", password="Str0ng!Pass1", confirm="Str0ng!Pass1",
                agreed=True,
            )
        else:
            register._render_form()
    at = AppTest.from_function(script, default_timeout=30)
    at.run()
    return at


def test_signup_creates_account_only_after_email_verified():
    at = register_app()
    assert on_otp_screen(at)
    assert len(SENT) == 1 and SENT[0]["to"] == "new.person@example.com"
    assert "newperson" not in json.loads(USERS.read_text())      # not created yet
    enter_code(at, SENT[0]["code"])
    users = json.loads(USERS.read_text())
    assert "newperson" in users and users["newperson"]["email"] == "new.person@example.com"


def test_signup_wrong_code_does_not_create_account():
    at = register_app()
    real = SENT[0]["code"]
    enter_code(at, "000000" if real != "000000" else "111111")
    assert "newperson" not in json.loads(USERS.read_text())


def test_signup_existing_email_sends_no_code():
    def script():
        from auth import register
        register._handle_registration("X", "otp.user@example.com", "someoneelse", "IT", "Analyst",
                                      "Str0ng!Pass1", "Str0ng!Pass1", True)
    at = AppTest.from_function(script, default_timeout=30); at.run()
    assert SENT == []
    assert any("already exists" in e.value for e in at.error)
