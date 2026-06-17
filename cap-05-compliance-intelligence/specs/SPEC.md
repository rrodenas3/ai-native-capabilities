# SPEC-05: Governed Knowledge & Compliance Intelligence
# BriefingScript v1.0 — Machine-readable · Human-reviewed · Agent-executable
# Status: APPROVED
# Codex-ready: YES

---

## goal_and_why

**Goal:** Build an agentic compliance intelligence system that continuously monitors regulatory changes, interprets obligations against an internal use-case inventory, surfaces compliance gaps, and routes them to qualified human experts with full provenance — before they become violations.

**Why:** Harvey AI reached $11B valuation and $190M ARR in two years with 25,000+ custom agents across the AmLaw 100. A&O Shearman saves 2-3 hours per week per lawyer. The EU AI Act's high-risk obligations enforce from August 2, 2026 — organisations building agentic systems ARE the regulated party. This capability is simultaneously the highest-risk (a false negative on a regulatory obligation can cost €35M or 7% of global turnover) and the highest-value ($1,000-$1,500/lawyer/month in the legal market alone). The critical design principle: the false-negative rate on obligations is THE metric. Everything else is secondary.

**Business value:**
- Catch regulatory obligations before enforcement rather than after
- Cut compliance team time on monitoring from days to hours
- Create a continuously-updated, cited, traceable obligation register
- Provide defensible audit trails for regulators
- Enable non-lawyers to query the regulatory landscape with guided, expert-reviewed outputs

---

## what_and_success_criteria

### What this system does

1. **Monitoring Agent** — watches regulatory feeds (EU AI Act, GDPR, NIST, SEC, FDA, sector-specific) for new publications, amendments, enforcement actions, and guidance
2. **Interpretation Agent** — reads regulatory text, extracts obligations, classifies by type (prohibited, high-risk, transparency, general), and maps to effective dates
3. **Gap Mapping Agent** — compares extracted obligations against internal AI use-case inventory to identify gaps, over-compliance, and ambiguities
4. **Knowledge Graph** — maintains entity relationships: regulation → article → obligation → use-case → owner → deadline → evidence
5. **Expert Gate** — routes ALL obligation interpretations to qualified human reviewers before any compliance action is recorded
6. **Audit Trail** — immutable provenance record: source → extraction → interpretation → gap → human decision → resolution
7. **Query Interface** — allows authorised users to query the obligation register with natural language, receiving cited, expert-reviewed answers

### Success criteria

```yaml
eval_gates:
  false_negative_rate_obligations:
    description: Rate of regulatory obligations missed (NOT detected) by the system
    threshold: <= 0.01  # <= 1% miss rate — this is the critical metric
    measurement: against a labelled set of 100 known obligations from EU AI Act + GDPR
    note: FALSE NEGATIVES ARE CATASTROPHIC. Missing an obligation = potential violation.

  citation_accuracy:
    description: Every extracted obligation links to the exact regulatory article/clause
    threshold: >= 0.98
    measurement: automated citation verification against source documents

  false_positive_rate_obligations:
    description: Rate of non-obligations classified as obligations
    threshold: <= 0.10  # FPs waste expert time but are not catastrophic
    measurement: against labelled set

  expert_review_coverage:
    description: Fraction of extracted obligations that pass through expert review before being recorded
    threshold: 1.00  # mandatory — no obligation recorded without expert sign-off
    measurement: audit log

  obligation_extraction_latency:
    description: Time from regulatory publication to obligation extracted and queued for review
    threshold: <= 24 hours
    measurement: end-to-end pipeline latency on test documents

  gap_detection_accuracy:
    description: Fraction of known gaps (use-case missing obligation coverage) correctly detected
    threshold: >= 0.90
    measurement: labelled gap test set (30 scenarios)

  knowledge_graph_accuracy:
    description: Fraction of entity relationships correctly mapped in the KG
    threshold: >= 0.92
    measurement: spot-check of 50 KG triples vs source documents

  query_answer_citation_rate:
    description: Fraction of query answers that include valid source citations
    threshold: 1.00  # every answer must cite its source
    measurement: automated audit on query response set
```

---

## all_needed_context

### Reference architecture

**Harvey AI pattern (source: CNBC Mar 2026, Harvey press releases):**
- 25,000+ custom agents, each scoped to a specific matter or use case
- RAG over proprietary legal corpus with mandatory citation
- Human expert review of all material outputs
- A&O Shearman: "agents do in minutes what previously took several hours"
- Pricing ~$1,000-1,500/lawyer/month → justifies deep investment in accuracy

