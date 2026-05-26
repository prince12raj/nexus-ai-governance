"""
ui/__init__.py — UI package for Nexus AI Governance Platform.
"""
from ui.styles import ENTERPRISE_CSS
from ui.sidebar import render_sidebar
from ui.dashboard import render_dashboard, render_page_header, render_kpi_card
from ui.upload_page import render_policy_upload
from ui.audit_report import render_compliance_auditor, render_audit_reports
from ui.governance_page import render_agentic_risk
from ui.knowledge_base import render_knowledge_base
from ui.analytics import render_analytics
from ui.admin_settings import render_admin_settings

__all__ = [
    "ENTERPRISE_CSS",
    "render_sidebar",
    "render_dashboard",
    "render_page_header",
    "render_kpi_card",
    "render_policy_upload",
    "render_compliance_auditor",
    "render_audit_reports",
    "render_agentic_risk",
    "render_knowledge_base",
    "render_analytics",
    "render_admin_settings",
]