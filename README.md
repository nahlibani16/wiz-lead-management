
# WIZ.ai Take-Home Assignment: AI-Assisted Mini Lead Management System

Backend service powered by FastAPI and SQLite to ingest, clean, search, deduplicate, and enrich marketing/sales leads. Built as a scoped-down system evaluating scalable hybrid AI workflows for CRM data resolution.

---

## Architectural Overview & Design Decisions

### 1. Storage Choice (SQLite)
We selected **SQLite** (`leads.db`) paired with **SQLAlchemy 2.0 ORM**. Given the dataset scale (~2,000 records), SQLite provides a zero-setup, lightweight, and highly portable solution that simplifies evaluation without requiring external container dependencies, while maintaining robust schema validation and query filtering capabilities.

### 2. Scalable AI Lead Deduplication Strategy (2-Step Hybrid Pipeline)
Running pair-wise comparisons using LLMs across ~2,000 raw lead entries requires ~4,000,000 comparisons (2000 × 2000), which is cost-prohibitive and introduces massive latency. To keep deduplication tractable and performant:
1. **Candidate Generation (Blocking / Heuristic Pre-filter):** Lightweight string matching (Levenshtein distance ratio via `thefuzz`), email domain checks, and cleaned phone digit extraction narrow millions of potential combinations down to <50 high-probability duplicate candidate pairs.
2. **LLM Evaluation & Scoring:** Only surviving candidate pairs are passed to `gpt-4o-mini` (with rule-based fallback if API keys are absent). The LLM evaluates complex typos, legal entity suffixes ("Pte Ltd" vs "Inc"), and contextual details to return structured confidence scores (0.0–1.0) and human-readable reasoning.

### 3. AI Source Extraction
Extracted marketing channels and contextual details from raw, unstructured free-text `Notes` using LLM Structured Outputs (JSON Schema) mapped strictly to defined channels (`Website`, `Event`, `LinkedIn`, `Organic Search`, `Referral`, `Manual/Sales`, `Other`). A deterministic keyword/regex fallback mechanism handles network or API quota errors seamlessly.

---
## Project Structure

```text
wiz-lead-management/
├── data/                       # Raw synthetic CRM datasets
│   ├── leads_seed.csv
│   └── website_form_submissions.json
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI REST API endpoints
│   ├── database.py             # SQLite connection & session engine
│   ├── models.py               # SQLAlchemy Lead database model
│   ├── schemas.py              # Pydantic request & response schemas
│   ├── ingest.py               # Seed data cleaning & ingestion script
│   └── services/
│       ├── __init__.py
│       ├── dedupe.py           # Blocking heuristic + LLM deduplication
│       └── extraction.py       # Source channel extraction from notes
├── tests/
│   ├── __init__.py
│   └── test_leads.py           # Pytest suite using SQLite in-memory mocking
├── .gitignore                  # Git exclusions (venv, .env, leads.db)
├── requirements.txt            # Project dependencies
└── README.md                   # Assignment documentation

```

---

## Setup & How to Run

### 1. Environment Setup

Clone the repository and set up a Python virtual environment:

```bash
# Create virtual environment
python -m venv venv

# Activate environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

```

### 2. Environment Variables (Optional)

Create a `.env` file in the root folder to supply your OpenAI API key for live LLM evaluations:

```env
OPENAI_API_KEY=sk-proj-your-api-key-here

```

*Note: If `OPENAI_API_KEY` is omitted, the application automatically defaults to rule-based fallback heuristics for both deduplication and source extraction.*

### 3. Seed Database Ingestion

Clean and ingest `data/leads_seed.csv` into the local SQLite database (`leads.db`):

```bash
python -m app.ingest

```

### 4. Run API Server

Launch the FastAPI development server:

```bash
uvicorn app.main:app --reload

```

Interactive OpenAPI / Swagger UI documentation will be accessible at:

👉 **[http://127.0.0.1:8000/docs](https://www.google.com/search?q=http://127.0.0.1:8000/docs)**

### 5. Run Test Suite

Execute automated unit tests (uses isolated SQLite in-memory database with `StaticPool`):

```bash
pytest

```

---

## API Summary

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/leads` | Filter leads by `status`, `owner`, `country`, and search query `q` |
| `GET` | `/leads/{id}` | Retrieve single lead detail |
| `PATCH` | `/leads/{id}` | Update lead fields (`status`, `owner`, `notes`) |
| `GET` | `/leads/export` | Export filtered lead selection as CSV |
| `POST` | `/leads/ingest` | Ingest web form submissions and update/create lead records |
| `POST` | `/leads/dedupe-candidates` | Run candidate generation + LLM evaluation to find candidate duplicates |
| `POST` | `/leads/extract-sources` | Batch process unstructured notes to extract channel and detail context |
| `GET` | `/dashboard` | Retrieve aggregation metrics by lead status and channel |

---

## Future Improvements

1. **Async Task Queue Architecture:** Offload heavy LLM batch extraction and candidate generation tasks to background processes using Celery and Redis.
2. **Vector Indexing (Semantic Blocking):** Implement embedding-based vector similarity search (e.g. via `chromadb` or `pgvector`) in the blocking layer to catch non-obvious cross-field semantic duplicates.
3. **Entity Resolution & Automated Merging:** Build a `POST /leads/merge` endpoint with field-level conflict resolution rules allowing sales agents to merge confirmed candidate duplicates.

```
Note for reviewer: Developed and tested on Windows environment using Python 3.12, FastAPI, and SQLite
