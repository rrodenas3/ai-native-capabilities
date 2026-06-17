"""FastAPI dashboard for ai-native-capabilities eval and demo runner."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = Path(__file__).parent / "templates"

app = FastAPI(title="ai-native-capabilities dashboard", docs_url="/docs", redoc_url="/redoc")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

CAPABILITIES: dict[str, dict[str, Any]] = {
    "cap-01": {
        "name": "Decision Intelligence",
        "demo": ROOT / "cap-01-decision-intelligence" / "demo.py",
        "eval": ROOT / "cap-01-decision-intelligence" / "evals" / "suite.py",
    },
    "cap-02": {
        "name": "Agentic Engineering",
        "demo": ROOT / "cap-02-agentic-engineering" / "demo.py",
        "eval": ROOT / "cap-02-agentic-engineering" / "evals" / "suite.py",
    },
    "cap-03": {
        "name": "Agentic Commerce",
        "demo": ROOT / "cap-03-agentic-commerce" / "demo.py",
        "eval": ROOT / "cap-03-agentic-commerce" / "evals" / "suite.py",
    },
    "cap-04": {
        "name": "Autonomous Operations",
        "demo": ROOT / "cap-04-autonomous-operations" / "demo.py",
        "eval": ROOT / "cap-04-autonomous-operations" / "evals" / "suite.py",
    },
    "cap-05": {
        "name": "Compliance Intelligence",
        "demo": ROOT / "cap-05-compliance-intelligence" / "demo.py",
        "eval": ROOT / "cap-05-compliance-intelligence" / "evals" / "suite.py",
    },
}

# Caps whose SSGM quarantine coverage metric should be highlighted
SSGM_CAPS = {"cap-04", "cap-05"}


def _load_report(cap_id: str) -> dict[str, Any]:
    path = ROOT / "reports" / f"{cap_id}.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _parse_json(text: str) -> Any | None:
    stripped = text.strip()
    if not stripped:
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return None


def _git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    return result.stdout if result.returncode == 0 else ""


def _run_subprocess(cap_id: str, *, kind: str) -> dict[str, Any]:
    meta = CAPABILITIES[cap_id]
    script = meta[kind]
    if not script.exists():
        return {
            "kind": kind,
            "cap": cap_id,
            "status": "missing",
            "error": f"{script} not found",
        }
    env = {
        **os.environ,
        "PYTHONPATH": str(ROOT),
        "LLM_MODE": os.environ.get("LLM_MODE", "mock"),
        "EVAL_MODE": "ci",
    }
    args: list[str] = [str(script)]
    if kind == "eval":
        output_path = ROOT / "reports" / f"{cap_id}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        args += ["--output", str(output_path)]
    completed = subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )
    payload: dict[str, Any] = {
        "kind": kind,
        "cap": cap_id,
        "returncode": completed.returncode,
        "status": "pass" if completed.returncode == 0 else "fail",
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
    parsed = _parse_json(completed.stdout)
    if parsed is not None:
        payload["json"] = parsed
    return payload


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    reports = {cap: _load_report(cap) for cap in CAPABILITIES}
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "caps": CAPABILITIES,
            "reports": reports,
            "ssgm_caps": SSGM_CAPS,
        },
    )


@app.get("/api/status")
async def status() -> dict[str, Any]:
    return {
        "project": "ai-native-capabilities",
        "root": str(ROOT),
        "python": sys.version.split()[0],
        "branch": _git(["branch", "--show-current"]).strip(),
        "capabilities": {
            cap_id: {
                "name": meta["name"],
                "demo_available": meta["demo"].exists(),
                "eval_available": meta["eval"].exists(),
            }
            for cap_id, meta in CAPABILITIES.items()
        },
    }


@app.get("/api/reports")
async def all_reports() -> dict[str, Any]:
    return {cap: _load_report(cap) for cap in CAPABILITIES}


@app.get("/api/reports/{cap_id}")
async def one_report(cap_id: str) -> dict[str, Any]:
    if cap_id not in CAPABILITIES:
        raise HTTPException(status_code=404, detail=f"Unknown capability: {cap_id}")
    return _load_report(cap_id)


@app.post("/api/evals/{cap_id}")
async def run_eval(cap_id: str) -> Any:
    if cap_id == "all":
        return [_run_subprocess(c, kind="eval") for c in CAPABILITIES]
    if cap_id not in CAPABILITIES:
        raise HTTPException(status_code=404, detail=f"Unknown capability: {cap_id}")
    return _run_subprocess(cap_id, kind="eval")


@app.post("/api/demos/{cap_id}")
async def run_demo(cap_id: str) -> dict[str, Any]:
    if cap_id not in CAPABILITIES:
        raise HTTPException(status_code=404, detail=f"Unknown capability: {cap_id}")
    return _run_subprocess(cap_id, kind="demo")
