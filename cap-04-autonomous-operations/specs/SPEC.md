# SPEC-04: Autonomous Operations & Supply Chain
# BriefingScript v1.0 — Machine-readable · Human-reviewed · Agent-executable
# Status: APPROVED
# Codex-ready: YES

---

## goal_and_why

**Goal:** Build a multi-agent, stateful supply chain system that executes the full loop from demand signal to replenishment action — with human approval gates, ERP/WMS integration via MCP, exception handling, and a digital-twin simulation layer for safe autonomous action.

**Why:** This is the highest-complexity, highest-ROI agentic pattern in the literature. Early adopters report up to 15% lower logistics costs and 35% lower inventory. One documented case avoided $394,000 in stockout penalties. Deutsche Telekom's RAN Guardian agent autonomously monitors and troubleshoots mobile networks with 20-40% savings. DHL uses genAI for data cleansing and solution design. The Flowr paper (arXiv 2604.05987) provides the most complete public architecture for agentic retail supply chain — this implementation is grounded in that framework.

The critical engineering insight: this is where LangGraph's stateful, durable execution is genuinely necessary — not just convenient. Supply chain tasks are long-running (hours to days), require state persistence across failures, involve irreversible actions (POs sent to suppliers), and need explicit human approval above defined thresholds.

---

## what_and_success_criteria

### What this system does

A multi-agent pipeline:
1. **Demand Forecast Agent** — reads sales signals, seasonality, promotions, and generates SKU-level demand forecasts
2. **Inventory Risk Agent** — computes stockout probability and overstock risk per SKU/location
3. **Optimisation Agent** — calculates optimal reorder quantities (economic order quantity + safety stock)
4. **Replenishment Action Agent** — generates PO drafts, checks supplier lead times, validates margins
5. **Exception Handler** — detects anomalies (demand spikes, supplier failures, lead time changes) and escalates
6. **Human Approval Gate** — mandatory gate above defined value/risk thresholds
7. **ERP/WMS Integration** — writes approved POs to ERP; updates WMS for expected receipts
8. **Digital Twin** — simulates actions before live execution above threshold

### Success criteria

```yaml
eval_gates:
  forecast_accuracy_mape:
    description: Mean Absolute Percentage Error of SKU-level demand forecasts
    threshold: <= 0.15  # 15% MAPE
    measurement: backtesting on 90 days of synthetic historical data

  stockout_reduction_rate:
    description: Simulated stockout events avoided vs baseline
    threshold: >= 0.30  # 30% reduction
    measurement: simulation run on 30-day test period

  inventory_turnover_improvement:
    description: Inventory turns improvement vs baseline ordering policy
    threshold: >= 0.10  # 10% improvement
    measurement: simulation comparison

  human_approval_coverage:
    description: Fraction of actions above threshold that pass through human gate
    threshold: 1.00  # must be 100% — no autonomous high-value actions
    measurement: action log audit

  autonomous_action_accuracy:
    description: Fraction of autonomous actions (below threshold) that were correct
    threshold: >= 0.95
    measurement: retrospective correctness review on simulation

  exception_detection_recall:
    description: Fraction of injected exceptions detected by exception handler
    threshold: >= 0.90
    measurement: exception injection test set (20 scenarios)

  digital_twin_validation:
    description: Digital twin simulation run before every action above $X threshold
    threshold: 1.00  # mandatory
    measurement: action log audit

  cost_per_replenishment_cycle:
    description: Token cost for full replenishment cycle (all agents)
    threshold: <= $1.00
    measurement: OTEL cost telemetry
```

---

## all_needed_context

### Reference architecture (Flowr + Walmart + Deutsche Telekom)

**Flowr (arXiv 2604.05987):** Agentic AI for retail supply chain. Multi-agent decomposition with:
- Specialised agents per supply chain function
- Human-in-the-loop via MCP-enabled interfaces
- Exception management as a first-class agent role
- Supervisor orchestration across specialist agents

**Walmart self-healing inventory:**
- Demand prediction → autonomous inventory adjustment
- AI-driven rerouting when disruptions detected
- Supplier coordination at scale
- Evidence: "self-healing supply chain" described in Walmart CTO communications (2025)

