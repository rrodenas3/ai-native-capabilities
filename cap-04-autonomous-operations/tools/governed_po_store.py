"""
GovernedPOStore: SSGMGovernor validation for PO drafts before ERP/WMS commit.

Every PO draft passes through three validation stages before it is eligible
for ERP commit:
  1. Poisoning scan (A-MemGuard) — quarantine_threshold=0.5
     Moderate threshold: wrong POs are costly but recoverable via human override,
     unlike missed compliance obligations (cap-05 threshold: 0.3).
  2. Consistency verification — blocks exact duplicate po_id/sku/quantity combos
     and semantic conflicts in the running session.
  3. Temporal decay — weights entries at creation time (half-life: 90 days,
     matching supplier lead-time horizons).

Quarantined drafts are not silently dropped — they are returned in `quarantined`
so callers can surface them in audit_trail for human review.

Research basis: core/harness/memory.py (SSGMGovernor, arXiv 2603.11768, 2510.02373)
Pattern reference: cap-05-compliance-intelligence/tools/governed_kg.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]  # ai-native-capabilities/
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.harness.memory import (  # noqa: E402
    GovernedMemoryEntry,
    MemoryWriteType,
    SSGMGovernor,
)

logger = logging.getLogger(__name__)


def _po_content_fingerprint(po_draft: dict[str, Any]) -> str:
    """Canonical content string for consistency hashing and poisoning scan."""
    return (
        f"{po_draft.get('po_id', '')}:"
        f"{po_draft.get('sku', '')}:"
        f"{po_draft.get('supplier_id', '')}:"
        f"{po_draft.get('quantity', '')}:"
        f"{po_draft.get('value_usd', '')}"
    )


class GovernedPOStore:
    """
    Validates PO drafts through SSGMGovernor before ERP commit.

    Usage (inside erp_wms_node):
        store = GovernedPOStore()
        for po in state["po_drafts"]:
            store.add_draft(po)
        # Only approved drafts reach ERP
        for po in store.approved_drafts:
            erp.create_po(po, approved=approved)
        # Quarantined drafts go to audit_trail
        for record in store.quarantined:
            audit_trail.append({"event": "po_quarantined", **record})
    """

    def __init__(
        self,
        capability: str = "cap-04",
        quarantine_threshold: float = 0.5,
        mock: bool = False,
    ) -> None:
        self._governor = SSGMGovernor(
            capability=capability,
            decay_half_life_days=90.0,
            quarantine_threshold=quarantine_threshold,
        )
        self._governed_entries: list[GovernedMemoryEntry] = []
        self.approved_drafts: list[dict[str, Any]] = []
        self.quarantined: list[dict[str, Any]] = []
        self._mock = mock

    def add_draft(self, po_draft: dict[str, Any]) -> bool:
        """
        Validate a PO draft through SSGMGovernor.
        Returns True if approved, False if quarantined.
        """
        content = _po_content_fingerprint(po_draft)
        po_id = po_draft.get("po_id", "unknown")

        entry = GovernedMemoryEntry.create(
            entry_id=po_id,
            capability=self._governor.capability,
            content=content,
            write_type=MemoryWriteType.INFERRED,
            source=f"replenishment_node:{po_id}",
        )
        validated = self._governor.validate_write(entry, self._governed_entries, mock=self._mock)

        if validated.validation_blocked:
            record = {
                "po_id": po_id,
                "sku": po_draft.get("sku"),
                "reason": validated.block_reason,
                "properties": po_draft,
            }
            self.quarantined.append(record)
            logger.warning(
                "[cap-04] PO draft %s QUARANTINED — %s", po_id, validated.block_reason
            )
            return False

        self._governed_entries.append(validated)
        self.approved_drafts.append(po_draft)
        return True

    @property
    def quarantine_count(self) -> int:
        return len(self.quarantined)
