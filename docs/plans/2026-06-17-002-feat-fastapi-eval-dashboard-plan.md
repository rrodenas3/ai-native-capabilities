---
title: "feat: FastAPI eval dashboard with rich score UI"
date: 2026-06-17
type: feat
capability: scripts/dashboard
status: ready
---

# feat: FastAPI eval dashboard with rich score UI

## Summary

Replace the stdlib HTTP server in `scripts/local_dashboard.py` with a FastAPI application served by uvicorn. Port existing eval/demo runner logic to proper REST semantics (POST for mutations, GET for reads). Add a Jinja2 template that renders color-coded score badges, per-cap metric tables, SSGM quarantine coverage highlighted for cap-04 and cap-05, and cached report data pre-loaded on page load. The `local-dashboard` CLI entry point continues to work with the same flags.

---

## Problem Frame

The existing dashboard at `scripts/local_dashboard.py` works but has three gaps:

**Wrong HTTP semantics.** Eval and demo runs are dispatched via GET — browsers retry GET on failure, caching proxies store the response, and safe HTTP semantics are violated. `GET /api/eval?cap=cap-04` is a side-effecting subprocess launch.

**Raw JSON output.** The `<pre>` output area dumps the full subprocess response. Score values, metric breakdowns, and SSGM quarantine coverage are buried in unformatted data.

**No cached report display.** The dashboard shows nothing on load — users must trigger a run to see any score, even though `reports/*.json` already exists from prior runs. Loading those files on startup is free.

---

## Requirements

- R1: POST `/api/evals/{cap}` triggers eval subprocess (replaces `GET /api/eval?cap=`)
- R2: POST `/api/demos/{cap}` triggers demo subprocess (replaces `GET /api/demo?cap=`)
- R3: GET `/api/reports` and GET `/api/reports/{cap}` serve cached `reports/*.json`
- R4: GET `/` renders Jinja2 template with pre-loaded report data
- R5: Score badges are color-coded: green (≥ 0.85), yellow (0.50–0.84), red (< 0.50), gray (no report)
- R6: Per-cap metric table displays all metrics; blocking failures are highlighted
- R7: `ssgm_quarantine_coverage` metric is visually prominent in cap-04 and cap-05 cards
- R8: `local-dashboard` entry point accepts `--host`, `--port`, `--open`, `--quiet` unchanged
- R9: FastAPI + uvicorn + Jinja2 added under `[project.optional-dependencies]` `dashboard` extra
- R10: `core/tests/test_local_dashboard.py` updated to target FastAPI app via TestClient

---

## Key Technical Decisions

**KTD-1: Optional dependency, not core.**
FastAPI, uvicorn, and Jinja2 are dashboard-only. Core pipeline capabilities don't need a web server. They go in `[project.optional-dependencies]` under a new `dashboard` extra alongside the existing `cap05`, `qdrant`, and `dev` groups. Jinja2 is a FastAPI optional dep — explicit pin ensures it is available for template rendering without relying on FastAPI's transitive resolution.

**KTD-2: POST for eval/demo runs.**
Eval and demo runs are side-effecting subprocess launches. POST `/api/evals/{cap}` and POST `/api/demos/{cap}` with empty JSON bodies are correct. The JS `fetch` calls change from `fetch(url)` to `fetch(url, {method: 'POST'})`.

**KTD-3: Separate Jinja2 template file.**
Template at `scripts/dashboard/templates/index.html`. Separates HTML/CSS/JS from Python logic; makes the template independently editable. Jinja2 variables: `reports` (dict of cap → report data), `caps` (capability registry), `status` (project metadata).

**KTD-4: Reports pre-loaded on GET /.**
`GET /` reads all `reports/*.json` at request time and passes the data to the template. The template renders score badges immediately on load. A missing report file returns `{}` — the badge renders gray with no crash.

**KTD-5: Replace `local_dashboard.py`, don't parallel.**
A second server script creates confusion. `local_dashboard.py` is deleted; the `local-dashboard` script entry in `pyproject.toml` updates to `scripts.dashboard.main:main`. Python 3 namespace packages mean `scripts/` doesn't need an `__init__.py` for the entry point to resolve — but `scripts/dashboard/__init__.py` is created explicitly so the subpackage is unambiguous.

**KTD-6: SSGM data comes from the `metrics` map, not a top-level field.**
Current `reports/*.json` do not include a top-level `quarantine_count` field. SSGM data appears as `metrics.ssgm_quarantine_coverage` (float, 0.0 or 1.0) for cap-04 and cap-05. The template reads from `metrics` for these caps. If a future eval emits `quarantine_count` as top-level, the template can adopt it without changing routes.

