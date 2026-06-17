"""Generate the deterministic Cap-01 demo corpus."""

from __future__ import annotations

import argparse
import random
from pathlib import Path

DOMAINS = [
    ("supply-chain", "Supply Chain", ["supplier concentration", "freight reliability", "inventory buffers"]),
    ("finance", "Finance", ["margin pressure", "cash conversion", "pricing discipline"]),
    ("customer", "Customer", ["retention", "enterprise expansion", "support responsiveness"]),
    ("ai-governance", "AI Governance", ["model controls", "review workflow", "policy adoption"]),
    ("market", "Market", ["competitive response", "demand signals", "regional growth"]),
]
ACCESS_TIERS = ["public", "internal", "restricted"]
CONTRADICTIONS = {
    1: ("Supplier concentration risk is increasing across tier-two manufacturers.", "Supplier concentration risk is decreasing after dual-source onboarding."),
    2: ("Pricing pressure is higher in enterprise renewals than forecast.", "Pricing pressure is lower in enterprise renewals than forecast."),
    3: ("AI adoption is accelerating in sales and operations workflows.", "AI adoption is slowing because review capacity is constrained."),
    4: ("Regulatory burden is increasing for customer-facing automation.", "Regulatory burden is decreasing as standard controls mature."),
    5: ("Cash conversion is improving as inventory turns recover.", "Cash conversion is deteriorating as inventory turns stall."),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    args.output.mkdir(parents=True, exist_ok=True)
    for existing in args.output.glob("*.md"):
        existing.unlink()

    for index in range(1, 101):
        domain_slug, domain_title, themes = DOMAINS[(index - 1) % len(DOMAINS)]
        tier = ACCESS_TIERS[(index - 1) % len(ACCESS_TIERS)]
        doc_type = ["board-memo", "operating-review", "risk-register", "strategy-note"][(index - 1) % 4]
        pair_id = (index + 1) // 2 if index <= 10 else None
        contradiction = _contradiction_sentence(index, pair_id)
        title = f"{domain_title} signal brief {index:03d}"
        body = _body(index, domain_title, themes, contradiction)
        frontmatter = [
            "---",
            f"doc_id: cap01-demo-{index:03d}",
            f"title: {title}",
            f"domain: {domain_slug}",
            f"doc_type: {doc_type}",
            f"access_tier: {tier}",
            f"date: 2026-05-{((index - 1) % 28) + 1:02d}",
        ]
        if pair_id is not None:
            frontmatter.append(f"contradiction_pair: pair-{pair_id:02d}")
        frontmatter.extend(["---", "", f"# {title}", "", body])
        (args.output / f"doc-{index:03d}-{domain_slug}.md").write_text("\n".join(frontmatter), encoding="utf-8")


def _contradiction_sentence(index: int, pair_id: int | None) -> str:
    if pair_id is None:
        return ""
    left, right = CONTRADICTIONS[pair_id]
    return left if index % 2 else right


def _body(index: int, domain_title: str, themes: list[str], contradiction: str) -> str:
    lead = contradiction or (
        f"The {domain_title.lower()} review shows stable execution with selective watch items for the next planning cycle."
    )
    paragraphs = [
        lead,
        (
            f"Management highlighted {themes[0]}, {themes[1]}, and {themes[2]} as the main signals for the quarter. "
            "The evidence is directionally consistent across operating reviews, leadership notes, and planning materials. "
            "Teams should treat the signal as useful for prioritisation while preserving human review for any external commitment."
        ),
        (
            "The board-facing implication is that owners need a concise evidence trail, clear confidence labels, and a visible path "
            "from source material to recommendation. The memo links each action to a measurable operating indicator so reviewers can "
            "challenge assumptions without reopening the entire discovery process."
        ),
        (
            f"For scenario {index:03d}, the recommended posture is to protect near-term commitments, monitor leading indicators weekly, "
            "and revisit the decision when new source documents change the confidence score. Risk appetite remains moderate because the "
            "available corpus contains useful signals but not enough independently measured evidence for automatic approval."
        ),
    ]
    filler = (
        f"Additional context for {domain_title.lower()} emphasizes accountable ownership, source-backed claims, explicit uncertainty, "
        "and repeatable follow-up. The same pattern appears in finance, operations, customer, governance, and market material, which "
        "allows retrieval tests to exercise cross-domain ranking and contradiction handling. "
    )
    while len(" ".join(paragraphs).split()) < 330:
        paragraphs.append(filler)
    return "\n\n".join(paragraphs)


if __name__ == "__main__":
    main()
