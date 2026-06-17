"""Document classification agent for regulatory publications."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass(frozen=True)
class ClassifiedDocument:
    document_id: str
    document_type: str
    jurisdiction: str
    sector_scope: tuple[str, ...]
    effective_dates: tuple[str, ...]
    relevance: str


def classify_document(document: dict[str, Any]) -> ClassifiedDocument:
    title = str(document.get("title", ""))
    text = str(document.get("text", ""))
    source = str(document.get("source", ""))
    document_id = str(document.get("id", "unknown"))
    blob = f"{title}\n{text}".lower()
    return ClassifiedDocument(
        document_id=document_id,
        document_type=_document_type(blob),
        jurisdiction=_jurisdiction(blob, source),
        sector_scope=tuple(_sector_scope(blob)),
        effective_dates=tuple(_effective_dates(blob)),
        relevance="HIGH" if any(term in blob for term in ("ai act", "artificial intelligence", "nist ai")) else "MEDIUM",
    )


def _document_type(blob: str) -> str:
    if any(term in blob for term in ("amendment", "amending", "omnibus", "supersedes")):
        return "AMENDMENT"
    if any(term in blob for term in ("fine", "penalty", "enforcement", "violation", "sanction")):
        return "ENFORCEMENT"
    if any(term in blob for term in ("guidance", "guideline", "code of practice", "nist")):
        return "GUIDANCE"
    return "REGULATION"


def _jurisdiction(blob: str, source: str) -> str:
    if "eur-lex" in source.lower() or "european union" in blob or "eu ai act" in blob:
        return "EU"
    if "federal register" in source.lower() or "united states" in blob:
        return "US"
    if "nist" in source.lower():
        return "US"
    return "UNKNOWN"


def _sector_scope(blob: str) -> list[str]:
    scopes = []
    mapping = {
        "biometric": "biometric",
        "employment": "employment",
        "education": "education",
        "critical infrastructure": "critical_infrastructure",
        "law enforcement": "law_enforcement",
        "migration": "migration",
        "justice": "justice",
        "gpai": "general_purpose_ai",
        "general-purpose": "general_purpose_ai",
        "health": "health",
    }
    for needle, scope in mapping.items():
        if needle in blob and scope not in scopes:
            scopes.append(scope)
    return scopes or ["general"]


def _effective_dates(blob: str) -> list[str]:
    dates = sorted(set(re.findall(r"\b20\d{2}-\d{2}-\d{2}\b", blob)))
    if not dates:
        friendly = {
            "2 august 2026": "2026-08-02",
            "august 2, 2026": "2026-08-02",
            "2 august 2025": "2025-08-02",
            "february 2, 2025": "2025-02-02",
        }
        for phrase, iso in friendly.items():
            if phrase in blob:
                dates.append(iso)
    if not dates:
        dates.append(date.today().isoformat())
    return dates
