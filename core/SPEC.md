# SPEC-CORE: Shared Infrastructure
# BriefingScript v1.0 — Machine-readable · Human-reviewed · Agent-executable
# Status: APPROVED — BUILD THIS FIRST
# Codex-ready: YES

---

## goal_and_why

**Goal:** Build the shared infrastructure that all 5 capabilities depend on. Every capability imports from `core/`. Nothing is duplicated across capabilities.

**Why:** A single, well-governed core prevents the "integration crisis" documented in enterprise AI deployments — where micro-agents operate in silos, duplicating logic and creating inconsistent governance. The core provides: the orchestration base, MCP connectivity, memory layers, evaluation scorecard, 5-gate governance engine, and observability.

---

## modules

### core/orchestration — LangGraph base

```python
# Base state that every capability extends
class BaseAgentState(TypedDict):
    run_id: str
    session_id: str
    capability_id: str          # cap-01 through cap-05
    messages: list[BaseMessage]
    current_agent: str
    agent_hops: list[AgentHop]
    error_state: str | None
    human_approved: bool | None
    audit_trail: list[AuditEvent]
    cost_tokens: int
    latency_ms: float

# Base graph builder with shared nodes
class BaseCapabilityGraph:
    def build(self) -> CompiledStateGraph: ...
    def add_human_gate(self, node_name: str, threshold_fn: Callable) -> None: ...
    def add_eval_node(self, metrics: list[str]) -> None: ...
    def add_cost_telemetry(self) -> None: ...
```

### core/mcp — Connector registry

```python
# All MCP connectors registered here
# Capabilities declare which connectors they need in their spec
# Core validates connectivity at startup

class MCPRegistry:
    def register(self, name: str, server: MCPServer) -> None: ...
    def get(self, name: str) -> MCPServer: ...
    def health_check(self) -> dict[str, bool]: ...

class MCPServer:
    name: str
    url: str | None
    tools: list[MCPTool]
    mock_mode: bool  # True in development

# Every MCP server has a mock implementation for testing
# Production server configured via environment variable: MCP_{NAME}_URL
```

### core/memory — Three memory layers

```python
# Episodic: past events, sessions, actions (PostgreSQL + pgvector)
class EpisodicMemory:
    def store(self, event: MemoryEvent) -> str: ...
    def retrieve_similar(self, query: str, k: int = 5) -> list[MemoryEvent]: ...
    def get_session_history(self, session_id: str) -> list[MemoryEvent]: ...

# Semantic: knowledge, facts, documents (pgvector index)
class SemanticMemory:
    def index(self, documents: list[Document]) -> None: ...
    def search(self, query: str, k: int = 10, filters: dict = None) -> list[Chunk]: ...
    def hybrid_search(self, query: str, k: int = 10) -> list[Chunk]: ...  # semantic + BM25

# Procedural: learned patterns, routing rules (Redis)
class ProceduralMemory:
    def store_pattern(self, key: str, pattern: dict, ttl: int = None) -> None: ...
    def get_pattern(self, key: str) -> dict | None: ...
    def increment_usage(self, key: str) -> None: ...
```

### core/evals — Common evaluation scorecard

```python
# Every capability has capability-specific metrics
# These are the 5 metrics EVERY capability must report

COMMON_METRICS = [
    "task_success_rate",        # did the agent complete the task?
    "human_override_rate",      # how often does the human reject/modify?
    "cost_per_task_usd",        # total token cost
    "response_latency_p95_ms",  # end-to-end latency
    "hallucination_rate",       # ungrounded claims (LLM-as-judge)
]

class EvalSuite:
    def run(self, capability_id: str, test_set: list[TestCase]) -> EvalReport: ...
    def run_common(self, results: list[AgentResult]) -> CommonMetrics: ...
    def run_capability_specific(self, capability_id: str, results: list) -> dict: ...
    def check_gates(self, report: EvalReport) -> GateResult: ...  # pass/fail/block
```

### core/governance — 5-gate approval engine

