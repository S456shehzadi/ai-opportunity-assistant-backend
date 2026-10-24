# AI Opportunity Assistant - Backend

Production-ready backend foundation for **AI Opportunity Assistant**, a global AI-powered opportunity discovery and reasoning platform.

---

## Architecture Overview

The backend is built with Python 3.12+ and FastAPI, designed to evolve into a multi-stage reasoning system that prevents hallucinations through source-grounded claims:

```text
User Request (Flutter / Web)
          ↓
     FastAPI API (/api/v1)
          ↓
    AI Orchestrator
          ↓
 Query Understanding Model
          ↓
Search Provider Abstraction (SearXNG / DuckDuckGo / Bing / Mock)
          ↓
Web Retriever (Robots.txt aware, rate-limited, cached)
          ↓
Extraction & Verification (SourceTrustService)
          ↓
  Eligibility & Ranking Engine
          ↓
Response Generation (GroundedClaim & SourceEvidence)
          ↓
Structured Response
```

### Key Architectural Pillars
- **Provider-Independent AI**: Core abstractions (`AIModel`, `AIModelProvider`) enable hot-swapping between local inference (Ollama, vLLM), self-hosted open-weights models, or external providers without touching business logic.
- **Hallucination Prevention**: Explicit grounding models (`GroundedClaim`, `SourceEvidence`, `ConfidenceLevel`) require claims to be anchored to verifiable source snippets.
- **Ethical Web Retrieval**: `WebRetriever` interface enforces `robots.txt` compliance, domain rate-limiting, size caps, and redirect tracking.
- **Async Database & Migrations**: Async SQLAlchemy 2.0 with PostgreSQL and Alembic migration foundation.

---

## Current Implementation Scope

### Implemented
- FastAPI lifespan, configuration, logging, CORS, security headers, and exception handlers.
- Health endpoint: `GET /api/v1/health` returning structured subsystem statuses.
- Centralized configuration via `pydantic-settings` and `.env.example`.
- Complete AI abstraction layer (`AIModel`, specialized models, `AIOrchestrator`, grounding schemas).
- Modular search provider and ethical web retrieval interfaces.
- Opportunity domain schemas (categories, funding types, eligibility criteria).
- Source trust system abstraction (`SourceTrustService`).
- Training architecture layout and sample dataset schemas (`training/`).
- Database configuration with async engine, declarative Base, and Alembic setup.
- Full pytest test suite with async HTTP fixtures.
- Multi-stage `Dockerfile` and `.dockerignore`.

### Intentionally NOT Implemented in This Phase
- Live web crawling and search engine scraping.
- Production LLM inference calls or vector database indexing.
- User authentication and authorization (JWT/OAuth).
- Full database entity schema migrations.
- Live opportunity extraction, notifications, payments, or recommendation engine.

---

## Quickstart

### 1. Prerequisites
- Python 3.12+
- (Optional) PostgreSQL and Docker

### 2. Setup Virtual Environment & Dependencies
```bash
python -m venv .venv

# Windows
.\.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

pip install -e ".[dev]"
```

### 3. Configure Environment Variables
```bash
cp .env.example .env
```

### 4. Run the Development Server
```bash
uvicorn app.main:app --reload --port 8000
```
Visit the interactive Swagger UI at: [http://localhost:8000/docs](http://localhost:8000/docs)
Verify the health endpoint at: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

## Development Commands

| Task | Command |
|---|---|
| **Install Dependencies** | `pip install -e ".[dev]"` |
| **Run Dev Server** | `uvicorn app.main:app --reload --port 8000` |
| **Run Tests** | `pytest` |
| **Run Linting** | `ruff check .` |
| **Run Formatting Check** | `ruff format --check .` |
| **Apply Formatting** | `ruff format .` |
| **Run Type Checking** | `mypy app` |
| **Run Migrations** | `alembic upgrade head` |
| **Build Docker Image** | `docker build -t ai-opportunity-assistant-backend .` |
| **Run Docker Container** | `docker run -p 8000:8000 ai-opportunity-assistant-backend` |
