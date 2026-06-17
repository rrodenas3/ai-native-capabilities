"""
GovernedKnowledgeGraph: KnowledgeGraph with SSGM governance on Obligation writes.

Every obligation node passes through SSGMGovernor before consolidation:
  1. Poisoning scan (A-MemGuard) — quarantine_threshold=0.3 (strict for compliance)
  2. Consistency verification — blocks exact duplicates and semantic conflicts
  3. Temporal decay — weights new entries at creation time

Quarantined obligations are held for human review; they do not enter the graph.
This directly protects the false_negative_rate_obligations gate: a poisoned or
contradictory obligation that slips through would cause the agent to assert a
non-existent requirement as law.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

import importlib.util as _ilu

REPO_ROOT = Path(__file__).resolve().parents[2]   # ai-native-capabilities/
CAP05_ROOT = Path(__file__).resolve().parents[1]  # cap-05-compliance-intelligence/
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.harness.memory import (  # noqa: E402
    GovernedMemoryEntry,
    MemoryWriteType,
    SSGMGovernor,
)


def _load_kg() -> type:
    """Load KnowledgeGraph directly from file to avoid sys.path issues with hyphenated dir."""
    _path = CAP05_ROOT / "tools" / "knowledge_graph.py"
    _spec = _ilu.spec_from_file_location("cap05_kg_base", _path)
    _mod = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    return _mod.KnowledgeGraph


KnowledgeGraph = _load_kg()

logger = logging.getLogger(__name__)


class GovernedKnowledgeGraph(KnowledgeGraph):
    """
    Wraps KnowledgeGraph and routes every Obligation write through SSGMGovernor.
    All other node types (Regulation, Article, UseCase, GapReport) bypass
    governance — only the obligation layer carries legal weight.
    """

    def __init__(
        self,
        capability: str = "cap-05",
        quarantine_threshold: float = 0.3,
        mock: bool = False,
    ) -> None:
        super().__init__()
        self._governor = SSGMGovernor(
            capability=capability,
            decay_half_life_days=14.0,  # regulatory text decays faster than ops data
            quarantine_threshold=quarantine_threshold,
        )
        self._governed_entries: list[GovernedMemoryEntry] = []
        self.quarantined: list[dict[str, Any]] = []
        self._mock = mock

    def add_node(self, label: str, node_id: str, properties: dict[str, Any]) -> dict[str, Any]:
        if label != "Obligation":
            return super().add_node(label, node_id, properties)

        content = properties.get("anchor_text") or str(properties)
        source = properties.get("source_url", "unknown")

        entry = GovernedMemoryEntry.create(
            entry_id=node_id,
            capability=self._governor.capability,
            content=content,
            write_type=MemoryWriteType.EXTERNAL,
            source=source,
        )
        validated = self._governor.validate_write(entry, self._governed_entries, mock=self._mock)

        if validated.validation_blocked:
            record = {"node_id": node_id, "reason": validated.block_reason, "properties": properties}
            self.quarantined.append(record)
            logger.warning(
                "[cap-05] Obligation %s QUARANTINED — %s", node_id, validated.block_reason
            )
            return {"id": node_id, "label": label, "quarantined": True, **dict(properties)}

        self._governed_entries.append(validated)
        return super().add_node(label, node_id, properties)

    @property
    def quarantine_count(self) -> int:
        return len(self.quarantined)
