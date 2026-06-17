"""Security gate for Cap-02 agent-generated files."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
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
    status = "BLOCKED" if result.critical > 0 else state.get("status", "SECURITY_PASSED")
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


def _bandit_findings(files: list[Path], *, timeout_s: int) -> list[SecurityFinding]:
    if shutil.which("bandit") is None or not files:
        return []
    completed = subprocess.run(
        ["bandit", "-f", "json", "-q", *[str(path) for path in files]],
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=False,
    )
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
    if shutil.which("semgrep") is None or not files:
        return []
    completed = subprocess.run(
        ["semgrep", "--config", "auto", "--json", *[str(path) for path in files]],
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=False,
    )
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