**Deutsche Telekom RAN Guardian:**
- Autonomous monitoring + troubleshooting of mobile network nodes
- 20-40% operations savings (McKinsey, 2026)
- The analogy for supply chain: autonomous monitoring + bounded action + human escalation

**Key design principle — the $X threshold:**
The value/volume threshold above which human approval is mandatory is NOT a fixed number. It is a configuration parameter (`settings.AUTONOMOUS_ACTION_THRESHOLD_USD`) that each deployment tunes. Starting value: $5,000. This is the single most important governance parameter in this capability.

### Agent graph

```
[Event Trigger]
    │ scheduled (daily/hourly) OR
    │ event-driven (stock alert, sales spike, supplier notification)
    │
    ▼
[Supervisor Agent]
    │ receives trigger
    │ determines scope (SKUs, locations, time horizon)
    │ dispatches to specialist agents
    │
    ├──────────────────────────────────────────────────────────┐
    ▼                                                           ▼
[Demand Forecast Agent]                             [Exception Handler Agent]
    │                                                    │ always running in parallel
    │ reads: sales history, promotions                   │ watches for anomalies:
    │        seasonality, external signals               │   demand spike > 2σ
    │ outputs: SKU-level 30-day forecast                 │   lead time change
    │          confidence intervals                      │   supplier failure signal
    │          anomaly flags                             │   stock level breach
    │                                                    │
    ▼                                                    ▼
[Inventory Risk Agent]                         [Human Alert + Escalation]
    │                                          (exception path — async)
    │ reads: current stock levels
    │        forecast output
    │        safety stock targets
    │ outputs: stockout probability per SKU
    │          days-of-cover metric
    │          overstock risk score
    │
    ▼
[Optimisation Agent]
    │ computes: EOQ (economic order quantity)
    │           safety stock adjustment
    │           supplier allocation
    │ reads: supplier catalog, lead times, pricing, MOQ
    │ outputs: recommended PO quantities per supplier
    │
    ▼
[Replenishment Action Agent]
    │ generates PO drafts
    │ validates: margin impact, budget, supplier capacity
    │ classifies: AUTONOMOUS (< threshold) or HUMAN_APPROVAL (>= threshold)
    │
    ├──────────────────────────┐
    ▼                           ▼
[< threshold]            [>= threshold]
    │                           │
    ▼                           ▼
[Digital Twin                [Digital Twin Simulation]
 Simulation (fast)]              │ simulate impact
    │                           │ risk assessment
    ▼                           ▼
[Auto-Execute]           [Human Approval Gate]
    │                           │ shows: PO draft, simulation result,
    │                           │        risk score, margin impact
    │                           │ human: APPROVE / MODIFY / REJECT
    │                           │
    └──────────┬────────────────┘
               ▼
    [ERP/WMS Write via MCP]
        │ creates PO in ERP
        │ updates expected receipt in WMS
        │ notifies supplier via supplier portal
        │
        ▼
    [Audit Log + State Persistence]
    [Checkpoint — LangGraph durable execution]
```

### State schema

```python
class SupplyChainState(TypedDict):
    # Run context
    run_id: str
    trigger_type: Literal["scheduled", "event", "manual", "exception"]
    trigger_event: dict | None
    scope_skus: list[str]
    scope_locations: list[str]
    time_horizon_days: int

    # Forecast
    demand_forecasts: list[DemandForecast]      # per SKU
    forecast_confidence: dict[str, float]
    anomaly_flags: list[AnomalyFlag]

    # Risk
    inventory_risks: list[InventoryRisk]         # stockout/overstock per SKU/location
    exception_events: list[ExceptionEvent]

    # Optimisation
    replenishment_recommendations: list[ReplenishmentRec]

    # Action
    po_drafts: list[PODraft]
    simulation_results: list[SimulationResult]
    autonomous_actions: list[ExecutedAction]

    # Human gate
    human_approval_required: bool
    human_approval_status: Literal["pending", "approved", "modified", "rejected"] | None
    human_modifications: list[dict] | None
    approver_id: str | None

    # Execution
    erp_writes: list[ERPWrite]
    wms_updates: list[WMSUpdate]
    supplier_notifications: list[SupplierNotification]

    # Audit
    checkpoint_id: str
    audit_trail: list[AuditEvent]
    cost_tokens: int
    run_duration_seconds: float
```

