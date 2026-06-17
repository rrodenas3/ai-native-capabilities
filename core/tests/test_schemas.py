from __future__ import annotations

from pydantic import ValidationError

from core.schemas import (
    AuditEvent,
    AuditEventType,
    CapabilityAuditEvent,
    CapabilityID,
    ChunkMetadata,
    DocumentChunk,
    DocumentIngest,
    HumanApprovalAuditEvent,
    HumanGateStatus,
    IngestedDocument,
    MemoryEvent,
)


def test_audit_event_round_trips_through_json() -> None:
    event = AuditEvent(
        capability=CapabilityID.DECISION_INTELLIGENCE,
        run_id="run-1",
        session_id="session-1",
        event_type="brief.created",
        payload={"ok": True},
    )

    restored = AuditEvent.model_validate_json(event.model_dump_json())

    assert restored == event


def test_memory_event_embedding_is_json_float_list() -> None:
    event = MemoryEvent(
        capability=CapabilityID.DECISION_INTELLIGENCE,
        session_id="session-1",
        event_type="memory",
        content="content",
        embedding=[0.1, 0.2, 0.3],
    )
    restored = MemoryEvent.model_validate_json(event.model_dump_json())

    assert restored.embedding == [0.1, 0.2, 0.3]
    assert isinstance(restored.embedding[0], float)


def test_capability_audit_event_is_immutable_and_json_serializable() -> None:
    event = CapabilityAuditEvent(
        capability=CapabilityID.AGENTIC_ENGINEERING,
        run_id="run-1",
        session_id="session-1",
        event_type=AuditEventType.AGENT_HOP,
        payload={"agent": "execution"},
    )

    restored = CapabilityAuditEvent.model_validate_json(event.model_dump_json())

    assert restored == event
    try:
        event.run_id = "changed"
    except ValidationError:
        pass
    else:
        raise AssertionError("CapabilityAuditEvent should be frozen")


def test_human_approval_event_round_trip() -> None:
    event = HumanApprovalAuditEvent(
        capability=CapabilityID.AUTONOMOUS_OPERATIONS,
        run_id="run-1",
        session_id="session-1",
        decision=HumanGateStatus.APPROVED,
        approved_by="ops-lead",
    )

    restored = HumanApprovalAuditEvent.model_validate_json(event.model_dump_json())

    assert restored.decision == HumanGateStatus.APPROVED
    assert restored.event_type == AuditEventType.HUMAN_GATE


def test_memory_ingest_schemas_round_trip() -> None:
    metadata = ChunkMetadata(
        title="Strategy",
        source="fixture",
        doc_type="strategy",
        date="2026-06-01",
    )
    ingest = DocumentIngest(
        doc_id="doc-1",
        capability=CapabilityID.DECISION_INTELLIGENCE,
        content="content",
        metadata=metadata,
    )
    chunk = DocumentChunk(
        capability=CapabilityID.DECISION_INTELLIGENCE,
        doc_id="doc-1",
        chunk_index=0,
        content="content",
        embedding=[0.1, 0.2],
        metadata=metadata.model_dump(),
    )
    result = IngestedDocument(
        doc_id=ingest.doc_id,
        capability=ingest.capability,
        chunks=[chunk],
    )

    restored = IngestedDocument.model_validate_json(result.model_dump_json())

    assert restored.chunks[0].embedding == [0.1, 0.2]
    assert restored.chunks[0].metadata["title"] == "Strategy"

