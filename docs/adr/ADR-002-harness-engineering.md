# ADR-002: Harness Engineering as the Cross-Cutting Discipline

**Date:** 2026-06-17
**Status:** Accepted
**Deciders:** Project maintainers
**Research basis:** Frontier Agentic AI Engineering Patterns Deep Research (June 2026)

---

## Context

The production gap in enterprise AI is not a model problem — it is a harness problem.
IDC (2026): 88% of AI POCs never reach widescale deployment.
McKinsey (2026): only 11% of enterprises run an AI agent in production at genuine scale.
Microsoft Azure SRE Agent (GA March 2026): App Service time-to-mitigation cut from
a 40.5-hour human-only average to 3 minutes — same models, radically better harness.

The defining equation of 2026 agentic engineering:

    Agent = Model + Harness

The harness is the system of constraints, feedback loops, sensors, and governance
that wraps a model to make it reliable, auditable, and safe. Anthropic's 2026
Agentic Coding Trends report found harness configuration alone can swing benchmark
results by 5+ percentage points — more than most model upgrades.

This decision extends ADR-001 (spec-driven development) with a harness engineering
discipline that applies uniformly across all five capabilities.

---

## Decision

Adopt **harness engineering** as the primary cross-cutting discipline across all
five capabilities. This means:

### 1. The canonical agentic loop

Every agent in this repo implements the same bounded loop:

```
PLAN  → agent proposes structured action (never raw tool call)
ACT   → harness validates: schema ✓ · permissions ✓ · budget ✓ → executes
OBSERVE → structured result injected into state (never raw string)
VERIFY  → computational sensor checks result (deterministic, cheap)
CORRECT → if verify fails: retry up to N times → CRP → human escalation
```

Stop conditions (enforced by harness, not model):
- `MAX_ITERATIONS` exceeded → alert human, halt
- Budget > 80% of `SESSION_BUDGET_USD` → alert, pause
- Destructive action above threshold → mandatory human gate
- Repeated identical error (3×) → CRP rather than retry

### 2. Risk taxonomy for tool calls

Every tool call is classified before execution:

```python
class ToolRiskTier(Enum):
    READ_ONLY    = "read_only"    # search, fetch, list — execute immediately
    IDEMPOTENT   = "idempotent"   # create with dedup, upsert — execute with logging
    FINANCIAL    = "financial"    # any money-moving or PO-generating action
    DESTRUCTIVE  = "destructive"  # delete, override, send to external party
```

Permission matrix (configurable per deployment):
- `READ_ONLY`: auto-execute, log to OTEL
- `IDEMPOTENT`: auto-execute, log + verify
- `FINANCIAL`: human gate if above `AUTONOMOUS_ACTION_THRESHOLD_USD`
- `DESTRUCTIVE`: always human gate, no exceptions

### 3. Sensor architecture (computational + inferential)

Sensors run **inside the loop** on every step, not just offline:

**Computational sensors** (deterministic, run every step, cheap):
- Schema validation on tool input/output
- Permission tier check before execution
- Budget check before LLM call
- Citation presence check on every Finding
- Test suite pass on agent-generated code

**Inferential sensors** (LLM-as-judge, run selectively at quality gates):
- Hallucination detection at brief assembly
- Security weakness scan on generated code
- Compliance obligation completeness check
- Cross-turn state consistency (the "1-in-5 P0 failures" blind spot)

### 4. Harness security requirements

- Model never calls tools directly: proposed action → harness validates → executes
- All tool schemas are validated against registered MCP tool contracts
- Prompt injection of inferential sensors is a named primary risk — judge models
  must differ from the agent model family (prevents self-preference/injection)
- Harness security eval suite runs in CI alongside capability evals

### 5. The "golden principles" anti-drift mechanism

Agent-generated artifacts accumulate "slop" (OpenAI's term: drift from standards).
Each capability maintains a `golden_principles.md` file with:
- Opinionated mechanical rules (naming conventions, schema requirements, etc.)
- Recurring cleanup tasks that run when slop is detected
- A `golden_principles_eval` that scores generated artifacts against the rules

---

## Consequences

**Positive:**
- Makes harness quality (not just model quality) a first-class engineering concern
- Provides a structural response to the 88% POC-to-production failure rate
- Deterministic sensors catch known failure modes without LLM cost
- Security is architecture, not an afterthought

**Negative:**
- Adds implementation complexity to every agent
- Harness setup cost is real (the "Ferrari with the handbrake on" dynamic
  until harness is mature — Ramp's Project Glass lesson)
- Risk taxonomy requires deployment-specific calibration

**Mitigations:**
- `core/harness/` provides the shared harness primitives so each capability
  inherits them without reimplementing
- `AUTONOMOUS_ACTION_THRESHOLD_USD` is a config value, not a code constant
- The `core/tests/test_harness_security.py` suite runs on every PR

---

## References
- OpenAI "Harness engineering: leveraging Codex in an agent-first world" (Feb 2026)
- Martin Fowler / Birgitta Böckeler "Thoughtworks on harness engineering" (Apr 2026)
- Microsoft Azure SRE Agent GA (Mar 2026): 35,000+ incidents mitigated, 3-min MTTM
- Ramp Project Glass: "the model was great but the harness was fundamentally broken"
- ADR-001: Spec-Driven Development as the Core Methodology
