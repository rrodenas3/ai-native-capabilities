from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from core.schemas import EvalReport

MODULE_PATH = Path(__file__).parents[1] / "evals" / "suite.py"
SPEC = importlib.util.spec_from_file_location("cap01_eval_suite", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load Cap-01 eval suite from {MODULE_PATH}")
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)

run_eval = module.run_eval
FIXTURE_PATH = module.FIXTURE_PATH


def test_cap01_eval_suite_runs_all_8_metrics(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")

    report = run_eval(FIXTURE_PATH)

    assert isinstance(report, EvalReport)
    assert report.cap == "cap-01"
    assert set(report.metrics) == {
        "citation_accuracy",
        "hallucination_rate",
        "retrieval_recall",
        "source_coverage",
        "response_latency_p95_s",
        "human_override_rate",
        "brief_usefulness",
        "cost_per_brief_usd",
    }
    assert report.metrics["citation_accuracy"] >= 0.95
    assert report.metrics["hallucination_rate"] == 0.0
    assert report.status == "pass"


def test_cap01_eval_fixture_has_minimum_20_cases() -> None:
    cases = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    assert len(cases) >= 20
    assert all(case["brief"]["key_findings"][0]["citations"] for case in cases)


def test_cap01_eval_cli_writes_valid_report_and_gate_check_passes(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    output = tmp_path / "cap01.json"

    subprocess.run(
        [
            sys.executable,
            str(MODULE_PATH),
            "--output",
            str(output),
        ],
        check=True,
        cwd=Path(__file__).parents[2],
    )

    report = EvalReport.model_validate_json(output.read_text(encoding="utf-8"))
    assert report.cap == "cap-01"
    gate = subprocess.run(
        [
            sys.executable,
            "scripts/check_eval_gates.py",
            str(output),
            "--capability",
            "cap-01",
        ],
        cwd=Path(__file__).parents[2],
        text=True,
        capture_output=True,
    )

    assert gate.returncode == 0, gate.stdout + gate.stderr
