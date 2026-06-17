from __future__ import annotations

from pathlib import Path

from core.utils.health import HealthChecker, HealthResult
from core.utils.settings import Settings


def mock_settings() -> Settings:
    return Settings(LLM_MODE="mock")


def test_health_checker_marks_optional_failures_as_warnings(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text("LLM_MODE=mock\n", encoding="utf-8")
    checker = HealthChecker(settings_factory=mock_settings)
    monkeypatch.setattr(checker, "check_postgres", lambda: "postgres ok")
    monkeypatch.setattr(checker, "check_redis", lambda: "redis ok")
    monkeypatch.setattr(checker, "check_openai", lambda: (_ for _ in ()).throw(ValueError("missing")))
    monkeypatch.setattr(checker, "check_langsmith", lambda: (_ for _ in ()).throw(ValueError("missing")))

    results = checker.run()

    assert checker.failed_required(results) == []
    assert [result.status for result in results if not result.required] == ["warn", "warn"]


def test_health_checker_reports_required_failures(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    checker = HealthChecker(settings_factory=mock_settings)
    monkeypatch.setattr(checker, "check_postgres", lambda: "postgres ok")
    monkeypatch.setattr(checker, "check_redis", lambda: "redis ok")

    results = checker.run()

    failed = checker.failed_required(results)
    assert [result.name for result in failed] == ["Environment"]


def test_model_check_rejects_deprecated_strings() -> None:
    settings = Settings(LLM_MODE="mock", LLM_DEFAULT="claude-sonnet-4-6")
    settings.LLM_DEFAULT = "claude-3-opus-20240229"
    checker = HealthChecker(settings_factory=lambda: settings)

    result = checker._run_check("Model strings", checker.check_models, True)

    assert result.status == "fail"
    assert "Deprecated model" in result.detail


def test_failed_required_filters_warnings() -> None:
    checker = HealthChecker(settings_factory=mock_settings)
    results = [
        HealthResult("required", "fail", "bad", required=True),
        HealthResult("optional", "warn", "missing", required=False),
    ]

    assert [result.name for result in checker.failed_required(results)] == ["required"]

