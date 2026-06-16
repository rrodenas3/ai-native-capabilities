# SPEC-02: Agentic Software Engineering (SASE)
# BriefingScript v1.0 — Machine-readable · Human-reviewed · Agent-executable
# Status: APPROVED
# Codex-ready: YES

---

## goal_and_why

**Goal:** Implement Structured Agentic Software Engineering (SASE) — a dual-modality engineering system where humans act as "Agent Coaches" (SE4H) and agents execute in a structured, predictable environment (SE4A). The system ships BriefingScripts, LoopScripts, MentorScripts, and Merge-Readiness Packs as first-class artifacts.

**Why:** Ramp achieved 84% of ALL employees — finance, marketing, ops, not just engineers — using coding agents weekly. The technical/non-technical barrier has dissolved. But unstructured agent use creates security risks (29.5% of Copilot-generated Python code contains security weaknesses), inconsistent quality, and no institutional memory. SASE provides the structure that makes agentic engineering safe, reproducible, and measurable.

**Business value:**
- Multiply engineering throughput without proportionally scaling headcount
- Enable non-engineers to ship production-quality code via structured agent delegation
- Reduce code review burden through automated Merge-Readiness verification
- Create institutional memory via version-controlled BriefingScripts that encode engineering intent
- Enforce security scanning on 100% of agent-generated code

---

## what_and_success_criteria

### What this system does

1. **BriefingEng (SE4H):** Human Agent Coach authors a structured BriefingScript (goal, success criteria, context, constraints, tests)
2. **Agent Command Environment (ACE):** Human-facing workbench where coaches manage briefs, review CRPs, approve Merge-Readiness Packs
3. **Execution loop (SE4A):** Agent reads BriefingScript, executes implementation via LoopScript, raises Consultation Request Packs (CRPs) when blocked
4. **Agent Execution Environment (AEE):** Agent-facing environment with MCP-connected tools (repo, tests, linter, security scanner)
5. **Verification:** MentorScript reviews agent output against BriefingScript acceptance criteria
6. **Security gate:** Every agent-generated file passes automated security scan before merge consideration
7. **Merge-Readiness Pack:** Agent produces structured package (code + tests + coverage + security report + diff) for human review

### Success criteria (definition of done)

```yaml
eval_gates:
  briefing_completeness:
    description: BriefingScript has all required sections before agent execution starts
    threshold: 1.0  # mandatory — incomplete brief = blocked
    measurement: schema validation

  acceptance_criteria_pass_rate:
    description: Fraction of BriefingScript acceptance criteria passing at merge
    threshold: >= 0.90
    measurement: automated test execution against criteria checklist

  security_weakness_rate:
    description: Security weaknesses per 1000 lines of agent-generated code
    threshold: <= 5.0  # vs baseline 29.5% files with issues in unstructured Copilot
    measurement: bandit + semgrep automated scan on all agent output

  test_coverage:
    description: Code coverage of agent-generated code by agent-generated tests
    threshold: >= 0.80
    measurement: pytest-cov

  crp_resolution_rate:
    description: Fraction of agent Consultation Requests resolved without human rewriting the brief
    threshold: >= 0.75
    measurement: logged CRP outcomes

  merge_readiness_accuracy:
    description: Fraction of Merge-Readiness Packs that pass human review without major revision
    threshold: >= 0.70
    measurement: reviewer action logs

  briefing_reuse_rate:
    description: Fraction of new tasks that reuse or adapt an existing BriefingScript
    threshold: >= 0.30  # signals institutional memory is working
    measurement: brief similarity search

  cost_per_completed_task:
    description: Token cost for a complete agentic engineering task
    threshold: <= $2.00
    measurement: OTEL cost telemetry
```

---

## all_needed_context

### SASE framework (source: Hassan et al., ACM 2026)

**The structured duality:**
- SE4H (Software Engineering for Humans): redefines the human role. The human is an "Agent Coach" — authoring briefs, reviewing CRPs, approving merges. Not writing implementation code.
- SE4A (Software Engineering for Agents): establishes a structured, predictable environment where agents can operate effectively. Agents consume BriefingScripts, execute LoopScripts, raise CRPs.

**Four pillars redefined:**
- Actors: human Agent Coaches + specialised software agents
- Processes: structured, repeatable activities (BriefingEng, LoopScript execution, CRP resolution, MergeEng)
- Artifacts: BriefingScript, LoopScript, MentorScript, CRP, Merge-Readiness Pack, Version-Controlled Resolutions
- Tools: ACE (human workbench) + AEE (agent workbench) — not a shared IDE

**BriefingScript structure:**
```
goal_and_why:          high-level objective + business value
what_and_success:      scope + verifiable acceptance criteria + invariants
all_needed_context:    curated context (architecture, patterns, constraints)
implementation_tasks:  ordered task list with explicit dependencies
failure_modes:         what to watch for; mitigation strategies
codex_instructions:    machine-readable directives for the agent
```

### Agent graph

