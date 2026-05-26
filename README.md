# ⚖️ Nexus AI Governance Platform — v2.0

> Enterprise-grade AI Policy Governance, Compliance & Agentic Risk Intelligence

![Python](https://img.shields.io/badge/Python-3.10%2B-blue) ![Streamlit](https://img.shields.io/badge/Streamlit-1.32%2B-red) ![License](https://img.shields.io/badge/License-MIT-green)

---

## 🚀 Quick Start

### 1 — Install dependencies

```bash
pip install -r requirements.txt
```

### 2 — Configure environment

```bash
python scripts/setup_env.py
# OR manually copy .env and fill in your OpenAI key
```

### 3 — Run

```bash
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

---

## 🔐 Demo Credentials

| Role             | Username     | Password       |
|------------------|-------------|----------------|
| Admin            | `admin`      | `Admin@2024!`  |
| Compliance Officer | `compliance` | `Comply@2024!` |
| Auditor          | `auditor`    | `Audit@2024!`  |

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
├── .env                      ← Environment config
├── config/                   ← Settings, constants, logging
├── auth/                     ← Login, sessions, roles
├── ui/                       ← All Streamlit page renderers
├── agents/                   ← Agent stubs (LangGraph v3.0)
├── rag/                      ← Chunking, regulations corpus
├── llm/                      ← LLM provider stubs
├── models/                   ← Pydantic schemas
├── ingestion/                ← File parsing (PDF, DOCX, TXT, CSV, JSON)
├── compliance/               ← PII, injection detection, engine, scoring
├── analytics/                ← Charts, metrics, trend analysis
├── database/                 ← Memory, FAISS, ChromaDB stores
├── utils/                    ← Helpers, validators, export utils
├── exports/                  ← PDF & CSV report exporters
├── tests/                    ← pytest test suite
├── docker/                   ← Dockerfile, docker-compose, nginx
├── scripts/                  ← Setup, seed, init scripts
└── docs/                     ← Architecture & API docs
```

---

## ✨ Features

- **Multi-framework compliance** — GDPR, ISO 27001, HIPAA, SOC 2, PCI-DSS
- **AI-powered analysis** — GPT-4o via OpenAI; deterministic mock for offline use
- **PII detection** — Email, SSN, phone, credit card, passport, NHS number, IBAN
- **Prompt injection guard** — 15 adversarial pattern detectors
- **Agentic risk pipeline** — 5-agent orchestration with human-in-the-loop
- **Interactive analytics** — Plotly dashboards, trend charts, radar coverage
- **Role-based access** — Admin, Compliance Officer, Auditor
- **PDF & CSV export** — Downloadable audit reports
- **Docker-ready** — Single-command deployment

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

---

## 📖 Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | _(blank)_ | OpenAI API key (blank = mock mode) |
| `OPENAI_MODEL` | `gpt-4o` | Primary model |
| `OLLAMA_HOST` | `http://localhost:11434` | Local LLM host |
| `APP_ENV` | `development` | `development` or `production` |
| `VECTOR_STORE_BACKEND` | `memory` | `memory`, `faiss`, or `chroma` |
| `ENABLE_PII_DETECTION` | `true` | Toggle PII scanning |
| `ENABLE_INJECTION_DETECTION` | `true` | Toggle injection guard |

---

## 📄 License

MIT — see [LICENSE](LICENSE) for details.
