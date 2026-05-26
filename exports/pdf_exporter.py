"""
exports/pdf_exporter.py — Generate PDF audit reports using ReportLab.

Install: pip install reportlab
"""
from __future__ import annotations

import io
from typing import Optional

from config.logging_config import get_logger
from models.audit_models import AuditReport

logger = get_logger("nexus.exports.pdf")


def generate_pdf_report(report: AuditReport) -> Optional[bytes]:
    """Return PDF bytes for *report*, or None if ReportLab is not installed."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        )
    except ImportError:
        logger.error("reportlab not installed. Run: pip install reportlab")
        return None

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()
    heading = ParagraphStyle("heading", parent=styles["Heading1"],
                              fontSize=18, textColor=colors.HexColor("#3b7ff5"))
    sub_h   = ParagraphStyle("sub", parent=styles["Heading2"],
                              fontSize=12, textColor=colors.HexColor("#0a0e1a"))
    body    = styles["Normal"]

    story = []

    # ── Title ──────────────────────────────────────────────────────────────────
    story.append(Paragraph("⚖️ Nexus AI Governance — Audit Report", heading))
    story.append(Spacer(1, 0.3*cm))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#3b7ff5")))
    story.append(Spacer(1, 0.5*cm))

    # ── Metadata ───────────────────────────────────────────────────────────────
    meta_data = [
        ["Framework",  report.framework_targeted],
        ["Score",      f"{report.compliance_score:.0f}%"],
        ["Findings",   str(report.total_findings)],
        ["Critical",   str(report.critical_findings)],
        ["Generated",  report.generated_timestamp],
    ]
    meta_table = Table(meta_data, colWidths=[4*cm, 12*cm])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (0, -1), colors.HexColor("#f0f4ff")),
        ("FONTNAME",     (0, 0), (0, -1), "Helvetica-Bold"),
        ("TEXTCOLOR",    (0, 0), (0, -1), colors.HexColor("#3b7ff5")),
        ("GRID",         (0, 0), (-1, -1), 0.5, colors.HexColor("#dde3f0")),
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[colors.white, colors.HexColor("#f7f9ff")]),
        ("PADDING",      (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.5*cm))

    # ── Executive summary ──────────────────────────────────────────────────────
    story.append(Paragraph("Executive Summary", sub_h))
    story.append(Paragraph(report.executive_summary, body))
    story.append(Spacer(1, 0.5*cm))

    # ── Findings ───────────────────────────────────────────────────────────────
    if report.findings:
        story.append(Paragraph("Findings", sub_h))
        sev_colors_map = {
            "Critical": colors.HexColor("#ff4757"),
            "High":     colors.HexColor("#ffc847"),
            "Medium":   colors.HexColor("#3b7ff5"),
            "Low":      colors.HexColor("#00e5a0"),
        }
        for i, f in enumerate(report.findings, 1):
            color = sev_colors_map.get(f.severity, colors.grey)
            story.append(Paragraph(
                f'<font color="{color.hexval()}"><b>[{f.severity}]</b></font> '
                f'{i}. {f.legal_reference}', body))
            story.append(Paragraph(f"<i>{f.explanation}</i>", body))
            story.append(Paragraph(f"<b>Fix:</b> {f.corrected_version}", body))
            story.append(Spacer(1, 0.3*cm))

    doc.build(story)
    return buf.getvalue()