```
Human Author (Agent Coach)
    │
    ▼
[BriefingEng — ACE]
    │ author BriefingScript
    │ validate completeness (schema check)
    │ estimate complexity
    │
    ▼
[BriefingScript] ──────────────────────────────────────────────┐
    │                                                            │
    ▼                                                            │ CRP (needs clarification)
[Execution Agent — AEE]                                          │
    │ reads BriefingScript                                       │
    │ plans implementation (LoopScript)                          │
    │ executes code changes via MCP tools                        │
    │ writes tests                                               │
    │ raises CRPs if blocked ────────────────────────────────────┘
    │ runs security scan (mandatory)
    │ assembles Merge-Readiness Pack
    │
    ▼
[MentorScript Review Agent]
    │ checks output vs BriefingScript acceptance criteria
    │ scores each criterion: PASS / FAIL / PARTIAL
    │ generates review notes
    │
    ▼
[Security Gate — mandatory]
    │ bandit + semgrep on all generated files
    │ BLOCK if critical issues found
    │ WARN on medium issues (must be acknowledged)
    │
    ▼
[Human Review Gate — ACE]
    │ reviews Merge-Readiness Pack
    │ sees: diff, tests, coverage, security report, criteria scores
    │ approves / requests changes / rejects
    │
    ▼
[Version-Controlled Resolution]
    │ merge approved
    │ BriefingScript archived with outcome
    │ patterns stored in procedural memory
    ▼
SHIPPED
```

### Artifact schemas

**BriefingScript (minimal valid)**
```yaml
briefing_id: BRIEF-{timestamp}-{slug}
version: 1
status: DRAFT | APPROVED | IN_PROGRESS | DONE | ARCHIVED
author: <human>
agent: <assigned-agent-or-codex>
created_at: <iso8601>

goal_and_why:
  goal: <string>
  why: <string>
  business_value: <string>

what_and_success:
  scope: <string>
  acceptance_criteria:
    - id: AC-01
      description: <string>
      testable: true
      test_command: <string | null>
  invariants: []
  anti_goals: []

all_needed_context:
  architecture_refs: []
  relevant_files: []
  patterns_to_follow: []
  constraints: []

implementation_tasks:
  - id: TASK-01
    description: <string>
    depends_on: []
    estimated_complexity: XS | S | M | L | XL

failure_modes: []
codex_instructions: <string>
```

**Merge-Readiness Pack (agent output)**
```yaml
briefing_id: <ref>
pack_id: MRP-{timestamp}
generated_at: <iso8601>
agent: <agent-id>

files_changed: []
tests_added: []
coverage_pct: <float>
security_scan:
  tool: bandit+semgrep
  critical: 0           # must be 0 to proceed
  high: <int>
  medium: <int>
  low: <int>

criteria_scores:
  - id: AC-01
    status: PASS | FAIL | PARTIAL
    evidence: <string>

crps_raised: []
crps_resolved: []
agent_notes: <string>
```

### MCP connectors required

```yaml
connectors:
  - name: git-repo
    type: mcp-server
    tools: [read_file, write_file, create_branch, diff, commit, list_files]

  - name: test-runner
    type: mcp-server
    tools: [run_tests, get_coverage, run_specific_test]

  - name: security-scanner
    type: mcp-server
    tools: [scan_file, scan_directory, get_report]
    models: [bandit, semgrep]

  - name: linter
    type: mcp-server
    tools: [lint_file, lint_directory, fix_lint]
    models: [ruff, mypy]

  - name: briefing-library
    type: mcp-server
    description: Library of past BriefingScripts for reuse detection
    tools: [search_briefs, get_brief, store_brief, find_similar]

  - name: crp-queue
    type: mcp-server
    description: Consultation Request queue (agent → human)
    tools: [raise_crp, resolve_crp, list_pending]
```

---

## implementation_tasks

```
TASK-02-01: BriefingScript schema + validator
  Acceptance: rejects invalid briefs; accepts valid ones with 0 false positives
  Files: cap-02/schemas/briefing_script.py, cap-02/tools/validator.py

TASK-02-02: Briefing Library (search + store past briefs)
  Acceptance: similarity search returns top-3 relevant briefs for 20 test queries
  Files: cap-02/memory/briefing_library.py

TASK-02-03: Execution Agent (reads brief → implements via MCP tools)
  Acceptance: completes 5 test BriefingScripts, all code runnable
  Files: cap-02/agents/execution_agent.py

TASK-02-04: LoopScript runtime (agent self-monitoring loop)
  Acceptance: agent detects when stuck, raises CRP rather than hallucinating
  Files: cap-02/agents/loop_runtime.py

TASK-02-05: MentorScript Review Agent (brief vs output evaluation)
  Acceptance: scores all acceptance criteria correctly on 10 test pairs
  Files: cap-02/agents/mentor_agent.py

TASK-02-06: Security Gate (bandit + semgrep via MCP)
  Acceptance: catches all test cases from known-vulnerable code set
  Files: cap-02/tools/security_gate.py

TASK-02-07: Merge-Readiness Pack assembler
  Acceptance: produces valid MRP for every completed execution
  Files: cap-02/agents/mrp_agent.py

TASK-02-08: LangGraph state machine connecting ACE ↔ AEE
  Files: cap-02/agents/graph.py

TASK-02-09: ACE CLI (human workbench — author, review, approve)
  Files: cap-02/cli/ace.py

TASK-02-10: Eval suite
  Files: cap-02/evals/suite.py

TASK-02-11: L0→L3 proficiency assessment tool
  Description: Assesses user AI proficiency, adapts brief templates accordingly
  Files: cap-02/tools/proficiency.py
```

