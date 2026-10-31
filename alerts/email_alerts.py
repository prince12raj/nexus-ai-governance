"""
alerts/email_alerts.py — Real email alerts for Nexus AI Governance Platform.

Sends over SMTP (Gmail, Outlook, SendGrid SMTP, etc.). Configure in Streamlit
secrets or .env:

    SMTP_HOST      = "smtp.gmail.com"
    SMTP_PORT      = "587"                 # 587 = STARTTLS, 465 = SSL
    SMTP_USER      = "you@gmail.com"
    SMTP_PASSWORD  = "app-password"        # Gmail: use an App Password
    SMTP_FROM      = "you@gmail.com"       # optional, defaults to SMTP_USER

Alert preferences (what to alert on + recipient) are stored in
data/alert_settings.json. NOTE: on Streamlit Cloud the filesystem is reset on
reboot/redeploy; set ALERT_EMAIL in secrets as a permanent default recipient.

Alerts never raise into the caller — a failed email must not break an audit.
"""
from __future__ import annotations

import html
import json
import re
import smtplib
import ssl
import threading
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from config.logging_config import get_logger
from config.settings import settings

logger = get_logger("nexus.alerts")

_SETTINGS_FILE = Path(settings.DATA_DIR) / "alert_settings.json"
_EMAIL_RE = re.compile(r"^[^@\s,;<>]+@[^@\s,;<>]+\.[^@\s,;<>]+$")

DEFAULTS: Dict[str, Any] = {
    "email_on_critical":  True,
    "email_on_injection": True,
    "notify_user":        True,   # send to the user who ran the audit
    "email_on_complete":  True,   # "audit complete" summary to that user after every audit
    "alert_email":        "",     # optional extra copy (admins / compliance team)
}


# ══════════════════════════════════════════════════════════════════════════════
# SETTINGS PERSISTENCE
# ══════════════════════════════════════════════════════════════════════════════

def load_alert_settings() -> Dict[str, Any]:
    """Saved alert preferences merged over defaults (+ ALERT_EMAIL secret)."""
    cfg = dict(DEFAULTS)
    try:
        if _SETTINGS_FILE.exists():
            cfg.update(json.loads(_SETTINGS_FILE.read_text(encoding="utf-8")))
    except Exception as exc:
        logger.warning("Could not read alert settings: %s", exc)
    if not cfg.get("alert_email") and settings.ALERT_EMAIL:
        cfg["alert_email"] = settings.ALERT_EMAIL
    return cfg


