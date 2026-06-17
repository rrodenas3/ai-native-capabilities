# Agent Routing Guide
# ai-native-capabilities — verified June 2026
# Which model, which pattern, for which task.

---

## The routing decision tree

Before choosing a model or orchestration pattern, answer these questions in order:

```
1. Is the task procedural and bounded?
   YES → single well-prompted model (arXiv 2604.27891: outperforms orchestration)
   NO  → continue

2. Does it require state across multiple steps or a restart?
   YES → LangGraph stateful graph (Cap-04 pattern)
   NO  → continue

3. Does it require parallel specialised work?
   YES → multi-agent (supervisor + specialist pattern)
   NO  → single agent with tool access

4. Does it require human approval at any point?
   YES → LangGraph interrupt() gate (mandatory, not optional)
   NO  → continue to model selection
```

**The most common mistake:** adding orchestration complexity to tasks that a single
well-prompted model handles better. The 2026 arXiv paper (2604.27891) showed that
in-context prompting outperformed LangGraph orchestration on procedural tasks across
all 15 tested pairings. Add agents when the task genuinely needs them.

---

## Model routing — June 2026

### Primary tier — Anthropic Claude

| Task type | Model | Rationale |
|---|---|---|
| Executive briefs, synthesis, board summaries | `claude-opus-4-8` | Highest reasoning quality; long-form coherence |
| Default agent reasoning, analysis, planning | `claude-sonnet-4-6` | 79.6% SWE-bench; $3/$15 per MTok; best value |
| Intent classification, routing, metadata | `claude-haiku-4-5-20251001` | Fast; cheap; adequate for bounded classification |
| High-volume subagent calls (Cap-03 Sparky) | `claude-haiku-4-5-20251001` | Cost control on volume; escalate to Sonnet if confidence < 0.7 |
| Security verification (Cap-02 MentorScript) | `claude-sonnet-4-6` | Quality-critical; haiku insufficient for nuanced security review |
| Regulatory interpretation (Cap-05) | `claude-opus-4-8` | False negatives are catastrophic; use the best model |
| Demand forecasting reasoning (Cap-04) | `claude-sonnet-4-6` | Statistical first; LLM augments, not replaces |

**Escalation rule:** if a haiku call returns confidence < 0.7 on a quality-critical path, re-route to sonnet. Log the escalation. Haiku → Sonnet escalations are a diagnostic signal for prompt quality.

### Secondary tier — OpenAI (swappable via provider interface)

| Model | When to use |
|---|---|
| `gpt-5.5` | Frontier comparison evals; highest-cost tasks where Claude Opus is insufficient |
| `gpt-5` | Strong baseline; use when benchmarking Claude vs OpenAI on same capability |
| `gpt-5-mini` | Cost comparison testing; not primary in production |

### Configuration

All model strings live in `core/utils/settings.py`. Never hardcode. Never reference
a deprecated model string. If a string not in the table above appears in a PR,
reject it.

```python
# settings.py — current valid model strings (June 2026)
VALID_ANTHROPIC_MODELS = {
    "claude-opus-4-8",
    "claude-sonnet-4-6",
    "claude-haiku-4-5-20251001",
    "claude-fable-5",           # GA June 9, 2026 — use only if explicitly needed
}

VALID_OPENAI_MODELS = {
    "gpt-5.5",
    "gpt-5",
    "gpt-5-mini",
    "gpt-5-nano",               # API-only; routing/classification only
}

# If a model string is not in these sets, reject at startup
```

---

## Orchestration pattern selection

### Pattern 1: Single prompted model
**Use when:** task is procedural, bounded, fits in one context window, no tool calls needed.
**Example:** summarising a document, extracting structured data from a single input.
**Framework:** none — direct API call via `anthropic.messages.create()`.
**Cost:** lowest. **Latency:** lowest.

### Pattern 2: Single agent with tools
**Use when:** task requires tool calls but is a single logical workflow.
**Example:** Cap-01 simple query → retrieve → synthesise → return.
**Framework:** LangGraph with single node + tool call loop, or simple ReAct pattern.
**Cost:** medium (1–5 LLM calls typical). **Latency:** 3–15s typical.

### Pattern 3: Supervisor + specialist agents
**Use when:** task decomposes into parallel or sequential specialised sub-tasks.
**Example:** Cap-01 complex brief (research + analysis + verification in parallel).
**Framework:** LangGraph supervisor node → specialist agent subgraph.
**Cost:** high (5–20 LLM calls). **Latency:** 10–60s.

### Pattern 4: Stateful durable graph (Cap-04)
**Use when:** task is long-running (hours to days), must survive failures, or requires human approval gates that may take hours to resolve.
**Example:** Cap-04 supply chain replenishment cycle.
**Framework:** LangGraph with PostgreSQL checkpointing (`langgraph-checkpoint-postgres`).
**Cost:** highest (many calls over extended time). **Latency:** minutes to hours.

### When to add a human gate

A human approval gate (`interrupt()` in LangGraph) is **mandatory** when:
- Any write action above `AUTONOMOUS_ACTION_THRESHOLD_USD` (Cap-04)
- Any externally-delivered communication (emails, supplier orders, customer responses above CSAT risk threshold)
- Any regulatory obligation interpretation (Cap-05) before it enters the confirmed register
- Any action that is irreversible and affects a third party

Human gates are **not** optional features. They are first-class architecture decisions documented in the spec.

---

## The complexity budget

Every agent hop costs tokens × the agentic multiplier (5–30x vs single-turn).
Before adding an agent or tool call, ask:

1. **Does this earn its cost?** Would a simpler approach produce equivalent quality?
2. **Is the complexity observable?** Can you trace every hop in LangSmith?
3. **Is it testable?** Does the eval suite cover this path?
4. **Is the failure mode handled?** What happens when this agent times out or returns low-confidence output?

If any answer is no, simplify before shipping.
