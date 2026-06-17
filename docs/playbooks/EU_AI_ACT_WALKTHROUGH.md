# EU AI Act Obligation Walkthrough — Enterprise Demo Playbook

> **Urgency:** Annex III high-risk AI system provisions enforce **August 2, 2026**. Fines reach €35M or 7% of global annual turnover.

---

## What This Demo Shows

Cap-05 Compliance Intelligence automates the most expensive part of EU AI Act compliance: reading 113 articles and 180 recitals, extracting every obligation that applies to your AI systems, and producing a documented audit trail showing expert review of each one.

A compliance lawyer at A&O Shearman estimated this takes **2-3 hours per lawyer per week** — manually. Cap-05 does it in minutes, with citations.

---

## What the System Actually Does

```
EU AI Act text
     │
     ▼
Interpretation Agent    → Extracts obligations per article
     │
     ▼
Expert Review Gate      → interrupt() — no obligation confirmed without sign-off
     │
     ▼
Knowledge Graph Agent   → Maps: Regulation → Article → Obligation → UseCase
     │
     ▼
Gap Mapping Agent       → Compares obligations vs. your use-case inventory
     │
     ▼
Query Agent             → Answers specific compliance questions with citations
```

Every step is eval-gated. `false_negative_rate ≤ 0.01` is a **blocking metric** — the system is calibrated to prefer false positives over false negatives. A missed obligation is potentially existential.

---

## Running the Demo

### Prerequisites

```bash
# Install dependencies
pip install -e ".[dev]"

# Infrastructure (postgres + redis)
docker compose up -d
```

### Mock mode (no API cost, < 30 seconds)

```bash
python scripts/walkthrough_eu_ai_act.py
```

Output: `reports/artifacts/eu_ai_act_walkthrough.md`

### Real mode (requires ANTHROPIC_API_KEY)

```bash
# Note: Cap-05 regulatory interpretation uses claude-opus-4-8
# Estimated cost: $0.50–$2.00 per full run
LLM_MODE=real python scripts/walkthrough_eu_ai_act.py
```

### Custom output path

```bash
python scripts/walkthrough_eu_ai_act.py --output ~/Desktop/eu_ai_act_report.md
```

---

## What to Say in the Meeting

### Opening (30 seconds)

> "I want to show you something specific. Your legal team is currently reading the EU AI Act manually — 113 articles, 180 recitals — trying to figure out which obligations apply to your AI systems. That takes weeks. The fine for getting it wrong is €35 million or 7% of global revenue. August 2nd is 46 days away."

> "Let me show you what this looks like when it's automated."

### During the demo

Run the walkthrough live:
```bash
python scripts/walkthrough_eu_ai_act.py
```

Point to what's happening:
1. **Obligation extraction** — Cap-05 reads the EU AI Act articles and identifies what the law requires
2. **Expert review gate** — every obligation passes through a human-in-the-loop gate before it's confirmed; no obligation is missed due to automation
3. **Citations** — every finding links back to the specific article and paragraph
4. **Audit trail** — `audit_events` count shows the full chain of evidence

### The leave-behind

```bash
python scripts/export_artifacts.py
# Opens: reports/artifacts/compliance_report.html
```

Hand them a browser tab showing their obligation list, gap analysis, and audit trail — formatted as a report they can share with their board or legal team.

---

## The Compliance Conversation

| Question they'll ask | How to answer |
|---|---|
| "Is this accurate?" | The `false_negative_rate` eval metric is blocking at ≤ 1%. Conservative extraction by design — we surface more, not less. |
| "Can we trust it for our actual obligations?" | The Expert Review Gate means nothing ships without legal sign-off. The system finds; your lawyers confirm. |
| "What about GDPR / sector-specific regs?" | The same pipeline works for any regulatory document. EU AI Act is the demo; your reg docs are the production input. |
| "How long to adapt this to our AI inventory?" | 4–8 week governed MVP on your specific use-case inventory and regulatory scope. That's the offer. |
| "Do you store our data?" | Local or your cloud. No external data sharing. Full audit trail stays in your environment. |

---

## Making It Real

The demo uses mock mode against fixture articles. To show real output:

1. Set `LLM_MODE=real` and provide `ANTHROPIC_API_KEY`
2. Add your actual AI use-case inventory to `cap-05-compliance-intelligence/agents/gap_agent.py` `UseCaseInventory`
3. Point the corpus loader at your specific regulatory documents

The 4-8 week "Governed AI Capability Sprint" delivers step 3 on your specific regulatory scope, with your data, in your environment.

---

## Architecture Reference

- **Spec:** `cap-05-compliance-intelligence/specs/SPEC.md`
- **Eval gates:** `false_negative_rate ≤ 0.01` · `citation_accuracy ≥ 0.98` · `expert_review_coverage = 1.00`
- **Model routing:** `claude-opus-4-8` for regulatory interpretation (no downgrade — false negatives are catastrophic)
- **Memory governance:** `SSGMGovernor` at `0.3` quarantine threshold — most conservative of all 5 capabilities
- **Deployment:** `DEPLOYMENT.md` at repo root
