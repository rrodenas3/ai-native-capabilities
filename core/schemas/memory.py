"""Memory-ingestion schemas."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from core.schemas.base import CapabilityID, DocumentChunk


class ChunkMetadata(BaseModel):
    """Metadata stored with each document chunk."""

    model_config = ConfigDict(frozen=True)

    title: str
    source: str
    doc_type: str
    date: str | None = None
    author: str | None = None
    access_tier: Literal["public", "internal", "restricted"] = "internal"
    extra: dict[str, Any] = Field(default_factory=dict)


class DocumentIngest(BaseModel):
    """Input document before chunking and embedding."""

    model_config = ConfigDict(frozen=True)

    doc_id: str
    capability: CapabilityID
    content: str
    metadata: ChunkMetadata


class IngestedDocument(BaseModel):
    """Document ingestion result."""

    model_config = ConfigDict(frozen=True)

    ingest_id: UUID = Field(default_factory=uuid4)
    doc_id: str
    capability: CapabilityID
    chunks: list[DocumentChunk]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

