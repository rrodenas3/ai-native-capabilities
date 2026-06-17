"""Regulatory feed monitor with deterministic adapters for test feeds."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any


@dataclass(frozen=True)
class FeedDocument:
    id: str
    source: str
    title: str
    url: str
    published_at: str
    text: str
    detected_at: str
    extraction_due_at: str


class RegulatoryFeedMonitor:
    """Polls regulatory feed payloads and queues unique documents for extraction."""

    SOURCES = ("EUR-Lex", "Federal Register", "NIST CSRC")

    def __init__(self) -> None:
        self._seen: set[str] = set()
        self._queued: list[FeedDocument] = []

    def poll_feeds(self, feed_documents: list[dict[str, Any]]) -> list[FeedDocument]:
        detected_at = datetime.now(UTC)
        new_documents: list[FeedDocument] = []
        for raw in feed_documents:
            try:
                source = str(raw["source"]).strip()
                title = str(raw["title"]).strip()
                url = str(raw["url"]).strip()
                published_at = str(raw["published_at"]).strip()
                text = str(raw["text"]).strip()
            except KeyError:
                continue
            if source not in self.SOURCES or not title or not url or not text:
                continue
            key = _dedupe_key(title, url, published_at)
            if key in self._seen:
                continue
            self._seen.add(key)
            doc = FeedDocument(
                id=f"doc-{len(self._seen):04d}",
                source=source,
                title=title,
                url=url,
                published_at=published_at,
                text=text,
                detected_at=detected_at.isoformat(),
                extraction_due_at=(detected_at + timedelta(minutes=60)).isoformat(),
            )
            self._queued.append(doc)
            new_documents.append(doc)
        return new_documents

    def get_new_documents(self) -> list[FeedDocument]:
        return list(self._queued)

    def queue_latency_hours(self, doc: FeedDocument) -> float:
        detected = datetime.fromisoformat(doc.detected_at)
        due = datetime.fromisoformat(doc.extraction_due_at)
        return (due - detected).total_seconds() / 3600


def _dedupe_key(title: str, url: str, published_at: str) -> str:
    normal_url = re.sub(r"[?#].*$", "", url.lower()).rstrip("/")
    normal_title = re.sub(r"\s+", " ", title.lower()).strip()
    normal_pub = published_at[:10]
    digest = hashlib.sha256(f"{normal_title}|{normal_url}|{normal_pub}".encode())
    return digest.hexdigest()
