# Stack Reference
# ai-native-capabilities — verified June 2026
# Every version, deprecation, and decision rationale documented.

---

## Language runtime

**Python 3.13** (minimum; 3.14 supported)

- 3.13 is the stable production sweet spot in June 2026 — strong package support, ~11% faster than 3.12, free-threaded mode (GIL-optional via `python3.13t`) now available for CPU-bound agent parallelism
- 3.14 (released October 2025) is production-ready for greenfield; template strings (t-strings) reduce prompt-injection risk
- 3.12 is in security-only mode; not recommended for new projects
- LangGraph 1.0.5 explicitly supports Python 3.13 (announced in January 2025 changelog)
- Rationale for not using 3.14 as minimum: major AI libraries (LangGraph, Anthropic SDK, OpenAI SDK) have production parity on 3.13; 3.14 adoption in the ecosystem is still maturing

**TypeScript** for MCP servers (official SDK: `@modelcontextprotocol/sdk`)

---

## Orchestration

**LangGraph 1.0.5** (October 17, 2025 GA; January 12, 2026 patch release)

What changed at 1.0: stable API commitment (no breaking changes until 2.0), deferred node execution, cross-thread memory support, improved interrupt() ergonomics, LangGraph Studio v2 (runs locally without desktop app). LangGraph Platform went GA May 14, 2025.

Production users at 1.0: Uber, LinkedIn, Klarna, JP Morgan, Blackrock, Cisco (cited in LangChain 1.0 announcement).

Why LangGraph over alternatives:
- Only framework with first-class durable execution (checkpointing) + human-in-the-loop interrupt() in the same runtime
- Cap-04 (Autonomous Operations) requires state persistence across process restarts — this is a hard requirement, not a preference
- LangSmith integration is native and deepest for LangGraph workflows; LangGraph Studio enables replay against new model versions
- AutoGen/Semantic Kernel: Microsoft retired both, replaced with Microsoft Agent Framework 1.0 (April 2026). Not using MAF because we want cloud-agnostic.
- CrewAI: faster to prototype, less control. Suitable for Cap-02 rapid prototyping; LangGraph for production.

**Also available: `langchain>=1.0.0`** — LangChain 1.0 GA October 22, 2025. Used as the "developer experience layer" for agent building blocks; LangGraph as the runtime.

---

## Protocol

**MCP spec 2025-11-25** (current stable as of June 2026)

Transport:
- **Streamable HTTP** (production): server runs as independent process, multiple concurrent clients, OAuth 2.1 auth, horizontal scaling. Introduced in spec 2025-03-26; replaced legacy HTTP+SSE which was deprecated the same day.
- **stdio** (local development only): MCP server runs as subprocess, communicates via stdin/stdout. Fast, no network config.

Authentication: OAuth 2.1 + PKCE (RFC 8707 Resource Indicators). MCP servers are classified as OAuth Resource Servers.

Governance: Donated to Linux Foundation Agentic AI Foundation (December 2025). Co-founded with Block and OpenAI; backed by Google, Microsoft, AWS, Cloudflare, Bloomberg.

Stats (March 2026): 97M monthly SDK downloads, 81,000+ GitHub stars, every major AI vendor supports it.

Next spec: **2026-07-28 RC** (May 21, 2026 release candidate) — stateless protocol core, Extensions framework, Tasks extension, MCP Apps, auth hardening, formal deprecation policy. Final spec: July 28, 2026. **Do not depend on RC features in production yet.**

Official SDKs: Python, TypeScript, Go, Kotlin, Java, C#, Swift, Rust, Ruby, PHP.

---

## Models

### Anthropic Claude — current strings (June 2026)

