"""
ui/analytics.py — Analytics & Insights page for Nexus AI Governance Platform.
"""
from __future__ import annotations

import streamlit as st

from compliance.scoring import score_color, grade_score
from ui.dashboard import render_page_header, render_kpi_card


def _layout(**overrides) -> dict:
    """Merge PLOTLY_DARK with per-chart overrides — prevents duplicate key errors."""
    from config.constants import PLOTLY_DARK
    base = dict(PLOTLY_DARK)
    for key in ("xaxis", "yaxis"):
        if key in overrides and key in base:
            merged = dict(base[key])
            merged.update(overrides.pop(key))
            overrides[key] = merged
    base.update(overrides)
    return base


def render_analytics() -> None:
    from auth.session_manager import get_current_user
    user = get_current_user()
    render_page_header(
        "Analytics & Insights",
        "Platform-wide compliance analytics, trend intelligence, and risk reporting",
        user.get("role", "") if user else "",
    )

    reports      = st.session_state.get("audit_history", [])
    all_findings = [f for r in reports for f in getattr(r, "findings", [])]

    total_audits   = len(reports)
    avg_score      = round(sum(getattr(r, "compliance_score", 0) for r in reports) / max(len(reports), 1), 1)
    total_findings = len(all_findings)
    critical_count = sum(1 for f in all_findings if getattr(f, "severity", "") == "Critical")

    delta = 0.0
    if len(reports) >= 2:
        delta = round(
            getattr(reports[-1], "compliance_score", 0) -
            getattr(reports[-2], "compliance_score", 0), 1
        )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi_card("Total Audits",    str(total_audits),   "Lifetime",          "neutral", "📋", "blue")
    with c2:
        render_kpi_card("Avg Score",       f"{avg_score}%",     f"{delta:+.1f}% trend",
                        "up" if delta >= 0 else "down", "📊", "green")
    with c3:
        render_kpi_card("Total Findings",  str(total_findings), "All audits",        "neutral", "🔍", "yellow")
    with c4:
        render_kpi_card("Critical Issues", str(critical_count), "Unresolved",
                        "down" if critical_count > 0 else "up", "🚨", "red")

    st.markdown("")

    if not reports:
        st.info("📊 No audit data yet. Run compliance audits to populate analytics.", icon="ℹ️")
        return

    tab_trend, tab_fw, tab_findings, tab_dept, tab_export = st.tabs([
        "📈 Trend", "🎯 Frameworks", "🔍 Findings", "🏢 Departments", "📥 Export"
    ])

    with tab_trend:
        st.markdown('<div class="section-header">📈 Compliance Score Over Time</div>', unsafe_allow_html=True)
        _render_trend_chart(reports)

        if len(reports) >= 2:
            from compliance.scoring import score_trend
            scores = [getattr(r, "compliance_score", 0) for r in reports]
            trend  = score_trend(scores)
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.metric("Trend",      f"{trend['trend_emoji']} {trend['trend'].title()}")
            with c2: st.metric("Change",      trend["change_str"] + "%")
            with c3: st.metric("Best Score",  f"{trend['best']}%")
            with c4: st.metric("Worst Score", f"{trend['worst']}%")

    with tab_fw:
        st.markdown('<div class="section-header">🎯 Performance by Framework</div>', unsafe_allow_html=True)
        _render_framework_breakdown(reports)

    with tab_findings:
        col_sev, col_conf = st.columns(2)
        with col_sev:
            st.markdown('<div class="section-header">🎯 Findings by Severity</div>', unsafe_allow_html=True)
            _render_severity_chart(all_findings)
        with col_conf:
            st.markdown('<div class="section-header">📊 Confidence Distribution</div>', unsafe_allow_html=True)
            _render_confidence_chart(all_findings)
        st.markdown('<div class="section-header">🔝 Most Common Violations</div>', unsafe_allow_html=True)
        _render_top_violations(all_findings)

    with tab_dept:
        st.markdown('<div class="section-header">🏢 Risk by Department</div>', unsafe_allow_html=True)
        _render_department_chart(all_findings)
        st.markdown('<div class="section-header">🕸️ Framework Coverage Radar</div>', unsafe_allow_html=True)
        _render_radar(reports)

    with tab_export:
        _render_export_panel(reports, all_findings)


# ══════════════════════════════════════════════════════════════════════════════
# CHART RENDERERS
# ══════════════════════════════════════════════════════════════════════════════

def _render_trend_chart(reports: list) -> None:
    try:
        import plotly.graph_objects as go

        dates  = [getattr(r, "generated_timestamp", "")[:10] for r in reports]
        scores = [getattr(r, "compliance_score", 0) for r in reports]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates, y=scores,
            mode="lines+markers",
            line=dict(color="#3b7ff5", width=2.5),
            marker=dict(color="#3b7ff5", size=8, line=dict(color="#0a0e1a", width=2)),
            fill="tozeroy",
            fillcolor="rgba(59,127,245,0.07)",
            name="Score",
            hovertemplate="<b>%{x}</b><br>Score: %{y:.1f}%<extra></extra>",
        ))
        fig.add_hline(
            y=80, line_dash="dot", line_color="rgba(0,229,160,0.4)",
            annotation_text="Target 80%",
            annotation_font_color="#00e5a0",
            annotation_font_size=10,
        )
        fig.update_layout(**_layout(
            height=280,
            xaxis_title="",
            yaxis_title="Compliance Score (%)",
            yaxis=dict(range=[0, 105]),
            showlegend=False,
        ))
        st.plotly_chart(fig, width='stretch')
    except ImportError:
        st.info("Install plotly: pip install plotly")