---

## High-Level Technical Design

### Request flow

```
Browser                 FastAPI (uvicorn)          Subprocess / File
  │                           │                          │
  ├── GET / ─────────────────►│                          │
  │                           ├─ read reports/*.json ────►│
  │                           │◄─ report data ───────────│
  │◄── rendered HTML ─────────│                          │
  │                           │                          │
  ├── POST /api/evals/cap-04 ─►│                          │
  │   body: {}                ├─ subprocess(suite.py) ───►│
  │                           │◄─ stdout JSON ───────────│
  │◄── {status, score, ...} ──│                          │
  │                           │                          │
  ├── GET /api/reports ───────►│                          │
  │                           ├─ read reports/*.json ────►│
  │◄── {cap-01:{...}, ...} ───│                          │
```

### Component layout

```
scripts/
  dashboard/
    __init__.py               ← marks subpackage explicitly
    app.py                    ← FastAPI app, all route handlers
    main.py                   ← CLI flags, uvicorn.run()
    templates/
      index.html              ← Jinja2 template (badges, metric tables)
  local_dashboard.py          ← DELETED (replaced by dashboard/)
core/
  tests/
    test_local_dashboard.py   ← updated to use TestClient against app.py
```

---

## Implementation Units

### U1. Add FastAPI + uvicorn + Jinja2 to optional dependencies

**Goal:** Introduce the three packages under a new `dashboard` optional-dependency group so existing installs are unaffected.

**Requirements:** R9

**Dependencies:** None

**Files:**
- `pyproject.toml` (modify `[project.optional-dependencies]`)
- `requirements.txt` (add `# ── Dashboard (optional)` comment block)

**Approach:**
- Add `dashboard = ["fastapi>=0.115.0", "uvicorn>=0.34.0", "jinja2>=3.1.0"]` to `[project.optional-dependencies]`
- In `requirements.txt`, add a commented block under `# ── Dashboard (optional) ─────────────────────────────────────────────────────` with the same three packages and a one-line install note (`pip install -e ".[dashboard]"`)
- The `dev` group does not need updating — `httpx` is already in core deps and is all that TestClient needs

**Patterns to follow:**
- Existing `cap05 = [...]` and `qdrant = [...]` entries for optional-dep format

**Test scenarios:**
- `Test expectation: none — pure config change. Verify by running `pip install -e ".[dashboard]"` and confirming `import fastapi`, `import uvicorn`, `import jinja2` succeed without error.`

---

### U2. Create FastAPI application with REST endpoints

**Goal:** Implement the FastAPI app at `scripts/dashboard/app.py` with correct REST semantics, report serving, and Jinja2 template rendering.

**Requirements:** R1, R2, R3, R4

**Dependencies:** U1

**Files:**
- `scripts/dashboard/__init__.py` (new, empty)
- `scripts/dashboard/app.py` (new)

**Approach:**
- `app.py` creates `FastAPI(title="ai-native-capabilities dashboard")` and mounts `Jinja2Templates(directory=str(Path(__file__).parent / "templates"))`
- Capability registry mirrors `local_dashboard.py`'s `CAPABILITIES` dict — same five keys, same path derivation from `ROOT = Path(__file__).resolve().parents[2]`
- `_load_report(cap_id)` reads `ROOT / "reports" / f"{cap_id}.json"`, returns `{}` on missing file or JSON parse error
- `_run_subprocess(cap_id, kind)` is a direct port of `_run_python` from `local_dashboard.py` — same `subprocess.run`, same env (`PYTHONPATH`, `LLM_MODE`, `EVAL_MODE=ci`), same 120-second timeout, same `_parse_json` logic
- Route handlers:
  - `GET /` — call `_load_report` for all 5 caps, pass `reports` dict and `caps` registry to `templates.TemplateResponse("index.html", {request, reports, caps})`
  - `GET /api/status` — return `{project, root, python, branch, capabilities}` (port of `status_payload`)
  - `GET /api/reports` — return `{cap: _load_report(cap) for cap in CAPABILITIES}`
  - `GET /api/reports/{cap}` — return `_load_report(cap)` or raise `HTTPException(404)` if `cap` not in `CAPABILITIES`
  - `POST /api/evals/{cap}` — `"all"` runs all caps sequentially and returns list; unknown cap raises `HTTPException(404)`; valid cap calls `_run_subprocess`
  - `POST /api/demos/{cap}` — same pattern, no `"all"` shortcut

**Patterns to follow:**
- `scripts/local_dashboard.py` — `_run_python`, `status_payload`, `_parse_json`, `_git`, subprocess env setup

