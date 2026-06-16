# SPEC-01: Decision Intelligence
# BriefingScript v1.0 — Machine-readable · Human-reviewed · Agent-executable
# Status: APPROVED
# Codex-ready: YES

---

## goal_and_why

**Goal:** Build an agentic decision intelligence system that transforms scattered internal knowledge into cited, uncertainty-labelled, board-ready intelligence — in real time.

**Why:** The single most documented enterprise AI gap is decision latency under information overload. McKinsey (2025): only 39% of organisations reach EBIT impact from AI. The root cause is not model quality but *retrieval quality, memory, and synthesis*. Morgan Stanley's system achieved 98% advisor-team adoption and lifted document access from 20% to 80% precisely because it solved retrieval, citation, and uncertainty — not because it added features. This MVP solves the same problem at the C-level and strategic decision-making layer.

**Business value:**
- Reduce time-to-insight for strategic decisions from days to minutes
- Ground executive decisions in cited, verifiable evidence rather than intuition or stale reports
- Surface blind spots across internal knowledge that no single human could hold in working memory
- Create an auditable decision trail for governance and board accountability

---

## what_and_success_criteria

### What this system does

1. Accepts a strategic question in natural language (e.g. "What are our three biggest supply chain risks entering Q3 and what have competitors done to address them?")
2. An orchestrator agent decomposes the question into sub-queries
3. A retrieval agent executes hybrid search (semantic + lexical + metadata) over the governed knowledge corpus
4. An analysis agent synthesises, cross-references, and identifies gaps
5. A verification agent checks every factual claim against the source
6. Output is a structured brief: answer + citations + confidence level + uncertainty flags + recommended follow-up actions
7. Episodic memory stores every session brief for future reference and pattern learning
8. Human reviews and approves before any externally-actioned decision

### Success criteria (definition of done)

All of the following must pass before this capability is considered production-ready:

```yaml
eval_gates:
  citation_accuracy:
    description: Every factual claim links to a verifiable source in the corpus
    threshold: >= 0.95
    measurement: automated citation verification against indexed documents

  hallucination_rate:
    description: Rate of ungrounded claims in final brief
    threshold: <= 0.02
    measurement: LLM-as-judge + human spot-check on 10% sample

  retrieval_recall:
    description: Fraction of relevant documents surfaced for a given query
    threshold: >= 0.85
    measurement: against labelled eval set of 50 query/relevant-docs pairs

  source_coverage:
    description: Document access rate (% of corpus accessible to retrieval)
    threshold: >= 0.80
    measurement: index coverage audit (target: Morgan Stanley benchmark)

  response_latency_p95:
    description: Time from query submission to full brief delivery
    threshold: <= 30 seconds
    measurement: traced end-to-end including all agent hops

  human_override_rate:
    description: Rate at which human reviewers reject or significantly alter the AI brief
    threshold: <= 0.15
    measurement: logged human review actions

  brief_usefulness:
    description: User-rated usefulness of the brief (1-5 scale)
    threshold: >= 4.0
    measurement: post-session feedback widget

  cost_per_brief:
    description: Total token cost per completed brief
    threshold: <= $0.50
    measurement: OTEL cost telemetry (tokens × model rate × agentic multiplier)
```

### Anti-goals (explicit non-requirements for v1)

- Does NOT make autonomous decisions or take autonomous actions
- Does NOT connect to real-time market data feeds (v2)
- Does NOT persist user identity across sessions (v1 is stateless per session for privacy)
- Does NOT replace human judgment — it augments it

---

## all_needed_context

### Reference architecture

Morgan Stanley pattern (source: OpenAI case study, 2024):
- Eval-first: every use case tested before deployment
- Forced citations: no answer without a source reference
- Zero retention: no company data retained in model training
- Human accountability: advisor reviews before client-facing action
- Retrieval over generation: retrieve > hallucinate always

Ramp Glass pattern (source: Midas Tools analysis, April 2026):
- Role-aware context pre-loading: every role gets relevant context at session start
- "Aha moment" design: first interaction must produce genuine value
- L0→L3 proficiency ladder: system adapts to user sophistication level

SASE BriefingScript (source: Hassan et al., ACM 2026):
- BriefingScript as the specification that drives agent execution
- Humans author high-quality briefs; agents execute against them
- Consultation Request Packs (CRPs) allow agents to request clarification

### Agent graph

