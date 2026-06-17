"""Conservative obligation extraction for regulatory text."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from core.utils.settings import get_settings

BINDING_TERMS = ("must", "shall", "required", "prohibited", "may not", "ensure", "provide")


def extract_obligations(document: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract all likely obligations, preferring false positives over false negatives."""

    article_reference = str(document.get("article_reference") or document.get("article") or "Article UNKNOWN")
    article_id = _article_id(article_reference)
    effective_date = str(document.get("effective_date") or "2026-08-02")
    jurisdiction = str(document.get("jurisdiction") or "EU")
    source_url = str(document.get("source_url") or document.get("url") or "fixture://eu-ai-act")
    text = str(document.get("text") or "")
    obligations: list[dict[str, Any]] = []
    for sentence in _sentences(text):
        lower = sentence.lower()
        if not _is_obligation(lower):
            continue
        obligation_type = _obligation_type(lower)
        obligation_id = _obligation_id(article_id, sentence)
        confidence = 0.93 if any(term in lower for term in ("must", "shall", "required", "prohibited", "may not")) else 0.45
        obligations.append(
            {
                "id": obligation_id,
                "article_id": article_id,
                "article_reference": article_reference,
                "obligation_type": obligation_type,
                "effective_date": effective_date,
                "subject": _subject(sentence),
                "action_required": _action_required(sentence),
                "penalty_max_eur": _penalty_max_eur(lower),
                "penalty_pct_revenue": 7.0 if "35,000,000" in sentence or "eur 35m" in lower else 3.0 if "15,000,000" in sentence or "eur 15m" in lower else None,
                "deadline_type": "ABSOLUTE" if re.search(r"\b20\d{2}-\d{2}-\d{2}\b", sentence) else "CONDITIONAL",
                "confidence": confidence,
                "anchor_text": sentence,
                "jurisdiction": jurisdiction,
                "source_url": source_url,
                "requires_expert_review": True,
                "expert_confirmed": False,
                "status": "PENDING",
                "extraction_model": get_settings().LLM_POWERFUL,
            }
        )
    return obligations


def extract_from_articles(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    extracted: list[dict[str, Any]] = []
    for article in articles:
        extracted.extend(extract_obligations(article))
    return extracted


def _sentences(text: str) -> list[str]:
    sentences: list[str] = []
    for line in text.splitlines():
        clean = re.sub(r"\s+", " ", line).strip()
        if not clean or clean.startswith("#") or ":" in clean[:24]:
            continue
        sentences.extend(part.strip() for part in re.split(r"(?<=\.)\s+", clean) if part.strip())
    return sentences


def _is_obligation(lower_sentence: str) -> bool:
    return any(term in lower_sentence for term in BINDING_TERMS)


def _article_id(article_reference: str) -> str:
    match = re.search(r"(\d+)", article_reference)
    return f"article-{int(match.group(1)):03d}" if match else "article-unknown"


def _obligation_id(article_id: str, anchor_text: str) -> str:
    digest = hashlib.sha256(anchor_text.encode("utf-8")).hexdigest()[:10]
    return f"obl-{article_id}-{digest}"


def _obligation_type(lower_sentence: str) -> str:
    if "prohibited" in lower_sentence or "may not" in lower_sentence:
        return "PROHIBITED"
    if "general-purpose" in lower_sentence or "gpai" in lower_sentence:
        return "GPAI"
    if "transparency" in lower_sentence or "inform" in lower_sentence or "provide information" in lower_sentence:
        return "TRANSPARENCY"
    if "high-risk" in lower_sentence:
        return "HIGH_RISK"
    return "GENERAL"


def _subject(sentence: str) -> str:
    match = re.match(r"([^.;]{1,90}?)(?:\s+must|\s+shall|\s+are required|\s+is required|\s+may not|\s+are prohibited)", sentence, re.IGNORECASE)
    if match:
        return match.group(1).strip(" ,")
    return "regulated entity"


def _action_required(sentence: str) -> str:
    return sentence.strip()


def _penalty_max_eur(lower_sentence: str) -> float | None:
    if "35,000,000" in lower_sentence or "eur 35m" in lower_sentence:
        return 35_000_000.0
    if "15,000,000" in lower_sentence or "eur 15m" in lower_sentence:
        return 15_000_000.0
    return None