| Model | API string | Use case | Cost (per 1M tokens) |
|---|---|---|---|
| Claude Opus 4.8 | `claude-opus-4-8` | Flagship; complex reasoning; long-horizon agentic coding | $15 in / $75 out |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` | **Default**; 79.6% SWE-bench; balanced cost/quality | $3 in / $15 out |
| Claude Haiku 4.5 | `claude-haiku-4-5-20251001` | Routing, classification, high-volume subagents | $0.80 in / $4 out |
| Claude Fable 5 | `claude-fable-5` | GA June 9, 2026; frontier; most capable widely-released | pricing TBD |

**Deprecated — never use these strings:**
- `claude-3-opus-*`, `claude-3-sonnet-*`, `claude-3-haiku-*`: retired January–April 2026
- `claude-3-5-sonnet-*`, `claude-3-5-haiku-*`: retired February 19, 2026
- `claude-3-7-sonnet-*`: retired February 19, 2026
- `claude-sonnet-4-20250514`, `claude-opus-4-20250514`: retiring June 15, 2026

**Routing logic for this project:**
- Supervisor agent: `claude-sonnet-4-6` (cost/quality balance)
- Subagents (routing, classification, extraction): `claude-haiku-4-5-20251001`
- Complex synthesis, verification: `claude-opus-4-8`
- Configuration: `settings.py` — never hardcode model strings

### OpenAI — current strings (June 2026)

| Model | Use case |
|---|---|
| `gpt-5.5` | Frontier (April 23, 2026); highest quality; highest cost |
| `gpt-5` | Strong agentic and coding baseline (August 2025) |
| `gpt-5-mini` | Cost-efficient; comparable to GPT-4o on most tasks |
| `gpt-5-nano` | API-only; cheapest; routing/classification |

**Deprecated — never use these strings:**
- `gpt-4o-*`: retired February 2026
- `o3`, `o4-mini`: retired or retiring mid-2026

---

## Memory

### pgvector 0.7.x + pgvectorscale

pgvector runs inside PostgreSQL — no separate service, no sync layer, native SQL joins. The 0.7.x release (current 2026) includes parallel index builds, improved HNSW performance, better memory management.

**When to use pgvector:**
- Production-grade under ~50M vectors with correct HNSW tuning
- When you already run PostgreSQL (this project uses it for audit trail, LangGraph checkpoints, episodic memory — adding vectors to the same instance is the right call)
- p50 latency at 1M vectors with HNSW: 5–8ms on NVMe storage

**When to switch to Qdrant:**
- 50M+ vectors, high throughput requirement
- ~850 QPS at p95 ~8ms on 1M vectors (self-hosted, Rust-based)
- Available as `[qdrant]` optional dependency in this project

Weaviate: dropped from consideration due to v3→v4 breaking changes and GraphQL verbosity overhead.

### Memory architecture (three layers)

```
Episodic memory:     PostgreSQL + pgvector
                     Past events, sessions, agent actions, brief outcomes
                     Schema: episodic_memory table (init_db.sql)

Semantic memory:     pgvector index over document corpus
                     Chunked documents, hybrid search (semantic + BM25)
                     Schema: document_chunks table (init_db.sql)

Procedural memory:   Redis
                     Learned patterns, routing rules, query heuristics
                     TTL-governed; eviction policy: allkeys-lru

Long-term cross-     LangGraph built-in store (cross-thread memory)
thread memory:       Added in LangGraph January 2025 changelog
                     Uses semantic search for relevant memory retrieval
```

---

## Evals

### Primary: LangSmith (per-capability integration)

Strongest choice when LangGraph is the runtime. Reasons:
- Auto-instrumentation: one environment variable, all runs traced
- LangGraph Studio: visualize graph, set breakpoints, modify state mid-run, replay against new model versions — the best agent IDE available
- Dataset management: build eval datasets from production traces
- Pairwise annotation queues (December 2025): compare two agent outputs side-by-side

**Limitation:** auto-instrumentation is mostly LangChain/LangGraph workflows; not available for self-hosting (cloud only).

### Secondary: Arize Phoenix OSS (RAG evals + framework-agnostic)

Best-in-class RAG evaluation. Framework-agnostic. OTEL-native. Self-hostable. Built-in RAGAS integration. 50M evaluations/month, 1T+ spans logged. Use for RAG-specific metrics (context precision, recall, faithfulness) and production drift monitoring.

### CI gates: custom scorecard per capability

Every capability has a `evals/suite.py` with YAML-defined metrics and blocking thresholds. Runs on every PR via GitHub Actions. PR is blocked if any blocking metric fails.

### Optional: Braintrust

Structured A/B eval runs with CI/CD gates. Free tier: 1M spans/month, 10K evals. Best for comparing model versions on the same eval set.

---

## Observability

**OpenTelemetry (OTLP)** — vendor-neutral; export to Datadog, Honeycomb, Grafana Cloud, New Relic, or self-hosted Prometheus+Grafana.

**Cost telemetry** — every LLM call logs: model, tokens_in, tokens_out, latency_ms, cost_usd, agent_name, run_id. Alerts at 80% of session/run/monthly budget thresholds. The agentic multiplier (5–30x vs single-turn) means a budget overshoot can happen in hours, not months.

---

## Security

**bandit 1.8+** — Python AST-based security scanner. Mandatory on all agent-generated code (Cap-02 security gate).

**semgrep 1.90+** — pattern-based; catches OWASP Top 10 patterns bandit misses. Runs alongside bandit in the Cap-02 security gate.

**MCP security:** OAuth 2.1 + PKCE per spec. Least-privilege tool permissions. All MCP server connections audited. Tool annotations (read-only vs write) declared in server manifests.

**Audit trail:** append-only PostgreSQL table (`audit_trail`). UPDATE and DELETE revoked at database level. Every agent action, human approval, and cost event logged immutably.

---

## CI

**GitHub Actions** — eval suite on every PR. Five capability eval jobs + core tests run in parallel. PR comment with eval summary posted automatically. Cost delta per run reported. Blocking metrics prevent merge.

**Requires `workflow` scope** on GitHub PAT to push `.github/workflows/` files. See CONTRIBUTING.md.

---

## Decisions log (ADRs)

| ADR | Decision | Rationale |
|---|---|---|
| ADR-001 | Spec-driven development | Unambiguous Codex/Claude Code instructions; measurable definition of done |
| ADR-002 (planned) | pgvector over Pinecone/Weaviate | Same Postgres instance, lower ops complexity, adequate for <50M vectors |
| ADR-003 (planned) | LangGraph over Microsoft Agent Framework | Cloud-agnostic; best human-in-the-loop; deepest observability with LangSmith |
| ADR-004 (planned) | MCP Streamable HTTP over custom tool integrations | Industry standard, 97M monthly downloads, vendor-neutral |
| ADR-005 (planned) | Dual eval (LangSmith + Arize Phoenix) | LangSmith for depth in LangGraph; Phoenix for RAG metrics and OTel-native export |

---

## Updates — June 17, 2026 (frontier research integration)

### New: Harness Engineering layer (ADR-002)

```
core/harness/      Canonical agentic loop, SSGM governed memory,
                   sensor registry, tool risk taxonomy, CRP format
