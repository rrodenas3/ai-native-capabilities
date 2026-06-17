# SPEC-03: Agentic Revenue & Commerce
# BriefingScript v1.0 — Machine-readable · Human-reviewed · Agent-executable
# Status: APPROVED
# Codex-ready: YES

---

## goal_and_why

**Goal:** Build a consolidated agentic commerce system — a small number of orchestrated "super agents" that replace a fragmented mesh of narrow bots. The system handles customer intent, product discovery, basket optimisation, supplier coordination, and post-purchase support through a unified agent architecture with MCP-connected tools.

**Why:** Walmart's journey from agent sprawl to four "super agents" (Sparky, Marty, Associate, Developer) is the canonical architecture lesson of 2025-2026. Lowe's Mylow doubled customer conversion. Coca-Cola reaches 3M+ outlets with AI-assisted ordering. The winning pattern is consolidation + orchestration via MCP, not proliferation of narrow bots. Agent sprawl creates governance chaos, inconsistent UX, and unmanageable cost.

**Business value:**
- Increase conversion rate through goal-directed, intent-aware shopping assistance
- Reduce customer service cost via intelligent deflection with human escalation for value tier
- Accelerate supplier coordination through autonomous negotiation of routine orders
- Enable margin-aware recommendations that optimise for business outcomes not just relevance
- Provide a single governed entry point for all commerce AI — observable, auditable, controllable

---

## what_and_success_criteria

### What this system does

Three primary agent roles (the "super agent" pattern):

**Agent 1 — Sparky (Customer):** Handles intent resolution, product discovery, basket building, reorder, and post-purchase support. Single entry point for all customer interactions.

**Agent 2 — Marty (Supplier/Operations):** Handles supplier queries, order placement, stock coordination, and advertiser/seller support.

**Agent 3 — Associate (Internal):** Store/operations assistant for associates — inventory lookup, task management, policy queries, scheduling.

Each "super agent" is an orchestrator that routes to specialised sub-agents based on intent.

### Success criteria

```yaml
eval_gates:
  intent_classification_accuracy:
    description: Correct classification of customer intent type
    threshold: >= 0.92
    measurement: labelled intent test set (500 queries)

  product_recommendation_accuracy:
    description: Top-3 recommendations contain at least 1 that matches stated need
    threshold: >= 0.85
    measurement: human-labelled relevance set

  conversion_lift:
    description: Sessions with agent assistance vs control (A/B)
    threshold: >= 1.15x  # 15% lift (vs Lowe's 2x benchmark)
    measurement: A/B test in demo environment

  escalation_accuracy:
    description: Correct routing to human for complex/frustrated/regulatory cases
    threshold: >= 0.90
    measurement: labelled escalation test set

  basket_margin_awareness:
    description: Recommendations do not suggest margin-negative items as primary
    threshold: >= 0.95
    measurement: margin audit on 200 recommendation outputs

  response_latency_p95_ms:
    description: Time from message to first meaningful agent response token
    threshold: <= 1500
    measurement: OTEL traces

  agent_sprawl_count:
    description: Number of distinct agent entry points visible to customer
    threshold: <= 2  # the consolidation constraint
    measurement: architecture audit

  cost_per_conversation:
    description: Token cost per complete commerce conversation
    threshold: <= $0.10
    measurement: OTEL cost telemetry
```

---

## all_needed_context

### Reference architecture (Walmart super-agent pattern)

Source: Walmart CTO Suresh Kumar statements, May 2025; Retail Dive, Digital Commerce 360, TechBrew analysis.

Key architectural decisions:
1. **Consolidation over proliferation:** Move from N narrow bots to ~4 orchestrated super agents
2. **MCP for interoperability:** Each super agent communicates with others and with third-party agents via MCP — enabling a customer's Sparky session to continue seamlessly across surfaces
3. **Wallaby-pattern domain LLM:** Commerce-specific LLM trained on retail data outperforms generic LLM for product understanding (we use a fine-tuned/prompted domain layer over base model)
4. **Nano-agent composability:** Super agent can spawn specialised sub-agents ("nano agents") for bounded tasks, assembled in ~1 week
5. **Observable by design:** All agent actions logged; Agentforce Supervisor-pattern for instant human takeover

### Agent graph

