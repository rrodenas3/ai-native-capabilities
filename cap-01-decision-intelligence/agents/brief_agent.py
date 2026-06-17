"""Brief assembly agent for Cap-01 board-ready output."""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from typing import Any

from core.schemas import AgentHop, AgentHopType, AuditEvent, CapabilityID, Citation, Finding, RetrievalResult
from core.utils.settings import get_settings

BriefOutput = _BriefOutput = None


def brief_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """Assemble verified analysis into a structured executive brief."""

    settings = get_settings()
    retrieval_results = list(state.get("retrieval_results", []))
    uncertainty_flags = _normalise_uncertainty(state)
    findings = _build_findings(state, retrieval_results, uncertainty_flags)
    executive_summary = _executive_summary(str(state.get("query", "")), findings, uncertainty_flags)
    recommended_actions = _recommended_actions(findings, uncertainty_flags)
    overall_confidence = _overall_confidence(findings)
    brief = _brief_output_schema()(
        executive_summary=executive_summary,
        key_findings=findings,
        uncertainty_flags=uncertainty_flags,
        recommended_actions=recommended_actions,
        overall_confidence=overall_confidence,
    )

    hop = AgentHop(
        agent_name="brief_assembly",
        hop_type=AgentHopType.ASSEMBLY,
        model=settings.LLM_POWERFUL,
        confidence=brief.overall_confidence,
        success=True,
    )
    audit_event = AuditEvent(
        capability=CapabilityID.DECISION_INTELLIGENCE,
        run_id=str(state.get("run_id", "")),
        session_id=str(state.get("session_id", "")),
        event_type="brief.completed",
        agent_name="brief_assembly",
        action="assemble_brief",
        payload={
            "finding_count": len(brief.key_findings),
            "uncertainty_count": len(brief.uncertainty_flags),
            "overall_confidence": brief.overall_confidence,
        },
    )

    return {
        **state,
        "current_agent": "brief_assembly",
        "brief": brief,
        "executive_summary": brief.executive_summary,
        "key_findings": brief.key_findings,
        "uncertainty_flags": brief.uncertainty_flags,
        "recommended_actions": brief.recommended_actions,
        "overall_confidence": brief.overall_confidence,
        "agent_hops": [*state.get("agent_hops", []), hop],
        "audit_trail": [*state.get("audit_trail", []), audit_event],
    }


def _build_findings(
    state: dict[str, Any],
    retrieval_results: list[RetrievalResult],
    uncertainty_flags: list[str],
) -> list[Finding]:
    candidates = _finding_claims(state)
    findings: list[Finding] = []
    used_claims: set[str] = set()
    for claim in candidates:
        citation = _best_citation(claim, retrieval_results)
        if citation is None:
            continue
        confidence = _finding_confidence(claim, citation, state)
        finding = Finding(
            claim=claim,
            citations=[citation],
            confidence=confidence,
            uncertainty_note=_uncertainty_for_claim(claim, uncertainty_flags, confidence),
        )
        key = finding.claim.lower()
        if key not in used_claims:
            used_claims.add(key)
            findings.append(finding)
        if len(findings) == 5:
            break

    if not findings:
        fallback = _fallback_finding(retrieval_results, uncertainty_flags)
        if fallback is not None:
            findings.append(fallback)

    return findings


def _finding_claims(state: dict[str, Any]) -> list[str]:
    analysis_notes = str(state.get("analysis_notes", ""))
    themes = list(state.get("key_themes", []))
    claims: list[str] = []

    for line in analysis_notes.splitlines():
        label, _, value = line.partition(":")
        if label.lower().strip() == "key themes" and value.strip() and value.strip().lower() != "none from retrieved evidence":
            claims.append(f"Evidence highlights {value.strip()}.")
        elif label.lower().strip() == "contradictions" and value.strip().lower() not in {"", "none detected"}:
            claims.append(f"Retrieved sources show unresolved tension: {value.strip()}.")

    for theme in themes:
        cleaned = _clean_text(str(theme))
        if cleaned:
            claims.append(f"{cleaned.capitalize()} is a recurring theme in the evidence.")

    if state.get("query"):
        claims.append(f"The available evidence directly informs the question: {_clean_text(str(state['query']))}.")

    return claims


def _best_citation(claim: str, retrieval_results: list[RetrievalResult]) -> Citation | None:
    if not retrieval_results:
        return None
    claim_terms = _terms(claim)
    scored = []
    for result in retrieval_results:
        content_terms = _terms(result.chunk.content)
        overlap = len(claim_terms & content_terms)
        score = overlap + result.combined_score
        scored.append((score, result))
    if not scored:
        return None
    scored.sort(key=lambda item: item[0], reverse=True)
    best = scored[0][1]
    metadata = best.chunk.metadata or {}
    return Citation(
        source_doc_id=best.chunk.doc_id,
        source_title=str(metadata.get("title") or best.chunk.doc_id),
        source_date=metadata.get("date"),
        chunk_index=best.chunk.chunk_index,
        excerpt=_excerpt(best.chunk.content),
        confidence=round(min(max(best.combined_score, 0.0), 1.0), 3),
        access_tier=best.chunk.access_tier,
    )