### MCP connectors required

```yaml
connectors:
  - name: erp-system
    tools: [get_purchase_orders, create_po, update_po, get_budget, get_suppliers]
    description: ERP integration (mock: SAP/Oracle compatible schema)
    write_gate: requires human_approval_status == "approved" for POs above threshold

  - name: wms-system
    tools: [get_stock_levels, get_locations, update_expected_receipt, get_movements]
    description: Warehouse Management System

  - name: sales-data
    tools: [get_sales_history, get_pos_data, get_promotions_calendar]
    description: Sales and POS data feed

  - name: supplier-portal
    tools: [get_catalog, get_lead_times, get_pricing, send_rfq, get_capacity]
    description: Supplier collaboration portal

  - name: digital-twin
    tools: [run_simulation, get_simulation_result, compare_scenarios]
    description: Supply chain simulation environment

  - name: external-signals
    tools: [get_weather_events, get_economic_signals, get_competitor_signals]
    description: External demand signals (optional, v2)

  - name: audit-log
    tools: [log_event, log_action, query_trail, get_audit_report]
```

---

## implementation_tasks

```
TASK-04-01: LangGraph stateful graph with checkpointing
  Acceptance: survives process restart mid-execution; resumes from checkpoint
  Files: cap-04/agents/supply_chain_graph.py

TASK-04-02: Demand Forecast Agent (time-series + LLM reasoning)
  Acceptance: MAPE <= 0.15 on backtest dataset
  Files: cap-04/agents/forecast_agent.py

TASK-04-03: Inventory Risk Agent (stockout/overstock scoring)
  Acceptance: correct risk classification for 90% of test SKU/location pairs
  Files: cap-04/agents/risk_agent.py

TASK-04-04: Optimisation Agent (EOQ + safety stock calculation)
  Acceptance: recommendations match analytical solution within 5% for test cases
  Files: cap-04/agents/optimisation_agent.py

TASK-04-05: Replenishment Action Agent (PO drafting)
  Acceptance: valid PO schema for all test cases; correct threshold classification
  Files: cap-04/agents/replenishment_agent.py

TASK-04-06: Exception Handler Agent (anomaly detection + escalation)
  Acceptance: detects 90% of injected exceptions; raises alert within 60s
  Files: cap-04/agents/exception_agent.py

TASK-04-07: Digital Twin simulation layer
  Acceptance: simulation completes in < 10s; produces risk/impact scores
  Files: cap-04/tools/digital_twin.py

TASK-04-08: Human Approval Gate (mandatory, threshold-based)
  Acceptance: 100% of above-threshold actions wait for human input
  Files: core/governance/human_gate.py (extend), cap-04/agents/approval_gate.py

TASK-04-09: ERP/WMS MCP connectors (mock implementations)
  Files: cap-04/tools/connectors/erp.py, cap-04/tools/connectors/wms.py

TASK-04-10: Synthetic data generator (100 SKUs, 90 days history)
  Files: cap-04/tests/fixtures/generate_data.py

TASK-04-11: Eval suite + simulation benchmark
  Files: cap-04/evals/suite.py

TASK-04-12: Demo: full replenishment cycle end-to-end
  Files: cap-04/demo.py
```

---

## failure_modes_to_design_against

