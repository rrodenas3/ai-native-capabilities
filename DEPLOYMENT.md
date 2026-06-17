# Deployment Guide

> Last verified: June 2026 · Python 3.13 · LangGraph 1.0.5

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | **3.13+** | Free-threaded GIL-optional build preferred |
| Docker Desktop | 4.x+ | Runs PostgreSQL, Redis, Neo4j |
| Git | any | |
| Anthropic API key | — | Required for real LLM runs; not needed for `LLM_MODE=mock` |
| OpenAI API key | — | Required for judge models only; optional for mock runs |

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/rrodenas3/ai-native-capabilities
cd ai-native-capabilities

# 2. Python environment
python3.13 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Install dev dependencies
pip install -e ".[dev]"

# 4. Configure environment
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY at minimum

# 5. Start infrastructure services
docker compose up -d               # postgres + redis
# Cap-05 only (compliance intelligence):
# docker compose --profile cap05 up -d

# 6. Verify everything is healthy
python scripts/health_check.py
```

If all checks pass, you are ready to run evals and demos.

---

## Install Extras

The project uses optional dependency groups. Install only what you need:

| Extra | Command | What it enables |
|---|---|---|
| `dev` | `pip install -e ".[dev]"` | Full development toolchain: pytest, ruff, mypy, arize-phoenix, braintrust |
| `ci` | `pip install -e ".[ci]"` | Lean CI install: pytest, fakeredis, semgrep. Used in GitHub Actions. |
| `cap05` | `pip install -e ".[cap05]"` | Cap-05 knowledge graph: neo4j, falkordb drivers |
| `dashboard` | `pip install -e ".[dashboard]"` | Local eval dashboard: fastapi, uvicorn, jinja2 |

For a minimal local run with no extra tooling:

```bash
pip install -e "."
```

---

## Infrastructure Services

All services are defined in `docker-compose.yml`. Start them before running any capability that requires a database.

| Service | Image | Port | When needed |
|---|---|---|---|
| `postgres` | `pgvector/pgvector:pg16` | `5432` | All capabilities (LangGraph checkpointing, episodic memory, pgvector) |
| `redis` | `redis:7-alpine` | `6379` | All capabilities (procedural memory, routing cache) |
| `neo4j` | `neo4j:5.24` | `7474` (browser) · `7687` (bolt) | Cap-05 only — knowledge graph |

```bash
# Start postgres + redis (all caps except Cap-05 KG)
docker compose up -d

# Start all services including Neo4j (Cap-05 knowledge graph)
docker compose --profile cap05 up -d

# Check service health
docker compose ps
```

The `postgres` service automatically runs `scripts/init_db.sql` on first start, which creates the `ai_native` database and enables the `pgvector` extension.

---

## Environment Variables

Copy `.env.example` to `.env` and set values. Required variables are marked **bold**.

### LLM Providers

| Variable | Default | Notes |
|---|---|---|
| **`ANTHROPIC_API_KEY`** | — | Required for real LLM runs |
| `OPENAI_API_KEY` | — | Required for judge model evals only |
| `LLM_DEFAULT` | `claude-sonnet-4-6` | Default model for most agents |
| `LLM_FAST` | `claude-haiku-4-5-20251001` | Routing and classification agents |
| `LLM_POWERFUL` | `claude-opus-4-8` | Cap-05 regulatory interpretation — do not downgrade |

> **Model strings are critical.** Claude 3.x was fully retired April 2026. Never use `claude-3-*` strings — they will produce API errors.

### Databases

| Variable | Default | Notes |
|---|---|---|
| **`DATABASE_URL`** | `postgresql://postgres:postgres@localhost:5432/ai_native` | PostgreSQL + pgvector |
| **`REDIS_URL`** | `redis://localhost:6379` | Procedural memory |
| `NEO4J_URI` | `bolt://localhost:7687` | Cap-05 only |
| `NEO4J_USER` | `neo4j` | Cap-05 only |
| `NEO4J_PASSWORD` | — | Cap-05 only; set to `ai-native-password` for local docker |

