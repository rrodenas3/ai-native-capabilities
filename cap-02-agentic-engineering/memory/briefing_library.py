"""In-memory BriefingScript library with deterministic similarity search."""

from __future__ import annotations

import importlib.util
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class BriefingSearchResult:
    briefing: Any
    outcome: str
    notes: str
    similarity: float


class BriefingLibrary:
    def __init__(self) -> None:
        self._records: list[tuple[Any, str, str, dict[str, float]]] = []

    def store_briefing(self, briefing: Any, outcome: str, notes: str = "") -> str:
        vector = _embed(str(briefing.goal_and_why.goal))
        self._records.append((briefing, outcome, notes, vector))
        return str(briefing.briefing_id)

    def search_similar(self, query: str, k: int = 3) -> list[BriefingSearchResult]:
        query_vector = _embed(query)
        scored = [
            BriefingSearchResult(briefing=briefing, outcome=outcome, notes=notes, similarity=_cosine(query_vector, vector))
            for briefing, outcome, notes, vector in self._records
        ]
        scored.sort(key=lambda result: result.similarity, reverse=True)
        return scored[:k]

    @property
    def briefing_reuse_rate(self) -> float:
        if not self._records:
            return 0.0
        reusable = sum(1 for _briefing, outcome, _notes, _vector in self._records if outcome in {"DONE", "ARCHIVED"})
        return reusable / len(self._records)


def _embed(text: str) -> dict[str, float]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    vector: dict[str, float] = {}
    for token in tokens:
        if len(token) > 2:
            vector[token] = vector.get(token, 0.0) + 1.0
    return vector


def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(value * right.get(key, 0.0) for key, value in left.items())
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    return round(dot / (left_norm * right_norm), 6) if left_norm and right_norm else 0.0


def minimal_valid_briefing(**overrides: Any) -> Any:
    schema_path = Path(__file__).parents[1] / "schemas" / "briefing_script.py"
    spec = importlib.util.spec_from_file_location("cap02_briefing_schema", schema_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load schema from {schema_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.minimal_valid_briefing(**overrides)