```yaml
failure_modes:
  autonomous_high_value_action:
    description: System executes PO above threshold without human approval
    mitigation: Hard gate in LangGraph graph — graph CANNOT proceed past approval node without approval status == "approved"
    test: inject above-threshold PO; verify graph pauses at gate

  forecast_error_cascade:
    description: Bad forecast → wrong PO → inventory disaster
    mitigation: Confidence intervals mandatory; low-confidence forecasts trigger human review regardless of value
    test: inject high-uncertainty forecast; verify human review triggered

  supplier_lock_failure:
    description: Supplier portal MCP connection fails mid-execution
    mitigation: LangGraph checkpointing; retry with exponential backoff; escalate if max retries exceeded
    test: inject MCP connector failure; verify checkpoint restored, escalation fired

  ghost_inventory:
    description: WMS shows stock that physically doesn't exist
    mitigation: Cross-reference multiple data sources; flag discrepancies > 10% for human review
    test: inject WMS/ERP discrepancy; verify flag and human alert

  budget_overrun:
    description: Aggregate POs across a run exceed approved budget
    mitigation: Budget check before every PO draft; aggregate spend tracked in state
    test: inject scenario where sequential POs exceed budget; verify last PO blocked

  exception_flooding:
    description: Exception handler alerts so frequently humans stop paying attention
    mitigation: Alert deduplication; severity tiering; rate limiting; digest mode
    test: inject 100 low-severity exceptions; verify digest rather than 100 alerts
```

---

## eval_scorecard

```yaml
metrics:
  forecast_accuracy_mape:           { target: 0.15, weight: 0.20, lower_is_better: true }
  stockout_reduction_rate:          { target: 0.30, weight: 0.20 }
  inventory_turnover_improvement:   { target: 0.10, weight: 0.15 }
  human_approval_coverage:          { target: 1.00, weight: 0.20, blocking: true }
  autonomous_action_accuracy:       { target: 0.95, weight: 0.10 }
  exception_detection_recall:       { target: 0.90, weight: 0.10 }
  digital_twin_validation:          { target: 1.00, weight: 0.03, blocking: true }
  cost_per_cycle_usd:               { target: 1.00, weight: 0.02, lower_is_better: true }

passing_threshold: weighted_score >= 0.85
blocking: [human_approval_coverage, digital_twin_validation]
```

---

## codex_instructions

```
When implementing this spec:

1. LangGraph stateful execution with PostgreSQL checkpointing is MANDATORY. This is not optional. Supply chain tasks are long-running and must survive failures.
2. The human approval gate is implemented as a LangGraph interrupt() node. The graph HALTS at this node. It resumes ONLY when human_approval_status is explicitly set to "approved" or "modified".
3. The AUTONOMOUS_ACTION_THRESHOLD_USD is read from settings.py. It is NEVER hardcoded.
4. Every PO draft runs through the digital twin simulation BEFORE being presented to human or auto-executed.
5. All ERP/WMS writes use the mock connector by default. Real connectors are configured via environment variable ERP_MODE=production.
6. Demand forecasting uses time-series decomposition first, LLM reasoning second. LLM does not replace statistical forecasting — it augments it with contextual signals.
7. Exception Handler runs as a PARALLEL branch in the LangGraph graph — it does not block the main pipeline.
8. State must be fully serialisable to JSON for checkpoint persistence. No Python objects in state.
9. Log every agent decision with: run_id, agent_name, decision_type, value_usd, confidence, timestamp.
10. The synthetic data generator (TASK-04-10) must produce realistic demand patterns with: seasonality, trend, stockout events, demand spikes. Used by eval suite and demo.
```

---

## frontier_improvements
# Added: 2026-06-17 — based on Frontier Agentic AI Engineering Patterns research

### self_healing_operations
**Finding:** Microsoft Azure SRE Agent (GA March 10, 2026) is the best-documented
production self-healing agentic system. 1,300+ agents at Microsoft. 35,000+ incidents
mitigated. 20,000+ engineering hours saved. App Service time-to-mitigation:
40.5-hour human-only average → 3 minutes. Human-in-the-loop governance throughout.
**Source:** Microsoft Azure SRE Agent GA announcement (March 2026)

Apply the Azure SRE Agent pattern to Cap-04 exception handling:

