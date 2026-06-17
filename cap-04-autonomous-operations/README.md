# Cap-04: Autonomous Operations & Supply Chain

> *Multi-agent stateful supply chain — demand to replenishment with human approval gates.*

**Reference case:** Walmart self-healing inventory · Flowr arXiv 2604.05987 · DHL + UPS
**AI layers:** Augmented → Agentic (LangGraph stateful)
**Status:** `spec-complete` · implementation in progress

---

See [`specs/SPEC.md`](./specs/SPEC.md) for the complete BriefingScript — the machine-readable spec that drives all implementation.

```bash
# From repo root (after python scripts/setup.py)
python cap-04-autonomous-operations/demo.py

# Run evals
python cap-04-autonomous-operations/evals/suite.py --output reports/cap04.json

# Run tests
pytest cap-04-autonomous-operations/tests -q
```

## Implemented baseline

- Stateful LangGraph replenishment flow with JSON-serializable state and PostgreSQL checkpointer factory.
- Statistical SKU-level demand forecasting with confidence intervals and MAPE backtest.
- Inventory risk scoring, EOQ optimisation, PO draft generation, and threshold classification from settings.
- Digital twin simulation runs before approval or execution.
- Human approval gate uses LangGraph `interrupt()` for above-threshold or low-confidence actions.
- Mock ERP/WMS connectors write approved POs and expected receipts.
- Exception handler detects demand spikes, lead-time changes, supplier failures, and stock breaches.
- Synthetic 100-SKU, 90-day fixture powers tests, evals, and demo.
