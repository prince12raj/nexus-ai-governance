"""
analytics/charts.py — Plotly chart factory functions.
"""
from __future__ import annotations

import datetime
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from config.constants import PLOTLY_DARK
from models.finding_models import Finding


# ── Gauge ─────────────────────────────────────────────────────────────────────

def create_compliance_gauge(score: float) -> go.Figure:
    color = "#00e5a0" if score >= 80 else "#ffc847" if score >= 60 else "#ff4757"
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"suffix": "%", "font": {"size": 36, "color": color, "family": "Syne"}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#4a5a78",
                     "tickfont": {"color": "#4a5a78", "size": 11}},
            "bar": {"color": color, "thickness": 0.25},
            "bgcolor": "#0f1628",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 40],   "color": "rgba(255,71,87,0.08)"},
                {"range": [40, 70],  "color": "rgba(255,200,71,0.08)"},
                {"range": [70, 100], "color": "rgba(0,229,160,0.08)"},
            ],
            "threshold": {"line": {"color": color, "width": 3}, "thickness": 0.8, "value": score},
        },
    ))
    fig.update_layout(**PLOTLY_DARK, height=260)
    return fig


# ── Donut ─────────────────────────────────────────────────────────────────────

def create_severity_donut(findings: List[Finding]) -> go.Figure:
    counts: Dict[str, int] = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1

    labels = list(counts.keys())
    values = list(counts.values())
    colors = ["#ff4757", "#ffc847", "#3b7ff5", "#00e5a0"]

    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.68,
        marker=dict(colors=colors[:len(labels)], line=dict(color="#0f1628", width=2)),
        textinfo="label+value",
        textfont=dict(family="DM Sans", color="white", size=11),
        hovertemplate="<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>",
    ))
    fig.update_layout(**PLOTLY_DARK, height=260,
                      title=dict(text="Finding Severity", font=dict(size=14)))
    return fig


# ── Trend line ────────────────────────────────────────────────────────────────

def create_compliance_trend(history: List[Dict[str, Any]]) -> go.Figure:
    if len(history) < 2:
        np.random.seed(42)
        dates  = pd.date_range(end=datetime.date.today(), periods=12, freq="ME")
        scores = np.clip(np.cumsum(np.random.randn(12) * 3) + 62, 30, 98).tolist()
        history = [{"date": str(d.date()), "score": round(s, 1)}
                   for d, s in zip(dates, scores)]

    df  = pd.DataFrame(history)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["score"],
        mode="lines+markers",
        line=dict(color="#3b7ff5", width=2.5, shape="spline"),
        marker=dict(color="#3b7ff5", size=7, line=dict(color="#0f1628", width=2)),
        fill="tozeroy", fillcolor="rgba(59,127,245,0.07)",
        name="Compliance Score",
        hovertemplate="%{x}<br>Score: <b>%{y:.1f}</b><extra></extra>",
    ))
    fig.add_hline(y=80, line_dash="dash", line_color="rgba(0,229,160,0.4)",
                  annotation_text="Target 80")
    fig.update_layout(**PLOTLY_DARK, height=280,
                      title=dict(text="Compliance Score Trend",
                                 font=dict(size=14, color="#8a9bbc")),
                      yaxis=dict(range=[0, 105]))
    return fig


# ── Bar chart ─────────────────────────────────────────────────────────────────

def create_department_risk_chart(findings: List[Finding]) -> go.Figure:
    if not findings:
        dept_risk: Dict[str, float] = {
            "Engineering": 45, "Legal": 30, "Data": 25, "IT Security": 20, "Product": 15
        }
    else:
        dept_risk = {}
        sev_score = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
        for f in findings:
            dept_risk[f.department] = dept_risk.get(f.department, 0) + sev_score.get(f.severity, 1)

    depts  = list(dept_risk.keys())
    scores = list(dept_risk.values())
    colors = ["#ff4757" if s >= 4 else "#ffc847" if s >= 2 else "#3b7ff5" for s in scores]

    fig = go.Figure(go.Bar(
        x=scores, y=depts, orientation="h",
        marker=dict(color=colors, line=dict(color="#0f1628", width=1)),
        hovertemplate="<b>%{y}</b><br>Risk Score: %{x}<extra></extra>",
        text=scores, textposition="outside",
        textfont=dict(color="#8a9bbc", size=11),
    ))
    fig.update_layout(**PLOTLY_DARK, height=280,
                      title=dict(text="Department Risk Exposure",
                                 font=dict(size=14, color="#8a9bbc")),
                      xaxis_title="Risk Score")
    return fig


