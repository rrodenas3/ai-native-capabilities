"""Tests for golden principles runner."""

from __future__ import annotations

from pathlib import Path

from core.harness.golden_principles import (
    CAP_DIRS,
    check_gp01_no_hardcoded_models,
    parse_principles,
    run_all,
)


def test_parse_principles_from_cap02() -> None:
    repo = Path(__file__).resolve().parents[2]
    gp_path = repo / CAP_DIRS["cap-02"] / "golden_principles.md"
    principles = parse_principles(gp_path, cap_id="cap-02", cap_dir=CAP_DIRS["cap-02"])
    ids = {p.principle_id for p in principles}
    assert "GP-01" in ids
    assert "GP-05" in ids
    assert len(principles) >= 5


def test_run_all_passes_on_clean_repo() -> None:
    report = run_all(Path(__file__).resolve().parents[2])
    blocking = report.blocking_failures
    assert report.passed, [f"{r.principle.principle_id}: {r.message}" for r in blocking]


def test_gp01_detects_hardcoded_model(tmp_path: Path) -> None:
    cap_dir = tmp_path / "cap-test"
    agents = cap_dir / "agents"
    agents.mkdir(parents=True)
    (agents / "bad_agent.py").write_text('MODEL = "claude-sonnet-4-6"\n', encoding="utf-8")
    violations = check_gp01_no_hardcoded_models(cap_dir)
    assert violations
