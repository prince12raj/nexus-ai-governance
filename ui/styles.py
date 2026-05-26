"""
ui/styles.py — Enterprise CSS for Nexus AI Governance Platform.
Injected via st.markdown(ENTERPRISE_CSS, unsafe_allow_html=True) in app.py.
"""

ENTERPRISE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500;600&family=DM+Mono&display=swap');

:root {
  --bg-primary:    #0a0e1a;
  --bg-secondary:  #0f1628;
  --bg-card:       #111827;
  --bg-elevated:   #161f35;
  --border:        rgba(59,127,245,0.12);
  --border-bright: rgba(59,127,245,0.3);
  --text-primary:  #e8edf8;
  --text-secondary:#8a9bbc;
  --text-muted:    #4a5a78;
  --accent-blue:   #3b7ff5;
  --accent-cyan:   #00d4ff;
  --accent-green:  #00e5a0;
  --accent-yellow: #ffc847;
  --accent-red:    #ff4757;
  --accent-purple: #9b59ff;
  --shadow:        0 4px 24px rgba(0,0,0,0.4);
  --shadow-glow:   0 0 40px rgba(59,127,245,0.06);
}

/* ── Global ───────────────────────────────────────────────────────────────── */
html, body, .stApp { background-color: var(--bg-primary) !important; color: var(--text-primary) !important; font-family: 'DM Sans', sans-serif; }
* { box-sizing: border-box; }
h1,h2,h3,h4 { font-family: 'Syne', sans-serif !important; color: var(--text-primary) !important; }

