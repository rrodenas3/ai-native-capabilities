<div align="center">

![ai-native-capabilities hero](docs/assets/hero-banner.png)

<br/>

[![Python 3.13](https://img.shields.io/badge/Python-3.13-3B6D11?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![LangGraph 1.0.5](https://img.shields.io/badge/LangGraph-1.0.5-534AB7?style=flat-square)](https://langchain.com/langgraph)
[![MCP 2025-11-25](https://img.shields.io/badge/MCP-2025--11--25-0F6E56?style=flat-square)](https://modelcontextprotocol.io)
[![Claude Sonnet 4.6](https://img.shields.io/badge/Claude-Sonnet_4.6-993C1D?style=flat-square)](https://anthropic.com)
[![pgvector 0.7](https://img.shields.io/badge/pgvector-0.7.x-185FA5?style=flat-square)](https://github.com/pgvector/pgvector)
[![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-1.29-854F0B?style=flat-square)](https://opentelemetry.io)
[![CI evals on every PR](https://img.shields.io/badge/CI-evals_on_every_PR-444441?style=flat-square)](/.github/workflows/evals.yml)
[![MIT License](https://img.shields.io/badge/License-MIT-A32D2D?style=flat-square)](./LICENSE)

<br/>

**Five production-grade agentic AI capabilities. Built spec-first. Evaluated obsessively. Governed by design.**

*Not a tutorial. A working reference implementation built to the engineering standards of companies actually winning AI transformation.*

</div>

---

## Why this exists

<div align="center">

| 88% of orgs use AI | Only 39% reach EBIT impact | 95% of pilots fail P&L | The gap is solvable |
|:---:|:---:|:---:|:---:|
| McKinsey 2025, n=1,993 | McKinsey 2025 | MIT NANDA 2025 | Architecture · Evals · Governance |

</div>

This project closes that gap — one capability at a time — and documents every decision so others can adapt the patterns.

---

## The three AI layers

![From augmented to agentic — the enterprise transformation stack](docs/assets/ai-stack-layers.png)

Every capability in this repo is built across all three layers. Augmented AI removes blindspots. Generative AI creates at scale. Agentic AI executes autonomously with human oversight. The value gap exists because most organisations stop at layer one.

---

## The five capabilities

| # | Capability | AI layer | Reference case | Issues |
|---|---|---|---|---|
| 01 | [**Decision Intelligence**](./cap-01-decision-intelligence/) | Augmented → Agentic RAG | Morgan Stanley 98% advisor adoption | [#13–#27](https://github.com/rrodenas3/ai-native-capabilities/issues?q=label%3Acap-01) |
| 02 | [**Agentic Engineering**](./cap-02-agentic-engineering/) | Generative → SASE | Ramp 84% cross-role coding agents | [#28–#52](https://github.com/rrodenas3/ai-native-capabilities/issues?q=label%3Acap-02) |
| 03 | [**Agentic Commerce**](./cap-03-agentic-commerce/) | Agentic multi-agent | Walmart super-agent consolidation | [#36–#53](https://github.com/rrodenas3/ai-native-capabilities/issues?q=label%3Acap-03) |
| 04 | [**Autonomous Operations**](./cap-04-autonomous-operations/) | Agentic stateful (durable) | Walmart + DHL + Flowr arXiv 2604.05987 | [#41–#45](https://github.com/rrodenas3/ai-native-capabilities/issues?q=label%3Acap-04) |
| 05 | [**Compliance Intelligence**](./cap-05-compliance-intelligence/) | Agentic RAG + Knowledge Graph | Harvey AI $11B · EU AI Act Aug 2026 | [#46–#49](https://github.com/rrodenas3/ai-native-capabilities/issues?q=label%3Acap-05) |

Each capability ships with: agent graph · MCP connectors · evaluation suite · governance gates · scaling roadmap · SPEC.md as source of truth.

---

## Cap-01 in depth — Decision Intelligence

![Cap-01 Decision Intelligence agent graph](docs/assets/cap01-agent-graph.png)

Six agents in sequence. Strategic query in, cited board-ready brief out. Every factual claim verified against its source. Human gate required before any externally-actioned decision. `citation_accuracy ≥ 0.95` is a blocking metric — the PR cannot merge without it.

The Morgan Stanley pattern: eval-first before deployment, forced citations on every answer, zero data retention, human advisor retains accountability. 98% adoption rate. Document access 20% → 80%.

---

## Spec-driven development

![Spec-driven development loop](docs/assets/sdd-loop.png)

**The spec is the source of truth. Not the code.**

Every capability begins with a machine-readable `SPEC.md` (BriefingScript) before a single line of agent code is written. Codex and Claude Code implement from the spec. Evals verify against acceptance criteria. Humans approve. Blocking metrics prevent merge.

```
cap-XX/specs/SPEC.md
├── goal_and_why           # business value, evidence grade
├── what_and_success       # acceptance criteria with thresholds
├── all_needed_context     # agent graph, state schema, MCP connectors
├── implementation_tasks   # ordered tasks with TASK-XX-NN IDs
├── failure_modes          # what breaks and how it's mitigated
├── eval_scorecard         # YAML blocking gates
└── codex_instructions     # machine-readable agent directives
```

To contribute: start by reading or writing the spec. The CI pipeline rejects PRs where implementation diverges from spec acceptance criteria.

---

## Evidence base

![Built on production evidence](docs/assets/evidence-wall.png)

Every architectural decision traces to documented production evidence, graded by quality:

- `[M]` **Measured** — independent, quantified, peer-reviewed or audited
- `[P]` **Partial** — company-reported, directionally credible, not independently verified  
- `[V]` **Vendor claim** — treat as directional only

Full evidence library: [`docs/case-studies/`](./docs/case-studies/)

---

## Architecture principles

**Spec-first** — BriefingScript written before any code. Codex implements. Humans review output, not write it. Enables consistent quality across 49 tracked tasks.

**MCP-native** — all tool integrations via [Model Context Protocol](https://modelcontextprotocol.io) (spec 2025-11-25, Streamable HTTP). No hardcoded API wrappers. Every connector is swappable.

**Eval on every PR** — common scorecard runs on every pull request. Blocking metrics prevent merge. Eval is the definition of done, not a post-launch check.

**Governance by design** — 5-gate approval engine (use-case → data → action → quality → scale) baked into `core/`. Human-in-the-loop via LangGraph `interrupt()` — not optional flags.

**In-context before orchestration** — following arXiv 2604.27891: multi-agent orchestration only when the task genuinely needs state, tool routing, memory, approvals, or long-running execution. For procedural tasks, a well-prompted frontier model is the default.

---

## Stack

> Verified against production releases as of June 2026. Every version pinned and justified in [`docs/architecture/STACK.md`](./docs/architecture/STACK.md).

```
Language         Python 3.13 · GIL-optional free-threaded mode · ~11% faster vs 3.12
                 TypeScript for MCP servers (@modelcontextprotocol/sdk)

Orchestration    LangGraph 1.0.5 — GA October 2025, stable API until 2.0
                 Production users: Uber · LinkedIn · JP Morgan · Klarna · Blackrock
                 Powers: stateful graphs · checkpointing · human-in-the-loop
                 interrupt() · cross-thread memory · streaming

Protocol         MCP spec 2025-11-25 · Streamable HTTP (SSE deprecated Mar 2025)
                 OAuth 2.1 + PKCE · 97M monthly SDK downloads
                 Linux Foundation Agentic AI Foundation governance
                 Next spec RC: 2026-07-28 (stateless core + Tasks extension)

Models           claude-opus-4-8        flagship · complex reasoning · long-horizon
                 claude-sonnet-4-6      default · 79.6% SWE-bench · $3/$15 per MTok
                 claude-haiku-4-5-20251001  routing · classification · subagents
                 gpt-5.5 / gpt-5 / gpt-5-mini (secondary, swappable via interface)
                 ⚠ Claude 3.x retired April 2026. GPT-4o retired Feb 2026.

Memory           pgvector 0.7.x (HNSW + IVFFlat · production-grade under ~50M vectors)
                 pgvectorscale (higher throughput, same Postgres instance)
                 Layers: episodic (PostgreSQL) · semantic (pgvector) · procedural (Redis)
                         long-term cross-thread (LangGraph store)

Evals            LangSmith — deepest LangGraph integration · LangGraph Studio replay
                 Arize Phoenix OSS — framework-agnostic RAG evals · OTEL-native
                 Custom YAML scorecard per capability · CI-enforced blocking metrics
                 Braintrust — structured A/B eval runs · 1M spans/month free tier

Observability    OpenTelemetry (OTLP) · cost telemetry (tokens × agentic multiplier 5–30x)
                 Budget alerts at 80% of session/run/monthly thresholds

Security         bandit 1.8+ · semgrep 1.90+ · mandatory on all agent-generated code
                 MCP OAuth 2.1 + PKCE · least-privilege tool permissions · audit trail

CI               GitHub Actions · eval suite on every PR · blocking metrics enforced
                 Eval summary posted as PR comment · cost delta per run reported
```

---

## Repo structure

```
ai-native-capabilities/
├── core/                         # Shared infrastructure — build this first
│   ├── orchestration/            # LangGraph base graphs + state schemas
│   ├── mcp/                      # MCP connector registry + base classes
│   ├── memory/                   # Episodic · semantic · procedural layers
│   ├── evals/                    # Common evaluation scorecard
│   ├── governance/               # 5-gate approval engine + human gate
│   ├── observability/            # OTEL + cost telemetry
│   ├── schemas/base.py           # Canonical Pydantic models (all capabilities)
│   └── utils/                    # Settings · logging · retry · DB
│
├── cap-01-decision-intelligence/ # 6-agent RAG pipeline → board-ready brief
├── cap-02-agentic-engineering/   # SASE: BriefingScript → MRP → human review
├── cap-03-agentic-commerce/      # Sparky super-agent · intent → basket → handoff
├── cap-04-autonomous-operations/ # Stateful supply chain · durable · approval gates
├── cap-05-compliance-intelligence/ # Regulatory RAG + KG · EU AI Act · expert gate
│
├── docs/
│   ├── assets/                   # Visual assets (hero, diagrams, evidence wall)
│   ├── architecture/             # STACK.md · AGENT_ROUTING.md · MEMORY.md
│   ├── adr/                      # Architecture Decision Records
│   ├── playbooks/                # RAMP_L0_L3.md · Shopify mandate · Moderna
│   └── case-studies/             # 40+ company evidence summaries
│
├── benchmarks/                   # Cross-capability comparison runs
├── scripts/                      # setup.py · health_check.py · run_evals.py
└── .github/workflows/evals.yml   # CI: eval suite on every PR
```

---

## Quick start

```bash
# 1. Clone
git clone https://github.com/rrodenas3/ai-native-capabilities
cd ai-native-capabilities

# 2. Install (Python 3.13+ required)
python3.13 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 3. Start services
docker compose up -d          # PostgreSQL + pgvector + Redis

# 4. Configure
cp .env.example .env          # Add ANTHROPIC_API_KEY

# 5. Verify
python scripts/health_check.py

# 6. Run eval suite (mock mode — no API cost)
python scripts/run_evals.py --all --mock
```

**With GitHub CLI installed** — feed any issue directly to Codex:
```bash
gh auth login
codex "$(gh issue view 10 --json title,body -q '.title + "\n\n" + .body')"
```

---

## Build order

The 49 open issues form a dependency-ordered build queue:

```
Phase 1 — Core infrastructure (issues #1–#12)
  #10 Settings → #1 Base graph → #2 MCP registry → #11 DB → #12 Health check
  → #3 Governance → #4 Episodic memory → #5 Semantic memory → #6 Procedural
  → #7 Eval suite → #8 Cost telemetry → #9 Schemas

Phase 2 — Cap-01 Decision Intelligence (issues #13–#27)
  Ingestion → Retrieval → Supervisor → 6 agents → LangGraph graph
  → Human gate → Eval suite → Demo

Phase 3 — Cap-02 through Cap-05 (issues #28–#53)
```

Every issue has the exact Codex prompt at the bottom. Read the spec, paste the prompt, review the output, run the evals, merge.

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md). The short version:

1. Read the spec for the capability you're working on
2. Open the GitHub issue for your task (find it via label `cap-01`, `core`, etc.)
3. Feed the issue to Codex: `codex "$(gh issue view N --json title,body -q '.title + "\n\n" + .body')"`
4. Review output against the acceptance criteria checkboxes
5. Run `python scripts/run_evals.py --cap cap-XX`
6. If blocking metrics pass → open PR → CI runs → merge closes the issue

If you hit an ambiguity, raise a [Consultation Request](/.github/ISSUE_TEMPLATE/crp.md) — don't guess.

Proficiency ladder: [L0 → L3](./docs/playbooks/RAMP_L0_L3.md) — where you are determines which tasks to start with.

---

## Roadmap

- [ ] `core` — shared infrastructure (12 tasks)
- [ ] `cap-01` — Decision Intelligence MVP (15 tasks)
- [ ] `cap-02` — Agentic Engineering / SASE (11 tasks)
- [ ] `cap-03` — Agentic Commerce (6 tasks)
- [ ] `cap-04` — Autonomous Operations (5 tasks)
- [ ] `cap-05` — Compliance Intelligence (4 tasks)
- [ ] Benchmark dashboard — compare all 5 capabilities side-by-side
- [ ] Web UI — interactive demo for each capability

---

## Evidence and references

*Grounded in: McKinsey State of AI 2025 (n=1,993) · MIT NANDA GenAI Divide 2025 · Stanford AI Index 2026 · SASE paper (Hassan et al., ACM 2026) · arXiv 2604.27891 (in-context vs orchestration) · Flowr arXiv 2604.05987 (agentic supply chain) · EU AI Act (Aug 2026 enforcement) · Anthropic API docs (June 2026)*

---

## License

MIT — use it, adapt it, build on it. If you deploy a version of this in production, a ⭐ and a case study in the issues would be deeply appreciated.

---

<div align="center">

*Built at the intersection of AI research, enterprise transformation, and engineering discipline.*

[`github.com/rrodenas3/ai-native-capabilities`](https://github.com/rrodenas3/ai-native-capabilities)

</div>
