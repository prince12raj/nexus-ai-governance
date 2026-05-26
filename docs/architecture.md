# Architecture — Nexus AI Governance Platform

## Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Frontend (ui/)                  │
│  Dashboard │ Upload │ Auditor │ Risk │ KB │ Reports │ Admin  │
└──────────────────────────┬──────────────────────────────────┘
                           │
              ┌────────────▼────────────┐
              │     app.py (router)      │
              └────────────┬────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼─────┐      ┌─────▼──────┐   ┌──────▼──────┐
   │  auth/   │      │ compliance/│   │  analytics/ │
   │ Login    │      │ Engine     │   │  Charts     │
   │ Roles    │      │ PII Guard  │   │  Metrics    │
   │ Sessions │      │ Injection  │   │  Trends     │
   └──────────┘      │ Scoring    │   └─────────────┘
                     └─────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼────┐  ┌────▼───┐  ┌────▼────┐
        │  models/ │  │  rag/  │  │database/│
        │ Finding  │  │ Corpus │  │ Memory  │
        │ Audit    │  │ Chunk  │  │ FAISS   │
        │ Decision │  │        │  │ Chroma  │
        └──────────┘  └────────┘  └─────────┘
```

## Data Flow

1. **Upload** → `ingestion/parser.py` extracts text from PDF/DOCX/TXT
2. **PII Scan** → `compliance/pii_detector.py` runs regex patterns
3. **Injection Check** → `compliance/injection_detector.py` guards against adversarial input
4. **RAG Retrieval** → `database/memory_store.py` fetches relevant regulations
5. **LLM Analysis** → `compliance/compliance_engine.py` calls OpenAI or mock
6. **Scoring** → `compliance/scoring.py` calculates 0–100 compliance score
7. **Reporting** → `models/audit_models.py` assembles `AuditReport`
8. **Export** → `exports/` generates PDF or CSV artefacts
