"""
auth/db_session.py — Per-user audit and document persistence helpers.

Called by session_manager to load/save user-specific data
from Supabase (cloud) or session_state (local fallback).
"""
import json
from typing import Any, Dict, List

from config.logging_config import get_logger

logger = get_logger("nexus.security.db_session")


def load_user_audits(username: str) -> List[Any]:
    """
    Load audit history for a specific user from Supabase.
    Returns list of AuditReport objects or dicts.
    Falls back to session_state if Supabase not configured.
    """
    try:
        from database.database_manager import db_get_user_audits, is_configured
        if not is_configured():
            return []

        rows = db_get_user_audits(username)
        if not rows:
            return []

        # Convert DB rows back to AuditReport-like dicts
        reports = []
        for row in rows:
            report = {
                "report_id":          row.get("report_id", ""),
                "framework_targeted": row.get("framework", ""),
                "document_name":      row.get("document_name", ""),
                "compliance_score":   row.get("compliance_score", 0),
                "total_findings":     row.get("total_findings", 0),
                "critical_findings":  row.get("critical_findings", 0),
                "high_findings":      row.get("high_findings", 0),
                "medium_findings":    row.get("medium_findings", 0),
                "low_findings":       row.get("low_findings", 0),
                "findings":           row.get("findings_json", []),
                "pii_detected":       row.get("pii_detected", {}),
                "injection_risk":     row.get("injection_risk", 0),
                "provider_used":      row.get("provider_used", ""),
                "executive_summary":  row.get("executive_summary", ""),
                "generated_timestamp":str(row.get("created_at", ""))[:19],
                "duration_sec":       row.get("duration_sec", 0),
            }
            reports.append(report)

        logger.info("Loaded %d audits from DB for user=%s", len(reports), username)
        return reports

    except Exception as exc:
        logger.warning("load_user_audits failed: %s", exc)
        return []


def save_audit_to_db(username: str, report: Any) -> None:
    """Save an audit report to Supabase for this user."""
    try:
        from database.database_manager import db_save_audit_report, is_configured
        if not is_configured():
            return
        db_save_audit_report(username, report)
    except Exception as exc:
        logger.warning("save_audit_to_db failed: %s", exc)


def load_user_documents(username: str) -> List[Dict[str, Any]]:
    """Load uploaded documents list for a specific user."""
    try:
        from database.database_manager import db_get_user_documents, is_configured
        if not is_configured():
            return []
        docs = db_get_user_documents(username)
        logger.info("Loaded %d documents from DB for user=%s", len(docs), username)
        return docs
    except Exception as exc:
        logger.warning("load_user_documents failed: %s", exc)
        return []


def save_document_to_db(username: str, doc: Dict[str, Any]) -> None:
    """Save a document record to Supabase for this user."""
    try:
        from database.database_manager import db_save_document, is_configured
        if not is_configured():
            return
        db_save_document(username, doc)
    except Exception as exc:
        logger.warning("save_document_to_db failed: %s", exc)