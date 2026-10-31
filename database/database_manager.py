"""
database/database_manager.py — Supabase persistent database for Nexus AI Governance Platform.

Handles:
  - User registration and retrieval (replaces data/users.json)
  - Audit report storage per user (no cross-user data leakage)
  - Uploaded document tracking per user
  - Falls back to local JSON file if Supabase not configured

Setup:
    pip install supabase
    Add DATABASE_URL to .env and Streamlit secrets
"""
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from config.logging_config import get_logger

logger = get_logger("nexus.database.manager")


# ══════════════════════════════════════════════════════════════════════════════
# CONNECTION
# ══════════════════════════════════════════════════════════════════════════════

def _get_client():
    """Get Supabase client. Returns None if not configured."""
    try:
        from supabase import create_client  # type: ignore
        url = _get_secret("SUPABASE_URL")
        key = _get_secret("SUPABASE_KEY")
        if not url or not key:
            return None
        return create_client(url, key)
    except ImportError:
        logger.warning("supabase package not installed — using local file fallback.")
        return None
    except Exception as exc:
        logger.warning("Supabase connection failed: %s — using local fallback.", exc)
        return None


def _get_secret(key: str) -> str:
    """Read from Streamlit secrets or environment."""
    try:
        import streamlit as st
        val = st.secrets.get(key)
        if val:
            return str(val)
    except Exception:
        pass
    return os.getenv(key, "")


def is_configured() -> bool:
    """Return True if Supabase is configured."""
    return bool(_get_secret("SUPABASE_URL") and _get_secret("SUPABASE_KEY"))


# ══════════════════════════════════════════════════════════════════════════════
# USER OPERATIONS
# ══════════════════════════════════════════════════════════════════════════════

def db_get_user(username: str) -> Optional[Dict[str, Any]]:
    """Get a user by username from Supabase — includes password_hash for login."""
    client = _get_client()
    if not client:
        return None
    try:
        result = client.table("users").select(
            "username, password_hash, role, name, email, avatar, "
            "department, permissions, registered_at, last_login, is_active"
        ).eq("username", username.lower()).execute()

        if result.data:
            user = result.data[0]
            # Parse JSON permissions field
            if isinstance(user.get("permissions"), str):
                try:
                    user["permissions"] = json.loads(user["permissions"])
                except Exception:
                    user["permissions"] = ["read"]
            return user
        return None
    except Exception as exc:
        logger.error("db_get_user failed: %s", exc)
        return None


def db_user_exists(username: str) -> bool:
    """Check if username exists in Supabase."""
    return db_get_user(username) is not None


def db_email_exists(email: str) -> bool:
    """Check if email exists in Supabase."""
    client = _get_client()
    if not client:
        return False
    try:
        result = client.table("users").select("username").eq(
            "email", email.lower()
        ).execute()
        return bool(result.data)
    except Exception as exc:
        logger.error("db_email_exists failed: %s", exc)
        return False


def db_register_user(
    username: str,
    password_hash: str,
    full_name: str,
    email: str,
    role: str = "Compliance Officer",
    department: str = "General",
) -> tuple[bool, str]:
    """Register a new user in Supabase."""
    client = _get_client()
    if not client:
        return False, "Database not configured"

    try:
        parts  = full_name.strip().split()
        avatar = (parts[0][0] + parts[-1][0]).upper() if len(parts) >= 2 else full_name[:2].upper()

        permissions_map = {
            "Admin":              ["read", "write", "audit", "export", "admin"],
            "Developer":          ["read", "write", "audit", "export", "admin", "developer"],
            "Compliance Officer": ["read", "write", "audit", "export"],
            "Auditor":            ["read", "audit", "export"],
            "Viewer":             ["read"],
        }

        data = {
            "username":      username.lower(),
            "password_hash": password_hash,
            "role":          role,
            "name":          full_name.strip(),
            "email":         email.lower(),
            "avatar":        avatar,
            "department":    department or "General",
            "permissions":   json.dumps(permissions_map.get(role, ["read"])),
            "registered_at": datetime.now().isoformat(),
        }

        client.table("users").insert(data).execute()
        logger.info("User registered in DB: %s", username)
        return True, f"Account created successfully! Welcome, {full_name.strip()}."

    except Exception as exc:
        logger.error("db_register_user failed: %s", exc)
        if "duplicate" in str(exc).lower() or "unique" in str(exc).lower():
            return False, "Username or email already exists."
        return False, f"Registration failed: {exc}"


def db_update_last_login(username: str) -> None:
    """Update last login timestamp."""
    client = _get_client()
    if not client:
        return
    try:
        client.table("users").update(
            {"last_login": datetime.now().isoformat()}
        ).eq("username", username.lower()).execute()
    except Exception as exc:
        logger.error("db_update_last_login failed: %s", exc)


def db_get_all_users() -> List[Dict[str, Any]]:
    """Get all registered users (without password hashes)."""
    client = _get_client()
    if not client:
        return []
    try:
        result = client.table("users").select(
            "username,role,name,email,avatar,department,registered_at,last_login"
        ).execute()
        return result.data or []
    except Exception as exc:
        logger.error("db_get_all_users failed: %s", exc)
        return []