**Test scenarios:**
- `GET /api/status` returns 200 with `python`, `branch`, `capabilities` keys and `project: "ai-native-capabilities"`
- `GET /api/reports` returns 200 with a dict containing all 5 cap keys; missing report files produce empty dicts, not errors
- `GET /api/reports/cap-01` returns 200 with report JSON when `reports/cap-01.json` exists; returns `{}` (or 200 with empty dict) when missing
- `GET /api/reports/cap-99` returns 404
- `POST /api/evals/cap-99` returns 404
- `POST /api/evals/cap-01` (subprocess mocked or env set to mock) returns 200 with `cap`, `status`, `returncode` fields
- `POST /api/evals/all` returns 200 with a list of 5 result dicts
- `POST /api/demos/cap-01` returns 200 with `kind: "demo"`
- `GET /` returns 200 and HTML body contains `"ai-native-capabilities"`

**Verification:** All test scenarios pass via TestClient. `python -c "from scripts.dashboard.app import app"` imports without error.

---

### U3. Build Jinja2 template with score badges and metric tables

**Goal:** Deliver the rich HTML UI: color-coded score badges, per-cap metric tables with blocking failure highlights, and a prominent SSGM quarantine coverage indicator for cap-04 and cap-05.

**Requirements:** R4, R5, R6, R7

**Dependencies:** U2

**Files:**
- `scripts/dashboard/templates/index.html` (new)

**Approach:**
- Template receives `reports` (dict of cap → report dict), `caps` (capability registry), and `request` from the route handler
- **Score badge:** rendered per cap as `<span class="badge badge-{{ color }}">{{ score_str }}</span>` where:
  - `color` is determined in the template via `{% if report.score >= 0.85 %}green{% elif report.score >= 0.5 %}yellow{% else %}red{% endif %}` — gray when `reports[cap]` is empty
  - `score_str` is `"%.2f"|format(report.score)` or `"—"` when no report
- **Cap card:** `<article>` with cap name, score badge, status label, and action buttons ("Run eval" / "Run demo"). An `<details>`/`<summary>` element expands to show the metric table — zero JavaScript required for expand/collapse.
- **Metric table:** `<table>` with `metric` and `value` columns. Rows where the metric name appears in `report.blocking_failures` get `class="metric-blocking"`. Value formatted to 4 decimal places for floats.
- **SSGM indicator:** for cap-04 and cap-05, the `ssgm_quarantine_coverage` row gets `class="ssgm-indicator"` plus a `🛡` prefix in the metric column. When value is `1.0`, the row is green; when `0.0`, red.
- **Action buttons:** `onclick="runEval('cap-04')"` and `onclick="runDemo('cap-04')"`. JS `runEval` / `runDemo` functions use `fetch(url, {method: 'POST'})`. Response JSON is pretty-printed into the `<pre id="output">` area.
- **Output panel:** keep the `<pre id="output">` area for raw result display after running.
- **CSS:** port the existing dark-mode CSS from `local_dashboard.py`. Add `.badge` (base), `.badge-green`, `.badge-yellow`, `.badge-red`, `.badge-gray`, `.metric-blocking` (red text / background), `.ssgm-indicator` (shield row styling).
- **Run All evals:** add a top-level "Run all evals" button that POSTs to `/api/evals/all` and renders the returned list.

**Patterns to follow:**
- `scripts/local_dashboard.py` `render_dashboard()` — CSS structure, dark-mode block, grid layout, `<pre>` output area
- `scripts/eval_summary.py` `cap_status()` — score-to-status classification logic to mirror in template

**Test scenarios:**
- Template renders without error when `reports` dict is `{}` — all 5 badges show gray, no exception
- Template renders without error when all 5 caps have `status: "pass"` and `score: 1.0` — all badges green
- Score badge is `badge-green` for score 1.0, `badge-yellow` for 0.7, `badge-red` for 0.3, `badge-gray` when key absent
- A metric in `blocking_failures` has `class="metric-blocking"` in the rendered row
- `ssgm_quarantine_coverage` row in cap-04 contains the `🛡` character
- "Run eval" button's onclick calls `runEval('cap-XX')`, not a GET link href
- "Run all evals" button is present at the top of the page

**Verification:** Load dashboard in browser with cached reports — badges render with correct colors without triggering a run. Expand a cap card — metric table shows all metrics. Click "Run eval" for cap-04 — network tab shows POST to `/api/evals/cap-04`.

---

### U4. Wire entry point and remove stdlib server

**Goal:** Update `pyproject.toml` to point `local-dashboard` at the new FastAPI entry point, create `scripts/dashboard/main.py`, delete `scripts/local_dashboard.py`, and update the test file.