**EU AI Act structure (critical context for this MVP):**
- Feb 2, 2025: Prohibited practices + AI literacy obligations LIVE
- Aug 2, 2025: GPAI (General Purpose AI) obligations LIVE
- Aug 2, 2026: High-risk obligations + enforcement LIVE ← KEY DATE
- High-risk AI systems in EU AI Act Annex III include: biometric, critical infrastructure, education, employment, essential services, law enforcement, migration, justice
- Fines: up to €35M or 7% global annual turnover (prohibited practices); €15M or 3% (other obligations)
- Autonomous agents with significant tool use → potential GPAI classification

**Moderna GPT governance pattern:**
- Use-case intake form before any GPT creation
- Business owner + SME + technical owner governance triangle
- Guardrail checklist embedded in creation workflow
- GPT catalogue with department tagging and access control

### Agent graph

```
[Regulatory Feed Monitor]
    │ watches: EUR-Lex, Federal Register, NIST, FDA, SEC, EBA, sector feeds
    │ detects: new publications, amendments, enforcement actions, guidance
    │ triggers: new_document event
    │
    ▼
[Document Classification Agent]
    │ classifies document type: regulation / amendment / guidance / enforcement
    │ extracts: effective dates, jurisdiction, sector scope
    │ routes high-relevance documents to Interpretation Agent
    │
    ▼
[Interpretation Agent]
    │ reads regulatory text via hybrid RAG (semantic + structured)
    │ extracts obligations with:
    │   - obligation_type: prohibited | high_risk | transparency | general
    │   - article_reference: exact article/clause
    │   - effective_date
    │   - subject: who this applies to
    │   - action_required: what must be done
    │   - penalty_if_missed: max fine / consequence
    │   - confidence: 0.0-1.0 (low confidence = ambiguous language, needs expert)
    │
    ▼
[Knowledge Graph Update Agent]
    │ adds: regulation → article → obligation → entity → deadline
    │ checks: conflicts with existing obligations
    │ identifies: amendments to prior obligations
    │
    ▼
[Expert Review Gate — MANDATORY]
    │ queues extracted obligations for qualified human reviewer
    │ shows: extracted text, source article, proposed interpretation, confidence
    │ expert: CONFIRM / MODIFY / REJECT / ESCALATE
    │ no obligation enters the register without expert sign-off
    │
    ▼
[Gap Mapping Agent]
    │ reads: confirmed obligation register + internal AI use-case inventory
    │ computes: coverage gaps (use-case X has no control for obligation Y)
    │ computes: overdue obligations (deadline passed, no evidence of compliance)
    │ outputs: gap report with priority (deadline + penalty × gap severity)
    │
    ▼
[Remediation Routing Agent]
    │ assigns gaps to owners (use-case owner, legal, compliance, engineering)
    │ sets deadline alerts
    │ tracks remediation status
    │
    ▼
[Audit Trail — immutable]
    │ source → extraction → interpretation → gap → human decision → resolution
    │ every event timestamped and cryptographically logged
    ▼

[Query Interface]
    │ natural language query from authorised user
    │ hybrid RAG over confirmed obligation register + source corpus
    │ answer MUST include: obligation reference, article citation, effective date, confidence
    │ every answer flagged: CONFIRMED (expert-reviewed) or DRAFT (pending review)
```

### Knowledge Graph schema

```yaml
entities:
  Regulation:
    properties: [id, name, jurisdiction, issuer, publication_date, effective_date, url]

  Article:
    properties: [id, regulation_id, number, title, text, last_amended]

  Obligation:
    properties:
      - id
      - article_id
      - obligation_type: PROHIBITED | HIGH_RISK | TRANSPARENCY | GENERAL | GPAI
      - subject: who it applies to
      - action_required: what must be done
      - effective_date
      - deadline_type: ABSOLUTE | ROLLING | CONDITIONAL
      - penalty_max_eur: float | null
      - penalty_pct_revenue: float | null
      - confidence: float (from interpretation agent)
      - expert_confirmed: bool
      - confirmed_by: str | null
      - confirmed_at: datetime | null

  UseCase:
    properties: [id, name, description, owner, ai_system_type, risk_tier, deployment_status]

  Coverage:
    relationship: UseCase → Obligation
    properties: [status: COVERED | GAP | PARTIAL | EXEMPT, evidence, owner, deadline]

  GapReport:
    properties: [id, use_case_id, obligation_id, severity, deadline, assigned_to, status]
```

### MCP connectors required

