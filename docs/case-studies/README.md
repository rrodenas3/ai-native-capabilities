# Evidence Base — Production AI Deployments

Every architectural decision in this project traces to documented production evidence. Evidence grades:

- `[M]` **Measured** — independent, quantified, peer-reviewed or audited
- `[P]` **Partial** — company-reported, directionally credible
- `[V]` **Vendor claim** — directional only, treat with caution

---

## Cap-01 · Decision Intelligence

### Morgan Stanley `[P]`
- 98% of advisor teams adopted internal GPT-4 assistant within months of launch
- Document access increased from 20% → 80% of available content
- Pattern: RAG with forced citations — every factual claim traced to source
- **Design implication:** `citation_accuracy ≥ 0.95` is non-negotiable. The reason Morgan Stanley could achieve 98% adoption is trust. Trust requires citations. No exceptions.

### Microsoft Azure SRE Agent `[M]`
- MTTM (Mean Time to Mitigate) reduced from 40.5 hours → 3 minutes
- Same underlying models — better harness engineering
- **Design implication:** `Agent = Model + Harness`. Model quality is table stakes. Harness quality determines production reliability. ADR-002 is grounded in this finding.

---

## Cap-02 · Agentic Engineering

### Ramp `[P]`
- 99.5% of employees (finance, marketing, ops) are active AI users
- 84% use coding agents weekly — the technical/non-technical divide has dissolved
- **Design implication:** SASE is designed for this world. Engineers are not the only users of coding agents. The BriefingScript format must work for anyone who can write a clear goal statement.

### Fu et al. (ACM 2025) `[M]`
- 29.5% of unscanned Copilot-generated Python contains security weaknesses
- Pattern: security scanning is not optional when agents write code
- **Design implication:** `security_weakness_rate ≤ 5.0 per 1000 lines` is a blocking eval metric. The harness enforces it; humans don't review raw agent output.

---

## Cap-03 · Agentic Commerce

### Walmart (Sparky / Marty) `[P]`
- Consolidated dozens of narrow bots into a single Sparky super-agent routing to specialist sub-agents
- Agent sprawl had created governance chaos — the solution was consolidation, not more agents
- **Design implication:** `agent_sprawl_count ≤ 2` is a blocking metric. Sparky is the single entry point. ADR-003 protocol layering enforces this.

### Klarna `[P]`
- Deployed AI customer service; CSAT reported by complexity tier, not aggregate
- Frustrated customers trigger immediate human handoff — no retries
- **Design implication:** `frustration_flag → escalation_accuracy ≥ 0.90`. CSAT aggregate scores hide frustration. Measure by tier.

### Lowe's (Mylow) `[P]`
- 2× conversion rate improvement with AI-assisted product discovery
- **Design implication:** Discovery Agent margin-negative item filtering (slot 1 blocked for margin-negative items).

---

## Cap-04 · Autonomous Operations

### Walmart (self-healing inventory) `[P]`
- Out-of-stocks reduced ~16% with AI-driven demand forecasting and replenishment
- **Design implication:** Cap-04's forecast→exception→replenish pipeline targets this directly. A 1% out-of-stock reduction at a $5B retailer recovers $50M.

### DHL `[M]`
- 15% logistics cost reduction
- 30% forecast accuracy improvement
- **Design implication:** Forecast accuracy improvement is the financial lever. The digital twin validates every action before commit — a wrong replenishment order is expensive.

### Flowr (arXiv 2604.05987) `[M]`
- Stateful, long-running agentic workflows require durable execution — not in-memory state
- **Design implication:** LangGraph with PostgreSQL checkpointing is the architecture. Not optional. Supply chain tasks run for hours to days.

### Deutsche Telekom (RAN Guardian) `[P]`
- Autonomous network operations with human approval gates above defined thresholds
- **Design implication:** The human approval gate in Cap-04 is a LangGraph `interrupt()`. The graph physically cannot proceed without an explicit human decision. `human_approval_coverage = 1.00` is blocking.

---

## Cap-05 · Compliance Intelligence

### Harvey AI `[P]`
- $11B valuation, $190M ARR in legal AI
- Pattern: AI-assisted document review + human sign-off, not full automation
- **Design implication:** Expert Gate is mandatory. `expert_review_coverage = 1.00` is blocking. No obligation is confirmed without human sign-off. The value is speed of extraction, not removal of expert judgment.

### A&O Shearman `[P]`
- 2-3 hours/week saved per lawyer on regulatory document review
- Pattern: AI does initial extraction; lawyer validates
- **Design implication:** The Interpretation Agent extracts obligations; Expert Gate confirms. `false_negative_rate ≤ 0.01` — a missed obligation is potentially existential.

### EU AI Act (August 2, 2026 enforcement) `[M]`
- Annex III high-risk AI systems enforcement begins August 2, 2026
- Fines: up to €35M or 7% of global annual turnover (whichever is higher) for prohibited practices
- 113 articles + 180 recitals requiring systematic obligation mapping
- **Design implication:** Cap-05's knowledge graph maps Regulation → Article → Obligation → UseCase. Conservative extraction always — false positives are reviewable; false negatives are existential.
