"""Tests for scripts/walkthrough_eu_ai_act.py."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
WALKTHROUGH = REPO_ROOT / "scripts" / "walkthrough_eu_ai_act.py"

sys.path.insert(0, str(REPO_ROOT))


def _run_walkthrough(*args: str, env_override: dict | None = None) -> subprocess.CompletedProcess:
    env = {**os.environ, "LLM_MODE": "mock", "PYTHONPATH": str(REPO_ROOT)}
    if env_override:
        env.update(env_override)
    return subprocess.run(
        [sys.executable, str(WALKTHROUGH), *args],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )


def test_walkthrough_exits_zero_in_mock_mode(tmp_path):
    out = tmp_path / "walkthrough.md"
    result = _run_walkthrough("--output", str(out))
    assert result.returncode == 0, result.stderr


def test_walkthrough_creates_markdown_file(tmp_path):
    out = tmp_path / "walkthrough.md"
    _run_walkthrough("--output", str(out))
    assert out.exists(), "Markdown output file was not created"
    content = out.read_text(encoding="utf-8")
    assert len(content) > 100


def test_walkthrough_markdown_contains_required_headings(tmp_path):
    out = tmp_path / "walkthrough.md"
    _run_walkthrough("--output", str(out))
    content = out.read_text(encoding="utf-8")
    assert "EU AI Act" in content
    assert "Obligation" in content
    assert "Audit Trail" in content


def test_walkthrough_creates_json_sidecar(tmp_path):
    out = tmp_path / "walkthrough.md"
    _run_walkthrough("--output", str(out))
    json_path = tmp_path / "eu_ai_act_demo.json"
    assert json_path.exists(), "JSON sidecar was not created"
    report = json.loads(json_path.read_text())
    assert report["cap"] == "cap-05"
    assert "metrics" in report


def test_walkthrough_is_idempotent(tmp_path):
    out = tmp_path / "walkthrough.md"
    _run_walkthrough("--output", str(out))
    first_size = out.stat().st_size
    _run_walkthrough("--output", str(out))
    second_size = out.stat().st_size
    # Timestamps differ but content size should be the same
    assert abs(first_size - second_size) < 50


def test_walkthrough_default_output_path_under_reports(tmp_path):
    """Default output lands in reports/artifacts/ which is auto-created."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("walkthrough_mod", WALKTHROUGH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert "reports" in str(mod.DEFAULT_OUTPUT)
    assert "artifacts" in str(mod.DEFAULT_OUTPUT)


# ── render_markdown unit tests ────────────────────────────────────────────────

def test_render_markdown_with_answers():
    import importlib.util
    spec = importlib.util.spec_from_file_location("walkthrough_mod2", WALKTHROUGH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    report = {
        "cap": "cap-05",
        "status": "pass",
        "score": 0.95,
        "metrics": {"query_answer_citation_rate": 0.95, "audit_events": 5},
        "answers": [
            {"text": "Annex III systems must register in EU DB", "citations": ["Art. 49"], "confidence": 0.9},
            {"text": "High-risk AI requires conformity assessment", "citations": ["Art. 43"], "confidence": 0.85},
        ],
    }
    md = mod.render_markdown(report, "mock")
    assert "EU AI Act" in md
    assert "Obligation Analysis" in md
    assert "Audit Trail" in md
    assert "2" in md  # 2 findings


def test_render_markdown_no_answers_shows_placeholder():
    import importlib.util
    spec = importlib.util.spec_from_file_location("walkthrough_mod3", WALKTHROUGH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    report = {
        "cap": "cap-05",
        "score": 0.0,
        "metrics": {"query_answer_citation_rate": 0.0, "audit_events": 0},
        "answers": [],
    }
    md = mod.render_markdown(report, "mock")
    assert "No obligations extracted" in md or "LLM_MODE=real" in md
