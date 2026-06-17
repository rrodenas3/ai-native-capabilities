from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.utils.settings import Settings, get_settings, validate_model_string


def clear_settings_cache() -> None:
    get_settings.cache_clear()


def test_settings_load_without_api_keys_in_mock_mode(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    clear_settings_cache()

    settings = get_settings()

    assert settings.LLM_MODE == "mock"
    assert settings.LLM_DEFAULT == "claude-sonnet-4-6"


def test_anthropic_key_required_in_real_mode(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "real")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(ValidationError, match="ANTHROPIC_API_KEY is required"):
        Settings()


def test_validate_model_string_accepts_current_models() -> None:
    assert validate_model_string("claude-sonnet-4-6") == "claude-sonnet-4-6"
    assert validate_model_string("gpt-5") == "gpt-5"


def test_validate_model_string_rejects_deprecated_models() -> None:
    for model in ("claude-3-opus-20240229", "claude-3-5-sonnet-20241022", "gpt-4o"):
        with pytest.raises(ValueError, match="Deprecated model"):
            validate_model_string(model)


def test_validate_model_string_rejects_unknown_models() -> None:
    with pytest.raises(ValueError, match="Unknown model"):
        validate_model_string("made-up-model")


def test_get_settings_returns_cached_instance(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    clear_settings_cache()

    first = get_settings()
    second = get_settings()

    assert first is second


def test_budget_and_threshold_settings(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    monkeypatch.setenv("AUTONOMOUS_ACTION_THRESHOLD_USD", "7500")
    monkeypatch.setenv("SESSION_BUDGET_USD", "12.5")
    clear_settings_cache()

    settings = get_settings()

    assert settings.AUTONOMOUS_ACTION_THRESHOLD_USD == 7500
    assert settings.SESSION_BUDGET_USD == 12.5

