"""
config/constants.py — Application-wide constants for Nexus AI Governance Platform.

All values here are STATIC — they never change at runtime.
For environment-driven values (API keys, paths, flags) use config/settings.py.

Import via the config package:
    from config import APP_NAME, SUPPORTED_FRAMEWORKS, SEVERITY_COLORS
"""
from __future__ import annotations

# ══════════════════════════════════════════════════════════════════════════════
# APP IDENTITY
# ══════════════════════════════════════════════════════════════════════════════

APP_NAME    = "Nexus AI Governance Platform"
APP_VERSION = "2.0.0"
APP_ICON    = "⚖️"
APP_TAGLINE = "Enterprise AI Policy Governance, Compliance & Agentic Risk Intelligence"


# ══════════════════════════════════════════════════════════════════════════════
# COMPLIANCE FRAMEWORKS
# ══════════════════════════════════════════════════════════════════════════════

SUPPORTED_FRAMEWORKS = [
    "GDPR",
    "ISO 27001",
    "HIPAA",
    "SOC 2",
    "PCI-DSS",
    "Combined Framework Mode",
]

FRAMEWORK_DESCRIPTIONS = {
    "GDPR":                   "EU General Data Protection Regulation",
    "ISO 27001":              "Information Security Management System",
    "HIPAA":                  "Health Insurance Portability and Accountability Act",
    "SOC 2":                  "System and Organisation Controls 2",
    "PCI-DSS":                "Payment Card Industry Data Security Standard",
    "Combined Framework Mode":"All frameworks analysed simultaneously",
}

FRAMEWORK_ICONS = {
    "GDPR":                   "🇪🇺",
    "ISO 27001":              "🔐",
    "HIPAA":                  "🏥",
    "SOC 2":                  "☁️",
    "PCI-DSS":                "💳",
    "Combined Framework Mode":"🔀",
}


# ══════════════════════════════════════════════════════════════════════════════
# SEVERITY LEVELS
# ══════════════════════════════════════════════════════════════════════════════

SEVERITIES = ["Critical", "High", "Medium", "Low"]

SEVERITY_SCORES = {
    "Critical": 4,
    "High":     3,
    "Medium":   2,
    "Low":      1,
}

SEVERITY_COLORS = {
    "Critical": "#ff4757",
    "High":     "#ffc847",
    "Medium":   "#3b7ff5",
    "Low":      "#00e5a0",
}

SEVERITY_ICONS = {
    "Critical": "🔴",
    "High":     "🟠",
    "Medium":   "🔵",
    "Low":      "🟢",
}

SEVERITY_DESCRIPTIONS = {
    "Critical": "Direct legal liability, regulatory fines, or active data breach risk",
    "High":     "Significant non-compliance that would fail a formal audit",
    "Medium":   "Partial compliance gap or best-practice shortfall",
    "Low":      "Minor wording issue or low-risk ambiguity",
}


# ══════════════════════════════════════════════════════════════════════════════
# LLM MODELS
# ══════════════════════════════════════════════════════════════════════════════

OPENAI_MODELS = [
    "GPT-4o",
    "GPT-4-Turbo",
    "GPT-3.5-Turbo",
]

LOCAL_ENGINES = [
    "Ollama",
    "LlamaCpp",
    "HuggingFace Transformers",
    "Disabled",
]

FALLBACK_MODELS = [
    "GPT-3.5-Turbo",
    "Llama 3 (Local)",
    "Mistral (Local)",
]

# All model options shown in the Admin Settings dropdown
ALL_MODEL_OPTIONS = OPENAI_MODELS + ["Mistral (HuggingFace)", "Llama 3 (Ollama)", "Mistral (Ollama)"]

# Embedding models
EMBEDDING_MODELS = {
    "openai":       "text-embedding-3-small",
    "huggingface":  "sentence-transformers/all-MiniLM-L6-v2",
    "ollama":       "nomic-embed-text",
}


# ══════════════════════════════════════════════════════════════════════════════
# RAG / CHUNKING
# ══════════════════════════════════════════════════════════════════════════════

DEFAULT_CHUNK_SIZE     = 800
DEFAULT_CHUNK_OVERLAP  = 100
DEFAULT_TOP_K          = 4
DEFAULT_MIN_CONFIDENCE = 0.70

# Vector store backend options
VECTOR_STORE_OPTIONS = ["memory", "faiss", "chroma"]


