# Memory Architecture

> Last verified: June 2026. Research basis: arXiv 2603.11768 (SSGM), 2510.02373 (A-MemGuard), arXiv 2503.xxxxx (A-MEM).

## Three memory layers

Every capability draws from three complementary memory systems, each optimized for a different retrieval pattern:

```
┌─────────────────────────────────────────────────────────────────────┐
│                     MEMORY ARCHITECTURE                             │
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │  EPISODIC        │  │  SEMANTIC        │  │  PROCEDURAL      │  │
│  │  (PostgreSQL)    │  │  (pgvector)      │  │  (Redis)         │  │
│  │                  │  │                  │  │                  │  │
│  │  What happened   │  │  What it means   │  │  What to do      │  │
│  │  Timestamped     │  │  Dense vectors   │  │  Routing rules   │  │
│  │  Structured      │  │  BM25 hybrid     │  │  Learned pats.   │  │
│  │  Auditable       │  │  Reranked        │  │  Fast lookup     │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
│            │                    │                    │              │
│            └────────────────────┴────────────────────┘              │
│                                 │                                   │
│                    ┌────────────▼────────────┐                      │
│                    │   SSGMGovernor          │                      │
│                    │   core/harness/memory.py│                      │
│                    │                         │                      │
│                    │  1. A-MemGuard scan     │                      │
│                    │  2. Consistency verify  │                      │
│                    │  3. Temporal decay      │                      │
│                    └─────────────────────────┘                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Episodic memory — `core/memory/episodic.py`

Stores timestamped agent events: tool calls, decisions, human approvals, errors. Backed by PostgreSQL. Every LangGraph state transition that matters is written here.

**Primary use:** Cap-04 (audit trail for PO commits), Cap-05 (obligation confirmation events).

**Schema:** `(run_id, cap, agent, event_type, payload JSONB, created_at TIMESTAMPTZ)`

## Semantic memory — `core/memory/semantic.py`

Dense vector store for retrieved knowledge. Hybrid search: pgvector HNSW (semantic) + BM25 (lexical) + metadata filter. Reranking via cross-encoder before returning top-K to the agent.

**Primary use:** Cap-01 (document retrieval for briefings), Cap-05 (regulatory document chunks).

**Index:** `pgvector 0.7.x` with `HNSW` index — ~850 QPS at p95 under 50M vectors.

## Procedural memory — `core/memory/procedural.py`

Redis-backed routing rules and learned patterns. Fast lookup (< 1ms). Stores: intent routing tables, escalation triggers, model selection rules.

**Primary use:** Cap-03 (Sparky intent routing), Cap-02 (security pattern cache).

## SSGM governance layer — `core/harness/memory.py`

All governed writes pass through `SSGMGovernor` before reaching any memory system. Three validation stages:

| Stage | What it checks | On failure |
|-------|---------------|------------|
| A-MemGuard poisoning scan | Injection patterns in content (`"ignore previous"`, `"you are now"`, etc.) | Quarantine if risk ≥ threshold |
| Consistency verification | Duplicate IDs, semantic conflicts with prior writes | Block + log |
| Temporal decay | Down-weights stale entries | Reduce weight, not quarantine |

**Quarantine thresholds by capability:**
- `cap-05` (compliance): `0.3` — missing obligation = potentially catastrophic
- `cap-04` (supply chain): `0.5` — wrong PO = costly but recoverable via human review

**Write types:**
- `EXTERNAL` — regulatory docs, sensor feeds (highest scrutiny)
- `INFERRED` — agent-computed outputs: PO drafts, obligation extractions
- `OBSERVED` — pipeline intermediate states
- `HUMAN` — human-approved decisions (bypasses poisoning scan)
- `SYNTHETIC` — test/eval data

## Capability × memory matrix

| Capability | Episodic | Semantic | Procedural | SSGM governed |
|-----------|---------|---------|-----------|--------------|
| Cap-01 Decision Intelligence | ✅ audit trail | ✅ doc retrieval | — | — |
| Cap-02 Agentic Engineering | ✅ security events | — | ✅ routing rules | — |
| Cap-03 Agentic Commerce | ✅ order events | ✅ catalog search | ✅ intent routing | — |
| Cap-04 Autonomous Operations | ✅ PO audit trail | — | — | ✅ PO drafts (0.5) |
| Cap-05 Compliance Intelligence | ✅ obligation events | ✅ reg. chunks | — | ✅ obligations (0.3) |

## Research basis

- **SSGM** (arXiv 2603.11768) — Self-supervised generative memory with consistency verification and temporal decay
- **A-MemGuard** (arXiv 2510.02373) — Adversarial memory poisoning detection via injection pattern scanning
- **A-MEM** — Agentic memory with self-linking and context-aware retrieval
