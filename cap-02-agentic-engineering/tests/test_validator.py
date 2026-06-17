from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]


def load(relative: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


schema = load("schemas/briefing_script.py", "cap02_schema_test")
validator = load("tools/validator.py", "cap02_validator_test")


def test_validate_spec_markdown_passes() -> None:
    result = validator.validate_briefing(ROOT / "specs" / "SPEC.md")

    assert result.valid is True
    assert result.briefing_completeness == 1.0


def test_valid_briefing_data_accepts_without_false_positive() -> None:
    briefing = schema.minimal_valid_briefing()

    result = validator.validate_briefing_data(briefing.model_dump(mode="json"))

    assert result.valid is True
    assert result.briefing_completeness == 1.0
    assert result.errors == []


def test_missing_required_section_returns_structured_error() -> None:
    data = schema.minimal_valid_briefing().model_dump(mode="json")
    data.pop("goal_and_why")

    result = validator.validate_briefing_data(data)

    assert result.valid is False
    assert result.briefing_completeness < 1.0
    assert result.errors
    assert result.errors[0].location == "goal_and_why"