```
Customer Message / API Request
        │
        ▼
[Super Agent — Sparky (Customer)]
        │
        │ intent classification
        ├──────────────────────────────────────────────────────────┐
        │                                                            │
        ▼                                                            ▼
[Intent: DISCOVERY]                                    [Intent: SUPPORT / ESCALATE]
        │                                                            │
        ▼                                                            ▼
[Discovery Sub-Agent]                              [Support Sub-Agent]
    │ hybrid search over catalog                       │ RAG over policy + order history
    │ filter: availability, price, specs               │ sentiment detection
    │ rank: relevance × margin × stock                 │ frustration threshold check ─────┐
    │                                                  │                                   │
    ▼                                                  ▼                           [Human Escalation]
[Recommendation Engine]                        [Resolution Agent]
    │ top-N products                               │ answer / action
    │ cross-sell / upsell (margin-aware)           │ refund / return handler
    │                                              │
    ▼                                              ▼
[Basket Agent]                              [Post-Resolution Memory]
    │ add to cart                                  stores interaction outcome
    │ validate stock
    │ apply promotions
    │
    ▼
[Checkout Handoff]
    human or automated checkout
        │
        ▼
[Session Memory Store]
    preferences, history, outcomes
```

**Marty (Supplier/Operations) graph:**
```
Supplier Query / Order Event
        │
        ▼
[Super Agent — Marty]
        ├── [Long-tail supplier negotiation sub-agent]
        │     autonomous for orders < $X threshold
        │     human gate for orders > $X
        │
        ├── [Inventory coordination sub-agent]
        │     reads inventory signals
        │     triggers replenishment alerts → Cap-04
        │
        └── [Seller/advertiser sub-agent]
              campaign setup, performance queries
```

### State schema

```python
class CommerceSessionState(TypedDict):
    # Session
    session_id: str
    agent_type: Literal["sparky", "marty", "associate"]
    channel: str                    # web, mobile, voice, in-store

    # Intent
    raw_message: str
    intent_class: str
    intent_confidence: float
    sub_intent: str | None

    # Customer context
    customer_id: str | None
    order_history: list[Order]
    preferences: CustomerPreferences
    sentiment_score: float          # -1.0 to 1.0
    frustration_flag: bool

    # Discovery
    search_query: str | None
    catalog_results: list[Product]
    recommendations: list[Recommendation]
    basket: list[BasketItem]

    # Margin awareness
    margin_scores: dict[str, float]  # product_id → margin score

    # Escalation
    escalation_triggered: bool
    escalation_reason: str | None
    human_agent_id: str | None

    # Audit
    agent_hops: list[AgentHop]
    cost_tokens: int
    session_outcome: str | None     # converted, deflected, escalated, abandoned
```

### MCP connectors required

```yaml
connectors:
  - name: product-catalog
    tools: [search, get_product, list_category, check_availability, get_pricing]
    description: Full product catalog with real-time stock and pricing

  - name: order-management
    tools: [get_order, create_order, cancel_order, initiate_return, track_shipment]
    description: OMS integration for order lifecycle

  - name: customer-profile
    tools: [get_profile, get_history, update_preferences]
    description: CRM / customer data platform

  - name: promotions
    tools: [get_applicable_promotions, apply_promotion, validate_coupon]

  - name: inventory
    tools: [check_stock, get_stock_level, flag_low_stock]

  - name: supplier-portal
    tools: [send_order, negotiate_price, get_lead_time, get_catalog]

  - name: human-escalation
    tools: [create_ticket, transfer_to_agent, log_escalation]
    description: Omnichannel supervisor / human takeover

  - name: session-memory
    tools: [store_session, retrieve_customer_history, update_preferences]
```

---

## implementation_tasks

```
TASK-03-01: Intent classification model (fine-tuned or few-shot prompted)
  Acceptance: >= 0.92 accuracy on 500-query test set
  Files: cap-03/agents/intent_classifier.py

TASK-03-02: Discovery sub-agent (hybrid catalog search + ranking)
  Acceptance: top-3 recommendations relevant for 85% of test queries
  Files: cap-03/agents/discovery_agent.py

TASK-03-03: Margin-aware recommendation layer
  Acceptance: no margin-negative primary recommendations in 200-item audit
  Files: cap-03/tools/margin_ranker.py

TASK-03-04: Basket agent (add/remove/validate/promote)
  Acceptance: correct basket state after 20 test interaction sequences
  Files: cap-03/agents/basket_agent.py

TASK-03-05: Support sub-agent (RAG over policy + order history)
  Acceptance: correct resolution for 80% of 50 test support queries
  Files: cap-03/agents/support_agent.py

TASK-03-06: Sentiment + frustration detector
  Acceptance: detects frustrated customer in 90% of labelled test cases
  Files: cap-03/tools/sentiment.py

TASK-03-07: Human escalation gate with routing
  Acceptance: escalates on all frustration/regulatory test cases
  Files: cap-03/agents/escalation_agent.py

TASK-03-08: Sparky super-agent orchestrator (LangGraph)
  Acceptance: end-to-end conversation flow for 20 test scenarios
  Files: cap-03/agents/sparky_graph.py

TASK-03-09: Marty supplier agent
  Acceptance: autonomous order placement under threshold, human gate above
  Files: cap-03/agents/marty_graph.py

TASK-03-10: Session memory (preferences + history)
  Files: cap-03/memory/session_store.py

TASK-03-11: MCP connectors (catalog, OMS, CRM, promotions)
  Files: cap-03/tools/connectors/

TASK-03-12: Eval suite + A/B test harness
  Files: cap-03/evals/suite.py

TASK-03-13: Demo: end-to-end commerce conversation runner
  Files: cap-03/demo.py
```

