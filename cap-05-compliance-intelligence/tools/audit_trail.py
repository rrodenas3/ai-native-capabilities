"""Append-only audit trail for compliance events."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    event_type: str
    payload: dict[str, Any]
    timestamp: str
    previous_hash: str
    event_hash: str


class AuditTrail:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self._events: list[AuditEvent] = []
        if path is not None and path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                data = json.loads(line)
                self._events.append(AuditEvent(**data))

    @property
    def events(self) -> tuple[AuditEvent, ...]:
        return tuple(self._events)

    def log_event(self, event_type: str, payload: dict[str, Any]) -> AuditEvent:
        timestamp = datetime.now(UTC).isoformat()
        previous_hash = self._events[-1].event_hash if self._events else "GENESIS"
        event_id = f"audit-{len(self._events) + 1:06d}"
        event_hash = _hash_event(event_id, event_type, payload, timestamp, previous_hash)
        event = AuditEvent(event_id, event_type, dict(payload), timestamp, previous_hash, event_hash)
        self._events.append(event)
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event.__dict__, sort_keys=True) + "\n")
        return event

    def query_trail(self, event_type: str | None = None) -> list[AuditEvent]:
        if event_type is None:
            return list(self._events)
        return [event for event in self._events if event.event_type == event_type]

    def export_audit_report(self) -> dict[str, Any]:
        return {
            "event_count": len(self._events),
            "integrity_valid": self.verify_integrity(),
            "events": [event.__dict__ for event in self._events],
        }

    def verify_integrity(self) -> bool:
        previous_hash = "GENESIS"
        for event in self._events:
            expected = _hash_event(
                event.event_id,
                event.event_type,
                event.payload,
                event.timestamp,
                previous_hash,
            )
            if event.previous_hash != previous_hash or event.event_hash != expected:
                return False
            previous_hash = event.event_hash
        return True

    def update_event(self, *_args: Any, **_kwargs: Any) -> None:
        raise PermissionError("AuditTrail is append-only; UPDATE is not permitted")

    def delete_event(self, *_args: Any, **_kwargs: Any) -> None:
        raise PermissionError("AuditTrail is append-only; DELETE is not permitted")


def _hash_event(
    event_id: str,
    event_type: str,
    payload: dict[str, Any],
    timestamp: str,
    previous_hash: str,
) -> str:
    canonical = json.dumps(
        {
            "event_id": event_id,
            "event_type": event_type,
            "payload": payload,
            "timestamp": timestamp,
            "previous_hash": previous_hash,
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
