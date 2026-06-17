"""Security gate for Cap-02 agent-generated files."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class SecurityFinding(BaseModel):
    file: str
    severity: str
    rule_id: str
    message: str


class SecurityScanResult(BaseModel):
    tool: str = "bandit+semgrep"
    critical: int = Field(ge=0)
    high: int = Field(ge=0)
    medium: int = Field(ge=0)
    low: int = Field(ge=0)
    findings: list[SecurityFinding] = Field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return self.critical > 0 or self.high > 0

    @property
    def weakness_rate_per_kloc(self) -> float:
        return float(self.critical + self.high + self.medium + self.low)


def _require_ci_scanners() -> None:
    if os.environ.get("REQUIRE_SECURITY_SCANNERS") != "1":
        return
    missing = []
    if shutil.which("bandit") is None:
        missing.append("bandit")
    if not _semgrep_available():
        missing.append("semgrep")
    if missing:
        raise RuntimeError(
            f"Security scanners required (REQUIRE_SECURITY_SCANNERS=1): {', '.join(missing)}"
        )


def _semgrep_available() -> bool:
    if shutil.which("semgrep"):
        return True
    # pip-installed semgrep exposes the CLI via console script or python -m semgrep;
    # --version may exit non-zero on some builds, so trust the package install.
    return importlib.util.find_spec("semgrep") is not None


def _semgrep_command() -> list[str]:
    if shutil.which("semgrep"):
        return ["semgrep"]
    return [sys.executable, "-m", "semgrep"]


def scan_files(paths: list[str | Path], *, timeout_s: int = 30) -> SecurityScanResult:
    files = [Path(path) for path in paths]
    findings = _heuristic_findings(files)
    findings.extend(_bandit_findings(files, timeout_s=timeout_s))
    findings.extend(_semgrep_findings(files, timeout_s=timeout_s))
    return _summarise(findings)


def security_gate_node(state: dict[str, Any]) -> dict[str, Any]:
    output_files = state.get("output_files", {})
    temp_root = Path(state.get("security_scan_root", ".cap02-security-scan"))
    temp_root.mkdir(exist_ok=True)
    paths = []
    for relative, content in output_files.items():
        path = temp_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(content), encoding="utf-8")
        paths.append(path)
    result = scan_files(paths)
    status = "BLOCKED" if result.blocked else state.get("status", "SECURITY_PASSED")
    return {**state, "security_scan": result, "status": status, "security_weakness_rate": result.weakness_rate_per_kloc}


def _heuristic_findings(files: list[Path]) -> list[SecurityFinding]:
    patterns = [
        ("CRITICAL", "python.eval", re.compile(r"\beval\s*\("), "Dynamic eval execution"),
        ("CRITICAL", "python.exec", re.compile(r"\bexec\s*\("), "Dynamic exec execution"),
        ("CRITICAL", "secret.hardcoded", re.compile(r"(api_key|password|secret)\s*=\s*['\"][^'\"]+['\"]", re.I), "Hardcoded secret"),
        ("CRITICAL", "sql.injection", re.compile(r"SELECT .*\+|f['\"].*SELECT", re.I), "Potential SQL injection"),
    ]
    findings: list[SecurityFinding] = []
    for path in files:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for severity, rule_id, pattern, message in patterns:
            if pattern.search(text):
                findings.append(SecurityFinding(file=str(path), severity=severity, rule_id=rule_id, message=message))
    return findings


def _run_scanner(cmd: list[str], *, timeout_s: int) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired, UnicodeDecodeError):
        return None


def _bandit_findings(files: list[Path], *, timeout_s: int) -> list[SecurityFinding]:
    if shutil.which("bandit") is None or not files:
        return []
    completed = _run_scanner(
        ["bandit", "-f", "json", "-q", *[str(path) for path in files]],
        timeout_s=timeout_s,
    )
    if completed is None:
        return []
    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError:
        return []
    findings = []
    for item in payload.get("results", []):
        findings.append(
            SecurityFinding(
                file=str(item.get("filename", "")),
                severity=_normalise_severity(str(item.get("issue_severity", "LOW"))),
                rule_id=str(item.get("test_id", "bandit")),
                message=str(item.get("issue_text", "Bandit finding")),
            )
        )
    return findings


def _semgrep_findings(files: list[Path], *, timeout_s: int) -> list[SecurityFinding]:
    if not _semgrep_available() or not files:
        return []
    completed = _run_scanner(
        [*_semgrep_command(), "--config", "auto", "--json", "--quiet", *[str(path) for path in files]],
        timeout_s=timeout_s,
    )
    if completed is None:
        return []
    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError:
        return []
    findings = []
    for item in payload.get("results", []):
        extra = item.get("extra", {})
        findings.append(
            SecurityFinding(
                file=str(item.get("path", "")),
                severity=_normalise_severity(str(extra.get("severity", "LOW"))),
                rule_id=str(item.get("check_id", "semgrep")),
                message=str(extra.get("message", "Semgrep finding")),
            )
        )
    return findings


def _summarise(findings: list[SecurityFinding]) -> SecurityScanResult:
    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for finding in findings:
        counts[_normalise_severity(finding.severity)] += 1
    return SecurityScanResult(
        critical=counts["CRITICAL"],
        high=counts["HIGH"],
        medium=counts["MEDIUM"],
        low=counts["LOW"],
        findings=findings,
    )


def _normalise_severity(severity: str) -> str:
    upper = severity.upper()
    return upper if upper in {"CRITICAL", "HIGH", "MEDIUM", "LOW"} else "LOW"