# ══════════════════════════════════════════════════════════════════════════════
# FILE UPLOAD
# ══════════════════════════════════════════════════════════════════════════════

ALLOWED_EXTENSIONS = [".pdf", ".docx", ".txt", ".csv", ".json"]
MAX_FILE_SIZE_MB   = 50

MIME_TYPES = {
    ".pdf":  "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt":  "text/plain",
    ".csv":  "text/csv",
    ".json": "application/json",
}


# ══════════════════════════════════════════════════════════════════════════════
# NAVIGATION
# ══════════════════════════════════════════════════════════════════════════════

NAV_PAGES = [
    ("🏠", "Dashboard"),
    ("📄", "Policy Upload"),
    ("🔍", "Compliance Auditor"),
    ("🤖", "Agentic Risk"),
    ("📚", "Knowledge Base"),
    ("📋", "Audit Reports"),
    ("📊", "Analytics"),
    ("⚙️",  "Admin Settings"),
]

# Page descriptions shown in sidebar tooltips
PAGE_DESCRIPTIONS = {
    "Dashboard":          "Overview of compliance posture and recent audits",
    "Policy Upload":      "Upload and manage policy documents",
    "Compliance Auditor": "Run AI-powered compliance audits",
    "Agentic Risk":       "AI system risk assessment and scoring",
    "Knowledge Base":     "Browse and search regulatory knowledge base",
    "Audit Reports":      "View, export, and share audit reports",
    "Analytics":          "Compliance trends and risk analytics",
    "Admin Settings":     "Configure LLM providers and platform settings",
}


# ══════════════════════════════════════════════════════════════════════════════
# PLOTLY DARK THEME
# ══════════════════════════════════════════════════════════════════════════════

PLOTLY_DARK = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans", color="#8a9bbc"),
    margin=dict(l=16, r=16, t=40, b=16),
    xaxis=dict(
        gridcolor="rgba(59,127,245,0.08)",
        showgrid=True,
        zeroline=False,
        linecolor="rgba(59,127,245,0.15)",
    ),
    yaxis=dict(
        gridcolor="rgba(59,127,245,0.08)",
        showgrid=True,
        zeroline=False,
        linecolor="rgba(59,127,245,0.15)",
    ),
)

# Severity bar colours for Plotly charts
PLOTLY_SEVERITY_COLORS = [
    SEVERITY_COLORS["Critical"],
    SEVERITY_COLORS["High"],
    SEVERITY_COLORS["Medium"],
    SEVERITY_COLORS["Low"],
]


# ══════════════════════════════════════════════════════════════════════════════
# AUTH / ROLES
# ══════════════════════════════════════════════════════════════════════════════

USER_ROLES = ["admin", "compliance_officer", "auditor", "viewer"]

ROLE_PERMISSIONS = {
    "admin":              ["read", "write", "audit", "export", "admin"],
    "compliance_officer": ["read", "write", "audit", "export"],
    "auditor":            ["read", "audit", "export"],
    "viewer":             ["read"],
}


# ══════════════════════════════════════════════════════════════════════════════
# COMPLIANCE RISK THRESHOLDS
# ══════════════════════════════════════════════════════════════════════════════

# Risk score = sum of SEVERITY_SCORES for all findings
RISK_THRESHOLDS = {
    "critical_risk": 20,   # score >= 20 → Critical Risk
    "high_risk":     10,   # score >= 10 → High Risk
    "medium_risk":   5,    # score >= 5  → Medium Risk
                           # score <  5  → Low Risk
}

RISK_LABELS = {
    "critical_risk": "Critical Risk",
    "high_risk":     "High Risk",
    "medium_risk":   "Medium Risk",
    "low_risk":      "Low Risk",
}

RISK_COLORS = {
    "critical_risk": "#ff4757",
    "high_risk":     "#ffc847",
    "medium_risk":   "#3b7ff5",
    "low_risk":      "#00e5a0",
}


# ══════════════════════════════════════════════════════════════════════════════
# AUDIT STATUS
# ══════════════════════════════════════════════════════════════════════════════

AUDIT_STATUSES = ["pending", "running", "complete", "failed"]

AUDIT_STATUS_COLORS = {
    "pending":  "#8a9bbc",
    "running":  "#3b7ff5",
    "complete": "#00e5a0",
    "failed":   "#ff4757",
}

AUDIT_STATUS_ICONS = {
    "pending":  "⏳",
    "running":  "🔄",
    "complete": "✅",
    "failed":   "❌",
}