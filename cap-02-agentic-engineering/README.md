# Cap-02: Agentic Software Engineering (SASE)

> *Structured Agentic Software Engineering — BriefingScripts, LoopScripts, Agent Coaches.*

**Reference case:** Ramp 84% cross-role coding agents · SASE paper (Hassan et al., ACM 2026)
**AI layers:** Generative → Agentic (SE4H + SE4A)
**Status:** `spec-complete` · implementation in progress

---

See [`specs/SPEC.md`](./specs/SPEC.md) for the complete BriefingScript — the machine-readable spec that drives all implementation.

```bash
# From repo root (after python scripts/setup.py)
python cap-02-agentic-engineering/tools/validator.py cap-02-agentic-engineering/specs/SPEC.md

# Run the Cap-02 SASE baseline tests
pytest cap-02-agentic-engineering/tests -q
```

## Implemented baseline

- BriefingScript and Merge-Readiness Pack Pydantic schemas
- Structured validator with `briefing_completeness == 1.0` blocking semantics
- In-memory Briefing Library similarity search
- LoopScript runtime with repeated-error and iteration-budget CRP escalation
- Deterministic Execution, MentorScript, Security Gate, and MRP agents
- LangGraph flow: validate -> search -> execute -> mentor -> security -> MRP -> human review

Critical security findings stop the graph before human review. Human review receives only the Merge-Readiness Pack artifact.