# ══════════════════════════════════════════════════════════════════════════════
# AUDIT REPORT OPERATIONS
# ══════════════════════════════════════════════════════════════════════════════

def db_save_audit_report(username: str, report: Any) -> bool:
    """
    Save an audit report to Supabase for a specific user.

    Args:
        username: The user who ran the audit.
        report:   AuditReport object or dict.

    Returns:
        True if saved successfully.
    """
    client = _get_client()
    if not client:
        return False

    try:
        # Convert report to dict
        if hasattr(report, "model_dump"):
            report_dict = report.model_dump()
        elif hasattr(report, "dict"):
            report_dict = report.dict()
        else:
            report_dict = dict(report)

        data = {
            "report_id":         report_dict.get("report_id", ""),
            "username":          username.lower(),
            "framework":         report_dict.get("framework_targeted", ""),
            "document_name":     report_dict.get("document_name", "Unknown"),
            "compliance_score":  report_dict.get("compliance_score", 0),
            "total_findings":    report_dict.get("total_findings", 0),
            "critical_findings": report_dict.get("critical_findings", 0),
            "high_findings":     report_dict.get("high_findings", 0),
            "medium_findings":   report_dict.get("medium_findings", 0),
            "low_findings":      report_dict.get("low_findings", 0),
            "findings_json":     json.dumps(
                report_dict.get("findings", []), default=str
            ),
            "pii_detected":      json.dumps(
                report_dict.get("pii_detected", {}), default=str
            ),
            "injection_risk":    report_dict.get("injection_risk", 0),
            "provider_used":     report_dict.get("provider_used", "unknown"),
            "executive_summary": report_dict.get("executive_summary", ""),
            "duration_sec":      report_dict.get("duration_sec", 0),
        }

        client.table("audit_reports").upsert(data).execute()
        logger.info("Audit report saved to DB: %s | user=%s", data["report_id"], username)
        return True

    except Exception as exc:
        logger.error("db_save_audit_report failed: %s", exc)
        return False


def db_get_user_audits(username: str) -> List[Dict[str, Any]]:
    """
    Get all audit reports for a specific user only.
    Other users' reports are never returned.

    Args:
        username: The user to fetch reports for.

    Returns:
        List of audit report dicts, newest first.
    """
    client = _get_client()
    if not client:
        return []

    try:
        result = client.table("audit_reports").select("*").eq(
            "username", username.lower()
        ).order("created_at", desc=True).execute()

        reports = []
        for row in (result.data or []):
            # Parse JSON fields back
            if isinstance(row.get("findings_json"), str):
                row["findings_json"] = json.loads(row["findings_json"])
            if isinstance(row.get("pii_detected"), str):
                row["pii_detected"] = json.loads(row["pii_detected"])
            reports.append(row)

        return reports

    except Exception as exc:
        logger.error("db_get_user_audits failed: %s", exc)
        return []


def db_delete_audit(report_id: str, username: str) -> bool:
    """Delete an audit report — only if it belongs to the user."""
    client = _get_client()
    if not client:
        return False
    try:
        client.table("audit_reports").delete().eq(
            "report_id", report_id
        ).eq("username", username.lower()).execute()
        return True
    except Exception as exc:
        logger.error("db_delete_audit failed: %s", exc)
        return False


# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL STATS (platform-wide, visible to all users)
# ══════════════════════════════════════════════════════════════════════════════

def db_get_global_stats() -> Dict[str, Any]:
    """
    Return platform-wide aggregate stats — safe to show all users.
    Never exposes individual audit content or user details.

    Returns dict with:
        total_audits        — total audits ever run on the platform
        total_users         — total registered users
        total_documents     — total documents uploaded
        avg_compliance_score — platform-wide average compliance score
        audits_by_framework — {framework: count} for bar chart
        audits_over_time    — [{date, count}] for trend chart
        platform_avg_score  — same as avg_compliance_score (alias)
    """
    client = _get_client()
    if not client:
        stats = _empty_global_stats()
        stats["_error"] = "Database client unavailable (check SUPABASE_URL / SUPABASE_KEY)."
        return stats

    stats = _empty_global_stats()
    errors: List[str] = []

    # Each section is fetched independently, so one failing table / permission
    # no longer zeroes the whole dashboard.

    # ── Audit aggregates ───────────────────────────────────────────────────────
    try:
        audit_rows = _fetch_all(client, "audit_reports", "framework, compliance_score, created_at")
        stats["total_audits"] = len(audit_rows)

        scores = [r.get("compliance_score") for r in audit_rows if r.get("compliance_score") is not None]
        avg_score = round(sum(float(x) for x in scores) / len(scores), 1) if scores else 0.0
        stats["avg_compliance_score"] = avg_score
        stats["platform_avg_score"]   = avg_score

        by_fw: Dict[str, int] = {}
        date_counts: Dict[str, int] = {}
        for row in audit_rows:
            fw = row.get("framework") or "Unknown"
            by_fw[fw] = by_fw.get(fw, 0) + 1
            created = str(row.get("created_at") or "")[:10]
            if created:
                date_counts[created] = date_counts.get(created, 0) + 1
        stats["audits_by_framework"] = by_fw
        stats["audits_over_time"] = [
            {"date": d, "count": c} for d, c in sorted(date_counts.items())
        ]
    except Exception as exc:
        logger.error("global stats: audit_reports query failed: %s", exc)
        errors.append(f"audit_reports: {exc}")

    # ── Total users ────────────────────────────────────────────────────────────
    try:
        stats["total_users"] = len(_fetch_all(client, "users", "username"))
    except Exception as exc:
        logger.error("global stats: users query failed: %s", exc)
        errors.append(f"users: {exc}")

    # ── Total documents ────────────────────────────────────────────────────────
    try:
        stats["total_documents"] = len(_fetch_all(client, "uploaded_documents", "doc_id"))
    except Exception as exc:
        logger.error("global stats: uploaded_documents query failed: %s", exc)
        errors.append(f"uploaded_documents: {exc}")

    if errors:
        stats["_error"] = " | ".join(errors)
    return stats