def _render_framework_breakdown(reports: list) -> None:
    try:
        import plotly.graph_objects as go

        fw_scores: dict = {}
        for r in reports:
            fw    = getattr(r, "framework_targeted", "Unknown")
            score = getattr(r, "compliance_score", 0)
            fw_scores.setdefault(fw, []).append(score)

        fws    = list(fw_scores.keys())
        avgs   = [round(sum(v) / len(v), 1) for v in fw_scores.values()]
        colors = [score_color(a) for a in avgs]

        fig = go.Figure(go.Bar(
            x=fws, y=avgs,
            marker=dict(color=colors, opacity=0.85, line=dict(color="#0a0e1a", width=1)),
            text=[f"{a}%" for a in avgs],
            textposition="outside",
            textfont=dict(color="#e8edf8", size=11),
            hovertemplate="<b>%{x}</b><br>Avg Score: %{y:.1f}%<extra></extra>",
        ))
        fig.add_hline(
            y=80, line_dash="dot", line_color="rgba(0,229,160,0.4)",
            annotation_text="Target",
            annotation_font_color="#00e5a0",
            annotation_font_size=10,
        )
        fig.update_layout(**_layout(
            height=300,
            xaxis_title="Framework",
            yaxis_title="Average Score (%)",
            yaxis=dict(range=[0, 110]),
            showlegend=False,
        ))
        st.plotly_chart(fig, width='stretch')

        import pandas as pd
        rows = []
        for fw, scores_list in fw_scores.items():
            avg = round(sum(scores_list) / len(scores_list), 1)
            rows.append({
                "Framework": fw,
                "Audits":    len(scores_list),
                "Avg Score": f"{avg}%",
                "Grade":     grade_score(avg),
                "Best":      f"{max(scores_list):.0f}%",
                "Worst":     f"{min(scores_list):.0f}%",
            })
        if rows:
            st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)

    except ImportError:
        st.info("Install plotly and pandas for charts.")


def _render_severity_chart(findings: list) -> None:
    try:
        import plotly.graph_objects as go
        from config.constants import SEVERITY_COLORS
        from collections import Counter

        counts = Counter(getattr(f, "severity", "Medium") for f in findings)
        labels = ["Critical", "High", "Medium", "Low"]
        values = [counts.get(l, 0) for l in labels]
        colors = [SEVERITY_COLORS.get(l, "#8a9bbc") for l in labels]

        fig = go.Figure(go.Bar(
            x=labels, y=values,
            marker=dict(color=colors, opacity=0.85),
            text=values, textposition="outside",
            hovertemplate="<b>%{x}</b><br>Count: %{y}<extra></extra>",
        ))
        fig.update_layout(**_layout(
            height=260,
            xaxis_title="Severity",
            yaxis_title="Count",
            showlegend=False,
        ))
        st.plotly_chart(fig, width='stretch')
    except ImportError:
        pass


def _render_confidence_chart(findings: list) -> None:
    try:
        import plotly.graph_objects as go

        scores = [getattr(f, "confidence_score", 0.0) for f in findings if hasattr(f, "confidence_score")]
        if not scores:
            st.info("No confidence data available.")
            return

        fig = go.Figure(go.Histogram(
            x=scores, nbinsx=10,
            marker=dict(color="#3b7ff5", opacity=0.8, line=dict(color="#0a0e1a", width=1)),
            hovertemplate="Range: %{x}<br>Count: %{y}<extra></extra>",
        ))
        fig.update_layout(**_layout(
            height=260,
            xaxis_title="Confidence Score",
            yaxis_title="Count",
            showlegend=False,
        ))
        st.plotly_chart(fig, width='stretch')
    except ImportError:
        pass


def _render_top_violations(findings: list) -> None:
    try:
        import pandas as pd
        from collections import Counter

        refs   = [getattr(f, "legal_reference", "Unknown") for f in findings]
        counts = Counter(refs).most_common(10)

        if not counts:
            st.info("No violation data yet.")
            return

        rows = [
            {
                "Regulation": ref,
                "Count":      cnt,
                "Severity":   next(
                    (getattr(f, "severity", "") for f in findings
                     if getattr(f, "legal_reference", "") == ref), ""
                ),
            }
            for ref, cnt in counts
        ]
        st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)
    except ImportError:
        pass