```
DETECT:      Exception Handler watches for anomaly signals (already in SPEC)
INVESTIGATE: Agent reads: inventory history, supplier data, forecast model output,
             recent operational logs → structured root-cause analysis
REMEDIATE:   Propose action (PO adjustment, supplier contact, route change)
             → Digital twin simulation → Human approval gate (if above threshold)
             → Execute → Verify resolution → Log to audit trail
LEARN:       Distilled lesson stored in procedural memory (A-MEM skill note)
             for next incident of same type
```

The detect→investigate→remediate loop is the Ralph-Wiggum loop pattern (arXiv
2603.24768): run agent until external validation passes, with bounded retries.

### ssgm_memory_governance
**Finding:** Cap-04 is the highest-risk capability for memory poisoning.
A malicious or corrupted supply chain signal → wrong PO → financial loss.
SSGM governance (ADR-002, arXiv 2603.11768) is mandatory for all memory writes.

```python
# Every memory write in Cap-04 MUST go through SSGMGovernor
governor = SSGMGovernor(
    capability="cap-04",
    decay_half_life_days=7.0,     # operational data decays fast
    quarantine_threshold=0.5,     # moderate strictness
)
result = governor.validate_write(new_entry, existing_entries)
if not result.validated:
    queue_for_human_review(result)  # NEVER silently discard
```

Decay half-life calibration:
  - Demand forecasts: 7 days (stale fast)
  - Supplier lead times: 14 days
  - Inventory snapshots: 1 day (real-time)
  - Historical seasonal patterns: 180 days

### heartbeat_proactive_scheduling
**Finding:** OpenClaw's Heartbeat pattern (proactive polling, not just reactive
event handling) is directly applicable to Cap-04's exception handler.

Current design: exception handler REACTS to events.
Improvement: exception handler also PROACTIVELY polls on a schedule:
  - Every 4h: check all SKU stockout probabilities
  - Every 1h: check supplier portal for lead-time updates
  - Every 15m: check for demand spikes > 1σ (early warning before 2σ threshold)
  - Daily: reconcile ERP PO status with WMS expected receipts

This converts Cap-04 from reactive to continuously vigilant.

### digital_twin_advancement
**Finding:** Microsoft Supply Chain 2.0 (March 2026) documents production digital
twins including Toyota Material Handling Europe forklift simulation (training time
-30%+) and Azure Digital Twins platform for supply chain simulation.

Upgrade Cap-04 digital twin from "simulate PO impact" to "simulate full supply
chain state change":
  - Inject proposed PO into full 30-day forward simulation
  - Model supplier capacity constraints
  - Model competing demand across product lines
  - Output: probabilistic distribution of outcomes (not single point estimate)
  - Confidence interval displayed in human approval gate

### a2a_for_operations
A2A v1.0 (Linux Foundation) for Cap-04 inter-system coordination:
  - Exception Handler publishes events as A2A tasks to downstream systems
  - Supplier agents receive A2A task requests (not direct API calls)
  - ERP/WMS systems expose A2A endpoints for PO creation/receipt update

### ramp_financial_agent_pattern
**Finding:** Ramp's AP (Accounts Payable) agents demonstrate enterprise-grade
financial agent patterns: auto-coding, fraud detection, approval workflow,
payment execution, ERP sync (NetSuite/QBO/Xero/Sage/Workday/Oracle).
Core principle: "never take money-moving actions without human confirmation."

Apply to Cap-04 ERP integration:
  - Auto-coding: classify POs to correct GL accounts automatically
  - Fraud detection: flag anomalous PO patterns (unit price, quantity, supplier)
  - Three-way matching: PO + receipt + invoice must reconcile before payment
  - Human confirmation: required before ANY financial transaction executes

### new_tasks_added
```
TASK-04-07: Heartbeat proactive scheduler (4h/1h/15m/daily polling schedule)
TASK-04-08: Self-healing operations loop (detect→investigate→remediate + learnings)
TASK-04-09: SSGM memory governance wiring with calibrated decay half-lives
TASK-04-10: Enhanced digital twin (probabilistic distribution, full-chain simulation)
TASK-04-11: A2A event publishing for exception handler + supplier coordination
TASK-04-12: Ramp-pattern financial agent (fraud detection, three-way matching)
TASK-04-13: Persistent agent identity records across process restarts
```
