"""Schema loader shim for direct script execution."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("cap03_schemas", ROOT / "schemas.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load Cap-03 schemas")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

IntentClass = MODULE.IntentClass
ResolutionType = MODULE.ResolutionType
ComplexityTier = MODULE.ComplexityTier
IntentResult = MODULE.IntentResult
Product = MODULE.Product
Recommendation = MODULE.Recommendation
SentimentResult = MODULE.SentimentResult
ResolutionResult = MODULE.ResolutionResult
EscalationResult = MODULE.EscalationResult
SessionRecord = MODULE.SessionRecord