---

## failure_modes_to_design_against

```yaml
failure_modes:
  agent_sprawl_regression:
    description: More than 2 entry points created for customer-facing commerce
    mitigation: Architecture constraint enforced in eval; 1 super agent per persona
    test: count distinct entry points; fail if > 2

  hallucinated_stock:
    description: Agent confirms availability for out-of-stock product
    mitigation: Always check live inventory MCP before confirming; never hallucinate stock
    test: inject OOS products; verify agent does not confirm availability

  margin_negative_recommendation:
    description: Agent recommends items that hurt business margin without business rationale
    mitigation: Margin score appended to every recommendation; primary slot blocked for margin < threshold
    test: inject margin-negative items; verify not surfaced as primary

  masked_quality_decay:
    description: Aggregate deflection looks good but complex cases are poorly handled (Klarna lesson)
    mitigation: CSAT segmented by complexity tier, not aggregate
    test: measure satisfaction separately for simple/medium/complex queries

  frustrated_customer_abandoned:
    description: Frustrated customer receives bot response when they need a human
    mitigation: Frustration threshold triggers mandatory human escalation; no override
    test: inject frustrated messages; verify 100% escalation rate

  transaction_error_propagation:
    description: Order placed for wrong item/quantity without customer confirmation
    mitigation: Order confirmation step required before any OMS write action
    test: verify all order placements require explicit confirmation
```

---

## eval_scorecard

```yaml
metrics:
  intent_classification_accuracy:    { target: 0.92, weight: 0.20 }
  product_recommendation_accuracy:   { target: 0.85, weight: 0.20 }
  conversion_lift:                   { target: 1.15, weight: 0.15 }
  escalation_accuracy:               { target: 0.90, weight: 0.15 }
  basket_margin_awareness:           { target: 0.95, weight: 0.10 }
  response_latency_p95_ms:           { target: 1500, weight: 0.10, lower_is_better: true }
  agent_sprawl_count:                { target: 2,    weight: 0.05, lower_is_better: true, blocking: true }
  cost_per_conversation_usd:         { target: 0.10, weight: 0.05, lower_is_better: true }

passing_threshold: weighted_score >= 0.85
blocking: [agent_sprawl_count, escalation_accuracy]
```

---

## reference_evidence

```yaml
evidence:
  - company: Walmart
    result: Consolidated to 4 super agents; shift planning cut 90→30 min; MCP-native interoperability
    source: Retail Dive, TechBrew, Digital Commerce 360 (Jul-Aug 2025); Walmart CTO statements
    grade: P

  - company: Lowe's (Mylow Companion)
    result: Customer conversion doubled; in-aisle associate satisfaction +200bps
    source: OpenAI Enterprise Report 2025
    grade: P

  - company: Coca-Cola
    result: AI-powered suggested orders for 3M+ outlets in Latin America and India
    source: Various press reports 2025
    grade: P

  - company: Salesforce Agentforce / Reddit
    result: Reddit: 46% case deflection, resolution time 8.9→1.4 min (-84%)
    source: Salesforce customer success stories (2025)
    grade: P

  - company: Klarna (cautionary)
    result: Reversed over-automation; CEO admitted "went too far"; rehiring humans for value tier
    source: Bloomberg, Reuters, MLQ.ai (May-Sept 2025)
    grade: M  # well-documented public reversal
```

---

## codex_instructions