```yaml
connectors:
  - name: regulatory-feeds
    tools: [watch_feed, get_new_documents, get_document_text, search_regulations]
    sources: [EUR-Lex, Federal Register, NIST, UK ICO, FDA, EBA]

  - name: knowledge-graph
    tools: [add_node, add_edge, query_graph, get_obligations, get_gaps, update_node]
    backend: Neo4j or FalkorDB

  - name: vector-store
    tools: [index_document, search, get_chunk, update_index]
    backend: pgvector (regulation corpus)

  - name: use-case-inventory
    tools: [list_use_cases, get_use_case, update_coverage, add_use_case]
    description: Internal AI use-case register

  - name: expert-review-queue
    tools: [queue_for_review, get_pending, submit_review, get_review_history]

  - name: audit-log
    tools: [log_event, query_trail, export_audit_report, verify_integrity]
    description: Immutable audit trail (append-only)

  - name: notification
    tools: [send_alert, schedule_reminder, send_digest]
```

---

## implementation_tasks

```
TASK-05-01: Regulatory feed monitor (RSS + API polling, document deduplication)
  Acceptance: correctly ingests 5 test regulatory documents without duplicates
  Files: cap-05/tools/feed_monitor.py

TASK-05-02: Document classification agent
  Acceptance: correctly classifies 20 test documents (regulation/guidance/enforcement)
  Files: cap-05/agents/classifier_agent.py

TASK-05-03: Obligation extraction agent (structured RAG over regulatory text)
  Acceptance: false_negative_rate <= 0.01 on EU AI Act article set
  Files: cap-05/agents/interpretation_agent.py

TASK-05-04: Knowledge graph setup (Neo4j/FalkorDB schema + CRUD)
  Acceptance: all entity types created; query returns correct results for 10 test queries
  Files: cap-05/tools/knowledge_graph.py, cap-05/schemas/kg_schema.py

TASK-05-05: KG update agent (obligation → graph)
  Acceptance: correctly maps 20 test obligations to KG entities
  Files: cap-05/agents/kg_agent.py

TASK-05-06: Expert review gate (queue + UI + audit)
  Acceptance: no obligation proceeds without expert status == "confirmed"
  Files: cap-05/agents/expert_gate.py, cap-05/cli/review.py

TASK-05-07: Use-case inventory connector + gap mapping agent
  Acceptance: detects 90% of gaps in labelled gap test set
  Files: cap-05/agents/gap_agent.py, cap-05/tools/connectors/use_case_inventory.py

TASK-05-08: Audit trail (immutable append-only log)
  Acceptance: cannot modify historical entries; exports valid audit report
  Files: cap-05/tools/audit_trail.py

TASK-05-09: Query interface (natural language → cited obligation answer)
  Acceptance: 100% of answers include valid citations; DRAFT/CONFIRMED flags correct
  Files: cap-05/agents/query_agent.py

TASK-05-10: EU AI Act seed corpus (full regulation + implementing acts)
  Files: cap-05/tests/fixtures/corpus/eu_ai_act/

TASK-05-11: Eval suite
  Files: cap-05/evals/suite.py

TASK-05-12: Demo: query the EU AI Act obligation register
  Files: cap-05/demo.py
```

---

## failure_modes_to_design_against

```yaml
failure_modes:
  missed_obligation_false_negative:
    description: System fails to detect a real regulatory obligation
    mitigation: Conservative extraction (prefer FP over FN); confidence threshold very low (0.3); expert review mandatory
    test: inject 10 real obligations; verify 100% detection
    severity: CRITICAL — can result in €35M fine

  hallucinated_interpretation:
    description: System extracts obligation that does not exist in the regulation text
    mitigation: Every extraction linked to exact article + text quote; no interpretation without anchor
    test: inject regulatory text with NO obligations; verify 0 extracted

  stale_obligation:
    description: System shows obligation that has been superseded by an amendment
    mitigation: Amendment detection in feed monitor; obligation version control in KG; recency checks on all queries
    test: inject amendment superseding an obligation; verify old obligation marked superseded

  expert_bypass:
    description: Obligation enters the confirmed register without expert review
    mitigation: Hard gate in LangGraph — expert_confirmed must be True; database constraint enforces this
    test: attempt to write to confirmed register without review; verify blocked

  knowledge_graph_poisoning:
    description: Incorrect entity relationship corrupts downstream gap detection
    mitigation: All KG writes are logged; rollback mechanism; expert re-review trigger on conflicts
    test: inject conflicting KG entries; verify conflict detection and human alert

  jurisdiction_confusion:
    description: EU obligation applied to US-only operation or vice versa
    mitigation: Jurisdiction metadata mandatory on every obligation; gap mapping filters by jurisdiction
    test: inject EU-only obligation against US-only use case; verify gap not created
```