```yaml
gates:
  gate_1_use_case:
    question: "Is this task worth automating or augmenting?"
    criteria:
      - high_frequency: bool     # > N times per week
      - high_friction: bool      # significant human time cost
      - addressable_data: bool   # data exists and is accessible
      - clear_kpi: bool          # measurable success metric defined
    outcome: PROCEED | HOLD | REJECT

  gate_2_data:
    question: "Can the system see the right data safely?"
    criteria:
      - permissions_mapped: bool
      - provenance_visible: bool
      - red_data_excluded: bool
      - privacy_assessed: bool
    outcome: PROCEED | HOLD | REJECT

  gate_3_action:
    question: "Can the agent act safely?"
    criteria:
      - tool_contracts_defined: bool
      - rollback_path_exists: bool
      - approval_rules_set: bool
      - escalation_tree_defined: bool
    outcome: PROCEED | HOLD | REJECT

  gate_4_quality:
    question: "Is performance better than status quo?"
    criteria:
      - eval_pass_rate: float    # >= capability threshold
      - hallucination_within_budget: bool
      - latency_within_budget: bool
      - cost_within_budget: bool
    outcome: PROCEED | HOLD | REJECT

  gate_5_scale:
    question: "Can it operate reliably in production?"
    criteria:
      - monitoring_live: bool
      - incident_response_defined: bool
      - rollback_tested: bool
      - cost_controls_set: bool
    outcome: PROCEED | HOLD | REJECT
```

### core/observability — OTEL + cost telemetry

```python
# Every agent hop is traced
# Every LLM call logs: model, tokens_in, tokens_out, latency_ms, cost_usd

class CostTelemetry:
    def record_llm_call(self, model: str, tokens_in: int, tokens_out: int,
                        latency_ms: float, agent_name: str, run_id: str) -> None: ...
    def get_run_cost(self, run_id: str) -> float: ...
    def alert_budget_exceeded(self, run_id: str, threshold_usd: float) -> None: ...

# Model pricing config — verified June 2026 (per 1M tokens, USD)
# CRITICAL: Claude 3.x retired April 2026. GPT-4o retired Feb 2026. Never use those strings.
MODEL_PRICING = {
    # Anthropic — current (June 2026)
    "claude-opus-4-8":              {"input": 15.00, "output": 75.00},  # flagship
    "claude-sonnet-4-6":            {"input": 3.00,  "output": 15.00},  # default
    "claude-haiku-4-5-20251001":    {"input": 0.80,  "output": 4.00},   # subagents
    # OpenAI — current (June 2026)
    "gpt-5.5":                      {"input": 10.00, "output": 30.00},  # frontier
    "gpt-5":                        {"input": 5.00,  "output": 20.00},  # strong baseline
    "gpt-5-mini":                   {"input": 0.40,  "output": 1.60},   # cost-efficient
}
# Agentic multiplier: multi-agent tasks use 5–30x more tokens than single-turn chat.
# Real case: Uber exhausted its full-year 2026 AI budget by April after Claude Code
# adoption jumped 32%→84% across ~5,000 engineers. Budget accordingly.
# Rule: alert when run_cost > session_budget * 0.8
```

---

## implementation_tasks

```
TASK-CORE-01: BaseAgentState + BaseCapabilityGraph (LangGraph)
  Files: core/orchestration/base_graph.py, core/orchestration/base_state.py

TASK-CORE-02: MCPRegistry + base MCPServer class + mock implementations
  Files: core/mcp/registry.py, core/mcp/base.py, core/mcp/mocks/

TASK-CORE-03: EpisodicMemory (PostgreSQL + pgvector)
  Files: core/memory/episodic.py

TASK-CORE-04: SemanticMemory (pgvector + BM25 hybrid search)
  Files: core/memory/semantic.py

TASK-CORE-05: ProceduralMemory (Redis)
  Files: core/memory/procedural.py

TASK-CORE-06: Common EvalSuite + 5 common metrics
  Files: core/evals/suite.py, core/evals/metrics.py

TASK-CORE-07: 5-gate governance engine
  Files: core/governance/gates.py, core/governance/human_gate.py

TASK-CORE-08: OTEL setup + CostTelemetry
  Files: core/observability/telemetry.py, core/observability/cost.py

TASK-CORE-09: Shared Pydantic schemas
  Files: core/schemas/base.py, core/schemas/events.py, core/schemas/memory.py

TASK-CORE-10: Settings + config management
  Files: core/utils/settings.py, .env.example

TASK-CORE-11: Database setup scripts (PostgreSQL + pgvector + Redis)
  Files: scripts/setup_db.py, scripts/docker-compose.yml

TASK-CORE-12: Health check CLI
  Files: scripts/health_check.py
```

---

## codex_instructions

```
Build TASK-CORE-01 through TASK-CORE-12 in order.
No capability implementation starts until core passes all its own tests.
Test file: core/tests/test_core.py — must achieve 100% import success and core health check pass.
Every class uses dependency injection for the LLM client (no hardcoded model calls).
Settings are loaded from environment variables via core/utils/settings.py (pydantic-settings).
Docker Compose provides: PostgreSQL (+ pgvector), Redis, and optional Neo4j for Cap-05.
The mock MCP implementations must behave identically to real ones for all test cases.
```

---

