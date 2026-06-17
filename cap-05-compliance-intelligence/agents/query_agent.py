"""Natural-language query interface over confirmed and draft obligations."""

from __future__ import annotations

import re
from typing import Any


def answer_query(query: str, obligations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    terms = _terms(query)
    article_filter = _article_filter(query)
    answers: list[dict[str, Any]] = []
    for obligation in obligations:
        haystack = " ".join(
            str(obligation.get(key, ""))
            for key in ("article_reference", "obligation_type", "subject", "action_required", "anchor_text")
        ).lower()
        if article_filter and article_filter not in str(obligation.get("article_reference", "")).lower():
            continue
        if terms and not any(term in haystack for term in terms):
            continue
        answers.append(
            {
                "obligation_id": obligation["id"],
                "obligation_reference": obligation["article_reference"],
                "article_citation": obligation["anchor_text"],
                "effective_date": obligation["effective_date"],
                "confidence": obligation["confidence"],
                "status": "CONFIRMED" if obligation.get("expert_confirmed") else "DRAFT",
                "answer": obligation["action_required"],
            }
        )
    return answers


def citation_rate(answers: list[dict[str, Any]]) -> float:
    if not answers:
        return 1.0
    cited = [answer for answer in answers if answer.get("article_citation") and answer.get("obligation_reference")]
    return len(cited) / len(answers)


def _terms(query: str) -> list[str]:
    ignored = {"what", "which", "show", "me", "the", "for", "and", "article", "obligations", "obligation"}
    return [term for term in re.findall(r"[a-z0-9-]+", query.lower()) if term not in ignored and len(term) > 2]


def _article_filter(query: str) -> str | None:
    match = re.search(r"article\s+(\d+)", query, re.IGNORECASE)
    return f"article {int(match.group(1))}" if match else None
