"""Tests for cap-05 demo.py CLI flags (--query, --output)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CAP05_ROOT = REPO_ROOT / "cap-05-compliance-intelligence"


def _run_demo_cli(*args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "LLM_MODE": "mock", "PYTHONPATH": str(REPO_ROOT)}
    return subprocess.run(
        [sys.executable, str(CAP05_ROOT / "demo.py"), *args],
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )


def test_default_run_prints_json():
    result = _run_demo_cli()
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert "query" in data
    assert "answers" in data
    assert "audit_events" in data


def test_query_flag_overrides_default():
    custom = "What are Article 9 obligations?"
    result = _run_demo_cli("--query", custom)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["query"] == custom


def test_output_flag_writes_report_envelope(tmp_path):
    out = tmp_path / "demo_out.json"
    result = _run_demo_cli("--output", str(out))
    assert result.returncode == 0, result.stderr
    assert out.exists(), "output file was not created"
    report = json.loads(out.read_text())
    assert report["cap"] == "cap-05"
    assert "score" in report
    assert "metrics" in report
    assert report["blocking_failures"] == []


def test_output_and_stdout_both_produced(tmp_path):
    out = tmp_path / "both.json"
    result = _run_demo_cli("--output", str(out))
    assert result.returncode == 0, result.stderr
    # stdout: raw demo result
    stdout_data = json.loads(result.stdout)
    assert "answers" in stdout_data
    # file: canonical report envelope
    file_data = json.loads(out.read_text())
    assert file_data["cap"] == "cap-05"


def test_query_appears_in_output_file(tmp_path):
    custom = "SSGM governance obligations"
    out = tmp_path / "query_test.json"
    result = _run_demo_cli("--query", custom, "--output", str(out))
    assert result.returncode == 0, result.stderr
    report = json.loads(out.read_text())
    assert report["query"] == custom



def test_metrics_key_present_in_envelope(tmp_path):
    out = tmp_path / "metrics.json"
    _run_demo_cli("--output", str(out))
    report = json.loads(out.read_text())
    assert "query_answer_citation_rate" in report["metrics"]
    assert "audit_events" in report["metrics"]