---

## failure_modes_to_design_against

```yaml
failure_modes:
  security_bypass:
    description: Agent-generated code with critical vulnerabilities merged without review
    mitigation: Security gate is MANDATORY and UNBYPASSABLE; critical findings = hard block
    test: inject OWASP Top 10 patterns; verify all blocked

  brief_drift:
    description: Agent implements something different from the brief without raising a CRP
    mitigation: MentorScript scores every criterion; divergence triggers CRP not silent failure
    test: brief specifies X; agent implements Y; verify CRP raised

  crp_flooding:
    description: Agent raises too many CRPs, blocking human throughput
    mitigation: Agent attempts 3 self-resolution strategies before CRP; CRP includes proposed solution
    test: ambiguous brief → verify agent attempts resolution before escalating

  cost_explosion:
    description: Execution loop burns tokens on a hard problem without making progress
    mitigation: Max iteration budget per task; progress check every N iterations; human alert
    test: unsolvable brief → verify budget limit triggered

  test_gaming:
    description: Agent writes tests that pass trivially without testing real behaviour
    mitigation: MentorScript reviews test quality; mutation testing on sample
    test: inject trivially-passing test; verify MentorScript flags it
```

---

## eval_scorecard

```yaml
metrics:
  briefing_completeness:        { target: 1.00, weight: 0.20, blocking: true }
  acceptance_criteria_pass:     { target: 0.90, weight: 0.20 }
  security_weakness_rate:       { target: 5.0,  weight: 0.25, lower_is_better: true, blocking: true }
  test_coverage:                { target: 0.80, weight: 0.15 }
  crp_resolution_rate:          { target: 0.75, weight: 0.10 }
  merge_readiness_accuracy:     { target: 0.70, weight: 0.05 }
  briefing_reuse_rate:          { target: 0.30, weight: 0.03 }
  cost_per_task_usd:            { target: 2.00, weight: 0.02, lower_is_better: true }

passing_threshold: weighted_score >= 0.85
blocking: [briefing_completeness, security_weakness_rate]
```

---

## reference_evidence

```yaml
evidence:
  - company: Ramp
    result: 99.5% employees active AI users; 84% use coding agents weekly including non-engineers
    source: Midas Tools citing Ramp internal data (Apr 2026)
    grade: P

  - research: Fu et al. (ACM TOSEM, Feb 2025)
    finding: 29.5% of Python and 24.2% of JavaScript Copilot-generated snippets contain security weaknesses
    source: arXiv 2310.02059, analysis of 733 snippets
    grade: M  # peer-reviewed

  - research: Hassan et al. (ACM, 2026)
    finding: SASE dual-modality (SE4H + SE4A) with BriefingScript/LoopScript/MentorScript artifacts
    source: Agentic Software Engineering: Foundational Pillars and a Research Roadmap
    grade: M

  - company: Shopify
    finding: AI fluency in 360 reviews; reflexive AI usage baseline expectation for all employees
    source: CEO Tobi Lütke internal memo, April 2025 (confirmed publicly)
    grade: P

  - company: GitHub / Accenture
    result: 55% faster task completion (controlled study); 84% successful builds (RCT, 4800 devs)
    source: GitHub research + Accenture RCT
    grade: M

  - research: Longitudinal study (arXiv 2509.20353)
    finding: No statistically significant org-level commit activity change after Copilot adoption
    source: NAV IT, 703 repos, 25 vs 14 users, 2 years
    grade: M  # caution: controlled-task gains ≠ org-level output
```

---

## codex_instructions

```
When implementing this spec:

1. The BriefingScript schema (TASK-02-01) MUST be implemented first. Nothing else starts until it validates correctly.
2. Every BriefingScript must be stored in version control (git-committed) before execution begins.
3. The Security Gate (TASK-02-06) is not optional. It runs on EVERY file the execution agent produces.
4. CRPs are the agent's escape valve. When blocked, RAISE CRP. Do not guess. Do not hallucinate a solution.
5. The MentorScript agent scores EVERY acceptance criterion, not just the ones it finds easy.
6. Use the L0→L3 proficiency model: adapt brief templates to user sophistication level.
7. Log all agent iterations, tool calls, and token costs to OTEL.
8. The Merge-Readiness Pack is the ONLY artifact that goes to human review. Raw diffs are not acceptable output.
9. When uncertain about architecture decisions, write a CRP with your proposed solution and tradeoffs.
10. Briefing reuse is a first-class feature. Always search the Briefing Library before starting from scratch.
```
