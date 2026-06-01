"""
ui/dashboard.py — Main dashboard page for Nexus AI Governance Platform.
"""

import datetime

import streamlit as st

from compliance.scoring import risk_level, score_color


def _get_field(r, field: str, default=None):
    """
    Safely read a field from either a dict (Supabase row) or an object (AuditReport).
    Supabase returns dicts; in-session reports are dataclass/Pydantic objects.
    Also handles field name aliases (e.g. framework_targeted vs framework).
    """
    if isinstance(r, dict):
        return r.get(field, default)
    return getattr(r, field, default)


def _layout(**overrides) -> dict:
    """
    Merge PLOTLY_DARK with per-chart overrides.
    Prevents 'multiple values for keyword argument' errors when PLOTLY_DARK
    already defines keys like margin, xaxis, yaxis.
    """
    from config.constants import PLOTLY_DARK
    base = dict(PLOTLY_DARK)
    for key in ("xaxis", "yaxis"):
        if key in overrides and key in base:
            merged = dict(base[key])
            merged.update(overrides.pop(key))
            overrides[key] = merged
    base.update(overrides)
    return base


# ══════════════════════════════════════════════════════════════════════════════
# SHARED COMPONENTS (used by all pages)
# ══════════════════════════════════════════════════════════════════════════════

def render_page_header(title: str, subtitle: str, badge: str = "") -> None:
    badge_html = f'<span class="nexus-badge">{badge}</span>' if badge else ""
    st.markdown(f"""
    <div class="nexus-header">
      <div class="nexus-header-title">{title} {badge_html}</div>
      <div class="nexus-header-subtitle">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)


def render_kpi_card(label, value, delta, delta_dir, icon, color) -> None:
    arrow = "↑" if delta_dir == "up" else "↓" if delta_dir == "down" else "–"
    st.markdown(f"""
    <div class="kpi-card {color}">
      <div class="kpi-icon">{icon}</div>
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}</div>
      <div class="kpi-delta {delta_dir}">{arrow} {delta}</div>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD PAGE
# ══════════════════════════════════════════════════════════════════════════════

