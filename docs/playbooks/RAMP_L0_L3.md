# AI Proficiency Ladder — L0 to L3
# Adapted from Ramp's internal AI adoption playbook (April 2026)
# Applied to the ai-native-capabilities project contributor model.

> Ramp achieved 99.5% active AI users and 84% using coding agents weekly —
> including finance, marketing, and ops, not just engineers.
> The line between "technical" and "non-technical" has dissolved.
> This ladder describes the journey.

---

## L0 — Aware (0–2 weeks)

**State:** You know AI tools exist. You may have tried ChatGPT or Claude conversationally.

**In this project:**
- You can read a SPEC.md and understand what it's asking for
- You can run `python scripts/health_check.py` and interpret the output
- You understand what a BriefingScript is and why it exists (read ADR-001)
- You can run `python scripts/run_evals.py --all --mock` and read the output

**Your primary contribution:** reading specs, raising questions as GitHub issues with label `question`.

**What to learn next:** write your first BriefingScript for a task you understand well.
Use the template in `cap-02/specs/SPEC.md` → `what_and_success_criteria` section.

---

## L1 — User (2–6 weeks)

**State:** You use AI tools daily as a productivity tool. You know when to use which model.
You've shipped something with AI assistance.

**In this project:**
- You can take a spec task (TASK-XX-NN), paste the relevant spec section into Codex/Claude Code, and review the output
- You understand the eval scorecard — you can read a `reports/cap-XX.json` and know what's passing and failing
- You can run the security gate: `bandit -r cap-02/ && semgrep --config auto cap-02/`
- You've submitted at least one PR that passes all CI gates
- You know when to escalate to a human (you recognise when AI output needs expert review)

**Your primary contribution:** implementing TASK-CORE-* and TASK-01-* (the simpler, well-specified tasks).

**Model routing at L1:**
- Default: `claude-sonnet-4-6` for most tasks
- Classification / routing / metadata extraction: `claude-haiku-4-5-20251001`
- Never use: any claude-3-* model (retired April 2026)

**What to learn next:** write a BriefingScript for a task you're about to implement.
Practice the loop: SPEC → Codex → eval → review → merge.

---

## L2 — Builder (6–16 weeks)

**State:** You design workflows with AI. You write BriefingScripts. You debug agent failures.
You understand the difference between when to use a single model vs an agent graph.

**In this project:**
- You write BriefingScripts from scratch (not just following templates)
- You can implement a LangGraph state graph from a spec — create nodes, edges, state schema
- You debug agent failures using LangSmith traces and LangGraph Studio
- You write eval suites (`cap-XX/evals/suite.py`) with correct blocking thresholds
- You can design an MCP connector (spec + mock implementation)
- You know when NOT to use multi-agent orchestration (you've read arXiv 2604.27891)

**Your primary contribution:** implementing capability agents, evals, and MCP connectors.
You can take a capability from spec to working MVP.

**Model routing at L2 — you know the tradeoffs:**
- `claude-opus-4-8` for: regulatory interpretation (Cap-05), complex verification, long-horizon synthesis
- `claude-sonnet-4-6` for: default reasoning, planning, analysis
- `claude-haiku-4-5-20251001` for: subagent routing, metadata, classification at scale
- You understand the cost model: `tokens × model_rate × agentic_multiplier (5–30x)`

**What to learn next:** design the human-in-the-loop architecture for a new capability.
Understand exactly when a human gate is mandatory vs optional (hint: always mandatory for irreversible external actions).

---

## L3 — Architect (16+ weeks)

**State:** You design AI systems end-to-end. You balance capability vs governance vs cost.
You can translate a business problem into a governed agentic system.
This is the AI-native transformation architect role.

**In this project:**
- You author capability specs (SPEC.md) from a business problem — not just implement them
- You make orchestration architecture decisions: single model vs agent vs stateful graph
- You design the governance model: which gates are hard (mandatory) vs soft (advisory)
- You review PRs for spec compliance, eval correctness, and architectural integrity
- You can explain any capability decision in terms of business value + risk + evidence grade
- You understand the full cost model including the agentic multiplier and FinOps implications
- You can represent the project to a C-suite audience with a defensible business case

**Your primary contribution:** spec authorship, architecture review, capability design, project direction.

**What this looks like professionally:**
- Chief AI Officer / Head of AI Engineering at a company building on these patterns
- AI-native transformation architect: translates business problems into governed agentic systems
- Forward-deployed AI engineer: adapts these patterns to specific enterprise contexts

---

## The proficiency assessment

The `scripts/proficiency.py` tool (TASK-02-11 in Cap-02) will assess your current level
and adapt the BriefingScript templates it surfaces to match.

For now, self-assess by answering:

| Question | L0 | L1 | L2 | L3 |
|---|---|---|---|---|
| Can you read a SPEC and explain it to someone else? | ✓ | ✓ | ✓ | ✓ |
| Can you run an eval and interpret failures? | | ✓ | ✓ | ✓ |
| Can you write a BriefingScript from scratch? | | | ✓ | ✓ |
| Can you design a LangGraph state machine? | | | ✓ | ✓ |
| Can you author a capability spec from a business problem? | | | | ✓ |
| Can you make the build-vs-orchestrate decision? | | | | ✓ |

---

## The Ramp lesson

Ramp's 84% coding-agent adoption across non-engineers happened in months.
The key: they didn't gate AI use behind a "technical" filter.
They created infrastructure (internal LLM proxy, clear guidelines, Ramp Glass context-aware interface)
and let everyone use it.

In this project: the BriefingScript is that infrastructure. Anyone who can write a clear spec
can direct Codex to implement it. The skill is spec quality, not code fluency.
