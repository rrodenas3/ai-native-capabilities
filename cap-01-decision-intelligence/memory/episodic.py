"""Cap-01 episodic memory wrapper for completed decision briefs."""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from core.memory import EpisodicMemory
from core.schemas import CapabilityID, MemoryEvent


class StoredBrief(BaseModel):
    """A completed decision brief restored from episodic memory."""

    model_config = ConfigDict(frozen=True)

    brief: Any
    session_id: str
    run_id: str | None
    query: str
    confidence: float
    cost_usd: float | None = None
    latency_ms: float | None = None
    created_at: datetime
    metadata: dict[str, Any]


class DecisionBriefEpisodicMemory:
    """Cap-01-specific persistence API over core episodic memory."""

    def __init__(self, memory: EpisodicMemory) -> None:
        self.memory = memory

    def store_brief(
        self,
        brief: Any,
        session_id: str,
        run_id: str,
        *,
        query: str = "",
        cost_usd: float | None = None,
        latency_ms: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Persist a completed brief, embedding its executive summary."""

        validated = _brief_output_schema().model_validate(brief)
        event = MemoryEvent(
            capability=CapabilityID.DECISION_INTELLIGENCE,
            session_id=session_id,
            run_id=run_id,
            event_type="decision_brief.completed",
            content=validated.executive_summary,
            metadata={
                "query": query,
                "confidence": validated.overall_confidence,
                "cost_usd": cost_usd,
                "latency_ms": latency_ms,
                "brief": validated.model_dump(mode="json"),
                **(metadata or {}),
            },
        )
        return self.memory.store(event)

    def retrieve_similar_briefs(self, query: str, k: int = 3) -> list[StoredBrief]:
        """Return past briefs most relevant to a query."""

        events = self.memory.retrieve_similar(query, k=k)
        return [_stored_brief(event) for event in events if event.event_type == "decision_brief.completed"]

    def get_session_history(self, session_id: str) -> list[StoredBrief]:
        """Return completed briefs for a session ordered by newest first."""

        events = self.memory.get_session_history(session_id)
        return [_stored_brief(event) for event in events if event.event_type == "decision_brief.completed"]


def _stored_brief(event: MemoryEvent) -> StoredBrief:
    metadata = event.metadata or {}
    brief_data = metadata.get("brief")
    if brief_data is None:
        raise ValueError("Stored decision brief event is missing brief metadata")
    brief = _brief_output_schema().model_validate(brief_data)
    return StoredBrief(
        brief=brief,
        session_id=event.session_id,
        run_id=event.run_id,
        query=str(metadata.get("query") or ""),
        confidence=float(metadata.get("confidence", brief.overall_confidence)),
        cost_usd=_optional_float(metadata.get("cost_usd")),
        latency_ms=_optional_float(metadata.get("latency_ms")),
        created_at=event.created_at,
        metadata=metadata,
    )


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _brief_output_schema():
    existing = sys.modules.get("cap01_brief_schema")
    if existing is not None and hasattr(existing, "BriefOutput"):
        return existing.BriefOutput

    schema_path = Path(__file__).parents[1] / "schemas" / "brief.py"
    spec = importlib.util.spec_from_file_location("cap01_brief_schema", schema_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load brief schema from {schema_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.BriefOutput
