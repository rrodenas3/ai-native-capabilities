"""Fast sentiment and frustration detector."""

from __future__ import annotations

import re

from cap03_schema_loader import SentimentResult

FRUSTRATION_PATTERNS = {
    "human_request": re.compile(r"\b(human|agent|representative|manager|supervisor)\b", re.I),
    "angry": re.compile(r"\b(angry|furious|unacceptable|terrible|awful|hate|ridiculous)\b", re.I),
    "profanity": re.compile(r"\b(damn|hell|crap)\b", re.I),
    "repeated": re.compile(r"\b(again|third time|second time|still waiting|keeps happening)\b", re.I),
    "brand_negative": re.compile(r"\b(never buying|lost my trust|cancel my account)\b", re.I),
}


def detect_sentiment(message: str) -> SentimentResult:
    triggers = [name for name, pattern in FRUSTRATION_PATTERNS.items() if pattern.search(message)]
    all_caps = len(message) >= 12 and message.upper() == message and any(char.isalpha() for char in message)
    if all_caps:
        triggers.append("all_caps")
    frustration = bool(triggers)
    score = -0.85 if frustration else (0.35 if re.search(r"\b(love|great|thanks|perfect)\b", message, re.I) else 0.0)
    return SentimentResult(sentiment_score=score, frustration_flag=frustration, triggers=triggers)
