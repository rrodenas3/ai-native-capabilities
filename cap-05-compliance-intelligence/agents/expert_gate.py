"""Mandatory expert review gate for extracted obligations."""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cap05_loader import load_attr  # noqa: E402

AuditTrail = load_attr("cap05_audit", "tools/audit_trail.py", "AuditTrail")


class ExpertReviewGate:
    def __init__(self, audit_trail: Any | None = None) -> None:
        self.audit_trail = audit_trail or AuditTrail()
        self.pending: dict[str, dict[str, Any]] = {}
        self.history: list[dict[str, Any]] = []

    def queue_for_review(self, obligation: dict[str, Any]) -> dict[str, Any]:
        if not obligation.get("anchor_text"):
            raise ValueError("expert review requires source anchor_text")
        queued = {**obligation, "status": "PENDING", "expert_confirmed": False}
        self.pending[str(queued["id"])] = queued
        self.audit_trail.log_event("expert_review_queued", {"obligation_id": queued["id"], "article_reference": queued["article_reference"]})
        return queued

    def get_pending(self) -> list[dict[str, Any]]:
        return list(self.pending.values())

    def submit_review(
        self,
        obligation_id: str,
        decision: str,
        reviewer_id: str,
        review_method: str = "read_full_text",
        ai_assistance_used: bool = False,
        human_confidence: float = 1.0,
        modifications: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if obligation_id not in self.pending:
            raise KeyError(obligation_id)
        if decision not in {"CONFIRM", "MODIFY", "REJECT", "ESCALATE"}:
            raise ValueError("decision must be CONFIRM, MODIFY, REJECT, or ESCALATE")
        original = self.pending.pop(obligation_id)
        reviewed = {**original, **(modifications or {})}
        now = datetime.now(UTC).isoformat()
        reviewed.update(
            {
                "review_decision": decision,
                "reviewed_by": reviewer_id,
                "review_method": review_method,
                "ai_assistance_used": ai_assistance_used,
                "human_confidence": human_confidence,
                "reviewed_at": now,
                "status": "CONFIRMED" if decision in {"CONFIRM", "MODIFY"} else decision,
                "expert_confirmed": decision in {"CONFIRM", "MODIFY"},
                "confirmed_by": reviewer_id if decision in {"CONFIRM", "MODIFY"} else None,
                "confirmed_at": now if decision in {"CONFIRM", "MODIFY"} else None,
            }
        )
        self.history.append(reviewed)
        self.audit_trail.log_event(
            "expert_review_decision",
            {
                "obligation_id": obligation_id,
                "decision": decision,
                "reviewed_by": reviewer_id,
                "review_method": review_method,
                "ai_assistance_used": ai_assistance_used,
                "human_confidence": human_confidence,
            },
        )
        return reviewed


def require_confirmed(obligation: dict[str, Any]) -> dict[str, Any]:
    if obligation.get("expert_confirmed") is not True:
        raise PermissionError("Obligation cannot enter confirmed register without expert sign-off")
    return obligation
