"""Analysis and synthesis agent for Cap-01."""

from __future__ import annotations

from collections import Counter
import re
from typing import Any

from core.schemas import AgentHop, AgentHopType, AuditEvent, CapabilityID, RetrievalResult
from core.utils.settings import get_settings

CONTRADICTION_PAIRS = [
    ("increase", "decrease"),
    ("higher", "lower"),
    ("risk", "no risk"),
    ("growth", "decline"),
]


def analysis_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    retrieval_results = list(state.get("retrieval_results", []))
    sub_queries = list(state.get("sub_queries", []))
    themes = _key_themes(retrieval_results)
    contradictions = _detect_contradictions(retrieval_results)
    gaps = _detect_gaps(sub_queries, retrieval_results)
    evidence_strength = _evidence_strength(retrieval_results)
    analysis_notes = _format_analysis(themes, evidence_strength, gaps, contradictions)

    hop = AgentHop(
        agent_name="analysis",
        hop_type=AgentHopType.ANALYSIS,
        model=settings.LLM_POWERFUL,
        confidence=evidence_strength,
    )
    audit_event = AuditEvent(
        capability=CapabilityID.DECISION_INTELLIGENCE,
        run_id=str(state.get("run_id", "")),
        session_id=str(state.get("session_id", "")),
        event_type="analysis.completed",
        agent_name="analysis",
        action="synthesise_retrieval",
        payload={
            "theme_count": len(themes),
            "gap_count": len(gaps),
            "contradiction_count": len(contradictions),
            "evidence_strength": evidence_strength,
        },
    )
    return {
        **state,
        "current_agent": "analysis",
        "analysis_notes": analysis_notes,
        "key_themes": themes,
        "contradictions": contradictions,
        "uncertainty_flags": gaps,
        "evidence_strength": evidence_strength,
        "agent_hops": [*state.get("agent_hops", []), hop],
        "audit_trail": [*state.get("audit_trail", []), audit_event],
    }


def _key_themes(results: list[RetrievalResult]) -> list[str]:
    counter: Counter[str] = Counter()
    for result in results:
        for token in result.chunk.content.lower().split():
            token = token.strip(".,;:()[]")
            if len(token) > 4:
                counter[token] += 1
    return [token for token, _count in counter.most_common(5)]


def _detect_contradictions(results: list[RetrievalResult]) -> list[str]:
    text_by_doc: dict[str, str] = {}
    for result in results:
        text_by_doc[result.chunk.doc_id] = " ".join(
            part for part in (text_by_doc.get(result.chunk.doc_id), result.chunk.content.lower()) if part
        )
    contradictions: list[str] = []
    for left, right in CONTRADICTION_PAIRS:
        left_docs = {doc_id for doc_id, text in text_by_doc.items() if left in text}
        right_docs = {doc_id for doc_id, text in text_by_doc.items() if right in text}
        left_only = sorted(left_docs - right_docs)
        right_only = sorted(right_docs - left_docs)
        if left_only and right_only:
            contradictions.append(
                f"Potential contradiction: '{left}' in {left_only}; '{right}' in {right_only}"
            )
    return contradictions


def _detect_gaps(sub_queries: list[str], results: list[RetrievalResult]) -> list[str]:
    corpus_text = " ".join(result.chunk.content.lower() for result in results)
    gaps: list[str] = []
    for query in sub_queries:
        keywords = _query_keywords(query)
        if keywords and not any(keyword in corpus_text for keyword in keywords):
            gaps.append(f"No retrieved evidence covers: {query}")
    if not results:
        gaps.append("No retrieved evidence available for analysis")
    return gaps


def _query_keywords(query: str) -> list[str]:
    stopwords = {"a", "an", "and", "are", "for", "how", "the", "what", "where", "which", "with"}
    tokens = re.findall(r"[a-z0-9]+", query.lower())
    return [token for token in tokens if len(token) >= 3 and token not in stopwords]


def _evidence_strength(results: list[RetrievalResult]) -> float:
    if not results:
        return 0.0
    average_score = sum(result.combined_score for result in results) / len(results)
    coverage_bonus = min(len(results) / 10, 1.0) * 0.2
    return round(min(average_score + coverage_bonus, 1.0), 3)


def _format_analysis(
    themes: list[str],
    evidence_strength: float,
    gaps: list[str],
    contradictions: list[str],
) -> str:
    return "\n".join(
        [
            "Key themes: " + (", ".join(themes) if themes else "none from retrieved evidence"),
            f"Evidence strength: {evidence_strength:.3f}",
            "Gaps: " + ("; ".join(gaps) if gaps else "none detected"),
            "Contradictions: " + ("; ".join(contradictions) if contradictions else "none detected"),
        ]
    )