/* ── Sidebar ──────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] { background: var(--bg-secondary) !important; border-right: 1px solid var(--border) !important; }
[data-testid="stSidebar"] * { color: var(--text-secondary) !important; }

/* ── Buttons ──────────────────────────────────────────────────────────────── */
.stButton > button { background: linear-gradient(135deg, var(--accent-blue), #2563eb) !important; color: white !important; border: none !important; border-radius: 8px !important; font-family: 'DM Sans', sans-serif !important; font-weight: 600 !important; transition: all 0.2s !important; }
.stButton > button:hover { transform: translateY(-1px) !important; opacity: 0.92 !important; }
.stButton > button[kind="secondary"] { background: var(--bg-elevated) !important; border: 1px solid var(--border) !important; color: var(--text-secondary) !important; }

/* ── Inputs ───────────────────────────────────────────────────────────────── */
.stTextInput > div > div > input, .stTextArea > div > div > textarea, .stSelectbox > div > div > div { background: var(--bg-elevated) !important; border: 1px solid var(--border) !important; border-radius: 8px !important; color: var(--text-primary) !important; font-family: 'DM Sans', sans-serif !important; }
.stTextInput > div > div > input:focus, .stTextArea > div > div > textarea:focus { border-color: var(--accent-blue) !important; box-shadow: 0 0 0 2px rgba(59,127,245,0.15) !important; }

/* ── Tabs ─────────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] { background: transparent !important; border-bottom: 1px solid var(--border) !important; gap: 4px; }
.stTabs [data-baseweb="tab"] { background: transparent !important; color: var(--text-secondary) !important; border: none !important; border-radius: 8px 8px 0 0 !important; padding: 0.6rem 1.2rem !important; font-family: 'DM Sans', sans-serif !important; font-weight: 500 !important; }
.stTabs [aria-selected="true"] { background: rgba(59,127,245,0.1) !important; color: var(--accent-blue) !important; }

/* ── Metrics ──────────────────────────────────────────────────────────────── */
[data-testid="metric-container"] { background: var(--bg-card) !important; border: 1px solid var(--border) !important; border-radius: 12px !important; padding: 1rem !important; }
[data-testid="metric-container"] label { color: var(--text-secondary) !important; font-size: 0.8rem !important; text-transform: uppercase !important; letter-spacing: 0.05em !important; }
[data-testid="metric-container"] [data-testid="stMetricValue"] { color: var(--text-primary) !important; font-family: 'Syne', sans-serif !important; font-size: 2rem !important; font-weight: 700 !important; }

/* ── Progress ─────────────────────────────────────────────────────────────── */
.stProgress > div > div > div { background: linear-gradient(90deg, var(--accent-blue), var(--accent-cyan)) !important; border-radius: 4px !important; }

/* ── Alerts ───────────────────────────────────────────────────────────────── */
.stInfo    { background: rgba(59,127,245,0.1)  !important; border-left: 3px solid var(--accent-blue)   !important; }
.stWarning { background: rgba(255,200,71,0.1)  !important; border-left: 3px solid var(--accent-yellow) !important; }
.stError   { background: rgba(255,71,87,0.1)   !important; border-left: 3px solid var(--accent-red)    !important; }
.stSuccess { background: rgba(0,229,160,0.1)   !important; border-left: 3px solid var(--accent-green)  !important; }

hr { border: none !important; border-top: 1px solid var(--border) !important; margin: 1.5rem 0 !important; }
code, pre { font-family: 'DM Mono', monospace !important; background: rgba(0,0,0,0.4) !important; color: var(--accent-cyan) !important; border-radius: 6px !important; border: 1px solid var(--border) !important; }

/* ── Layout components ────────────────────────────────────────────────────── */
.nexus-header { background: linear-gradient(135deg,#0f1628 0%,#131d35 50%,#0a0e1a 100%); border: 1px solid var(--border); border-radius: 16px; padding: 1.8rem 2rem; margin-bottom: 1.5rem; position: relative; overflow: hidden; }
.nexus-header::before { content:''; position:absolute; top:0;left:0;right:0; height:2px; background:linear-gradient(90deg,transparent,var(--accent-blue),var(--accent-cyan),transparent); }
.nexus-header-title { font-family:'Syne',sans-serif; font-size:1.6rem; font-weight:800; color:var(--text-primary); letter-spacing:-0.02em; margin:0; }
.nexus-header-subtitle { font-size:0.85rem; color:var(--text-secondary); margin:0.3rem 0 0 0; }
.nexus-badge { display:inline-block; background:rgba(59,127,245,0.15); border:1px solid rgba(59,127,245,0.4); color:var(--accent-blue); font-size:0.72rem; font-weight:600; letter-spacing:0.08em; text-transform:uppercase; padding:3px 10px; border-radius:20px; margin-left:0.8rem; vertical-align:middle; }

.kpi-card { background:var(--bg-card); border:1px solid var(--border); border-radius:14px; padding:1.4rem 1.6rem; transition:all 0.2s; position:relative; overflow:hidden; }
.kpi-card::after { content:''; position:absolute; bottom:0;left:0;right:0; height:2px; opacity:0; transition:opacity 0.2s; }
.kpi-card:hover { border-color:var(--border-bright); transform:translateY(-2px); }
.kpi-card:hover::after { opacity:1; }
.kpi-card.blue::after  { background:var(--accent-blue); }
.kpi-card.green::after { background:var(--accent-green); }
.kpi-card.red::after   { background:var(--accent-red); }
.kpi-card.yellow::after{ background:var(--accent-yellow); }
.kpi-label { font-size:0.72rem; font-weight:600; letter-spacing:0.08em; text-transform:uppercase; color:var(--text-muted); margin-bottom:0.4rem; }
.kpi-value { font-family:'Syne',sans-serif; font-size:2.2rem; font-weight:800; color:var(--text-primary); line-height:1; }
.kpi-delta { font-size:0.78rem; margin-top:0.4rem; display:flex; align-items:center; gap:4px; }
.kpi-delta.up   { color:var(--accent-green); }
.kpi-delta.down { color:var(--accent-red); }
.kpi-delta.neutral { color:var(--text-muted); }
.kpi-icon { position:absolute; top:1.2rem;right:1.4rem; font-size:1.6rem; opacity:0.35; }

.finding-card { background:var(--bg-card); border:1px solid var(--border); border-radius:12px; padding:1.4rem; margin:0.8rem 0; position:relative; }
.finding-card.critical { border-left:4px solid var(--accent-red); }
.finding-card.high     { border-left:4px solid var(--accent-yellow); }
.finding-card.medium   { border-left:4px solid var(--accent-blue); }
.finding-card.low      { border-left:4px solid var(--accent-green); }

.severity-badge { display:inline-block; font-size:0.7rem; font-weight:700; letter-spacing:0.06em; text-transform:uppercase; padding:3px 10px; border-radius:20px; }
.severity-badge.critical { background:rgba(255,71,87,0.15);  color:var(--accent-red);    border:1px solid rgba(255,71,87,0.3);  }
.severity-badge.high     { background:rgba(255,200,71,0.15); color:var(--accent-yellow); border:1px solid rgba(255,200,71,0.3); }
.severity-badge.medium   { background:rgba(59,127,245,0.15); color:var(--accent-blue);   border:1px solid rgba(59,127,245,0.3); }
.severity-badge.low      { background:rgba(0,229,160,0.15);  color:var(--accent-green);  border:1px solid rgba(0,229,160,0.3);  }

.score-banner { background:var(--bg-card); border:1px solid var(--border); border-radius:16px; padding:2rem; text-align:center; margin:1rem 0; }
.score-number { font-family:'Syne',sans-serif; font-size:5rem; font-weight:800; line-height:1; }
.score-label  { font-size:0.85rem; letter-spacing:0.1em; text-transform:uppercase; color:var(--text-secondary); margin-top:0.5rem; }

.agent-row  { display:flex; align-items:center; gap:12px; padding:0.8rem 1rem; background:var(--bg-card); border:1px solid var(--border); border-radius:8px; margin:4px 0; }
.agent-dot  { width:10px;height:10px;border-radius:50%;flex-shrink:0; }
.agent-dot.running { background:var(--accent-blue);  animation:pulse 1.2s infinite; }
.agent-dot.done    { background:var(--accent-green); }
.agent-dot.idle    { background:var(--text-muted);   }
.agent-dot.error   { background:var(--accent-red);   }
@keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.5;transform:scale(0.7)} }
.agent-name  { font-weight:600;font-size:0.88rem;color:var(--text-primary); }
.agent-status-text { font-size:0.78rem;color:var(--text-secondary);margin-left:auto; }

.timeline-item { display:flex;gap:14px;padding:0.6rem 0;border-left:2px solid var(--border);margin-left:8px;padding-left:20px;position:relative; }
.timeline-item::before { content:'';position:absolute;left:-5px;top:12px;width:8px;height:8px;border-radius:50%;background:var(--accent-blue); }
.timeline-time { font-size:0.72rem;color:var(--text-muted);min-width:80px; }
.timeline-text { font-size:0.82rem;color:var(--text-secondary); }

.profile-card { background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:1.2rem;margin:0.5rem; }
.avatar-circle { width:48px;height:48px;border-radius:50%;background:linear-gradient(135deg,var(--accent-blue),var(--accent-purple));display:flex;align-items:center;justify-content:center;font-family:'Syne',sans-serif;font-weight:700;font-size:1.1rem;color:white;margin-bottom:0.8rem; }
.profile-name { font-weight:700;font-size:0.95rem;color:var(--text-primary); }
.profile-role { font-size:0.72rem;letter-spacing:0.06em;text-transform:uppercase;color:var(--accent-blue);margin:2px 0; }
.profile-dept { font-size:0.78rem;color:var(--text-secondary); }

.status-chip { display:inline-flex;align-items:center;gap:5px;font-size:0.72rem;font-weight:600;letter-spacing:0.04em;padding:4px 10px;border-radius:20px; }
.status-chip.online  { background:rgba(0,229,160,0.12); color:var(--accent-green);  border:1px solid rgba(0,229,160,0.25);  }
.status-chip.warning { background:rgba(255,200,71,0.12); color:var(--accent-yellow); border:1px solid rgba(255,200,71,0.25); }
.status-chip.offline { background:rgba(255,71,87,0.12);  color:var(--accent-red);    border:1px solid rgba(255,71,87,0.25);  }

.login-container { max-width:460px;margin:0 auto;padding:2.5rem;background:var(--bg-card);border:1px solid var(--border);border-radius:20px;box-shadow:var(--shadow),var(--shadow-glow);position:relative;overflow:hidden; }
.login-container::before { content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,var(--accent-blue),var(--accent-cyan),var(--accent-purple)); }
.login-logo { font-family:'Syne',sans-serif;font-size:1.8rem;font-weight:800;text-align:center;margin-bottom:0.3rem; }
.login-logo span { color:var(--accent-blue); }
.login-tagline { text-align:center;font-size:0.8rem;color:var(--text-secondary);margin-bottom:2rem;letter-spacing:0.04em; }
.demo-creds { background:rgba(59,127,245,0.06);border:1px solid rgba(59,127,245,0.15);border-radius:8px;padding:0.8rem 1rem;font-size:0.77rem;color:var(--text-secondary);margin-top:1rem; }
.demo-creds code { color:var(--accent-cyan);font-size:0.77rem; }

.reg-card { background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:1.4rem;margin:0.6rem 0;transition:border-color 0.2s; }
.reg-card:hover { border-color:var(--border-bright); }
.reg-title   { font-weight:700;font-size:0.95rem;color:var(--text-primary);margin-bottom:0.4rem; }
.reg-citation{ font-size:0.75rem;color:var(--accent-blue);font-family:'DM Mono',monospace;margin-bottom:0.6rem; }
.reg-text    { font-size:0.82rem;color:var(--text-secondary);line-height:1.6; }

.exec-summary { background:linear-gradient(135deg,rgba(59,127,245,0.06),rgba(0,212,255,0.04)); border:1px solid rgba(59,127,245,0.2); border-radius:12px; padding:1.5rem; margin:1rem 0; }
.exec-summary-title { font-family:'Syne',sans-serif;font-weight:700;font-size:0.95rem;color:var(--accent-cyan);margin-bottom:0.8rem;letter-spacing:0.02em; }
.exec-summary-text  { font-size:0.88rem;color:var(--text-secondary);line-height:1.7; }

.pii-alert { background:rgba(255,71,87,0.08);border:1px solid rgba(255,71,87,0.25);border-radius:10px;padding:1rem 1.2rem;margin:0.5rem 0;font-size:0.84rem;color:var(--text-secondary); }
.pii-alert-title { font-weight:700;color:var(--accent-red);margin-bottom:0.3rem;font-size:0.88rem; }
.injection-alert { background:rgba(155,89,255,0.08);border:1px solid rgba(155,89,255,0.25);border-radius:10px;padding:1rem 1.2rem;margin:0.5rem 0;font-size:0.84rem;color:var(--text-secondary); }
.injection-alert-title { font-weight:700;color:var(--accent-purple);margin-bottom:0.3rem;font-size:0.88rem; }

.fix-card { background:rgba(0,229,160,0.06);border:1px solid rgba(0,229,160,0.2);border-radius:10px;padding:1rem 1.2rem;margin:0.5rem 0; }
.fix-card-title { font-weight:700;color:var(--accent-green);margin-bottom:0.3rem;font-size:0.85rem; }
.fix-card-text  { font-size:0.84rem;color:var(--text-secondary);line-height:1.6; }

.gradient-text { background:linear-gradient(135deg,var(--accent-blue),var(--accent-cyan)); -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; }
.section-header { font-family:'Syne',sans-serif;font-size:1.15rem;font-weight:700;color:var(--text-primary);margin:1.5rem 0 0.8rem 0;letter-spacing:-0.01em; }
.report-card { background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:1.4rem;margin:0.6rem 0;transition:border-color 0.2s;cursor:pointer; }
.report-card:hover { border-color:var(--border-bright); }
.governance-card { background:linear-gradient(135deg,rgba(155,89,255,0.06),rgba(59,127,245,0.04));border:1px solid rgba(155,89,255,0.2);border-radius:14px;padding:1.6rem;margin:1rem 0; }
.nav-item { display:flex;align-items:center;gap:10px;padding:0.65rem 1rem;border-radius:8px;margin:2px 8px;cursor:pointer;transition:all 0.15s;font-size:0.88rem;font-weight:500;color:var(--text-secondary); }
.nav-item:hover  { background:rgba(59,127,245,0.08);color:var(--text-primary); }
.nav-item.active { background:rgba(59,127,245,0.15);color:var(--accent-blue);  }
</style>
"""


def card(content: str, color: str = "blue") -> str:
    """Return an HTML KPI card string."""
    return f'<div class="kpi-card {color}">{content}</div>'


def severity_badge(severity: str) -> str:
    """Return an HTML severity badge."""
    return f'<span class="severity-badge {severity.lower()}">{severity}</span>'


def status_chip(label: str, status: str = "online") -> str:
    """Return an HTML status chip."""
    return f'<span class="status-chip {status}">● {label}</span>'


def section_header(title: str) -> str:
    """Return an HTML section header."""
    return f'<div class="section-header">{title}</div>'