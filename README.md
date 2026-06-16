# ai-native-capabilities

> **Five production-grade agentic AI capabilities. Built spec-first. Evaluated obsessively. Governed by design.**

This is not a tutorial repository. It is a working reference implementation of the five human capabilities most transformed by the convergence of augmented AI, generative AI, and agentic AI — built to the engineering standards of the companies that are actually winning this transformation.

Every capability ships as a functional MVP with agent graphs, MCP connectors, evaluation suites, governance gates, and scaling roadmaps. Every design decision is evidence-grounded and documented.

---

## Why this exists

The enterprise AI literature (McKinsey State of AI 2025, MIT NANDA GenAI Divide, Stanford AI Index 2026, Gartner Hype Cycle) converges on one uncomfortable finding: **88% of organisations use AI. Only 39% reach enterprise EBIT impact.** The gap is not model capability. It is architecture, evaluation, workflow redesign, and governance.

This project closes that gap — one capability at a time — and documents every decision so others can adapt the patterns.

---

## The five capabilities

| # | Capability | Primary layer | Reference case | Status |
|---|---|---|---|---|
| 01 | [Decision Intelligence](./cap-01-decision-intelligence/) | Augmented → Agentic RAG | Morgan Stanley 98% adoption | `in-progress` |
| 02 | [Agentic Software Engineering](./cap-02-agentic-engineering/) | Generative → SASE | Ramp 84% cross-role coding agents | `in-progress` |
| 03 | [Agentic Revenue & Commerce](./cap-03-agentic-commerce/) | Agentic multi-agent | Walmart super-agent consolidation | `in-progress` |
| 04 | [Autonomous Operations](./cap-04-autonomous-operations/) | Agentic stateful | Walmart + DHL + Flowr arXiv | `in-progress` |
| 05 | [Compliance Intelligence](./cap-05-compliance-intelligence/) | Agentic RAG + KG | Harvey AI $11B · EU AI Act Aug 2026 | `in-progress` |

---

## Architecture principles

**Spec-first.** Every capability begins with a machine-readable BriefingScript spec before a single line of agent code is written. Codex and Claude Code consume these specs. Humans review and approve the output.

**MCP-native.** All tool integrations use the [Model Context Protocol](https://modelcontextprotocol.io) standard. No hardcoded API wrappers. Every connector is swappable.

**Eval-on-every-PR.** A common evaluation scorecard runs on every pull request. No capability ships without passing its quality gates. The eval is not an afterthought — it is the definition of done.

**Governance by design.** A five-gate approval engine (use-case → data → action → quality → scale) is baked into the shared core, not bolted on. Human-in-the-loop checkpoints are explicit, not implicit.

**In-context before orchestration.** Following arXiv 2604.27891: multi-agent orchestration is used only when the task genuinely requires state, tool routing, memory, approvals, long-running execution, or specialised roles. For procedural tasks, a well-prompted frontier model is the default.

---

## Stack

```
Language:        Python 3.12+ · TypeScript (MCP servers)
Orchestration:   LangGraph 1.x (stateful, durable, human-in-loop)
Protocol:        MCP (Model Context Protocol) — all tool integrations
Models:          Claude 3.x · OpenAI GPT-4o (swappable via interface)
Memory:          pgvector (< 50M vectors) · episodic + semantic + procedural
Evals:           LangSmith · custom scorecard (per capability)
Observability:   OpenTelemetry · cost telemetry (token × multiplier)
CI:              GitHub Actions — evals on every PR
```

---

## Repo structure

```
ai-native-capabilities/
├── core/                        # Shared infrastructure (all capabilities build on this)
│   ├── orchestration/           # LangGraph base graphs and state schemas
│   ├── mcp/                     # MCP connector registry and base classes
│   ├── memory/                  # Episodic, semantic, procedural memory layers
│   ├── evals/                   # Common evaluation scorecard
│   ├── governance/              # 5-gate approval engine
│   ├── observability/           # OTEL setup, cost telemetry
│   ├── schemas/                 # Shared Pydantic models
│   └── utils/                   # Logging, retry, config
│
├── cap-01-decision-intelligence/
├── cap-02-agentic-engineering/
├── cap-03-agentic-commerce/
├── cap-04-autonomous-operations/
├── cap-05-compliance-intelligence/
│
├── docs/
│   ├── architecture/            # System diagrams, agent graphs
│   ├── adr/                     # Architecture Decision Records
│   ├── playbooks/               # Ramp L0-L3, Shopify mandate, Moderna
│   ├── governance/              # EU AI Act mapping, NIST RMF
│   └── case-studies/            # 40+ company evidence summaries
│
├── benchmarks/                  # Cross-capability comparison runs
├── .github/workflows/           # CI: evals on every PR
└── scripts/                     # Setup, seed data, demo runners
```

---

## Getting started

```bash
git clone https://github.com/YOUR_USERNAME/ai-native-capabilities
cd ai-native-capabilities
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # Add your API keys
python scripts/setup.py       # Seeds vector store, checks connectivity
```

Run the Decision Intelligence demo:
```bash
python cap-01-decision-intelligence/demo.py
```

Run the full eval suite:
```bash
python scripts/run_evals.py --all
```

---

## Spec-driven development workflow

Each capability follows this loop:

```
SPEC (BriefingScript) → CODEX/CLAUDE CODE (implement) → EVAL (automated) → HUMAN REVIEW → MERGE
```

Specs live in `cap-XX/specs/`. They are the source of truth — not the code.

To contribute a new capability or extend an existing one, start by writing or updating the spec. The CI pipeline will reject PRs where implementation diverges from the spec's acceptance criteria.

---

## Evidence base

Every architectural decision traces to documented production evidence. The evidence quality is graded:

- `[M]` — Measured (independent, quantified results)
- `[P]` — Partial (company-reported, directionally credible)
- `[V]` — Vendor claim (directional only, treat with caution)

See [`docs/case-studies/`](./docs/case-studies/) for the full evidence library.

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md). The short version: write the spec first, run the evals, document your evidence sources.

---

## Roadmap

- [ ] `core` — shared infrastructure complete
- [ ] `cap-01` — Decision Intelligence MVP
- [ ] `cap-02` — Agentic Engineering (SASE) MVP
- [ ] `cap-03` — Agentic Commerce MVP
- [ ] `cap-04` — Autonomous Operations MVP
- [ ] `cap-05` — Compliance Intelligence MVP
- [ ] Benchmark dashboard (compare all 5 side-by-side)
- [ ] Web UI for each capability demo

---

## License

MIT — use it, adapt it, build on it. If you deploy a version of this in production, a star and a case study in the issues would be deeply appreciated.

---

*Built at the intersection of AI research, enterprise transformation, and engineering discipline.*
*Grounded in: McKinsey State of AI 2025 · MIT NANDA GenAI Divide · Stanford AI Index 2026 · SASE paper (Hassan et al.) · arXiv 2604.27891 · Flowr arXiv 2604.05987*