## frontier_improvements
# Added: 2026-06-17 — based on Frontier Agentic AI Engineering Patterns research
# See: docs/adr/ADR-002-harness-engineering.md
# See: docs/adr/ADR-003-protocol-layering.md

### core/harness — NEW module (ADR-002)

```
core/harness/
├── loop.py           # Canonical agentic loop + stop conditions + CRP
├── memory.py         # SSGM governed memory + A-MemGuard defense
├── sensors.py        # Computational + inferential sensor registry
├── risk.py           # Tool risk taxonomy + permission matrix
└── golden_principles.py  # Anti-drift mechanism + artifact scoring
```

Primary types (see loop.py):
  ToolRiskTier:          READ_ONLY | IDEMPOTENT | FINANCIAL | DESTRUCTIVE
  LoopState:             iteration/budget/stop-condition tracking
  ConsultationRequestPack: structured CRP with proposed solution
  SensorResult:          passed/score/blocking per sensor run
  SSGMGovernor:          SSGM memory validation pipeline (memory.py)

### updated_common_metrics (core/evals)

The 5 common metrics expand to 8 following frontier research:

```python
COMMON_METRICS = [
    # Original 5 (unchanged)
    "task_success_rate",
    "human_override_rate",
    "cost_per_task_usd",
    "response_latency_p95_ms",
    "hallucination_rate",

    # New: CLEAR framework additions (frontier eval, 2026)
    "trajectory_success_rate",      # did the full multi-step chain succeed?
    "cross_turn_state_accuracy",    # ~20% blind spot: arXiv 2606.10315
    "harness_security_score",       # injection/timeout/over-tooling defense
]
```

CLEAR framework (Cost / Latency / Efficiency / Accuracy / Reliability):
  - cost: `cost_per_task_usd` with OTEL `gen_ai.*` hop-level attribution
  - latency: `response_latency_p95_ms` (p50 and p99 also tracked)
  - efficiency: task_success_rate / cost_per_task_usd (value per dollar)
  - accuracy: hallucination_rate + trajectory_success_rate
  - reliability: cross_turn_state_accuracy + harness_security_score

### otel_genai_conventions
OTEL GenAI semantic conventions (v1.41, still Development status as of June 2026).
Add to core/observability/telemetry.py:

```python
# gen_ai.* attributes — hop-level attribution
span.set_attribute("gen_ai.system",        "anthropic")
span.set_attribute("gen_ai.request.model", model)
span.set_attribute("gen_ai.usage.input_tokens",  tokens_in)
span.set_attribute("gen_ai.usage.output_tokens", tokens_out)
span.set_attribute("gen_ai.usage.cache_read_input_tokens",    cache_read)
span.set_attribute("gen_ai.usage.cache_creation_input_tokens", cache_write)
span.set_attribute("gen_ai.cost.usd", cost_usd)
span.set_attribute("gen_ai.operation.name", "chat")  # or "generate"

# Agent-specific spans
span.set_attribute("gen_ai.agent.name", agent_name)
span.set_attribute("gen_ai.agent.hop_number", hop_number)
span.set_attribute("gen_ai.tool.name",   tool_name)
span.set_attribute("gen_ai.tool.tier",   tool_risk_tier)  # ADR-002
```

Note: OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai required to enable `gen_ai.*`.
Attribute names are subject to change until GenAI conventions reach Stable.

### mcp_migration_plan (ADR-003)

Current target: MCP spec 2025-11-25 (stable).
Migration target: MCP spec 2026-07-28 (RC final July 28, 2026).

All MCP servers must be stateless NOW:
  - Request handlers must not rely on server-side session state
  - Session data passed as explicit handles per request
  - Annotate stateful patterns: `# MCP-MIGRATE: session-to-handle`

Phase 2 (post July 28):
  - Drop `Mcp-Session-Id`; add `Mcp-Method`/`Mcp-Name` routing headers
  - Move tasks to Tasks extension polling model
  - Enable `ttlMs`/`cacheScope` on read-only tools
  - Add Cloudflare Workers / Vercel / Lambda deployment manifests

### new_core_tasks
```
TASK-CORE-13: core/harness/loop.py — canonical loop + stop conditions + CRP
TASK-CORE-14: core/harness/memory.py — SSGM + A-MemGuard (already scaffolded)
TASK-CORE-15: core/harness/sensors.py — sensor registry + eval wiring
TASK-CORE-16: OTEL GenAI conventions (gen_ai.* attributes) in observability
TASK-CORE-17: MCP stateless annotations (MCP-MIGRATE comments + compliance check)
TASK-CORE-18: Braintrust A/B eval gates + regression testing in CI
```