```
User Query
    │
    ▼
[Supervisor Agent]
    │ decomposes query into sub-tasks
    │ checks permission / data gate
    │ routes to specialist agents
    ├──────────────────────────────┐
    ▼                              ▼
[Retrieval Agent]          [Web Research Agent]
    │                              │  (optional, external)
    │ hybrid search:               │  only if gap in corpus
    │  - semantic (pgvector)       │
    │  - lexical (BM25)            │
    │  - metadata filter           │
    │                              │
    └──────────┬───────────────────┘
               ▼
    [Analysis & Synthesis Agent]
        │ cross-references sources
        │ identifies contradictions
        │ gaps → uncertainty flags
        │ structures brief
        ▼
    [Verification Agent]
        │ checks every factual claim
        │ against cited source
        │ flags unverifiable claims
        ▼
    [Brief Assembly Agent]
        │ formats output:
        │  - executive summary
        │  - key findings + citations
        │  - confidence scores
        │  - uncertainty flags
        │  - recommended next actions
        ▼
    [Human Review Gate]
        │ human approves / edits / rejects
        │ decision logged to audit trail
        ▼
    [Episodic Memory Store]
        │ stores brief + outcome
        │ learns patterns across sessions
        ▼
    OUTPUT: Structured Brief
```

### State schema

```python
class DecisionBriefState(TypedDict):
    # Input
    query: str
    session_id: str
    user_role: str
    corpus_scope: list[str]         # which knowledge sources to search

    # Orchestration
    sub_queries: list[str]
    retrieval_results: list[RetrievalResult]
    analysis_notes: str
    verification_flags: list[VerificationFlag]

    # Output
    executive_summary: str
    key_findings: list[Finding]     # each Finding has: claim, source, confidence
    uncertainty_flags: list[str]
    recommended_actions: list[str]
    overall_confidence: float       # 0.0 - 1.0

    # Control
    human_approved: bool
    human_edits: str | None
    audit_trail: list[AuditEvent]
    cost_tokens: int
```

### Memory architecture

```
Session Memory (working):     LangGraph state — lives for duration of one session
Episodic Memory (long-term):  PostgreSQL + pgvector — past briefs, outcomes, user edits
Semantic Memory (knowledge):  pgvector index over corpus — chunked, embedded, metadata-tagged
Procedural Memory (patterns): Redis — learned query patterns, routing heuristics
```

### MCP connectors required

```yaml
connectors:
  - name: internal-knowledge-base
    type: mcp-server
    description: Index of internal documents (strategy papers, board decks, financials, research)
    tools: [search, get_document, list_recent, get_metadata]

  - name: web-research
    type: mcp-server
    description: Controlled web search for external evidence gaps
    tools: [search, fetch_url]
    guardrail: only triggered when internal corpus has < 0.3 confidence

  - name: episodic-memory
    type: mcp-server
    description: Past decision briefs and outcomes
    tools: [store_brief, retrieve_similar, get_session_history]

  - name: audit-log
    type: mcp-server
    description: Immutable audit trail for governance
    tools: [log_event, query_trail]
```

### Data requirements

- Internal corpus: minimum 100 documents to seed the system meaningfully
- Supported formats: PDF, DOCX, MD, TXT, HTML
- Chunk size: 512 tokens with 64-token overlap
- Embedding model: text-embedding-3-large (OpenAI) or claude equivalent
- Metadata schema: `{title, author, date, doc_type, access_tier, source}`
- Access control: document-level permissions checked before retrieval

---

## implementation_tasks

### Phase 1 — Core infrastructure (depends on: `core/` complete)

```
TASK-01-01: Implement pgvector index setup and document ingestion pipeline
  Acceptance: 100 test documents indexed, search returns results in < 2s
  Files: core/memory/vector_store.py, cap-01/tools/ingestor.py

TASK-01-02: Implement hybrid retrieval (semantic + BM25 + metadata filter)
  Acceptance: retrieval_recall >= 0.85 on eval set
  Files: cap-01/tools/retriever.py

TASK-01-03: Implement Supervisor Agent with query decomposition
  Acceptance: decomposes 20 test queries correctly, routes to right agents
  Files: cap-01/agents/supervisor.py

TASK-01-04: Implement Retrieval Agent
  Acceptance: calls hybrid retrieval, deduplicates, ranks by relevance
  Files: cap-01/agents/retrieval_agent.py

TASK-01-05: Implement Analysis & Synthesis Agent
  Acceptance: produces structured analysis with gap detection
  Files: cap-01/agents/analysis_agent.py

TASK-01-06: Implement Verification Agent
  Acceptance: citation_accuracy >= 0.95 on test brief set
  Files: cap-01/agents/verification_agent.py

TASK-01-07: Implement Brief Assembly Agent
  Acceptance: output matches BriefOutput schema, all fields populated
  Files: cap-01/agents/brief_agent.py

TASK-01-08: Wire LangGraph state machine connecting all agents
  Acceptance: end-to-end flow completes for 10 test queries
  Files: cap-01/agents/graph.py
```

### Phase 2 — Memory, governance, eval

```
TASK-01-09: Implement episodic memory store (brief storage + similarity retrieval)
  Files: cap-01/memory/episodic.py

TASK-01-10: Implement Human Review Gate with audit logging
  Acceptance: every brief requires human approval before action; logged
  Files: core/governance/human_gate.py, cap-01/agents/graph.py

TASK-01-11: Implement evaluation suite
  Acceptance: all 8 eval metrics run automatically on CI
  Files: cap-01/evals/suite.py

TASK-01-12: Implement cost telemetry (token counting per agent hop)
  Files: core/observability/cost_telemetry.py
```

