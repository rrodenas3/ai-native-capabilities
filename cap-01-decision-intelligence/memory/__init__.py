"""Cap-01 memory helpers."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any


def _load_attr(module_name: str, file_name: str, attr: str) -> Any:
    existing = sys.modules.get(module_name)
    if existing is not None and hasattr(existing, attr):
        return getattr(existing, attr)

    module_path = Path(__file__).parent / file_name
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {attr} from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return getattr(module, attr)


DecisionBriefEpisodicMemory = _load_attr("cap01_episodic_memory", "episodic.py", "DecisionBriefEpisodicMemory")
StoredBrief = _load_attr("cap01_episodic_memory", "episodic.py", "StoredBrief")

__all__ = ["DecisionBriefEpisodicMemory", "StoredBrief"]
