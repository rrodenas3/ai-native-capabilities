from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
REPO = ROOT.parents[0]


def load(relative: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


eval_suite = load("evals/suite.py", "cap02_eval_suite_test")
proficiency = load("tools/proficiency.py", "cap02_proficiency_test")
demo = load("demo.py", "cap02_demo_test")
schema = load("schemas/briefing_script.py", "cap02_schema_eval_cli_test")


def test_cap02_eval_suite_reports_all_8_metrics() -> None:
    report = eval_suite.run_eval()
    assert report["status"] == "pass"
    assert set(report["metrics"]) == {
        "briefing_completeness",
        "security_weakness_rate",
        "acceptance_criteria_pass",
        "test_coverage",
        "crp_resolution_rate",
        "merge_readiness_accuracy",
        "briefing_reuse_rate",
        "cost_per_task_usd",
    }
    assert report["metrics"]["briefing_completeness"] == 1.0
    assert report["metrics"]["security_weakness_rate"] <= 5.0


def test_proficiency_assigns_levels_and_templates() -> None:
    l0 = proficiency.assess([False] * 10)
    l2 = proficiency.assess([True, True, True, True, True, True, False, False, False, False])
    l3 = proficiency.assess([True] * 10)
    assert l0["level"] == "L0"
    assert l2["level"] == "L2"
    assert l3["level"] == "L3"
    assert "briefing_id" in str(l3["template"])


def test_demo_returns_ready_mrp() -> None:
    pack = demo.run_demo()
    assert pack["ready"] is True
    assert pack["security_scan"]["critical"] == 0
    assert pack["criteria_scores"][0]["status"] == "PASS"


def test_ace_run_and_review_commands(tmp_path) -> None:
    brief_path = tmp_path / "briefing.json"
    mrp_path = tmp_path / "mrp.json"
    brief_path.write_text(schema.minimal_valid_briefing().model_dump_json(indent=2), encoding="utf-8")
    mrp_path.write_text(json.dumps(demo.run_demo()), encoding="utf-8")

    run_completed = subprocess.run(
        [sys.executable, str(ROOT / "cli" / "ace.py"), "run", str(brief_path)],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )
    assert run_completed.returncode == 0, run_completed.stderr
    assert "Merge-Readiness Pack" in run_completed.stdout

    review_completed = subprocess.run(
        [sys.executable, str(ROOT / "cli" / "ace.py"), "review", str(mrp_path), "--decision", "approve"],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )
    assert review_completed.returncode == 0, review_completed.stderr
    assert "Decision: APPROVE" in review_completed.stdout


def test_proficiency_cli_non_interactive() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "proficiency.py"),
            "--answers",
            "y,y,y,y,y,y,n,n,n,n",
        ],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0
    assert "Level: L2" in completed.stdout
