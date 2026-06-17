"""Local loader for Cap-04 modules in a hyphenated directory."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent


def load_attr(module_name: str, relative_path: str, attr: str) -> Any:
    existing = sys.modules.get(module_name)
    if existing is not None and hasattr(existing, attr):
        return getattr(existing, attr)
    if existing is not None:
        raise AttributeError(f"Module {module_name} does not expose {attr}")
    module_path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {attr} from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    if not hasattr(module, attr):
        raise AttributeError(f"Module {module_name} does not expose {attr}")
    return getattr(module, attr)