**Requirements:** R8, R10

**Dependencies:** U2, U3

**Files:**
- `scripts/dashboard/main.py` (new)
- `pyproject.toml` (modify `[project.scripts]` only)
- `scripts/local_dashboard.py` (delete)
- `core/tests/test_local_dashboard.py` (modify)

**Approach:**
- `main.py` parses `--host`, `--port`, `--open`, `--quiet` with `argparse` (same flags as existing). Calls `uvicorn.run("scripts.dashboard.app:app", host=host, port=port, log_level="error" if quiet else "info")`. If `--open`, calls `webbrowser.open(f"http://{host}:{port}")` after `time.sleep(0.5)` to let uvicorn bind.
- Update `[project.scripts]`: `local-dashboard = "scripts.dashboard.main:main"` (was `scripts.local_dashboard:main`)
- Delete `scripts/local_dashboard.py`
- Update `core/tests/test_local_dashboard.py`:
  - Replace `from scripts.local_dashboard import ...` imports with `from scripts.dashboard.app import app` and `from fastapi.testclient import TestClient`
  - Replace `ThreadingHTTPServer`-era tests with `TestClient(app)` calls
  - Preserve equivalent behavioral coverage: status endpoint, report loading, unknown-cap error, HTML content check, `_parse_json` helper

**Patterns to follow:**
- `scripts/local_dashboard.py` `serve()` and `main()` — flag names, webbrowser open, serve_forever → uvicorn equivalent

**Test scenarios:**
- `TestClient(app).get("/api/status").status_code == 200`
- `TestClient(app).get("/api/status").json()["project"] == "ai-native-capabilities"`
- `TestClient(app).post("/api/evals/cap-99").status_code == 404`
- `TestClient(app).get("/").status_code == 200` and response body contains `"ai-native-capabilities"`
- `TestClient(app).get("/api/reports").json()` has keys for all 5 caps
- `_parse_json("")` returns `None`; `_parse_json('{"a":1}')` returns `{"a": 1}`

**Verification:** `pytest core/tests/test_local_dashboard.py -v` passes. `local-dashboard --help` shows the four flags. `local-dashboard --open` starts uvicorn and opens a browser tab.

---

## Scope Boundaries

### In scope
- FastAPI app replacing stdlib HTTP server
- Jinja2 template with score badges, metric tables, SSGM quarantine visibility
- REST-correct endpoints (POST for runs, GET for reads)
- Optional dependency group
- Updated tests

### Deferred to Follow-Up Work
- WebSocket streaming of subprocess stdout in real time — YAGNI until eval runs exceed a few seconds (currently < 1s in mock mode)
- Persistent run history beyond `reports/*.json` — the JSON files serve adequately
- `quarantine_count` as a top-level report field — currently only inside `metrics`; template already handles it; eval suite can add the field later

### Out of scope
- React/Next.js frontend
- Authentication or HTTPS (localhost-only tool)
- Production deployment or Docker
- Changes to eval suites or `core/harness/`

---

## Risks and Dependencies

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| `scripts.dashboard.main:main` entry point fails if Python treats `scripts/` as not importable | Low | `scripts/` already resolves as a namespace package — existing `scripts.health_check:main` entry point proves it. `scripts/dashboard/__init__.py` makes the subpackage explicit. |
| `fastapi.testclient.TestClient` requires `httpx` — already in core deps | None | `httpx>=0.28.0` is in core `[project]` deps; no extra install needed for tests |
| TestClient import fails if `dashboard` extra is not installed in test env | Medium | Document: `pytest core/tests/test_local_dashboard.py` requires `pip install -e ".[dashboard]"`. Add note to test file docstring. |
| `uvicorn.run` with `"scripts.dashboard.app:app"` string import may fail if project root is not on `sys.path` at runtime | Low | `local-dashboard` entry point is called after `pip install -e .` which adds project root to `sys.path` via the editable install. Direct `uvicorn.run(app)` (passing the object) is the safer alternative if string form causes issues. |

---

## Sources and Research

- `scripts/local_dashboard.py` — route structure, subprocess env, `_run_python`, `_parse_json`, CSS/HTML base
- `reports/cap-*.json` — report envelope: `cap`, `status`, `score`, `metrics`, `blocking_failures`; `ssgm_quarantine_coverage` is inside `metrics` for cap-04 and cap-05
- `core/tests/test_local_dashboard.py` — existing test coverage to preserve in updated form
- `pyproject.toml` — optional-dependency group format, script entry point convention
- `scripts/eval_summary.py` — `cap_status()` score-to-color classification logic
