# ⚖️ Nexus AI Governance Platform — v2.0

> Enterprise-grade AI Policy Governance, Compliance & Agentic Risk Intelligence

![Python](https://img.shields.io/badge/Python-3.11%2B-blue) ![Streamlit](https://img.shields.io/badge/Streamlit-1.32%2B-red) ![License](https://img.shields.io/badge/License-MIT-green)

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://your-app.streamlit.app)

---

## 🚀 Quick Start

### 1 — Install dependencies

```bash
pip install -r requirements.txt
```

### 2 — Configure environment

```bash
# Copy the template and fill in your API keys
cp .env .env.local
# Edit .env and add your OPENAI_API_KEY
```

### 3 — Run

```bash
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

---

## 🔐 First Login

This platform uses **registered accounts only** — no shared demo credentials.

1. Open the app and click **"✨ Create New Account"**
2. Fill in your details and choose your role
3. Roles requiring a secret key:

| Role | Secret Key Required |
|------|-------------------|
| Admin | ✅ Contact platform owner |
| Developer | ✅ Contact platform owner |
| Compliance Officer | ❌ No key needed |
| Auditor | ❌ No key needed |
| Viewer | ❌ No key needed |

---

## 🐳 Docker

```bash
cd docker
docker compose up --build
```

Access at **http://localhost**

---

## 🗂 Project Structure

```
nexus-ai-governance/
├── app.py                    ← Main entry point
├── requirements.txt
├── .env                      ← Environment config (never commit)
├── .streamlit/
│   ├── config.toml           ← Theme & server settings
│   └── secrets.toml          ← API keys for Streamlit Cloud (never commit)
├── config/                   ← Settings, constants, logging
├── auth/                     ← Login, registration, sessions, roles
│   ├── login.py
│   ├── register.py
│   ├── session_manager.py
│   ├── user_store.py         ← Persistent JSON user database
│   ├── roles.py
│   └── security.py
├── ui/                       ← All Streamlit page renderers
├── agents/                   ← Governance, risk, remediation agents
├── rag/                      ← Chunking, embeddings, regulations corpus
├── llm/                      ← OpenAI, HuggingFace, Ollama providers
├── models/                   ← Pydantic data models
├── compliance/               ← PII detection, injection guard, scoring
├── analytics/                ← Charts, metrics, trend analysis
├── database/                 ← Memory, FAISS, ChromaDB vector stores
├── utils/                    ← Helpers, validators, export utils
├── exports/                  ← PDF & CSV report exporters
├── tests/                    ← pytest test suite
├── docker/                   ← Dockerfile, docker-compose, nginx
├── scripts/                  ← Setup, seed, init scripts
├── data/                     ← User database & vector cache (never commit)
│   ├── users.json            ← Registered users (auto-created)
│   └── vector_cache/         ← FAISS / ChromaDB index files
└── logs/                     ← Application logs (never commit)
```

---

## ✨ Features

- **Multi-framework compliance** — GDPR, ISO 27001, HIPAA, SOC 2, PCI-DSS
- **AI-powered analysis** — GPT-4o via OpenAI; HuggingFace & Ollama supported
- **PII detection** — 22 pattern types: email, SSN, phone, card, passport, NHS, IBAN
- **Prompt injection guard** — 30 adversarial pattern detectors across 6 categories
- **Agentic risk pipeline** — 5-agent orchestration with NIST RMF & EU AI Act alignment
- **Interactive analytics** — Plotly dashboards, trend charts, radar coverage
- **Role-based access** — Admin, Developer, Compliance Officer, Auditor, Viewer
- **Persistent user accounts** — Registration with secret-key protected roles
- **PDF & CSV export** — Downloadable audit reports
- **Docker-ready** — Single-command deployment

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

---

## ☁️ Streamlit Cloud Deployment

1. Push repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo → select `app.py`
4. Add secrets in **Advanced Settings**:

```toml
OPENAI_API_KEY = "sk-your-key"
HUGGINGFACE_API_KEY = "hf-your-key"
APP_SECRET_KEY = "your-32-char-secret"
APP_ENV = "production"
VECTOR_STORE_BACKEND = "memory"
```

5. Click **Deploy**

---

## 📖 Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | _(blank)_ | OpenAI API key — blank = mock mode |
| `OPENAI_MODEL` | `gpt-4o` | Primary LLM model |
| `HUGGINGFACE_API_KEY` | _(blank)_ | HuggingFace API key |
| `OLLAMA_HOST` | `http://localhost:11434` | Local Ollama server |
| `APP_ENV` | `development` | `development` or `production` |
| `APP_SECRET_KEY` | _(change me)_ | Session encryption key |
| `VECTOR_STORE_BACKEND` | `memory` | `memory`, `faiss`, or `chroma` |
| `ENABLE_PII_DETECTION` | `true` | Toggle PII scanning |
| `ENABLE_INJECTION_DETECTION` | `true` | Toggle injection guard |

---

## 🔒 Security Notes

- All user passwords are hashed — never stored in plain text
- API keys must be set via `.env` (local) or Streamlit secrets (cloud)
- Never commit `.env`, `secrets.toml`, `data/users.json`, or `logs/` to Git
- Admin and Developer roles are protected by secret keys

---

## 📄 License

MIT — see [LICENSE](LICENSE) for details.