# ── Radar ─────────────────────────────────────────────────────────────────────

def create_framework_coverage_radar() -> go.Figure:
    categories = ["GDPR", "ISO 27001", "HIPAA", "SOC 2", "PCI-DSS"]
    current    = [72, 85, 58, 78, 65]
    target     = [90, 90, 85, 90, 80]

    fig = go.Figure()
    for vals, name, color, fill in [
        (target,  "Target",  "rgba(0,229,160,0.7)",  "rgba(0,229,160,0.05)"),
        (current, "Current", "rgba(59,127,245,0.8)", "rgba(59,127,245,0.15)"),
    ]:
        fig.add_trace(go.Scatterpolar(
            r=vals + [vals[0]], theta=categories + [categories[0]],
            fill="toself", fillcolor=fill,
            line=dict(color=color, width=2),
            name=name,
            hovertemplate="%{theta}: <b>%{r}%</b><extra></extra>",
        ))
    fig.update_layout(
        **PLOTLY_DARK, height=320,
        polar=dict(
            bgcolor="#0f1628",
            radialaxis=dict(visible=True, range=[0, 100],
                            gridcolor="rgba(59,127,245,0.1)",
                            tickfont=dict(color="#4a5a78", size=10),
                            tickcolor="rgba(59,127,245,0.1)"),
            angularaxis=dict(gridcolor="rgba(59,127,245,0.1)",
                             tickcolor="rgba(59,127,245,0.1)",
                             tickfont=dict(color="#8a9bbc", size=11)),
        ),
        title=dict(text="Framework Coverage", font=dict(size=14, color="#8a9bbc")),
        legend=dict(font=dict(color="#8a9bbc")),
    )
    return fig


# ── Confidence histogram ──────────────────────────────────────────────────────

def create_confidence_histogram(findings: List[Finding]) -> go.Figure:
    scores = [int(f.confidence_score * 100) for f in findings]
    fig = px.histogram(
        x=scores, nbins=20,
        color_discrete_sequence=["#3b7ff5"],
        labels={"x": "Confidence Score (%)"},
    )
    fig.update_layout(
        **PLOTLY_DARK, height=240, showlegend=False,
        title=dict(text="AI Confidence Distribution",
                   font=dict(size=14, color="#8a9bbc")),
    )
    return fig


# ── Framework bar ─────────────────────────────────────────────────────────────

def create_framework_bar(all_reports: list) -> go.Figure:
    from models.audit_models import AuditReport
    fw_scores: Dict[str, list] = {}
    for r in all_reports:
        fw = r.framework_targeted
        fw_scores.setdefault(fw, []).append(r.compliance_score)

    frameworks = list(fw_scores.keys())
    avg_scores  = [round(sum(v) / len(v), 1) for v in fw_scores.values()]
    colors      = ["#00e5a0" if s >= 80 else "#ffc847" if s >= 60 else "#ff4757"
                   for s in avg_scores]

    fig = go.Figure(go.Bar(
        x=frameworks, y=avg_scores,
        marker=dict(color=colors, line=dict(color="#0f1628", width=1)),
        text=[f"{s}%" for s in avg_scores], textposition="outside",
        textfont=dict(color="#8a9bbc", size=11),
        hovertemplate="<b>%{x}</b><br>Avg Score: %{y}%<extra></extra>",
    ))
    fig.update_layout(
        **PLOTLY_DARK, height=280,
        title=dict(text="Average Score by Framework",
                   font=dict(size=14, color="#8a9bbc")),
        yaxis=dict(range=[0, 110]),
    )
    return fig