```
When implementing this spec:

1. The consolidation principle is non-negotiable: customer-facing AI must flow through ONE entry point (Sparky). Do not create parallel customer-facing agents.
2. Every catalog lookup and stock check MUST use the live MCP connector. Never use cached data for availability confirmation.
3. Margin scores must be computed and stored in state before recommendations are returned. Never return recommendations without margin scores.
4. Sentiment detection runs on EVERY customer message. Frustration threshold triggers escalation IMMEDIATELY — no retries.
5. Order placement requires explicit customer confirmation turn. This is not optional.
6. A/B test infrastructure is required from day 1 — not a post-launch addition.
7. CSAT must be measured per complexity tier (simple/medium/complex), not aggregate.
8. Session memory must be opt-in (privacy by default) and TTL-governed (clear after X days).
9. All agent hops logged to OTEL with session_id, agent_type, intent_class, tokens, latency.
10. Marty (supplier agent) has a hard dollar threshold above which it cannot act autonomously — human approval required. This value is configured in settings.py, not hardcoded.
```

---

## frontier_improvements
# Added: 2026-06-17 — based on Frontier Agentic AI Engineering Patterns research

### protocol_layering
**Finding:** The agentic commerce stack has consolidated into 4 distinct protocol layers.
Cap-03 should implement all four to be genuinely interoperable.
**Source:** ADR-003-protocol-layering.md

```
Layer 1 — Discovery:    MCP 2025-11-25 (→ 2026-07-28 when final)
                        Product catalog, inventory, policy tools
                        All MCP servers implement stateless handlers (SEP-2567 prep)

Layer 2 — Coordination: A2A v1.0 (Linux Foundation, GA March 2026)
                        Sparky publishes signed Agent Card
                        Marty ↔ third-party supplier agents via A2A
                        Signed tasks with version negotiation

Layer 3 — Checkout:     ACP (OpenAI + Stripe, Apache 2.0) OR
                        UCP (Universal Commerce Protocol, Google + Shopify, Apache 2.0)
                        Configurable per deployment via settings.COMMERCE_PROTOCOL

Layer 4 — Payment:      AP2 (Google, W3C Verifiable Credentials)
                        Cryptographically signed payment mandates
                        NEVER auto-generate above AUTONOMOUS_ACTION_THRESHOLD_USD
                        Human gate required for all AP2 mandates
```

**Naming correction:** "UCP" = Universal **Commerce** Protocol (not "Context").
MCP remains the tool/context protocol. These are complementary, not competing.

### stateless_mcp_migration
All Cap-03 MCP servers (catalog, OMS, CRM, promotions, inventory, supplier-portal)
must implement stateless request handlers NOW (2025-11-25 compliant):
  - No server-side session state
  - Session data in explicit per-request handles
  - Mark with `# MCP-MIGRATE: session-to-handle` for 2026-07-28 upgrade

### webmcp_evaluation
WebMCP (W3C, Chrome preview, Feb 2026): browser-native `navigator.modelContext`
exposes in-page tools. Evaluated for agent-facing commerce surfaces.
Status: optional prototype — not required for MVP. Add as TASK-03-07 stretch goal.

### shopify_renaissance_patterns
Shopify "Renaissance" (Winter '26) introduces patterns directly applicable to Cap-03:
  - **Agentic Storefronts:** products surfaced inside ChatGPT/Perplexity/Copilot
    via ACP/UCP — Sparky's product discovery should support this surface
  - **SimGym:** AI shopper agents simulate traffic for A/B testing
    → Apply to Cap-03 eval: synthetic shoppers validate recommendation quality
  - **Sidekick Pulse:** proactive task surfacing (Heartbeat pattern from OpenClaw)
    → Add to Marty: proactively alert on low-stock before stockout, not after

### harness_sensors_for_cap03
Computational sensors:
  - margin_sensor: blocks margin-negative items from slot-1 (already in SPEC)
  - stock_sensor: blocks OOS items from primary recommendation (already in SPEC)
  - frustration_sensor: triggers immediate escalation (already in SPEC)
  - order_confirmation_sensor: no OMS write without explicit confirmation

New sensors following ADR-002:
  - agent_sprawl_sensor: counts distinct customer-facing entry points → BLOCKING if > 2
  - commerce_protocol_sensor: validates ACP/UCP/AP2 message structure before send
  - csat_tier_sensor: routes CSAT measurement to correct complexity tier bucket

### new_tasks_added
```
TASK-03-05: A2A Agent Cards for Sparky + Marty (signed, versioned, published)
TASK-03-06: Layered commerce protocol (ACP OR UCP checkout + AP2 mandates)
TASK-03-07: SimGym synthetic shopper eval harness
TASK-03-08: Heartbeat proactive alerting for Marty (Shopify Pulse pattern)
TASK-03-09: Stateless MCP server migration annotations (MCP-MIGRATE comments)
```
