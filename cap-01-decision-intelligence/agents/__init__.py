"""Cap-01 agent entrypoints."""

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


analysis_agent_node = _load_attr("cap01_analysis_agent", "analysis_agent.py", "analysis_agent_node")
brief_agent_node = _load_attr("cap01_brief_agent", "brief_agent.py", "brief_agent_node")
build_graph = _load_attr("cap01_graph", "graph.py", "build_graph")
build_postgres_checkpointer = _load_attr("cap01_graph", "graph.py", "build_postgres_checkpointer")
build_retrieval_agent = _load_attr("cap01_retrieval_agent", "retrieval_agent.py", "build_retrieval_agent")
initial_state = _load_attr("cap01_graph", "graph.py", "initial_state")
supervisor_node = _load_attr("cap01_supervisor", "supervisor.py", "supervisor_node")
verification_agent_node = _load_attr("cap01_verification_agent", "verification_agent.py", "verification_agent_node")

__all__ = [
    "analysis_agent_node",
    "brief_agent_node",
    "build_graph",
    "build_postgres_checkpointer",
    "build_retrieval_agent",
    "initial_state",
    "supervisor_node",
    "verification_agent_node",
]