def save_alert_settings(cfg: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate and persist. Returns (ok, message)."""
    emails = parse_recipients(cfg.get("alert_email", ""))
    if cfg.get("alert_email") and not emails:
        return False, "Enter a valid email address (separate several with commas)."
    clean = {
        "email_on_critical":  bool(cfg.get("email_on_critical")),
        "email_on_injection": bool(cfg.get("email_on_injection")),
        "notify_user":        bool(cfg.get("notify_user", True)),
        "email_on_complete":  bool(cfg.get("email_on_complete", True)),
        "alert_email":        ", ".join(emails),
    }
    try:
        _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _SETTINGS_FILE.write_text(json.dumps(clean, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.error("Could not save alert settings: %s", exc)
        return False, f"Could not save settings: {exc}"
    return True, "Alert settings saved."


def parse_recipients(raw: str) -> List[str]:
    """Split a comma/semicolon separated string into valid email addresses."""
    out = []
    for part in re.split(r"[,;]", raw or ""):
        part = part.strip()
        if part and _EMAIL_RE.match(part):
            out.append(part)
    return out


# ══════════════════════════════════════════════════════════════════════════════
# SENDING
# ══════════════════════════════════════════════════════════════════════════════

def smtp_configured() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD)


def _send(to: Iterable[str], subject: str, text: str, html_body: str) -> Tuple[bool, str]:
    """Send one email. Returns (ok, error_message)."""
    recipients = list(to)
    if not recipients:
        return False, "No valid recipient email set."
    if not smtp_configured():
        return False, "SMTP is not configured (set SMTP_HOST, SMTP_USER, SMTP_PASSWORD)."

    def _build(rcpt: str) -> EmailMessage:
        m = EmailMessage()
        m["Subject"] = subject.replace("\r", " ").replace("\n", " ")[:200]
        m["From"]    = settings.SMTP_FROM or settings.SMTP_USER
        m["To"]      = rcpt
        m.set_content(text)
        m.add_alternative(html_body, subtype="html")
        return m

    try:
        port = int(settings.SMTP_PORT)
        ctx  = ssl.create_default_context()
        if port == 465:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, port, context=ctx, timeout=15) as s:
                s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                for r in recipients:
                    s.send_message(_build(r))
        else:
            with smtplib.SMTP(settings.SMTP_HOST, port, timeout=15) as s:
                s.starttls(context=ctx)
                s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                for r in recipients:
                    s.send_message(_build(r))
        logger.info("Alert email sent | to=%s | subject=%s", recipients, subject)
        return True, ""
    except Exception as exc:
        logger.error("Alert email failed: %s", exc)
        return False, str(exc)


def _wrap_html(title: str, body_html: str) -> str:
    return (
        '<div style="font-family:Arial,sans-serif;max-width:640px;margin:auto;'
        'border:1px solid #e0e4ee;border-radius:8px;overflow:hidden">'
        f'<div style="background:#0f1628;color:#fff;padding:14px 20px;font-size:16px">'
        f'🛡️ Nexus AI Governance — {html.escape(title)}</div>'
        f'<div style="padding:20px;color:#222;font-size:14px;line-height:1.5">{body_html}</div>'
        f'<div style="padding:10px 20px;background:#f5f7fb;color:#888;font-size:12px">'
        f'Sent {datetime.now().strftime("%Y-%m-%d %H:%M")} · '
        'Change alert settings in Admin Settings → Alert Configuration.</div></div>'
    )


def _val(f: Any, key: str, default: Any = "") -> Any:
    return f.get(key, default) if isinstance(f, dict) else getattr(f, key, default)


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC ALERT FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def send_test_email(to: Optional[str] = None) -> Tuple[bool, str]:
    recipients = parse_recipients(to or load_alert_settings()["alert_email"])
    body = "<p>This is a test alert. Your email alert configuration is working. ✅</p>"
    return _send(
        recipients, "Nexus test alert",
        "This is a test alert. Your email alert configuration is working.",
        _wrap_html("Test alert", body),
    )


def send_digest(reports: List[Any], to: Optional[str] = None) -> Tuple[bool, str]:
    """Compliance digest of the given audit reports (dicts or objects)."""
    recipients = parse_recipients(to or load_alert_settings()["alert_email"])
    if not reports:
        return False, "No audits to include in the digest yet."

    scores = [float(_val(r, "compliance_score", 0) or 0) for r in reports]
    avg    = sum(scores) / len(scores)
    crit   = sum(int(_val(r, "critical_findings", 0) or 0) for r in reports)
    rows_t, rows_h = [], []
    for r in reports[:15]:
        fw  = _val(r, "framework_targeted", "") or _val(r, "framework", "")
        doc = _val(r, "document_name", "")
        sc  = float(_val(r, "compliance_score", 0) or 0)
        rows_t.append(f"- {fw} | {doc} | {sc:.0f}%")
        rows_h.append(
            f"<tr><td>{html.escape(str(fw))}</td><td>{html.escape(str(doc))}</td>"
            f"<td>{sc:.0f}%</td></tr>"
        )
    text = (
        f"Compliance digest\nAudits: {len(reports)}\nAverage score: {avg:.0f}%\n"
        f"Critical findings: {crit}\n\n" + "\n".join(rows_t)
    )
    body = (
        f"<p><b>{len(reports)}</b> audits · average score <b>{avg:.0f}%</b> · "
        f"<b>{crit}</b> critical findings</p>"
        '<table cellpadding="6" style="border-collapse:collapse;width:100%" border="1">'
        "<tr><th>Framework</th><th>Document</th><th>Score</th></tr>"
        + "".join(rows_h) + "</table>"
    )
    return _send(recipients, "Nexus compliance digest", text, _wrap_html("Compliance digest", body))


def notify_audit_result(
    result: Dict[str, Any],
    framework: str,
    doc_name: str = "Policy Document",
    background: bool = True,
    user_email: Optional[str] = None,
) -> List[str]:
    """
    Called after every audit. Emails:
      * the user who ran it — an "audit complete" summary (setting: email_on_complete),
        which also lists real Critical findings;
      * admins in alert_email — Critical findings and injection attempts only;
      * the user AND admins — if a document was blocked for prompt injection.
    Returns the list of addresses emailed. Never raises.
    """
    try:
        cfg   = load_alert_settings()
        user_list  = parse_recipients(user_email or "") if cfg.get("notify_user", True) else []
        admin_list = parse_recipients(cfg.get("alert_email", ""))
        user_list  = list(dict.fromkeys(r.lower() for r in user_list))
        admin_list = [r.lower() for r in dict.fromkeys(admin_list) if r.lower() not in user_list]
        logger.info(
            "Alert recipients resolved | user_email_found=%s | notify_user=%s | users=%d | admins=%d",
            bool(parse_recipients(user_email or "")), cfg.get("notify_user", True),
            len(user_list), len(admin_list),
        )
        if not (user_list or admin_list) or not smtp_configured():
            return []

        findings  = result.get("findings", []) or []
        placeholder = result.get("provider_used") == "mock"
        criticals = [f for f in findings if str(_val(f, "severity", "")).lower() == "critical"]
        real_criticals = [] if placeholder else criticals
        injected  = bool(result.get("error")) and "injection" in str(result.get("error")).lower()
        score     = float(result.get("score", 0) or 0)
        grade     = result.get("grade", "")
        counts: Dict[str, int] = {}
        for f in findings:
            sev = str(_val(f, "severity", "Unknown")).title()
            counts[sev] = counts.get(sev, 0) + 1

        def _crit_lists(items):
            li = "".join(
                f"<li><b>{html.escape(str(_val(f, 'legal_reference', '')))}</b> — "
                f"{html.escape(str(_val(f, 'explanation', '') or '')[:200])}</li>"
                for f in items[:10]
            )
            tx = "\n".join(
                f"- {_val(f, 'legal_reference', '')}: {str(_val(f, 'explanation', '') or '')[:200]}"
                for f in items[:10]
            )
            return li, tx

        jobs = []   # (recipients, subject, text, html)

        # ── Injection blocked (user + admins) ────────────────────────────────
        if injected and cfg.get("email_on_injection"):
            body = (
                "<p>A document was <b>blocked</b> because it contains patterns that look like "
                f"prompt injection.</p><p>Document: <b>{html.escape(doc_name)}</b><br>"
                f"Framework: {html.escape(framework)}<br>"
                f"Injection risk score: {float(result.get('injection_risk', 0)):.2f}</p>"
            )
            jobs.append((
                user_list + admin_list,
                f"[Nexus] Prompt injection detected in {doc_name}",
                f"Prompt injection detected. Document: {doc_name}. Framework: {framework}.",
                _wrap_html("Injection detected", body),
            ))

        # ── Audit complete summary (the user who ran the audit) ──────────────
        completion_sent_to_user = False
        if not injected and user_list and cfg.get("email_on_complete", True):
            sev_line = ", ".join(f"{n} {k}" for k, n in counts.items()) or "no findings"
            note_h = note_t = ""
            if placeholder:
                note_h = ("<p style='background:#fff4e5;padding:10px;border-radius:6px'>⚠️ No AI "
                          "provider was available, so these are <b>sample placeholder findings</b>, "
                          "not a real analysis of your document.</p>")
                note_t = ("NOTE: No AI provider was available - these are sample placeholder "
                          "findings, not a real analysis.\n")
            crit_h = crit_t = ""
            if real_criticals:
                li, tx = _crit_lists(real_criticals)
                crit_h = f"<p><b>{len(real_criticals)} critical finding(s):</b></p><ul>{li}</ul>"
                crit_t = f"\nCritical findings:\n{tx}\n"
            body = (
                f"<p>Your <b>{html.escape(framework)}</b> audit of <b>{html.escape(doc_name)}</b> "
                f"has finished.</p><p>Compliance score: <b>{score:.0f}%</b> {html.escape(str(grade))}"
                f"<br>Findings: {html.escape(sev_line)}</p>{note_h}{crit_h}"
            )
            prefix = f"⚠️ {len(real_criticals)} critical · " if real_criticals else ""
            jobs.append((
                user_list,
                f"[Nexus] {prefix}{framework} audit complete: {doc_name} ({score:.0f}%)",
                f"Your {framework} audit of {doc_name} has finished.\n"
                f"Compliance score: {score:.0f}% {grade}\nFindings: {sev_line}\n{note_t}{crit_t}",
                _wrap_html("Audit complete", body),
            ))
            completion_sent_to_user = True

        # ── Critical findings alert ──────────────────────────────────────────
        if real_criticals and cfg.get("email_on_critical"):
            crit_to = list(admin_list)
            if not completion_sent_to_user:
                crit_to = user_list + crit_to        # user not already covered by summary
            if crit_to:
                li, tx = _crit_lists(real_criticals)
                body = (
                    f"<p><b>{len(real_criticals)} critical finding(s)</b> in "
                    f"<b>{html.escape(doc_name)}</b> ({html.escape(framework)}). "
                    f"Compliance score: <b>{score:.0f}%</b>.</p><ul>{li}</ul>"
                )
                jobs.append((
                    crit_to,
                    f"[Nexus] {len(real_criticals)} critical finding(s): {framework} audit of {doc_name}",
                    f"{len(real_criticals)} critical finding(s) in {doc_name} ({framework}), "
                    f"score {score:.0f}%.\n{tx}",
                    _wrap_html("Critical findings", body),
                ))
        elif criticals and placeholder:
            logger.info("Skipping critical-findings alert: findings are mock placeholders.")

        jobs = [j for j in jobs if j[0]]
        if not jobs:
            return []

        def _run():
            for rcpts, subject, text, html_body in jobs:
                _send(rcpts, subject, text, html_body)

        if background:
            threading.Thread(target=_run, daemon=True).start()
        else:
            _run()
        return list(dict.fromkeys(r for j in jobs for r in j[0]))
    except Exception as exc:  # never break an audit because of an alert
        logger.error("notify_audit_result failed: %s", exc)
        return []
