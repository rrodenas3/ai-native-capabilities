# Cap-01: Decision Intelligence

> *Transform scattered internal knowledge into cited, uncertainty-labelled, board-ready intelligence — in real time.*

**Reference case:** Morgan Stanley — 98% advisor-team adoption, document access 20% → 80%
**AI layers:** Augmented → Generative → Agentic RAG
**Status:** `spec-complete` · implementation in progress

---

## The problem this solves

Executives and knowledge workers drown in information but starve for insight. The average C-level leader can access only a fraction of their organisation's knowledge at decision time — the rest is buried in documents, presentations, and reports that no single person could hold in working memory.

The result: decisions made on intuition, incomplete information, or last quarter's data.

Morgan Stanley solved this for 16,000 financial advisors. Their system achieved 98% adoption not through features, but through three disciplined choices: **forced citations** (no answer without a source), **eval-first deployment** (every use case tested before launch), and **human accountability preserved** (advisor reviews before client-facing action).

This capability applies the same pattern to executive decision-making.

---

## What it builds

```
User query (natural language)
      ↓
Supervisor Agent         — decomposes, routes, governs
      ↓
Retrieval Agent          — hybrid search (semantic + BM25 + metadata)
      ↓
Analysis Agent           — synthesis, cross-reference, gap detection
      ↓
Verification Agent       — every claim checked against source
      ↓
Brief Assembly Agent     — structured output: findings + citations + confidence
      ↓
Human Review Gate        — required before any externally-actioned decision
      ↓
Episodic Memory          — learns from every session
```

**Output:** A structured brief with executive summary, key findings (each with citation and confidence score), uncertainty flags, and recommended next actions.

---

## Eval gates

| Metric | Target | Blocking |
|---|---|---|
| Citation accuracy | ≥ 0.95 | ✓ |
| Hallucination rate | ≤ 0.02 | ✓ |
| Retrieval recall | ≥ 0.85 | |
| Source coverage | ≥ 0.80 | |
| Response latency p95 | ≤ 30s | |
| Human override rate | ≤ 0.15 | |
| Brief usefulness (1–5) | ≥ 4.0 | |
| Cost per brief | ≤ $0.50 | |

---

## Quick start

```bash
# From repo root (after python scripts/setup.py)
python cap-01-decision-intelligence/demo.py

# Run evals
python scripts/run_evals.py --cap cap-01
```

---

## Implementation tasks

See [`specs/SPEC.md`](./specs/SPEC.md) for the complete BriefingScript.

| Task | Description | Status |
|---|---|---|
| TASK-01-01 | pgvector index + document ingestion | `todo` |
| TASK-01-02 | Hybrid retrieval (semantic + BM25) | `todo` |
| TASK-01-03 | Supervisor Agent | `todo` |
| TASK-01-04 | Retrieval Agent | `todo` |
| TASK-01-05 | Analysis & Synthesis Agent | `todo` |
| TASK-01-06 | Verification Agent | `todo` |
| TASK-01-07 | Brief Assembly Agent | `todo` |
| TASK-01-08 | LangGraph state machine | `todo` |
| TASK-01-09 | Episodic memory | `todo` |
| TASK-01-10 | Human Review Gate + audit log | `todo` |
| TASK-01-11 | Eval suite | `todo` |
| TASK-01-12 | Cost telemetry | `todo` |
| TASK-01-13 | CLI demo | `todo` |

---

## Evidence

- Morgan Stanley: 98% advisor adoption · document access 20%→80% — `[P]` OpenAI case study
- Ramp Glass: role-aware context, first-interaction value — `[P]` company data
- McKinsey 2025: only 39% reach enterprise EBIT impact — `[M]` n=1,993

`[M]` = Measured (independent) · `[P]` = Partial (company-reported) · `[V]` = Vendor claim
