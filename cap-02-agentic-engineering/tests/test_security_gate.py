from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("cap02_security_test", ROOT / "tools" / "security_gate.py")
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def test_security_gate_catches_vulnerable_samples() -> None:
    samples = sorted((ROOT / "tests" / "fixtures" / "vulnerable_samples").glob("*.py"))

    result = module.scan_files(samples)

    assert len(samples) >= 5
    assert result.critical >= 5
    assert result.blocked is True


def test_security_gate_node_blocks_critical_findings(tmp_path) -> None:
    output = {"unsafe.py": "password = 'secret'\nvalue = eval('1+1')\n"}

    state = module.security_gate_node({"output_files": output, "security_scan_root": tmp_path})

    assert state["status"] == "BLOCKED"
    assert state["security_scan"].critical >= 1
