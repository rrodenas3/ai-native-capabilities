# Contributing to ai-native-capabilities

This project uses **spec-driven development**. The spec is the source of truth. Code implements the spec. Evals verify the implementation. Humans approve the merge.

---

## The workflow

```
SPEC → CODEX/CLAUDE CODE → EVAL → HUMAN REVIEW → MERGE
```

Every contribution starts with the spec. Every PR must pass the eval suite.

---

## Before you start

1. Read the spec for the capability you're working on: `cap-XX/specs/SPEC.md`
2. Read the core infrastructure spec: `core/SPEC.md`
3. Run `python scripts/health_check.py` — ensure your environment is ready
4. Run `python scripts/run_evals.py --cap cap-XX` — understand the current baseline

---

## Making changes

### If you're implementing a spec task

1. Find the task ID in `cap-XX/specs/SPEC.md` (format: `TASK-XX-NN`)
2. Create a branch: `git checkout -b task/TASK-XX-NN-description`
3. Implement the task following the `codex_instructions` section of the spec
4. Write or extend tests in `cap-XX/tests/`
5. Run the eval suite: `python cap-XX/evals/suite.py`
6. If blocking metrics fail → fix before opening PR
7. Open PR with title: `[TASK-XX-NN] description`

### If you're changing the spec

Specs are contracts between humans and agents. Changes require:
1. Document the reason in an Architecture Decision Record: `docs/adr/ADR-NNN-description.md`
2. Update `cap-XX/specs/SPEC.md` with the change
3. Update any affected implementation files
4. Run the full eval suite
5. Get approval from a maintainer before merging

### If you're adding a new MCP connector

1. Add the connector spec to `cap-XX/specs/SPEC.md` under `connectors`
2. Implement the real connector in `cap-XX/tools/connectors/your_connector.py`
3. Implement the mock connector in `cap-XX/tools/connectors/mocks/your_connector_mock.py`
4. Register in `core/mcp/registry.py`
5. Mock must behave identically to real for all test cases

---

## Consultation Requests (CRPs)

If you're stuck on an implementation decision, don't guess. Raise a CRP:

```python
# CRP: [TASK-XX-NN] Should we use BM25 or TF-IDF for lexical search?
# Proposed solution: BM25 (Okapi) because it handles varying document lengths better.
# Tradeoffs: BM25 is slightly slower; TF-IDF is simpler to implement.
# Blocking: YES — need decision before TASK-01-02 can proceed.
```

Open a GitHub issue with label `crp` and include the CRP comment.

---

## Eval gates

Every PR runs the eval suite automatically. Blocking metrics will fail the PR:

| Capability | Blocking metrics |
|---|---|
| Core | All core tests must pass |
| Cap-01 | citation_accuracy, hallucination_rate |
| Cap-02 | briefing_completeness, security_weakness_rate |
| Cap-03 | agent_sprawl_count, escalation_accuracy |
| Cap-04 | human_approval_coverage, digital_twin_validation |
| Cap-05 | false_negative_rate_obligations, citation_accuracy, expert_review_coverage, query_answer_citation_rate |

A PR that fails a blocking metric **cannot be merged**, regardless of other metrics.

---

## Evidence standards

Every capability design decision must trace to evidence. Evidence is graded:

- `[M]` Measured — independent, quantified, peer-reviewed or audited
- `[P]` Partial — company-reported, directionally credible, not independently verified
- `[V]` Vendor claim — treat as directional only

If you add a reference to a spec, include the evidence grade.

---

## Code standards

- Python 3.12+
- Type hints on all functions
- Pydantic models for all data structures
- No hardcoded model names — use `settings.py`
- No hardcoded thresholds — use `settings.py`
- Every LLM call logs: model, tokens_in, tokens_out, latency_ms
- Every function that takes an action logs to audit trail
- Mock implementations for all external dependencies

---

## Questions?

Open an issue with label `question`. Include which capability and task you're working on.
