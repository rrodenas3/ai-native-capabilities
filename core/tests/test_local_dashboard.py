"""Tests for the FastAPI eval dashboard.

Requires: pip install -e ".[dashboard]"
Uses FastAPI's TestClient (httpx-backed) — httpx is in core deps.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from scripts.dashboard.app import _load_report, _parse_json, app

client = TestClient(app)


# ── _parse_json ────────────────────────────────────────────────────────────────

def test_parse_json_empty_string() -> None:
    assert _parse_json("") is None


def test_parse_json_whitespace() -> None:
    assert _parse_json("   \n  ") is None


def test_parse_json_valid() -> None:
    assert _parse_json('{"a": 1}') == {"a": 1}


def test_parse_json_invalid() -> None:
    assert _parse_json("not json {{{") is None


# ── _load_report ───────────────────────────────────────────────────────────────

def test_load_report_missing_file(tmp_path: Path) -> None:
    with patch("scripts.dashboard.app.ROOT", tmp_path):
        result = _load_report("cap-01")
    assert result == {}


def test_load_report_valid_json(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "cap-01.json").write_text(
        json.dumps({"cap": "cap-01", "status": "pass", "score": 1.0}), encoding="utf-8"
    )
    with patch("scripts.dashboard.app.ROOT", tmp_path):
        result = _load_report("cap-01")
    assert result["status"] == "pass"
    assert result["score"] == 1.0


def test_load_report_corrupted_json(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "cap-01.json").write_text("not valid json", encoding="utf-8")
    with patch("scripts.dashboard.app.ROOT", tmp_path):
        result = _load_report("cap-01")
    assert result == {}


# ── GET /api/status ────────────────────────────────────────────────────────────

def test_status_200() -> None:
    resp = client.get("/api/status")
    assert resp.status_code == 200


def test_status_project_name() -> None:
    data = client.get("/api/status").json()
    assert data["project"] == "ai-native-capabilities"


def test_status_has_required_keys() -> None:
    data = client.get("/api/status").json()
    assert "python" in data
    assert "branch" in data
    assert "capabilities" in data


def test_status_all_caps_present() -> None:
    caps = client.get("/api/status").json()["capabilities"]
    for cap_id in ("cap-01", "cap-02", "cap-03", "cap-04", "cap-05"):
        assert cap_id in caps


# ── GET /api/reports ───────────────────────────────────────────────────────────

def test_all_reports_200() -> None:
    resp = client.get("/api/reports")
    assert resp.status_code == 200


def test_all_reports_has_all_caps() -> None:
    data = client.get("/api/reports").json()
    for cap_id in ("cap-01", "cap-02", "cap-03", "cap-04", "cap-05"):
        assert cap_id in data


def test_all_reports_missing_files_return_empty_dicts(tmp_path: Path) -> None:
    with patch("scripts.dashboard.app.ROOT", tmp_path):
        data = client.get("/api/reports").json()
    for cap_id in ("cap-01", "cap-02", "cap-03", "cap-04", "cap-05"):
        assert data[cap_id] == {}


# ── GET /api/reports/{cap} ─────────────────────────────────────────────────────

def test_single_report_unknown_cap_404() -> None:
    resp = client.get("/api/reports/cap-99")
    assert resp.status_code == 404


def test_single_report_missing_file_empty_dict(tmp_path: Path) -> None:
    with patch("scripts.dashboard.app.ROOT", tmp_path):
        resp = client.get("/api/reports/cap-01")
    assert resp.status_code == 200
    assert resp.json() == {}


def test_single_report_existing_file(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    reports.mkdir()
    payload = {"cap": "cap-01", "status": "pass", "score": 0.95, "metrics": {}, "blocking_failures": []}
    (reports / "cap-01.json").write_text(json.dumps(payload), encoding="utf-8")
    with patch("scripts.dashboard.app.ROOT", tmp_path):
        data = client.get("/api/reports/cap-01").json()
    assert data["score"] == 0.95


# ── POST /api/evals/{cap} ──────────────────────────────────────────────────────

def test_eval_unknown_cap_404() -> None:
    resp = client.post("/api/evals/cap-99")
    assert resp.status_code == 404


def test_eval_all_returns_list() -> None:
    fake_result: dict[str, Any] = {"kind": "eval", "cap": "cap-01", "status": "pass", "returncode": 0, "stdout": "", "stderr": ""}
    with patch("scripts.dashboard.app._run_subprocess", return_value=fake_result):
        data = client.post("/api/evals/all").json()
    assert isinstance(data, list)
    assert len(data) == 5


def test_eval_single_cap_returns_dict() -> None:
    fake_result: dict[str, Any] = {"kind": "eval", "cap": "cap-04", "status": "pass", "returncode": 0, "stdout": "", "stderr": ""}
    with patch("scripts.dashboard.app._run_subprocess", return_value=fake_result):
        data = client.post("/api/evals/cap-04").json()
    assert data["cap"] == "cap-04"
    assert data["kind"] == "eval"


# ── POST /api/demos/{cap} ──────────────────────────────────────────────────────

def test_demo_unknown_cap_404() -> None:
    resp = client.post("/api/demos/cap-99")
    assert resp.status_code == 404


def test_demo_single_cap_returns_dict() -> None:
    fake_result: dict[str, Any] = {"kind": "demo", "cap": "cap-01", "status": "pass", "returncode": 0, "stdout": "", "stderr": ""}
    with patch("scripts.dashboard.app._run_subprocess", return_value=fake_result):
        data = client.post("/api/demos/cap-01").json()
    assert data["kind"] == "demo"


# ── GET / (HTML) ───────────────────────────────────────────────────────────────

def test_index_200() -> None:
    resp = client.get("/")
    assert resp.status_code == 200


def test_index_html_content_type() -> None:
    resp = client.get("/")
    assert "text/html" in resp.headers["content-type"]


def test_index_contains_project_name() -> None:
    resp = client.get("/")
    assert "ai-native-capabilities" in resp.text


def test_index_contains_all_cap_ids() -> None:
    resp = client.get("/")
    for cap_id in ("cap-01", "cap-02", "cap-03", "cap-04", "cap-05"):
        assert cap_id in resp.text


def test_index_run_all_button_present() -> None:
    resp = client.get("/")
    assert "Run all evals" in resp.text


def test_index_uses_post_for_evals() -> None:
    resp = client.get("/")
    assert "method: 'POST'" in resp.text