def _render_department_chart(findings: list) -> None:
    try:
        import plotly.graph_objects as go
        from collections import Counter

        depts  = Counter(getattr(f, "department", "General") for f in findings)
        labels = list(depts.keys())[:10]
        values = [depts[l] for l in labels]

        fig = go.Figure(go.Bar(
            x=values, y=labels, orientation="h",
            marker=dict(color="#3b7ff5", opacity=0.85),
            text=values, textposition="outside",
        ))
        fig.update_layout(**_layout(
            height=max(250, len(labels) * 30 + 60),
            xaxis_title="Finding Count",
            yaxis_title="",
            showlegend=False,
            margin=dict(l=10, r=40, t=10, b=10),
        ))
        st.plotly_chart(fig, width='stretch')
    except ImportError:
        pass


def _render_radar(reports: list) -> None:
    try:
        import plotly.graph_objects as go

        labels    = ["GDPR", "ISO 27001", "HIPAA", "SOC 2", "PCI-DSS"]
        fw_scores: dict = {fw: [] for fw in labels}

        for r in reports:
            fw = getattr(r, "framework_targeted", "")
            if fw in fw_scores:
                fw_scores[fw].append(getattr(r, "compliance_score", 0))

        values = [
            round(sum(v) / len(v), 1) if v else 50.0
            for v in fw_scores.values()
        ]
        closed_vals   = values + [values[0]]
        closed_labels = labels + [labels[0]]

        fig = go.Figure(go.Scatterpolar(
            r=closed_vals, theta=closed_labels, fill="toself",
            fillcolor="rgba(59,127,245,0.12)",
            line=dict(color="#3b7ff5", width=2),
            marker=dict(color="#3b7ff5", size=6),
        ))
        fig.update_layout(**_layout(
            height=300,
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(
                    range=[0, 100], visible=True,
                    gridcolor="rgba(59,127,245,0.15)",
                    tickfont=dict(size=9, color="#4a5a78"),
                ),
                angularaxis=dict(
                    gridcolor="rgba(59,127,245,0.12)",
                    tickfont=dict(size=11, color="#8a9bbc"),
                ),
            ),
            margin=dict(l=40, r=40, t=20, b=20),
        ))
        st.plotly_chart(fig, width='stretch')
    except ImportError:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# EXPORT PANEL
# ══════════════════════════════════════════════════════════════════════════════

def _render_export_panel(reports: list, findings: list) -> None:
    st.markdown('<div class="section-header">📥 Export Analytics Data</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**📋 Audit History (JSON)**")
        if st.button("Export Audit History", width='stretch'):
            import json
            try:
                data = [
                    r.model_dump() if hasattr(r, "model_dump") else r.dict()
                    for r in reports
                ]
                st.download_button(
                    "💾 Download audit_history.json",
                    data=json.dumps(data, indent=2, default=str),
                    file_name="audit_history.json",
                    mime="application/json",
                )
            except Exception as e:
                st.error(f"Export failed: {e}")

    with col2:
        st.markdown("**🔍 All Findings (CSV)**")
        if st.button("Export Findings CSV", width='stretch'):
            try:
                import pandas as pd
                rows = []
                for f in findings:
                    rows.append({
                        "legal_reference":  getattr(f, "legal_reference", ""),
                        "severity":         getattr(f, "severity", ""),
                        "department":       getattr(f, "department", ""),
                        "confidence_score": getattr(f, "confidence_score", ""),
                        "explanation":      getattr(f, "explanation", "")[:100],
                    })
                if rows:
                    csv = pd.DataFrame(rows).to_csv(index=False)
                    st.download_button(
                        "💾 Download findings.csv",
                        data=csv,
                        file_name="compliance_findings.csv",
                        mime="text/csv",
                    )
                else:
                    st.info("No findings to export.")
            except ImportError:
                st.error("Install pandas: pip install pandas")

    with col3:
        st.markdown("**📊 Summary Report (Markdown)**")
        if st.button("Export Summary", width='stretch'):
            md = _build_summary_markdown(reports, findings)
            st.download_button(
                "💾 Download summary.md",
                data=md,
                file_name="compliance_summary.md",
                mime="text/markdown",
            )


def _build_summary_markdown(reports: list, findings: list) -> str:
    from collections import Counter
    import datetime

    avg_score  = round(
        sum(getattr(r, "compliance_score", 0) for r in reports) / max(len(reports), 1), 1
    )
    sev_counts = Counter(getattr(f, "severity", "") for f in findings)

    lines = [
        "# Nexus AI Governance — Compliance Analytics Report",
        f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Summary",
        f"- Total Audits: **{len(reports)}**",
        f"- Average Compliance Score: **{avg_score}%**",
        f"- Total Findings: **{len(findings)}**",
        f"- Critical: **{sev_counts.get('Critical', 0)}** | "
        f"High: **{sev_counts.get('High', 0)}** | "
        f"Medium: **{sev_counts.get('Medium', 0)}** | "
        f"Low: **{sev_counts.get('Low', 0)}**",
        "",
        "## Audit History",
    ]
    for r in reports:
        lines.append(
            f"- **{getattr(r, 'framework_targeted', '')}** — "
            f"Score: {getattr(r, 'compliance_score', 0):.0f}% — "
            f"{getattr(r, 'generated_timestamp', '')[:10]}"
        )

    return "\n".join(lines)