---

## eval_scorecard

```yaml
metrics:
  false_negative_rate_obligations:    { target: 0.01, weight: 0.35, lower_is_better: true, blocking: true }
  citation_accuracy:                  { target: 0.98, weight: 0.20, blocking: true }
  expert_review_coverage:             { target: 1.00, weight: 0.20, blocking: true }
  false_positive_rate_obligations:    { target: 0.10, weight: 0.05, lower_is_better: true }
  obligation_extraction_latency_hrs:  { target: 24.0, weight: 0.05, lower_is_better: true }
  gap_detection_accuracy:             { target: 0.90, weight: 0.08 }
  knowledge_graph_accuracy:           { target: 0.92, weight: 0.05 }
  query_answer_citation_rate:         { target: 1.00, weight: 0.02, blocking: true }

passing_threshold: weighted_score >= 0.90  # higher bar due to regulatory stakes
blocking: [false_negative_rate_obligations, citation_accuracy, expert_review_coverage, query_answer_citation_rate]
```

---

## codex_instructions

```
When implementing this spec:

1. The false_negative_rate metric is THE blocking metric. It takes absolute priority over speed, cost, and every other metric. When in doubt, extract the obligation (false positive) rather than miss it (false negative).
2. Every obligation extraction MUST include the exact text quote from the source article. No extraction without anchor text.
3. The expert review gate is implemented as a LangGraph interrupt() node with a timeout. Obligations do NOT auto-confirm after timeout — they stay in PENDING state.
4. The knowledge graph is NOT a vector store. It stores relationships and structured data. The vector store is for semantic search over the regulation corpus. Both are required.
5. Jurisdiction metadata is MANDATORY on every entity. Default to UNKNOWN if not extractable, and flag for expert review.
6. The audit trail is append-only. Use a database constraint (no UPDATE/DELETE on audit table) to enforce this.
7. DRAFT vs CONFIRMED distinction must be visible in every query response. Never present a DRAFT interpretation as definitive.
8. The EU AI Act seed corpus (TASK-05-10) must include: the full regulation text, recitals, implementing acts, and the 2025 "AI omnibus" simplification text.
9. Confidence scores below 0.6 trigger mandatory expert review regardless of obligation type.
10. Log everything: extraction runs, KG updates, expert decisions, gap detections, query responses. The audit trail is the product.
```

---

## frontier_improvements
# Added: 2026-06-17 — based on Frontier Agentic AI Engineering Patterns research

### eu_ai_act_enforcement_reality
**Finding:** EU AI Act enforcement dates are confirmed and imminent.
**Source:** EU AI Act official timeline + AI omnibus Political Agreement May 7, 2026

```
LIVE NOW (Feb 2, 2025):     Prohibited practices + AI literacy obligations
LIVE NOW (Aug 2, 2025):     GPAI model obligations + GPAISR (>10²⁵ FLOPs)
AUG 2, 2026 — KEY DATE:     High-risk Annex III + transparency (Art. 50)
                            AI governance structure operational
                            Commission GPAI enforcement powers (fines ≤ 3% / €15M)
AUG 2, 2027:                Pre-Aug-2025 GPAI models must comply
                            Product-embedded high-risk (amended by omnibus)
```

**GPAI Code of Practice (July 2025):** Transparency/Copyright/Safety chapters.
Conformity gives "presumption of conformity" safe harbor — implement it.

**Digital Omnibus (trilogue, proposal):** PROPOSES delaying some Annex III
high-risk to Dec 2, 2027. DO NOT rely on this — plan for Aug 2, 2026.

**GDPR × AI Act dual framework:** Art. 82 GDPR damages claims can compound AI Act
non-compliance. Both frameworks must be modeled simultaneously in the obligation KG.

### harvey_lab_benchmark
**Finding:** Harvey AI released LAB (Legal Agent Benchmark, May 2026) — open-source,
1,250 tasks across 24 practice areas, long-horizon, multi-step.
**Source:** Harvey AI blog (harvey.ai/blog/introducing-harveys-legal-agent-benchmark)

Cap-05's eval methodology should align with LAB's approach:
  - Long-horizon tasks (not single-turn Q&A)
  - Multi-step reasoning across multiple regulatory documents
  - Practice-area specificity (not just "compliance")
  - Trajectory-level scoring (not just output accuracy)

New eval metric (add to eval_scorecard):
  lab_alignment_score:
    description: Task completion rate on LAB-style long-horizon regulatory tasks
    threshold: >= 0.70
    measurement: private subset of LAB-style tasks from EU AI Act corpus

