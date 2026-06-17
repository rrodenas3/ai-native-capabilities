from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("cap02_loop_test", ROOT / "agents" / "loop_runtime.py")
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def test_repeated_error_raises_crp_after_three_attempts() -> None:
    runtime = module.LoopRuntime(max_iterations=10)

    assert runtime.record_step("AC-01", "try one", matched=False, error="same failure") is None
    assert runtime.record_step("AC-01", "try two", matched=False, error="same failure") is None
    crp = runtime.record_step("AC-01", "try three", matched=False, error="same failure")

    assert crp is not None
    assert crp.proposed_solution
    assert crp.what_failed == ["same failure", "same failure", "same failure"]


def test_iteration_budget_raises_crp() -> None:
    runtime = module.LoopRuntime(max_iterations=1)

    crp = runtime.record_step("AC-01", "first iteration", matched=False)

    assert crp is not None
    assert "budget" in crp.what_failed[0].lower()
