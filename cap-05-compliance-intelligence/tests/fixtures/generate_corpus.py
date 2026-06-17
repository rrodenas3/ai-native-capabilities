"""Generate deterministic EU AI Act fixture corpus for Cap-05 tests."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "corpus" / "eu_ai_act"

OBLIGATION_TOPICS = (
    ("PROHIBITED", "providers and deployers", "must not place prohibited AI practices on the Union market", "2025-02-02", "EUR 35M"),
    ("HIGH_RISK", "providers of high-risk AI systems", "shall maintain a documented risk management system", "2026-08-02", "EUR 15M"),
    ("HIGH_RISK", "providers of high-risk AI systems", "shall keep automatically generated logs", "2026-08-02", "EUR 15M"),
    ("HIGH_RISK", "deployers of high-risk AI systems", "must ensure human oversight by trained personnel", "2026-08-02", "EUR 15M"),
    ("TRANSPARENCY", "providers and deployers of AI systems that interact with persons", "shall inform natural persons that they are interacting with an AI system", "2026-08-02", "EUR 15M"),
    ("GPAI", "providers of general-purpose AI models", "must draw up and maintain technical documentation", "2025-08-02", "EUR 15M"),
    ("GPAI", "providers of general-purpose AI models", "shall put in place a policy to comply with Union copyright law", "2025-08-02", "EUR 15M"),
    ("GENERAL", "providers and deployers", "are required to ensure a sufficient level of AI literacy for staff", "2025-02-02", "EUR 15M"),
)


def main() -> None:
    article_dir = ROOT / "articles"
    recital_dir = ROOT / "recitals"
    amendment_dir = ROOT / "amendments"
    article_dir.mkdir(parents=True, exist_ok=True)
    recital_dir.mkdir(parents=True, exist_ok=True)
    amendment_dir.mkdir(parents=True, exist_ok=True)

    known = []
    for number in range(1, 114):
        topic = OBLIGATION_TOPICS[(number - 1) % len(OBLIGATION_TOPICS)]
        obligation_type, subject, action, effective_date, penalty = topic
        anchor = f"{subject.title()} {action}; non-compliance may be subject to administrative fines up to {penalty}."
        article_text = "\n".join(
            [
                f"# Article {number} - Synthetic EU AI Act Article {number}",
                "",
                f"Effective date: {effective_date}",
                "Jurisdiction: EU",
                "",
                anchor,
                f"Providers shall preserve evidence for Article {number} where necessary for competent authority review.",
                "This fixture is deterministic and supports compliance pipeline evaluation.",
            ]
        )
        (article_dir / f"article-{number:03d}.md").write_text(article_text, encoding="utf-8")
        if len(known) < 100:
            known.append(
                {
                    "article_reference": f"Article {number}",
                    "article_id": f"article-{number:03d}",
                    "obligation_type": obligation_type,
                    "subject": subject,
                    "effective_date": effective_date,
                    "anchor_text": anchor,
                }
            )

    for number in range(1, 181):
        text = "\n".join(
            [
                f"# Recital {number}",
                "",
                "This recital explains the context, objectives, and proportionality considerations of the EU AI Act.",
                "It does not create standalone obligations in this fixture.",
            ]
        )
        (recital_dir / f"recital-{number:03d}.md").write_text(text, encoding="utf-8")

    (amendment_dir / "2025-ai-omnibus.md").write_text(
        "\n".join(
            [
                "# 2025 AI Omnibus simplification text",
                "",
                "The proposal amends administrative timing, but regulated parties must continue planning for the 2026-08-02 high-risk obligations.",
                "Superseded obligations shall remain traceable through amendment history.",
            ]
        ),
        encoding="utf-8",
    )
    (ROOT / "known_obligations.json").write_text(json.dumps(known, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