### graph_rag_for_compliance
**Finding:** GraphRAG wins on relationship-heavy, multi-hop queries — exactly
the compliance use case. "Do We Still Need GraphRAG?" (arXiv 2604.09666) confirms:
GraphRAG still outperforms agentic dense RAG on regulation → article → obligation
→ use-case multi-hop chains. The offline preprocessing cost IS justified here.

**Hybrid architecture (pgvector + property graph):**
```
pgvector:      semantic search over regulation text chunks
Neo4j/FalkorDB: Regulation → Article → Obligation → UseCase → Owner → Deadline
               Amendment tracking (obligation version graph)
               GDPR × AI Act cross-references
               Temporal graph (validity_from / validity_until per obligation node)
```

**Temporal knowledge graph:** every obligation node has:
  - `valid_from: datetime`
  - `valid_until: datetime | None`
  - `superseded_by: ObligationNode | None`
  - `amendment_history: list[Amendment]`

This directly addresses the "semantically relevant but no longer valid" failure mode.

### multi_judge_panel
**Finding:** Single LLM-as-judge misses ~1 in 5 production P0 failures in
multi-turn agents. For Cap-05 (highest stakes), a multi-judge panel is required.
**Source:** arXiv 2606.10315 "Catching One in Five" (June 2026)

Cap-05 evaluation uses a 3-judge panel for obligation extraction:
  - Judge 1 (legal perspective): does this read as a binding obligation?
  - Judge 2 (technical perspective): is the subject/action/deadline specified?
  - Judge 3 (regulator perspective): would a regulator expect compliance here?
  Majority vote required. All three must agree for CONFIRMED status.
  All judges MUST differ from the extraction agent model family (ADR-002).

### ssgm_for_compliance
**Finding:** Cap-05 has the highest SSGM governance requirements.
A poisoned obligation (injected via regulatory feed manipulation) → false compliance
→ regulatory violation → up to €35M fine.

SSGM configuration for Cap-05:
```python
governor = SSGMGovernor(
    capability="cap-05",
    decay_half_life_days=90.0,    # regulatory obligations decay slowly
    quarantine_threshold=0.3,     # very strict — errors are existential
)
```

Memory write classification for Cap-05:
  - EXTERNAL (from EUR-Lex, Federal Register): full SSGM validation mandatory
  - INFERRED (LLM-extracted obligation): full SSGM + multi-judge confirmation
  - HUMAN (expert-reviewed and confirmed): TRUSTED — bypass poisoning scan
  - SYNTHETIC (summary/analysis): quarantine threshold 0.2 — maximum strictness

### recursive_ai_governance
**Finding:** Cap-05 governs AI systems using AI agents — the recursive governance
problem. The audit trail must capture "who governed the governor."

Every expert review decision must record:
  - `reviewed_by: str` (human expert ID, never an agent ID)
  - `review_method: str` (read full text / AI-assisted / delegated)
  - `ai_assistance_used: bool` (if AI assisted the human's review, log which model)
  - `confidence: float` (human expert's stated confidence in the decision)

This creates a defensible record if the compliance system itself is audited.

### updated_eval_scorecard
New metrics added to the existing scorecard:

```yaml
lab_alignment_score:
  description: Completion rate on LAB-style long-horizon regulatory tasks
  threshold: >= 0.70
  weight: 0.10

temporal_obligation_accuracy:
  description: Fraction of obligations with correct valid_from/valid_until
  threshold: >= 0.95
  weight: 0.08

multi_judge_consensus_rate:
  description: Rate at which 3-judge panel reaches unanimous agreement
  threshold: >= 0.85
  weight: 0.05
  note: Low consensus → flag for human review, not automatic block

gdpr_ai_act_dual_coverage:
  description: Fraction of AI Act obligations cross-referenced with relevant GDPR articles
  threshold: >= 0.80
  weight: 0.05
```

### new_tasks_added
```
TASK-05-05: SSGM governance wiring with quarantine_threshold=0.3 + decay calibration
TASK-05-06: Multi-judge panel (3-judge, different model families, majority vote)
TASK-05-07: Temporal knowledge graph (obligation version graph, amendment tracking)
TASK-05-08: GraphRAG hybrid (pgvector + Neo4j/FalkorDB for multi-hop compliance)
TASK-05-09: GDPR × AI Act dual-framework obligation mapping
TASK-05-10: LAB-style long-horizon eval harness
TASK-05-11: Recursive AI governance audit trail (who-governed-the-governor)
TASK-05-12: EU AI Act GPAI Code of Practice conformity checker
```
