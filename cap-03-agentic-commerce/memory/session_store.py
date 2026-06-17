"""Opt-in TTL-governed commerce session memory."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from cap03_schema_loader import SessionRecord


class SessionStore:
    def __init__(self, ttl_days: int = 30) -> None:
        self.ttl_days = ttl_days
        self._records: dict[str, SessionRecord] = {}

    def store_session(
        self,
        session_id: str,
        *,
        opt_in: bool,
        customer_id: str | None = None,
        preferences: dict | None = None,
        order_history: list[dict] | None = None,
        session_outcome: str | None = None,
    ) -> SessionRecord | None:
        if not opt_in:
            return None
        record = SessionRecord(
            session_id=session_id,
            customer_id=customer_id,
            preferences=preferences or {},
            order_history=order_history or [],
            session_outcome=session_outcome,
            opt_in=True,
            expires_at=datetime.now(UTC) + timedelta(days=self.ttl_days),
        )
        self._records[session_id] = record
        return record

    def retrieve_session(self, session_id: str) -> SessionRecord | None:
        record = self._records.get(session_id)
        if record is None:
            return None
        if record.expires_at <= datetime.now(UTC):
            self._records.pop(session_id, None)
            return None
        return record

    def update_preferences(self, session_id: str, preferences: dict) -> SessionRecord | None:
        record = self.retrieve_session(session_id)
        if record is None:
            return None
        updated = record.model_copy(update={"preferences": {**record.preferences, **preferences}})
        self._records[session_id] = updated
        return updated