```

**Agent = Model + Harness** (the defining 2026 equation).
The harness quality, not the model quality, is the primary differentiator
between the 11% of enterprises running agents at genuine production scale
and the 88% still stuck at POC.

### New: Protocol stack (ADR-003)

```
Tool access:        MCP 2025-11-25 (stable) → 2026-07-28 (RC final July 28)
                    All servers: stateless request handlers from day one
                    Routing: Mcp-Method/Mcp-Name headers (2026-07-28)
                    Hosting: Cloudflare Workers/Vercel/Lambda (post-stateless)

Agent coordination: A2A v1.0 (Linux Foundation, GA March 2026, 150+ orgs)
                    Signed Agent Cards, gRPC+JSON-RPC, multi-tenancy
                    Used in: Cap-03 (Sparky↔Marty), Cap-04 (exception events)

Commerce (Cap-03):  ACP (OpenAI+Stripe) | UCP (Google+Shopify) — configurable
                    AP2 (W3C Verifiable Credentials payment mandates)
                    WebMCP (W3C, Chrome preview) — optional evaluation

⚠ Naming: "UCP" = Universal Commerce Protocol (not "Context Protocol")
  MCP remains the tool/context protocol. These are complementary.
```

### Updated: Evals

```
Primary:     LangSmith (LangGraph-native) + LangGraph Studio (state replay)
RAG evals:   Arize Phoenix OSS (OTEL-native, self-hostable, RAGAS integration)
Trajectory:  Agent-as-a-Judge (Zhuge et al.) — full trajectory, not just output
CI gates:    Braintrust (A/B + regression; @braintrust/otel; 1M spans/month free)
Framework:   CLEAR (Cost/Latency/Efficiency/Accuracy/Reliability)
Judge rule:  Judge model MUST differ from agent model family (anti-self-preference)
Blind spot:  Cross-turn state evals — catches ~20% P0 failures missed by output evals

NEW common metrics (8 total):
  task_success_rate · human_override_rate · cost_per_task_usd
  response_latency_p95_ms · hallucination_rate
  + trajectory_success_rate · cross_turn_state_accuracy · harness_security_score
```

### Updated: Memory

```
Flat retrieval:  pgvector 0.7.x + pgvectorscale (unchanged)
Graph layer:     Neo4j/FalkorDB for Cap-01/Cap-05 multi-hop reasoning
                 Property graph: Regulation→Article→Obligation→UseCase
Self-linking:    A-MEM pattern (arXiv 2502.12110) — Zettelkasten notes
Governance:      SSGM (arXiv 2603.11768) — consistency/decay/access control
Poisoning def:   A-MemGuard (arXiv 2510.02373) — quarantine_threshold per cap
Temporal:        Decay weights + valid_from/valid_until on all entries

SSGM quarantine thresholds by capability:
  Cap-05 (compliance): 0.3  — existential risk if obligation missed
  Cap-04 (operations): 0.5  — financial risk if PO from bad memory
  Cap-01 (decision):   0.6  — quality risk if brief from stale memory
```

### Updated: SWE-bench position (Cap-02)

```
SWE-bench Verified: SATURATED + partially contaminated (Claude Fable 5: 95.0%)
                    OpenAI stopped reporting it Feb 2026.
SWE-bench Pro:      Honest measure (standardized, 1,865 tasks, 250-turn scaffold)
                    Opus 4.6 thinking: ~51.9%. Same model varies 15-16pts by harness.
                    → Harness quality matters as much as model quality.
Cap-02 evals:       Private-codebase eval set + DORA metrics + FP rate
                    NOT SWE-bench Verified. Never cite vendor numbers.
```