### Runtime Mode

| Variable | Default | Notes |
|---|---|---|
| `LLM_MODE` | `real` | Set to `mock` for zero-cost local runs (no API calls) |
| `EVAL_MODE` | `development` | Set to `ci` during automated eval runs |
| `ERP_MODE` | `mock` | Cap-04 ERP integration mode |

### Observability (optional)

| Variable | Notes |
|---|---|
| `LANGCHAIN_API_KEY` | LangSmith tracing — deepest LangGraph integration |
| `LANGCHAIN_TRACING_V2` | Set to `true` to enable LangSmith |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP export (Datadog, Honeycomb, Grafana Cloud) |

### MCP Servers (optional)

All `MCP_*_URL` variables default to empty, which activates the built-in mock implementations. Set these when connecting to real external services (ERP, WMS, regulatory feeds, etc.).

---

## Running Capabilities

### Eval suite (all capabilities, mock mode — no API cost)

```bash
python scripts/run_evals.py --all --mock
```

Eval reports are written to `reports/cap-XX.json`. To generate a Markdown summary:

```bash
python scripts/eval_summary.py reports/
# Output: reports/summary.md
```

### Local eval dashboard

```bash
pip install -e ".[dashboard]"
local-dashboard              # opens at http://localhost:8000
```

### Individual capability demos

```bash
# Cap-01 — Decision Intelligence
python cap-01-decision-intelligence/demo.py

# Cap-02 — Agentic Engineering (SASE)
python cap-02-agentic-engineering/demo.py

# Cap-03 — Agentic Commerce (Sparky)
python cap-03-agentic-commerce/demo.py

# Cap-04 — Autonomous Operations
python cap-04-autonomous-operations/demo.py

# Cap-05 — Compliance Intelligence
python cap-05-compliance-intelligence/demo.py --query "What are Article 13 obligations?"
```

All demos default to `LLM_MODE=mock` when the env var is set.

### EU AI Act walkthrough (enterprise demo)

```bash
python scripts/walkthrough_eu_ai_act.py
# Output: reports/artifacts/eu_ai_act_walkthrough.md
```

### Export leave-behind reports

```bash
pip install -e ".[dashboard]"     # required for HTML rendering
python scripts/export_artifacts.py
# Output: reports/artifacts/{scorecard,compliance_report,mrp_report}.{md,html}
```

---

## Verification

After setup, confirm the system is working end-to-end:

```bash
# 1. Infrastructure health
python scripts/health_check.py

# 2. Unit tests
pytest

# 3. Eval gates (mock mode — no API cost, < 60s)
python scripts/run_evals.py --all --mock

# 4. Golden principles check
python scripts/check_golden_principles.py
```

All four should exit 0.

---

## Cost Notes

Running in `LLM_MODE=real` incurs API costs. The agentic multiplier is **5–30× vs. single-turn** — a pipeline that calls Claude 20 times costs 20× more than a single prompt.

| Model | Input | Output | Use case |
|---|---|---|---|
| `claude-sonnet-4-6` | $3/MTok | $15/MTok | Default agent reasoning |
| `claude-haiku-4-5-20251001` | $0.80/MTok | $4/MTok | Routing, classification |
| `claude-opus-4-8` | $15/MTok | $75/MTok | Cap-05 regulatory interpretation |

Set `SESSION_BUDGET_USD` and `RUN_BUDGET_USD` in `.env` to trigger alerts at 80% of budget.

---

## Cloud Deployment

This guide covers local and development deployment. Production cloud deployment (AWS ECS, GCP Cloud Run, Azure Container Apps) is not yet documented. The stack requires:

- PostgreSQL 16 with `pgvector` extension (AWS RDS + pgvector, Supabase, or Neon)
- Redis (AWS ElastiCache, Upstash)
- Neo4j (Neo4j AuraDB, or self-hosted on Cap-05 only)
- Python 3.13 runtime

See `docs/architecture/STACK.md` for full technology reference.
