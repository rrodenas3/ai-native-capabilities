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

Every capability is built across all three layers. Augmented AI removes blindspots. Generative AI creates at scale. Agentic AI executes autonomously with human oversight. The value gap exists because most organisations stop at layer one.

---

## The five capabilities

| # | Capability | AI layer | Reference case | Issues |
|---|---|---|---|---|
| 01 | [**Decision Intelligence**](./cap-01-decision-intelligence/) | Augmented → Agentic RAG | Morgan Stanley 98% advisor adoption | [15 tasks](https://github.com/rrodenas3/ai-native-capabilities/issues?q=label%3Acap-01) |
| 02 | [**Agentic Engineering**](./cap-02-agentic-engineering/) | Generative → SASE | Ramp 84% cross-role coding agents | [11 tasks](https://github.com/rrodenas3/ai-native-capabilities/issues?q=label%3Acap-02) |
| 03 | [**Agentic Commerce**](./cap-03-agentic-commerce/) | Agentic multi-agent | Walmart super-agent consolidation | [6 tasks](https://github.com/rrodenas3/ai-native-capabilities/issues?q=label%3Acap-03) |
| 04 | [**Autonomous Operations**](./cap-04-autonomous-operations/) | Agentic stateful (durable) | Walmart + DHL + Flowr arXiv | [5 tasks](https://github.com/rrodenas3/ai-native-capabilities/issues?q=label%3Acap-04) |
| 05 | [**Compliance Intelligence**](./cap-05-compliance-intelligence/) | Agentic RAG + Knowledge Graph | Harvey AI $11B · EU AI Act Aug 2026 | [4 tasks](https://github.com/rrodenas3/ai-native-capabilities/issues?q=label%3Acap-05) |

---

## Cap-01 — Decision Intelligence

![Cap-01 Decision Intelligence — 6-agent pipeline](docs/assets/cap01-agent-graph.png)

Six agents in sequence. Strategic query in, cited board-ready brief out. Every factual claim verified against its source before the human gate is reached.

The **Morgan Stanley pattern**: eval-first before deployment, forced citations on every answer, zero data retention, human advisor retains accountability. Result: 98% adoption rate across 16,000 advisors. Document access lifted from 20% to 80%.

| Agent | Role | Model |
|---|---|---|
| Supervisor | Decomposes query into sub-tasks | `claude-sonnet-4-6` |
| Retrieval | Hybrid search (semantic + BM25) | — |
| Analysis | Synthesis + contradiction + gap detection | `claude-opus-4-8` |
| Verification | Every claim checked against source | `claude-opus-4-8` |
| Brief Assembly | Executive summary + findings + actions | `claude-sonnet-4-6` |
| Human Gate | `interrupt()` — required, unbypassable | — |

**Blocking eval:** `citation_accuracy ≥ 0.95` · `hallucination_rate ≤ 0.02`
→ [`cap-01-decision-intelligence/specs/SPEC.md`](./cap-01-decision-intelligence/specs/SPEC.md)

---

## Cap-02 — Agentic Engineering (SASE)

<!-- cap02-sase-graph.png goes here once generated -->
<!-- ![Cap-02 Agentic Engineering — SASE pipeline](docs/assets/cap02-sase-graph.png) -->

The **Ramp insight**: 84% of all employees — finance, marketing, ops — use coding agents weekly. The technical/non-technical line has dissolved. But unstructured agent use creates security risks: 29.5% of unscanned Copilot-generated Python contains security weaknesses (Fu et al., ACM 2025).

SASE (Structured Agentic Software Engineering) provides the discipline: humans are **Agent Coaches** (SE4H), agents execute in a structured environment (SE4A). BriefingScripts replace ad-hoc prompting. MergeReadiness Packs replace raw diffs. Security gates are mandatory, not optional.

| Artifact | Owner | Purpose |
|---|---|---|
| BriefingScript | Human (Agent Coach) | Goal + acceptance criteria + constraints |
| LoopScript | Execution Agent | Self-monitoring iteration plan |
| MentorScript | Review Agent | Scores every acceptance criterion |
| CRP | Execution Agent | Consultation when blocked — never guess |
| MergeReadiness Pack | Execution Agent | The only artifact that reaches human review |

**Blocking eval:** `briefing_completeness = 1.0` · `security_weakness_rate ≤ 5.0 per 1000 lines`
→ [`cap-02-agentic-engineering/specs/SPEC.md`](./cap-02-agentic-engineering/specs/SPEC.md)

---

## Cap-03 — Agentic Commerce

<!-- cap03-sparky-graph.png goes here once generated -->
<!-- ![Cap-03 Agentic Commerce — Sparky super-agent](docs/assets/cap03-sparky-graph.png) -->

The **Walmart lesson**: agent sprawl — dozens of narrow single-purpose bots — creates governance chaos, inconsistent UX, and unmanageable cost. The solution is consolidation: a small number of orchestrated **super-agents** via MCP.

Sparky (customer), Marty (supplier/ops), Associate (internal). Each is a single entry point that routes to specialist sub-agents. The Klarna cautionary case is built in: CSAT is measured **per complexity tier**, not aggregate. Frustrated customers trigger mandatory human escalation — no retries, no delay.

| Agent | Handles | Critical constraint |
|---|---|---|
| Sparky | All customer interactions | Single entry point — `agent_sprawl_count ≤ 2` blocking |
| Discovery | Product search + ranking | Margin-aware — negative-margin items blocked from slot 1 |
| Support | Policy RAG + order lookup | Live OMS data only — never hallucinate order details |
| Escalation | Human handoff | Fires on frustration_flag — no retries, immediate |
| Marty | Suppliers · sellers · advertisers | Autonomous below $X threshold, human gate above |

**Blocking eval:** `agent_sprawl_count ≤ 2` · `escalation_accuracy ≥ 0.90`
→ [`cap-03-agentic-commerce/specs/SPEC.md`](./cap-03-agentic-commerce/specs/SPEC.md)

---

## Cap-04 — Autonomous Operations

<!-- cap04-supply-chain-graph.png goes here once generated -->
<!-- ![Cap-04 Autonomous Operations — stateful supply chain](docs/assets/cap04-supply-chain-graph.png) -->

The most architecturally demanding capability. Supply chain tasks are **long-running** (hours to days), involve **irreversible actions** (purchase orders sent to suppliers), and require **human approval above dollar thresholds**. LangGraph's PostgreSQL durable execution is not optional — it is the architecture.

The digital twin runs before every action above the autonomy threshold. The human sees the simulation result alongside the PO draft. The approval gate is a LangGraph `interrupt()` — the graph physically cannot proceed without a human decision.

```
Demand forecast → Inventory risk → EOQ optimisation → PO draft
                                                           │
                              ┌────────────────────────────┤
                              │ < $5,000 threshold         │ ≥ $5,000 threshold
                              ▼                            ▼
                       Digital twin (fast)      Digital twin + Human gate
                              │                            │
                              └──────────┬─────────────────┘
                                         ▼
                                  ERP/WMS write via MCP
                                  Audit trail logged
```

**Blocking eval:** `human_approval_coverage = 1.00` · `digital_twin_validation = 1.00`
→ [`cap-04-autonomous-operations/specs/SPEC.md`](./cap-04-autonomous-operations/specs/SPEC.md)

---

## Cap-05 — Compliance Intelligence

<!-- cap05-compliance-graph.png goes here once generated -->
<!-- ![Cap-05 Compliance Intelligence — regulatory pipeline](docs/assets/cap05-compliance-graph.png) -->

The highest-stakes capability. Harvey AI reached $11B valuation and $190M ARR serving this market. A&O Shearman saves 2-3 hours per lawyer per week. EU AI Act high-risk obligations enforce from **August 2, 2026**. Fines reach **€35M or 7% of global turnover**.

The critical design principle: **the false-negative rate on obligations is the one metric that can create existential company risk.** Conservative extraction always. Confident hallucination is catastrophic. Expert review is mandatory — not a quality check, a legal requirement.

| Stage | Agent | Critical constraint |
|---|---|---|
| Monitor | Feed Monitor | EUR-Lex · Federal Register · NIST ingested continuously |
| Classify | Classifier Agent | REGULATION / AMENDMENT / GUIDANCE / ENFORCEMENT |
| Extract | Interpretation Agent | `false_negative_rate ≤ 0.01` — **the critical metric** |
| Map | KG Agent | Obligation → Article → UseCase → Coverage in Neo4j |
| Review | Expert Gate | `interrupt()` — no obligation enters register without sign-off |
| Gap | Gap Mapping Agent | `gap_detection_accuracy ≥ 0.90` on 30 labelled scenarios |

**Blocking eval:** `false_negative_rate ≤ 0.01` · `citation_accuracy ≥ 0.98` · `expert_review_coverage = 1.00` · `query_answer_citation_rate = 1.00`
→ [`cap-05-compliance-intelligence/specs/SPEC.md`](./cap-05-compliance-intelligence/specs/SPEC.md)

---

## Spec-driven development

![Spec-driven development loop](docs/assets/sdd-loop.png)

**The spec is the source of truth. Not the code.**

Every capability begins with a machine-readable `SPEC.md` (BriefingScript) before a single line of agent code is written. Codex and Claude Code implement from the spec. Evals verify against acceptance criteria. Blocking metrics prevent merge.

```
cap-XX/specs/SPEC.md
├── goal_and_why           # business value, evidence grade
├── what_and_success       # acceptance criteria with thresholds
├── all_needed_context     # agent graph, state schema, MCP connectors
├── implementation_tasks   # ordered tasks with TASK-XX-NN IDs
├── failure_modes          # what breaks and how it's mitigated
├── eval_scorecard         # YAML blocking gates
└── codex_instructions     # machine-readable directives for the agent
```

Feed any issue to Codex in one command:
```bash
codex "$(gh issue view 10 --json title,body -q '.title + "\n\n" + .body')"
```

---

## Evidence base

![Built on production evidence](docs/assets/evidence-wall.png)

Every architectural decision traces to documented production evidence, graded:

- `[M]` **Measured** — independent, quantified, peer-reviewed or audited
- `[P]` **Partial** — company-reported, directionally credible, not independently verified
- `[V]` **Vendor claim** — treat as directional only

Full evidence library: [`docs/case-studies/`](./docs/case-studies/)

---

## Architecture principles

**Spec-first** — BriefingScript before code. Codex implements. Humans review output, not write it.

**MCP-native** — all tool integrations via [Model Context Protocol](https://modelcontextprotocol.io) (spec 2025-11-25, Streamable HTTP). No hardcoded wrappers. Every connector swappable.

**Eval on every PR** — common scorecard on every pull request. Blocking metrics prevent merge. The eval is the definition of done.

**Governance by design** — 5-gate engine (use-case → data → action → quality → scale) in `core/`. Human-in-the-loop via `interrupt()` — not flags.

**In-context before orchestration** — following arXiv 2604.27891: orchestration only when the task genuinely needs state, memory, approvals, or long-running execution. A well-prompted model is the default.

---

## Stack

> Verified June 2026. Full detail: [`docs/architecture/STACK.md`](./docs/architecture/STACK.md)

```
Language         Python 3.13 · GIL-optional · TypeScript for MCP servers
Orchestration    LangGraph 1.0.5 — Uber · LinkedIn · JP Morgan · Blackrock in production
Protocol         MCP spec 2025-11-25 · Streamable HTTP · OAuth 2.1 · Linux Foundation
Models           claude-sonnet-4-6 (default) · claude-opus-4-8 (complex) · claude-haiku-4-5 (subagents)
                 gpt-5.5 / gpt-5 (secondary, swappable) ⚠ Claude 3.x retired Apr 2026
Memory           pgvector 0.7.x · pgvectorscale · episodic · semantic · procedural (Redis)
Evals            LangSmith · Arize Phoenix OSS · custom YAML scorecard · Braintrust A/B
Observability    OpenTelemetry (OTLP) · cost telemetry (5–30x agentic multiplier)
Security         bandit 1.8+ · semgrep 1.90+ · mandatory on all agent-generated code
CI               GitHub Actions · eval suite on every PR · cost delta per run
```

---

## Quick start

```bash
git clone https://github.com/rrodenas3/ai-native-capabilities
cd ai-native-capabilities
python3.13 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
docker compose up -d
cp .env.example .env          # add ANTHROPIC_API_KEY
python scripts/health_check.py
python scripts/run_evals.py --all --mock
```

---

## Build order

```
Phase 1 — Core infrastructure  (issues #1–#12, start here)
  #10 Settings → #1 Base graph → #2 MCP → #11 DB → #12 Health check
  → #3 Governance → #4–6 Memory layers → #7 Evals → #8 Cost telemetry → #9 Schemas

Phase 2 — Cap-01 Decision Intelligence  (issues #13–#27)
Phase 3 — Cap-02 Agentic Engineering    (issues #28–#52)
Phase 4 — Cap-03 Agentic Commerce       (issues #36–#53)
Phase 5 — Cap-04 Autonomous Operations  (issues #41–#45)
Phase 6 — Cap-05 Compliance Intelligence (issues #46–#49)
```

Proficiency ladder: [L0 → L3](./docs/playbooks/RAMP_L0_L3.md)

---

## Repo structure

```
ai-native-capabilities/
├── core/                         # Shared infra — build first
│   ├── orchestration/            # LangGraph base graphs + state schemas
│   ├── mcp/                      # MCP connector registry + base classes
│   ├── memory/                   # Episodic · semantic · procedural
│   ├── evals/                    # Common evaluation scorecard
│   ├── governance/               # 5-gate approval engine + human gate
│   ├── observability/            # OTEL + cost telemetry
│   ├── schemas/base.py           # Canonical Pydantic models
│   └── utils/                    # Settings · logging · retry · DB
├── cap-01-decision-intelligence/ # 6-agent RAG → board-ready brief
├── cap-02-agentic-engineering/   # SASE: BriefingScript → MRP → review
├── cap-03-agentic-commerce/      # Sparky super-agent commerce mesh
├── cap-04-autonomous-operations/ # Stateful supply chain · durable
├── cap-05-compliance-intelligence/ # Regulatory RAG + KG · expert gate
├── docs/
│   ├── assets/                   # Visual assets (5 infographics)
│   ├── architecture/             # STACK.md · AGENT_ROUTING.md
│   ├── adr/                      # Architecture Decision Records
│   └── playbooks/                # RAMP_L0_L3.md
├── benchmarks/
├── scripts/                      # setup · health_check · run_evals
└── .github/workflows/evals.yml
```

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md). Write the spec first, run the evals, document your evidence sources. Open a [Consultation Request](/.github/ISSUE_TEMPLATE/crp.md) when blocked — never guess.

---

## Roadmap

- [x] Repo structure + all 5 capability specs (SPEC.md)
- [x] Core infrastructure: base graph, MCP registry, episodic memory (issues #1–#3 merged)
- [ ] Core infrastructure complete (issues #4–#12)
- [ ] Cap-01 Decision Intelligence MVP
- [ ] Cap-02 Agentic Engineering MVP
- [ ] Cap-03 Agentic Commerce MVP
- [ ] Cap-04 Autonomous Operations MVP
- [ ] Cap-05 Compliance Intelligence MVP
- [ ] Benchmark dashboard — all 5 capabilities side-by-side
- [ ] Visual agent graphs for Cap-02 through Cap-05

---

<div align="center">

*Grounded in: McKinsey State of AI 2025 · MIT NANDA GenAI Divide · SASE paper (Hassan et al., ACM 2026) · arXiv 2604.27891 · Flowr arXiv 2604.05987 · EU AI Act · Anthropic API docs June 2026*

**MIT License** · [`github.com/rrodenas3/ai-native-capabilities`](https://github.com/rrodenas3/ai-native-capabilities)

</div>
