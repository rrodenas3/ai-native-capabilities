# Cap-03: Agentic Revenue & Commerce

> *Consolidated super-agent commerce mesh — intent, discovery, basket, supplier coordination.*

**Reference case:** Walmart super-agent consolidation · Lowe's 2x conversion lift
**AI layers:** Generative → Agentic multi-agent
**Status:** `spec-complete` · implementation in progress

---

See [`specs/SPEC.md`](./specs/SPEC.md) for the complete BriefingScript — the machine-readable spec that drives all implementation.

```bash
# From repo root (after python scripts/setup.py)
python cap-03-agentic-commerce/demo.py

# Run evals
python cap-03-agentic-commerce/evals/suite.py --output reports/cap03.json

# Run tests
pytest cap-03-agentic-commerce/tests -q
```

## Implemented baseline

- Sparky is the single customer-facing super-agent entry point.
- Intent classification covers DISCOVERY, REORDER, SUPPORT, COMPLAINT, ESCALATION, BROWSE, and COMPARISON with a 500-query fixture.
- Discovery uses a mock catalog connector plus margin and stock-aware ranking.
- Support uses live mock OMS lookups for order-specific answers and cites policy sections.
- Sentiment detection triggers immediate escalation for frustration, payment disputes, regulatory requests, and explicit human requests.
- Session memory is opt-in and TTL-governed.
- Mock catalog, OMS, CRM, and promotions connectors support the demo and eval suite.
