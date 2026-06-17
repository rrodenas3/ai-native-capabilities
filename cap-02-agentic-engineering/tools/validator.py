"""BriefingScript validation CLI and helper."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

REQUIRED_MARKDOWN_SECTIONS = {
    "goal_and_why",
    "what_and_success_criteria",
    "all_needed_context",
    "implementation_tasks",
    "codex_instructions",
}


class ValidationIssue(BaseModel):
    location: str
    message: str


class ValidationResult(BaseModel):
    valid: bool
    briefing_completeness: float = Field(ge=0.0, le=1.0)
    errors: list[ValidationIssue] = Field(default_factory=list)
    briefing: Any = None


def validate_briefing(path: str | Path) -> ValidationResult:
    file_path = Path(path)
    try:
        raw = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        return ValidationResult(
            valid=False,
            briefing_completeness=0.0,
            errors=[ValidationIssue(location=str(file_path), message=str(exc))],
        )

    if file_path.suffix.lower() == ".md":
        return _validate_markdown_spec(raw)
    try:
        data = _load_structured(raw, file_path.suffix.lower())
    except ValueError as exc:
        return ValidationResult(
            valid=False,
            briefing_completeness=0.0,
            errors=[ValidationIssue(location=str(file_path), message=str(exc))],
        )
    return validate_briefing_data(data)


def validate_briefing_data(data: dict[str, Any]) -> ValidationResult:
    briefing_script_model = _schema_attr("BriefingScript")
    try:
        briefing = briefing_script_model.model_validate(data)
    except ValidationError as exc:
        errors = [
            ValidationIssue(location=".".join(str(part) for part in issue["loc"]), message=issue["msg"])
            for issue in exc.errors()
        ]
        return ValidationResult(valid=False, briefing_completeness=_completeness_from_data(data), errors=errors)
    return ValidationResult(valid=True, briefing_completeness=briefing.briefing_completeness, briefing=briefing)


def _validate_markdown_spec(raw: str) -> ValidationResult:
    sections = {
        line.lstrip("#").strip().lower()
        for line in raw.splitlines()
        if line.startswith("## ")
    }
    missing = sorted(REQUIRED_MARKDOWN_SECTIONS - sections)
    completeness = (len(REQUIRED_MARKDOWN_SECTIONS) - len(missing)) / len(REQUIRED_MARKDOWN_SECTIONS)
    return ValidationResult(
        valid=not missing,
        briefing_completeness=round(completeness, 3),
        errors=[
            ValidationIssue(location=section, message="Required BriefingScript section is missing")
            for section in missing
        ],
    )


def _load_structured(raw: str, suffix: str) -> dict[str, Any]:
    if suffix == ".json":
        return json.loads(raw)
    try:
        import yaml
    except ImportError as exc:
        raise ValueError("PyYAML is required to validate YAML BriefingScripts") from exc
    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise ValueError("BriefingScript must be a mapping")
    return data


def _completeness_from_data(data: dict[str, Any]) -> float:
    required = [
        "goal_and_why",
        "what_and_success",
        "all_needed_context",
        "implementation_tasks",
        "codex_instructions",
    ]
    present = sum(1 for key in required if data.get(key))
    return round(present / len(required), 3)


def _schema_attr(name: str) -> Any:
    schema_path = Path(__file__).parents[1] / "schemas" / "briefing_script.py"
    spec = importlib.util.spec_from_file_location("cap02_briefing_schema", schema_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load schema from {schema_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return getattr(module, name)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a Cap-02 BriefingScript or SPEC.md")
    parser.add_argument("path")
    args = parser.parse_args()
    result = validate_briefing(args.path)
    print("PASS" if result.valid else "FAIL")
    print(result.model_dump_json(indent=2, exclude={"briefing"}))
    raise SystemExit(0 if result.valid else 1)


if __name__ == "__main__":
    main()
