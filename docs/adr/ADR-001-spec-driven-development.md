# ADR-001: Spec-Driven Development as the Core Methodology

**Date:** 2026-06-16
**Status:** Accepted
**Deciders:** Project maintainers

---

## Context

Building production-grade agentic AI systems requires a different development methodology than traditional software. Two key differences:

1. **Agents are non-deterministic.** The same prompt may produce different code, different decisions, different outputs. Without a spec as ground truth, there is no way to evaluate whether the agent is doing the right thing.

2. **Codex and Claude Code are the primary implementors.** Human developers are Agent Coaches (SE4H), not implementation authors. The spec is the human's primary artifact. The code is the agent's primary artifact.

The SASE framework (Hassan et al., ACM 2026) formalises this: "A BriefingScript is a specification for action: a version-controlled, testable, and machine-readable document that is as central to the engineering process as the source code itself."

---

## Decision

Every capability in this project is defined by a machine-readable `SPEC.md` (BriefingScript) before any implementation begins. The spec defines:

- Goal and business value
- Success criteria with measurable thresholds
- Agent graph and state schema
- MCP connectors required
- Implementation tasks with acceptance criteria
- Failure modes and mitigations
- Eval scorecard with blocking metrics
- Evidence base with quality grades
- `codex_instructions` — machine-readable directives for the implementing agent

The spec is the contract between human intent and agent execution.

---

## Consequences

**Positive:**
- Codex and Claude Code have unambiguous instructions — no hallucination of requirements
- Evals are derived from the spec — there is no disagreement about what "done" means
- Specs accumulate as institutional memory — future contributors read the spec to understand intent
- PRs can be evaluated automatically against spec acceptance criteria
- The human role is sharply defined: author specs, review CRPs, approve merges

**Negative:**
- More upfront investment before first line of code
- Specs must be maintained alongside implementations — drift is a risk
- Rigid specs can block valid implementation decisions — managed via CRP process

**Mitigations:**
- Specs are versioned in git — changes are tracked
- CRP (Consultation Request) process allows agents to surface spec gaps without halting
- Specs are living documents — PRs can update spec and implementation together

---

## Alternatives considered

**Alternative 1: Traditional TDD (tests first)**
Rejected: Tests verify implementation behaviour, not business intent. Specs are richer — they include agent graphs, evidence bases, failure modes, and codex instructions.

**Alternative 2: README-only documentation**
Rejected: READMEs are for humans. Specs are for both humans and agents. Machine-readable structure (YAML gates, typed schemas, codex_instructions sections) is essential.

**Alternative 3: Informal prompting to Codex**
Rejected: Ad-hoc prompting produces inconsistent results with no evaluation baseline. This is what the NANDA GenAI Divide identifies as the root cause of the 95% failure rate.

---

## References

- Hassan et al., "Agentic Software Engineering: Foundational Pillars and a Research Roadmap," ACM 2026
- Amazon Kiro "spec-driven development" as industry pattern
- arXiv 2604.27891: in-context prompting vs orchestration tradeoffs
- MIT NANDA GenAI Divide: 95% of pilots fail due to learning/memory/structure gap
