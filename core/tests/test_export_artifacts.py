"""Tests for scripts/export_artifacts.py."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
EXPORT_SCRIPT = REPO_ROOT / "scripts" / "export_artifacts.py"


def _run_export(*args: str, env_override: dict | None = None) -> subprocess.CompletedProcess:
    env = {**os.environ, "LLM_MODE": "mock", "PYTHONPATH": str(REPO_ROOT)}
    if env_override:
        env.update(env_override)
    return subprocess.run(
        [sys.executable, str(EXPORT_SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )


def test_default_run_exits_zero(tmp_path):
    result = _run_export("--output-dir", str(tmp_path))
    assert result.returncode == 0, result.stderr


def test_all_six_files_created(tmp_path):
    _run_export("--output-dir", str(tmp_path))
    stems = ["scorecard", "compliance_report", "mrp_report"]
    exts = [".md", ".html"]
    for stem in stems:
        for ext in exts:
            path = tmp_path / f"{stem}{ext}"
            assert path.exists(), f"{stem}{ext} was not created"


def test_md_only_format(tmp_path):
    result = _run_export("--output-dir", str(tmp_path), "--formats", "md")
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "scorecard.md").exists()
    assert not (tmp_path / "scorecard.html").exists()


def test_html_only_format(tmp_path):
    result = _run_export("--output-dir", str(tmp_path), "--formats", "html")
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "scorecard.html").exists()
    assert not (tmp_path / "scorecard.md").exists()


def test_scorecard_md_has_required_headings(tmp_path):
    _run_export("--output-dir", str(tmp_path))
    content = (tmp_path / "scorecard.md").read_text(encoding="utf-8")
    assert "AI Capability Eval Scorecard" in content
    assert "cap-01" in content
    assert "cap-05" in content


def test_compliance_md_has_eu_ai_act_content(tmp_path):
    _run_export("--output-dir", str(tmp_path))
    content = (tmp_path / "compliance_report.md").read_text(encoding="utf-8")
    assert "EU AI Act" in content
    assert "Obligation" in content
    assert "Audit Trail" in content
    assert "August" in content  # enforcement date


def test_mrp_md_has_decision(tmp_path):
    _run_export("--output-dir", str(tmp_path))
    content = (tmp_path / "mrp_report.md").read_text(encoding="utf-8")
    assert "Merge Readiness Pack" in content
    assert "Decision" in content


def test_scorecard_html_is_valid_html(tmp_path):
    _run_export("--output-dir", str(tmp_path))
    content = (tmp_path / "scorecard.html").read_text(encoding="utf-8")
    assert "<!doctype html>" in content.lower()
    assert "<table" in content
    assert "cap-01" in content


def test_compliance_html_contains_enforcement_date(tmp_path):
    _run_export("--output-dir", str(tmp_path))
    content = (tmp_path / "compliance_report.html").read_text(encoding="utf-8")
    assert "August" in content
    assert "Obligation" in content


def test_json_sidecars_created(tmp_path):
    _run_export("--output-dir", str(tmp_path))
    eu_json = tmp_path / "eu_ai_act_demo.json"
    cap02_json = tmp_path / "cap02_mrp.json"
    assert eu_json.exists(), "EU AI Act JSON sidecar not created"
    assert cap02_json.exists(), "Cap-02 MRP JSON sidecar not created"
    eu_data = json.loads(eu_json.read_text())
    assert eu_data["cap"] == "cap-05"
    cap02_data = json.loads(cap02_json.read_text())
    assert cap02_data["cap"] == "cap-02"


def test_idempotent_run(tmp_path):
    _run_export("--output-dir", str(tmp_path))
    sizes_1 = {p.name: p.stat().st_size for p in tmp_path.iterdir()}
    _run_export("--output-dir", str(tmp_path))
    sizes_2 = {p.name: p.stat().st_size for p in tmp_path.iterdir()}
    for name in sizes_1:
        assert abs(sizes_1[name] - sizes_2.get(name, 0)) < 100, f"{name} changed size significantly"


# ── render_* unit tests ───────────────────────────────────────────────────────

def _load_export_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location("export_artifacts_mod", EXPORT_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_render_scorecard_md_all_caps():
    mod = _load_export_module()
    reports = {cap: {"status": "pass", "score": 0.95, "blocking_failures": []} for cap in mod.CAP_NAMES}
    md = mod.render_scorecard_md(reports, "2026-06-17 00:00 UTC", "mock")
    for cap in mod.CAP_NAMES:
        assert cap in md


def test_render_compliance_md_no_answers_shows_placeholder():
    mod = _load_export_module()
    data = {"cap": "cap-05", "score": 0.0, "metrics": {}, "answers": [], "query": "test"}
    md = mod.render_compliance_md(data, "2026-06-17 00:00 UTC", "mock")
    assert "No obligations extracted" in md or "LLM_MODE=real" in md


def test_render_compliance_md_with_answers():
    mod = _load_export_module()
    data = {
        "cap": "cap-05",
        "score": 0.95,
        "metrics": {"query_answer_citation_rate": 0.95, "audit_events": 3},
        "query": "Annex III obligations",
        "answers": [
            {"text": "High-risk AI must register", "citations": ["Art. 49"], "confidence": 0.9},
        ],
    }
    md = mod.render_compliance_md(data, "2026-06-17 00:00 UTC", "mock")
    assert "High-risk AI must register" in md
    assert "Art. 49" in md