### Phase 3 — Polish and demo

```
TASK-01-13: CLI demo runner (takes query, prints brief to terminal)
  Files: cap-01/demo.py

TASK-01-14: Seed dataset (100 documents for testing)
  Files: cap-01/tests/fixtures/corpus/

TASK-01-15: Cap-01 README with usage, architecture diagram, evidence
  Files: cap-01-decision-intelligence/README.md
```

---

## failure_modes_to_design_against

```yaml
failure_modes:
  confident_hallucination:
    description: Agent states a fact confidently that is not in any source
    mitigation: Verification agent blocks any claim without source; confidence < 0.7 triggers uncertainty flag
    test: inject 5 unanswerable questions; verify all flagged as uncertain

  stale_retrieval:
    description: Returns outdated document when newer version exists
    mitigation: Metadata date filter; recency weighting in ranking; TTL on index entries
    test: index doc v1 and v2 of same report; verify v2 is returned

  source_leakage:
    description: Retrieval crosses access tier boundaries
    mitigation: Document-level permission check before every retrieval
    test: query with low-privilege user; verify restricted docs not returned

  context_overflow:
    description: Too many retrieved chunks overwhelm the synthesis context
    mitigation: Dynamic context budget; rank and truncate to fit model window
    test: query that retrieves > 50 chunks; verify output quality maintained

  over_trust:
    description: Human uses brief without reading citations, acts on error
    mitigation: Human gate required; confidence scores prominently displayed; low-confidence briefs require explicit acknowledgment
    test: UX review of review gate flow
```

---

## eval_scorecard

```yaml
# Run with: python cap-01/evals/suite.py
# Runs automatically on every PR via .github/workflows/evals.yml

metrics:
  citation_accuracy:       { target: 0.95, weight: 0.25 }
  hallucination_rate:      { target: 0.02, weight: 0.25, lower_is_better: true }
  retrieval_recall:        { target: 0.85, weight: 0.20 }
  source_coverage:         { target: 0.80, weight: 0.10 }
  response_latency_p95_s:  { target: 30.0, weight: 0.05, lower_is_better: true }
  human_override_rate:     { target: 0.15, weight: 0.05, lower_is_better: true }
  brief_usefulness:        { target: 4.0,  weight: 0.05 }
  cost_per_brief_usd:      { target: 0.50, weight: 0.05, lower_is_better: true }

passing_threshold: weighted_score >= 0.85
blocking: [citation_accuracy, hallucination_rate]  # these alone block the PR
```

---

## reference_evidence

```yaml
evidence:
  - company: Morgan Stanley
    capability: RAG-based advisor knowledge augmentation
    result: 98% advisor-team adoption; document access 20% → 80%
    source: OpenAI case study (openai.com/index/morgan-stanley/)
    grade: P  # Partial — company + vendor reported, independently credible

  - company: Ramp
    capability: Role-aware AI interface (Glass) driving 99.5% employee adoption
    result: 99.5% active AI users; 84% using coding agents weekly
    source: Midas Tools analysis citing Ramp internal data (Apr 2026)
    grade: P

  - company: Moderna
    capability: Enterprise GPT factory — 750 internal GPTs
    result: 100% legal team adoption; 120 conversations/user/week
    source: OpenAI case study (openai.com/index/moderna/)
    grade: P

  - research: McKinsey State of AI 2025
    finding: 39% of organisations report enterprise EBIT impact; high performers redesign workflows end-to-end
    source: McKinsey Global Survey, Nov 2025 (n=1,993)
    grade: M

  - research: MIT NANDA GenAI Divide
    finding: 95% of GenAI pilots deliver no measurable P&L impact; root cause is learning/memory gap
    source: MIT Project NANDA, 2025 (n=150 exec interviews, 350 employees)
    grade: P  # contested methodology, directionally important
```

---

## codex_instructions

```
When implementing this spec:

1. Start with TASK-01-01 (vector store). Do not skip to agents before the retrieval layer works.
2. Use LangGraph StateGraph with TypedDict state (DecisionBriefState defined above).
3. Every agent is a pure function: (state: DecisionBriefState) -> DecisionBriefState
4. MCP connectors go in cap-01/tools/ as separate modules, one file per connector.
5. Do NOT hardcode model names — use config/settings.py for model selection.
6. Every function that calls an LLM must log: model, tokens_in, tokens_out, latency_ms.
7. The Human Review Gate is NOT optional and must NOT be bypassable in production.
8. Run `python cap-01/evals/suite.py` before every PR. Do not submit if blocking metrics fail.
9. Follow the state schema exactly — do not add fields without updating this spec.
10. When uncertain, open a Consultation Request (comment in code: # CRP: <question>) rather than guessing.
```