def _fallback_finding(
    retrieval_results: list[RetrievalResult],
    uncertainty_flags: list[str],
) -> Finding | None:
    if not retrieval_results:
        return None
    citation = _best_citation(retrieval_results[0].chunk.content, retrieval_results)
    if citation is None:
        return None
    confidence = round(min(max(retrieval_results[0].combined_score, 0.0), 1.0), 3)
    return Finding(
        claim=_clean_sentence(retrieval_results[0].chunk.content),
        citations=[citation],
        confidence=confidence,
        uncertainty_note=_uncertainty_for_claim(retrieval_results[0].chunk.content, uncertainty_flags, confidence),
    )


def _finding_confidence(claim: str, citation: Citation, state: dict[str, Any]) -> float:
    evidence_strength = float(state.get("evidence_strength", citation.confidence))
    citation_accuracy = float(state.get("citation_accuracy", 1.0))
    claim_support = citation.confidence
    return round((claim_support * 0.5) + (evidence_strength * 0.3) + (citation_accuracy * 0.2), 3)


def _overall_confidence(findings: list[Finding]) -> float:
    if not findings:
        return 0.0
    weights = [max(len(finding.citations), 1) for finding in findings]
    total_weight = sum(weights)
    return round(
        sum(finding.confidence * weight for finding, weight in zip(findings, weights, strict=True)) / total_weight,
        3,
    )


def _normalise_uncertainty(state: dict[str, Any]) -> list[str]:
    flags = [str(flag).strip() for flag in state.get("uncertainty_flags", []) if str(flag).strip()]
    verification_flags = state.get("verification_flags", [])
    for flag in verification_flags:
        claim = getattr(flag, "claim", None) or (flag.get("claim") if isinstance(flag, dict) else None)
        if claim:
            flags.append(f"Unverified claim: {claim}")
    return _dedupe(flags)


def _executive_summary(query: str, findings: list[Finding], uncertainty_flags: list[str]) -> str:
    subject = _clean_text(query) or "the decision question"
    if not findings:
        return (
            f"The current evidence base is insufficient to answer {subject} with confidence. "
            "The brief should be treated as a request for additional source material before decision-making."
        )
    lead = findings[0].claim.rstrip(".")
    lead_text = (lead[0].lower() + lead[1:]) if lead else subject
    summary = f"The evidence indicates that {lead_text}."
    confidence = _overall_confidence(findings)
    if uncertainty_flags:
        return f"{summary} Overall confidence is {confidence:.2f}, with explicit uncertainties requiring review."
    return f"{summary} Overall confidence is {confidence:.2f}, supported by cited internal evidence."


def _recommended_actions(findings: list[Finding], uncertainty_flags: list[str]) -> list[str]:
    actions = [
        "Review the cited source excerpts before using the brief in a decision forum.",
        "Assign an owner to validate the highest-impact finding with the relevant business function.",
        "Use the uncertainty flags as the agenda for follow-up evidence gathering.",
    ]
    if findings:
        actions.insert(1, f"Prioritise action on: {findings[0].claim.rstrip('.')}.")
    if not uncertainty_flags:
        actions.append("Proceed to human review with the cited findings and confidence scores.")
    return actions[:5]


def _uncertainty_for_claim(claim: str, uncertainty_flags: list[str], confidence: float) -> str | None:
    claim_terms = _terms(claim)
    for flag in uncertainty_flags:
        if claim_terms & _terms(flag):
            return flag
    if confidence < 0.7:
        return "Confidence below review threshold; validate before action."
    return None


def _brief_output_schema():
    global _BriefOutput
    if _BriefOutput is not None:
        return _BriefOutput

    existing = sys.modules.get("cap01_brief_schema")
    if existing is not None and hasattr(existing, "BriefOutput"):
        _BriefOutput = existing.BriefOutput
        return _BriefOutput

    schema_path = Path(__file__).parents[1] / "schemas" / "brief.py"
    spec = importlib.util.spec_from_file_location("cap01_brief_schema", schema_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load brief schema from {schema_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    _BriefOutput = module.BriefOutput
    return _BriefOutput


def _terms(text: str) -> set[str]:
    stopwords = {"and", "are", "for", "from", "the", "this", "that", "with"}
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 2 and token not in stopwords}


def _excerpt(content: str, max_chars: int = 260) -> str:
    cleaned = _clean_text(content)
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3].rstrip() + "..."


def _clean_sentence(content: str) -> str:
    cleaned = _clean_text(content).rstrip(".")
    return cleaned + "." if cleaned else "Retrieved evidence is available."


def _clean_text(content: str) -> str:
    return re.sub(r"\s+", " ", content).strip()


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        key = value.lower()
        if key not in seen:
            seen.add(key)
            output.append(value)
    return output