def render_dashboard() -> None:
    from auth.session_manager import get_current_user
    user = get_current_user()

    render_page_header(
        "AI Governance Dashboard",
        f"Welcome back, {user.get('name', 'User')} — "
        f"{datetime.date.today().strftime('%B %d, %Y')}",
        user.get("role", "") if user else "",
    )

    reports = st.session_state.get("audit_history", [])

    # Reports from Supabase are dicts; in-session reports are objects.
    # Use _get_field() everywhere so both work transparently.
    # findings_json is the DB column name; findings is the object attribute.
    all_findings = []
    for r in reports:
        findings = _get_field(r, "findings") or _get_field(r, "findings_json") or []
        if isinstance(findings, list):
            all_findings.extend(findings)

    # ── KPI row ────────────────────────────────────────────────────────────────
    avg_score      = _avg_score(reports)
    total_findings = sum(_get_field(r, "total_findings", 0) for r in reports)
    critical_count = sum(_get_field(r, "critical_findings", 0) for r in reports)
    docs_count     = len(st.session_state.get("uploaded_docs", []))

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi_card(
            "Compliance Score", f"{avg_score}%",
            "+4.2% this month", "up" if avg_score >= 60 else "down",
            "🛡️", "blue",
        )
    with c2:
        render_kpi_card(
            "Docs Analysed", str(docs_count),
            "This session", "neutral", "📄", "green",
        )
    with c3:
        render_kpi_card(
            "Total Findings", str(total_findings),
            "Across all audits", "neutral", "🔍", "yellow",
        )
    with c4:
        render_kpi_card(
            "Critical Issues", str(critical_count),
            "Require immediate action" if critical_count > 0 else "All clear",
            "down" if critical_count > 0 else "up",
            "🚨", "red",
        )

    st.markdown("")

    # ── Charts row 1 ───────────────────────────────────────────────────────────
    col_g, col_d, col_r = st.columns([1.2, 1, 1.8])

    with col_g:
        st.markdown('<div class="section-header">📊 Compliance Score</div>',
                    unsafe_allow_html=True)
        _render_score_gauge(avg_score)

    with col_d:
        st.markdown('<div class="section-header">🎯 Severity Breakdown</div>',
                    unsafe_allow_html=True)
        _render_severity_donut(all_findings)

    with col_r:
        st.markdown('<div class="section-header">🕸️ Framework Coverage</div>',
                    unsafe_allow_html=True)
        _render_framework_radar()

    # ── Charts row 2 ───────────────────────────────────────────────────────────
    col_t, col_dr = st.columns([1.5, 1])

    with col_t:
        st.markdown('<div class="section-header">📈 Compliance Trend</div>',
                    unsafe_allow_html=True)
        _render_trend_chart(reports)

    with col_dr:
        st.markdown('<div class="section-header">🏢 Department Risk</div>',
                    unsafe_allow_html=True)
        _render_dept_chart(all_findings)

    # ── Platform-wide stats (visible to all users) ─────────────────────────────
    _render_platform_stats()

    # ── Recent activity ────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">🕐 Recent Activity</div>',
                unsafe_allow_html=True)
    if reports:
        for r in reversed(reports[-5:]):
            # DB rows use created_at + framework; objects use generated_timestamp + framework_targeted
            ts    = _get_field(r, "generated_timestamp") or _get_field(r, "created_at") or ""
            score = _get_field(r, "compliance_score", 0) or 0
            fw    = _get_field(r, "framework_targeted") or _get_field(r, "framework") or ""
            total = _get_field(r, "total_findings", 0) or 0
            ts    = str(ts)
            st.markdown(f"""
            <div class="timeline-item">
              <span class="timeline-time">{ts[11:19] if len(ts) > 10 else ts}</span>
              <span class="timeline-text">
                Audit completed — <strong>{fw}</strong> |
                Score: <strong>{score:.0f}%</strong> |
                {total} finding(s)
              </span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("🔍 No audits yet. Upload a policy document on the **Policy Upload** page to get started.", icon="ℹ️")

    # ── Quick actions ──────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">⚡ Quick Actions</div>',
                unsafe_allow_html=True)
    qa1, qa2, qa3, qa4 = st.columns(4)
    with qa1:
        if st.button("📄 Upload Policy", width='stretch', type="secondary"):
            st.session_state["current_page"] = "Policy Upload"
            st.rerun()
    with qa2:
        if st.button("🔍 Run Audit", width='stretch', type="secondary"):
            st.session_state["current_page"] = "Compliance Auditor"
            st.rerun()
    with qa3:
        if st.button("📚 Knowledge Base", width='stretch', type="secondary"):
            st.session_state["current_page"] = "Knowledge Base"
            st.rerun()
    with qa4:
        if st.button("⚙️ Settings", width='stretch', type="secondary"):
            st.session_state["current_page"] = "Admin Settings"
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PLATFORM-WIDE STATS SECTION
# ══════════════════════════════════════════════════════════════════════════════

def _render_platform_stats() -> None:
    """Global platform statistics — visible to ALL users. Shows counts + charts."""
    st.markdown('<div class="section-header">🌐 Platform Statistics</div>',
                unsafe_allow_html=True)

    stats = _load_global_stats()

    total_audits   = stats.get("total_audits", 0)
    total_users    = stats.get("total_users", 0)
    total_docs     = stats.get("total_documents", 0)
    platform_score = stats.get("avg_compliance_score", 0.0)

    p1, p2, p3, p4 = st.columns(4)
    with p1:
        st.metric("🔍 Total Audits Run",    total_audits,              help="All audits ever run on the platform")
    with p2:
        st.metric("👥 Registered Users",    total_users,               help="Total registered accounts")
    with p3:
        st.metric("📄 Documents Uploaded",  total_docs,                help="Total documents uploaded platform-wide")
    with p4:
        st.metric("🛡️ Platform Avg Score", f"{platform_score:.1f}%",  help="Average compliance score across all audits")

    st.markdown("")

    col_fw, col_trend = st.columns([1, 1.4])
    with col_fw:
        st.markdown('<div class="section-header">📊 Audits by Framework</div>',
                    unsafe_allow_html=True)
        _render_global_framework_bar(stats.get("audits_by_framework", {}))

    with col_trend:
        st.markdown('<div class="section-header">📈 Audits Over Time</div>',
                    unsafe_allow_html=True)
        _render_global_trend(stats.get("audits_over_time", []))


def _load_global_stats() -> dict:
    """Load global stats from Supabase; fall back to session counts for local dev."""
    try:
        from database.database_manager import db_get_global_stats, is_configured
        if is_configured():
            return db_get_global_stats()
    except Exception:
        pass

    # Local fallback
    reports = st.session_state.get("audit_history", [])
    fw_counts: dict = {}
    date_counts: dict = {}
    for r in reports:
        fw = _get_field(r, "framework_targeted") or _get_field(r, "framework") or "Unknown"
        fw_counts[fw] = fw_counts.get(fw, 0) + 1
        ts = str(_get_field(r, "generated_timestamp") or _get_field(r, "created_at") or "")[:10]
        if ts:
            date_counts[ts] = date_counts.get(ts, 0) + 1

    scores = [_get_field(r, "compliance_score", 0) or 0 for r in reports]
    avg    = round(sum(scores) / len(scores), 1) if scores else 0.0

    return {
        "total_audits":         len(reports),
        "total_users":          1,
        "total_documents":      len(st.session_state.get("uploaded_docs", [])),
        "avg_compliance_score": avg,
        "platform_avg_score":   avg,
        "audits_by_framework":  fw_counts,
        "audits_over_time":     [
            {"date": d, "count": c}
            for d, c in sorted(date_counts.items())
        ],
    }


def _render_global_framework_bar(audits_by_framework: dict) -> None:
    try:
        import plotly.graph_objects as go

        if not audits_by_framework:
            st.info("No audits recorded yet.")
            return

        frameworks = list(audits_by_framework.keys())
        counts     = [audits_by_framework[fw] for fw in frameworks]
        palette    = {
            "GDPR":      "#3b7ff5",
            "HIPAA":     "#00e5a0",
            "ISO 27001": "#f5a623",
            "PCI-DSS":   "#ff4757",
            "SOC 2":     "#a78bfa",
        }
        colors = [palette.get(fw, "#8a9bbc") for fw in frameworks]

        fig = go.Figure(go.Bar(
            x=counts, y=frameworks, orientation="h",
            marker=dict(color=colors, opacity=0.9),
            text=counts, textposition="outside",
            textfont=dict(color="#e8edf8", size=12),
        ))
        fig.update_layout(**_layout(
            height=260, xaxis_title="Number of Audits", yaxis_title="",
            showlegend=False, margin=dict(l=10, r=40, t=10, b=10),
        ))
        st.plotly_chart(fig, width='stretch')
    except ImportError:
        for fw, cnt in audits_by_framework.items():
            st.metric(fw, cnt)


def _render_global_trend(audits_over_time: list) -> None:
    try:
        import plotly.graph_objects as go

        if not audits_over_time:
            st.info("No audit history to display yet.")
            return

        dates  = [item["date"]  for item in audits_over_time]
        counts = [item["count"] for item in audits_over_time]

        cumulative = []
        total = 0
        for c in counts:
            total += c
            cumulative.append(total)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=dates, y=counts, name="Daily Audits",
            marker=dict(color="rgba(59,127,245,0.4)"),
        ))
        fig.add_trace(go.Scatter(
            x=dates, y=cumulative, name="Cumulative",
            mode="lines+markers",
            line=dict(color="#00e5a0", width=2.5),
            marker=dict(size=6), yaxis="y2",
        ))
        fig.update_layout(**_layout(
            height=260, showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02,
                        xanchor="right", x=1, font=dict(color="#8a9bbc", size=11)),
            xaxis_title="",
            yaxis=dict(title="Daily", side="left"),
            yaxis2=dict(title="Cumulative", overlaying="y", side="right",
                        showgrid=False, tickfont=dict(color="#00e5a0")),
            margin=dict(l=10, r=50, t=30, b=10),
            barmode="overlay",
        ))
        st.plotly_chart(fig, width='stretch')
    except ImportError:
        for item in audits_over_time[-5:]:
            st.write(f"{item['date']}: {item['count']} audit(s)")


# ══════════════════════════════════════════════════════════════════════════════
# CHART HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _avg_score(reports: list) -> float:
    if not reports:
        return 0.0
    scores = [_get_field(r, "compliance_score", 0) or 0 for r in reports]
    return round(sum(scores) / len(scores), 1)


def _render_score_gauge(score: float) -> None:
    try:
        import plotly.graph_objects as go

        color = score_color(score)
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=score,
            domain={"x": [0, 1], "y": [0, 1]},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#4a5a78"},
                "bar":  {"color": color, "thickness": 0.3},
                "bgcolor": "#161f35",
                "bordercolor": "rgba(59,127,245,0.2)",
                "steps": [
                    {"range": [0, 40],   "color": "rgba(255,71,87,0.08)"},
                    {"range": [40, 65],  "color": "rgba(255,200,71,0.08)"},
                    {"range": [65, 85],  "color": "rgba(59,127,245,0.08)"},
                    {"range": [85, 100], "color": "rgba(0,229,160,0.08)"},
                ],
            },
            number={"suffix": "%", "font": {"family": "Syne", "color": color, "size": 36}},
        ))
        fig.update_layout(**_layout(height=220, margin=dict(l=20, r=20, t=20, b=10)))
        st.plotly_chart(fig, width='stretch')

        level = risk_level(score)
        st.markdown(
            f'<div style="text-align:center;font-size:0.85rem;color:{color};'
            f'font-weight:700;margin-top:-10px;">{level}</div>',
            unsafe_allow_html=True,
        )
    except ImportError:
        st.metric("Compliance Score", f"{score}%")


def _render_severity_donut(findings: list) -> None:
    try:
        import plotly.graph_objects as go
        from config.constants import PLOTLY_DARK, SEVERITY_COLORS

        counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
        for f in findings:
            # findings may be dicts or objects
            sev = (f.get("severity") if isinstance(f, dict) else getattr(f, "severity", "Medium")) or "Medium"
            counts[sev] = counts.get(sev, 0) + 1

        labels = [k for k, v in counts.items() if v > 0]
        values = [v for v in counts.values() if v > 0]
        colors = [SEVERITY_COLORS.get(l, "#8a9bbc") for l in labels]

        if not values:
            st.info("No findings yet.")
            return

        fig = go.Figure(go.Pie(
            labels=labels, values=values, hole=0.65,
            marker=dict(colors=colors, line=dict(color="#0a0e1a", width=2)),
            textinfo="label+value",
            textfont=dict(family="DM Sans", size=11, color="#e8edf8"),
        ))
        fig.update_layout(**_layout(height=220, showlegend=False,
                          margin=dict(l=10, r=10, t=10, b=10)))
        st.plotly_chart(fig, width='stretch')
    except ImportError:
        for sev, cnt in {"Critical": 0, "High": 0}.items():
            st.metric(sev, cnt)


def _render_framework_radar() -> None:
    try:
        import plotly.graph_objects as go

        reports   = st.session_state.get("audit_history", [])
        labels    = ["GDPR", "ISO 27001", "HIPAA", "SOC 2", "PCI-DSS"]
        fw_scores = {fw: [] for fw in labels}

        for r in reports:
            fw = _get_field(r, "framework_targeted") or _get_field(r, "framework") or ""
            if fw in fw_scores:
                fw_scores[fw].append(_get_field(r, "compliance_score", 0) or 0)

        values = [
            round(sum(v) / len(v), 1) if v else 50.0
            for v in fw_scores.values()
        ]
        values_closed = values + [values[0]]
        labels_closed = labels + [labels[0]]

        fig = go.Figure(go.Scatterpolar(
            r=values_closed, theta=labels_closed, fill="toself",
            fillcolor="rgba(59,127,245,0.15)",
            line=dict(color="#3b7ff5", width=2),
        ))
        fig.update_layout(**_layout(
            height=260,
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(range=[0, 100], visible=True,
                                gridcolor="rgba(59,127,245,0.15)",
                                tickfont=dict(size=9, color="#4a5a78")),
                angularaxis=dict(gridcolor="rgba(59,127,245,0.12)",
                                 tickfont=dict(size=10, color="#8a9bbc")),
            ),
            margin=dict(l=40, r=40, t=20, b=20),
        ))
        st.plotly_chart(fig, width='stretch')
    except ImportError:
        st.info("Install plotly for charts.")


def _render_trend_chart(reports: list) -> None:
    try:
        import plotly.graph_objects as go

        if not reports:
            st.info("Run audits to see the compliance trend.")
            return

        dates  = [str(_get_field(r, "generated_timestamp") or _get_field(r, "created_at") or "")[:10] for r in reports]
        scores = [_get_field(r, "compliance_score", 0) or 0 for r in reports]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates, y=scores, mode="lines+markers",
            line=dict(color="#3b7ff5", width=2.5),
            marker=dict(color="#3b7ff5", size=7),
            fill="tozeroy", fillcolor="rgba(59,127,245,0.08)",
            name="Score",
        ))
        fig.update_layout(**_layout(
            height=240, xaxis_title="", yaxis_title="Score (%)",
            yaxis=dict(range=[0, 105]), showlegend=False,
        ))
        st.plotly_chart(fig, width='stretch')
    except ImportError:
        st.info("Install plotly for trend chart.")


def _render_dept_chart(findings: list) -> None:
    try:
        import plotly.graph_objects as go

        if not findings:
            st.info("No findings to display.")
            return

        dept_counts: dict = {}
        for f in findings:
            dept = (f.get("department") if isinstance(f, dict) else getattr(f, "department", "General")) or "General"
            dept_counts[dept] = dept_counts.get(dept, 0) + 1

        depts  = list(dept_counts.keys())[:8]
        counts = [dept_counts[d] for d in depts]

        fig = go.Figure(go.Bar(
            x=counts, y=depts, orientation="h",
            marker=dict(color="#3b7ff5", opacity=0.85),
            text=counts, textposition="outside",
        ))
        fig.update_layout(**_layout(
            height=240, xaxis_title="Findings", yaxis_title="",
            showlegend=False, margin=dict(l=10, r=30, t=10, b=10),
        ))
        st.plotly_chart(fig, width='stretch')
    except ImportError:
        for dept, cnt in list({"Engineering": 0}.items()):
            st.metric(dept, cnt)