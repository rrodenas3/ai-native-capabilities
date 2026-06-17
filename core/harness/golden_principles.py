"""Golden principles runner — enforces cap golden_principles.md in CI."""

from __future__ import annotations

import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

CAP_DIRS: dict[str, str] = {
    "cap-01": "cap-01-decision-intelligence",
    "cap-02": "cap-02-agentic-engineering",
    "cap-03": "cap-03-agentic-commerce",
    "cap-04": "cap-04-autonomous-operations",
    "cap-05": "cap-05-compliance-intelligence",
}

_MODEL_PATTERN = re.compile(r"claude-|gpt-", re.IGNORECASE)
_DIRECT_TOOL_PATTERN = re.compile(
    r"\.invoke_tool|\.call_tool|requests\.get|requests\.post",
    re.IGNORECASE,
)
_GATE_BYPASS_PATTERN = re.compile(
    r"skip.*gate|bypass.*gate|if.*approved.*skip",
    re.IGNORECASE,
)
_LLM_CALL_HINT = re.compile(r"\binvoke\b|\bainvoke\b|\bgenerate\b")
_LLM_LOG_HINT = re.compile(r"record_llm_call|log_llm")


@dataclass
class Principle:
    principle_id: str
    name: str
    rule: str
    severity: str
    cap_id: str
    cap_dir: str


@dataclass
class PrincipleResult:
    principle: Principle
    passed: bool
    message: str = ""


@dataclass
class GoldenPrinciplesReport:
    results: list[PrincipleResult] = field(default_factory=list)

    @property
    def blocking_failures(self) -> list[PrincipleResult]:
        return [
            r for r in self.results if not r.passed and r.principle.severity == "blocking"
        ]

    @property
    def passed(self) -> bool:
        return not self.blocking_failures


def parse_principles(path: Path, *, cap_id: str, cap_dir: str) -> list[Principle]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    principles: list[Principle] = []
    for chunk in text.split("\n---\n"):
        if "principle_id:" not in chunk:
            continue
        fields = _parse_frontmatter(chunk)
        if "principle_id" not in fields:
            continue
        principles.append(
            Principle(
                principle_id=fields["principle_id"],
                name=fields.get("name", fields["principle_id"]),
                rule=fields.get("rule", ""),
                severity=fields.get("severity", "warning"),
                cap_id=cap_id,
                cap_dir=cap_dir,
            )
        )
    return principles


def _parse_frontmatter(chunk: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in chunk.splitlines():
        if ":" not in line or line.strip().startswith("#"):
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if key and value and key.replace("_", "").isalnum():
            fields[key] = value
    return fields


def _agent_tool_py_files(cap_dir: Path) -> list[Path]:
    files: list[Path] = []
    for sub in ("agents", "tools"):
        root = cap_dir / sub
        if root.is_dir():
            files.extend(root.rglob("*.py"))
    return files


def check_gp01_no_hardcoded_models(cap_dir: Path) -> list[str]:
    violations: list[str] = []
    for path in _agent_tool_py_files(cap_dir):
        if "test" in path.name:
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if "#" in line:
                line = line.split("#", 1)[0]
            if not _MODEL_PATTERN.search(line):
                continue
            if "settings" in line.lower():
                continue
            violations.append(f"{path}:{line_no}: hardcoded model string")
    return violations


def check_gp02_llm_logging(cap_dir: Path) -> list[str]:
    violations: list[str] = []
    agents_dir = cap_dir / "agents"
    if not agents_dir.is_dir():
        return violations
    for path in agents_dir.glob("*.py"):
        src = path.read_text(encoding="utf-8")
        if _LLM_CALL_HINT.search(src) and not _LLM_LOG_HINT.search(src):
            violations.append(f"{path}: LLM call without record_llm_call/log_llm")
    return violations


def check_gp03_no_direct_tool_calls(cap_dir: Path) -> list[str]:
    violations: list[str] = []
    agents_dir = cap_dir / "agents"
    if not agents_dir.is_dir():
        return violations
    for path in agents_dir.rglob("*.py"):
        if "test" in path.name:
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if "#" in line:
                line = line.split("#", 1)[0]
            if not _DIRECT_TOOL_PATTERN.search(line):
                continue
            if any(token in line for token in ("harness", "mcp", "test")):
                continue
            violations.append(f"{path}:{line_no}: direct tool/HTTP call from agent")
    return violations


def check_gp04_human_gate_bypass(cap_dir: Path) -> list[str]:
    violations: list[str] = []
    agents_dir = cap_dir / "agents"
    if not agents_dir.is_dir():
        return violations
    for path in agents_dir.rglob("*.py"):
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if _GATE_BYPASS_PATTERN.search(line):
                violations.append(f"{path}:{line_no}: possible human-gate bypass")
    return violations


def check_gp05_json_serializable_state(cap_dir: Path) -> list[str]:
    violations: list[str] = []
    agents_dir = cap_dir / "agents"
    if not agents_dir.is_dir():
        return violations
    for path in agents_dir.glob("*.py"):
        src = path.read_text(encoding="utf-8")
        if "datetime" in src and "TypedDict" in src and "isoformat" not in src:
            violations.append(f"{path}: possible non-serialisable datetime in TypedDict state")
    return violations


_CHECKERS: dict[str, Callable[[Path], list[str]]] = {
    "GP-01": check_gp01_no_hardcoded_models,
    "GP-02": check_gp02_llm_logging,
    "GP-03": check_gp03_no_direct_tool_calls,
    "GP-04": check_gp04_human_gate_bypass,
    "GP-05": check_gp05_json_serializable_state,
}


def evaluate_principle(principle: Principle, repo_root: Path) -> PrincipleResult:
    cap_dir = repo_root / principle.cap_dir
    checker = _CHECKERS.get(principle.principle_id)
    if checker is None:
        return PrincipleResult(principle=principle, passed=True, message="no native checker")
    violations = checker(cap_dir)
    if violations:
        return PrincipleResult(
            principle=principle,
            passed=False,
            message="; ".join(violations[:3]) + (f" (+{len(violations) - 3} more)" if len(violations) > 3 else ""),
        )
    return PrincipleResult(principle=principle, passed=True)


def run_all(repo_root: Path | None = None) -> GoldenPrinciplesReport:
    root = repo_root or Path(__file__).resolve().parents[2]
    report = GoldenPrinciplesReport()
    for cap_id, cap_dir_name in CAP_DIRS.items():
        cap_dir = root / cap_dir_name
        gp_path = cap_dir / "golden_principles.md"
        for principle in parse_principles(gp_path, cap_id=cap_id, cap_dir=cap_dir_name):
            report.results.append(evaluate_principle(principle, root))
    return report


def main(argv: list[str] | None = None) -> int:
    report = run_all()
    for result in report.results:
        status = "PASS" if result.passed else "FAIL"
        prefix = f"[{result.principle.cap_id} {result.principle.principle_id}]"
        line = f"{prefix} {status} — {result.principle.name}"
        if result.message and not result.passed:
            line += f": {result.message}"
        print(line)
    if report.passed:
        print("\nGolden principles: all blocking checks passed")
        return 0
    print(f"\nGolden principles: {len(report.blocking_failures)} blocking failure(s)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