def _fetch_all(client, table: str, columns: str, page_size: int = 1000) -> List[Dict[str, Any]]:
    """Fetch every row of a table (Supabase returns at most 1000 rows per request)."""
    rows: List[Dict[str, Any]] = []
    start = 0
    while True:
        res = client.table(table).select(columns).range(start, start + page_size - 1).execute()
        batch = res.data or []
        rows.extend(batch)
        if len(batch) < page_size:
            return rows
        start += page_size


def db_diagnose() -> Dict[str, str]:
    """Per-table connectivity check for the Admin Settings page. 'ok (N rows)' or the error."""
    if not is_configured():
        return {"configuration": "SUPABASE_URL / SUPABASE_KEY not set"}
    client = _get_client()
    if not client:
        return {"connection": "could not create Supabase client"}
    out: Dict[str, str] = {}
    for table, col in (("users", "username"), ("audit_reports", "report_id"),
                       ("uploaded_documents", "doc_id")):
        try:
            res = client.table(table).select(col, count="exact").limit(1).execute()
            out[table] = f"ok ({res.count if res.count is not None else len(res.data or [])} rows)"
        except Exception as exc:
            out[table] = f"FAILED: {exc}"
    return out


def _empty_global_stats() -> Dict[str, Any]:
    """Return zeroed-out stats when DB is unavailable."""
    return {
        "total_audits":         0,
        "total_users":          0,
        "total_documents":      0,
        "avg_compliance_score": 0.0,
        "platform_avg_score":   0.0,
        "audits_by_framework":  {},
        "audits_over_time":     [],
    }


# ══════════════════════════════════════════════════════════════════════════════
# DOCUMENT OPERATIONS
# ══════════════════════════════════════════════════════════════════════════════

def db_save_document(username: str, doc: Dict[str, Any]) -> bool:
    """Save an uploaded document record for a user."""
    client = _get_client()
    if not client:
        return False
    try:
        data = {
            "doc_id":        doc.get("id", ""),
            "username":      username.lower(),
            "name":          doc.get("name", ""),
            "framework":     doc.get("framework", "GDPR"),
            "text_content":  doc.get("text", "")[:10000],  # cap at 10k chars
            "char_count":    len(doc.get("text", "")),
            "word_count":    len(doc.get("text", "").split()),
            "pii_detected":  json.dumps(doc.get("pii_detected", {})),
            "injection_risk":doc.get("injection_risk", 0),
        }
        client.table("uploaded_documents").upsert(data).execute()
        return True
    except Exception as exc:
        logger.error("db_save_document failed: %s", exc)
        return False


def db_get_user_documents(username: str) -> List[Dict[str, Any]]:
    """Get all documents uploaded by a specific user only."""
    client = _get_client()
    if not client:
        return []
    try:
        result = client.table("uploaded_documents").select(
            "doc_id,name,framework,char_count,word_count,pii_detected,injection_risk,uploaded_at"
        ).eq("username", username.lower()).order(
            "uploaded_at", desc=True
        ).execute()
        return result.data or []
    except Exception as exc:
        logger.error("db_get_user_documents failed: %s", exc)
        return []


def db_get_document_text(username: str, doc_name: str) -> str:
    """
    Fetch the full text_content for a specific document by name and username.
    Used by the audit page when a doc was loaded from DB without full text.

    Returns:
        The stored text_content string, or "" if not found.
    """
    client = _get_client()
    if not client:
        return ""
    try:
        result = client.table("uploaded_documents").select(
            "text_content"
        ).eq("username", username.lower()).eq("name", doc_name).limit(1).execute()

        if result.data:
            return result.data[0].get("text_content") or ""
        return ""
    except Exception as exc:
        logger.error("db_get_document_text failed: %s", exc)
        return ""