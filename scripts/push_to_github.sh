#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  ai-native-capabilities — GitHub repo creation + first push
#  Run: bash scripts/push_to_github.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
REPO_NAME="ai-native-capabilities"
DESCRIPTION="Five production-grade agentic AI capabilities built spec-first. Decision Intelligence · Agentic Engineering (SASE) · Commerce Agents · Autonomous Supply Chain · Compliance Intelligence."
TOPICS='["agentic-ai","llm","langgraph","mcp","ai-native","multi-agent","rag","langchain","python","openai","anthropic","ai-agents","spec-driven-development","enterprise-ai"]'

# ── Validate ──────────────────────────────────────────────────────────────────
if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "❌  GITHUB_TOKEN not set."
  echo "    Export it: export GITHUB_TOKEN=ghp_your_token_here"
  echo "    Get one at: https://github.com/settings/tokens/new"
  echo "    Required scopes: repo (full)"
  exit 1
fi

if [[ -z "${GITHUB_USERNAME:-}" ]]; then
  echo "❌  GITHUB_USERNAME not set."
  echo "    Export it: export GITHUB_USERNAME=your_github_username"
  exit 1
fi

echo ""
echo "  Creating GitHub repo: ${GITHUB_USERNAME}/${REPO_NAME}"
echo ""

# ── Create repo via GitHub API ────────────────────────────────────────────────
HTTP_STATUS=$(curl -s -o /tmp/gh_create_response.json -w "%{http_code}" \
  -X POST \
  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  https://api.github.com/user/repos \
  -d "{
    \"name\": \"${REPO_NAME}\",
    \"description\": \"${DESCRIPTION}\",
    \"private\": false,
    \"has_issues\": true,
    \"has_wiki\": false,
    \"auto_init\": false,
    \"allow_squash_merge\": true,
    \"allow_merge_commit\": false,
    \"allow_rebase_merge\": true,
    \"delete_branch_on_merge\": true
  }")

if [[ "$HTTP_STATUS" == "201" ]]; then
  REPO_URL=$(python3 -c "import json,sys; d=json.load(open('/tmp/gh_create_response.json')); print(d['html_url'])")
  echo "  ✓ Repo created: ${REPO_URL}"
elif [[ "$HTTP_STATUS" == "422" ]]; then
  echo "  ℹ Repo already exists — pushing to existing repo"
  REPO_URL="https://github.com/${GITHUB_USERNAME}/${REPO_NAME}"
else
  echo "  ✗ Repo creation failed (HTTP ${HTTP_STATUS})"
  cat /tmp/gh_create_response.json
  exit 1
fi

# ── Add topics ────────────────────────────────────────────────────────────────
curl -s -o /dev/null \
  -X PUT \
  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "https://api.github.com/repos/${GITHUB_USERNAME}/${REPO_NAME}/topics" \
  -d "{\"names\": $(echo $TOPICS | python3 -c 'import json,sys; print(json.dumps(json.loads(sys.stdin.read())))')}"
echo "  ✓ Topics added"

# ── Push code ─────────────────────────────────────────────────────────────────
REMOTE_URL="https://${GITHUB_USERNAME}:${GITHUB_TOKEN}@github.com/${GITHUB_USERNAME}/${REPO_NAME}.git"

git remote remove origin 2>/dev/null || true
git remote add origin "$REMOTE_URL"
git push -u origin main

echo ""
echo "  ✓ Code pushed!"
echo ""

# ── Pin the first good issue ──────────────────────────────────────────────────
echo "  Creating starter issue..."
curl -s -o /dev/null \
  -X POST \
  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/${GITHUB_USERNAME}/${REPO_NAME}/issues" \
  -d '{
    "title": "[TASK-CORE-01] BaseAgentState + BaseCapabilityGraph (LangGraph)",
    "body": "## First task — start here\n\nImplement the shared LangGraph base from `core/SPEC.md`.\n\n**Task:** `TASK-CORE-01`\n**Spec:** `core/SPEC.md` → Implementation Tasks section\n\n### What to build\n\n- `core/orchestration/base_state.py` — `BaseAgentState` TypedDict\n- `core/orchestration/base_graph.py` — `BaseCapabilityGraph` with `build()`, `add_human_gate()`, `add_eval_node()`, `add_cost_telemetry()`\n\n### Acceptance criteria\n\n- All capabilities can import and extend `BaseAgentState`\n- `BaseCapabilityGraph.build()` returns a valid `CompiledStateGraph`\n- Human gate can be added to any node via `add_human_gate()`\n- `core/tests/test_orchestration.py` passes\n\n### Codex prompt to start\n\n```\nRead core/SPEC.md and implement TASK-CORE-01. Create core/orchestration/base_state.py and core/orchestration/base_graph.py exactly as specified. Write tests in core/tests/test_orchestration.py.\n```\n\n**Build order:** CORE before any capability. This is task 1 of 12 in core.",
    "labels": ["task", "core", "good first task"]
  }'
echo "  ✓ Starter issue created"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "  🚀  ${REPO_URL}"
echo ""
echo "  Next steps:"
echo "  1. Star your own repo (signals engagement to GitHub discovery)"
echo "  2. Add a social preview image (Settings → Social preview)"  
echo "  3. Open Codex with core/SPEC.md and start TASK-CORE-01"
echo "  4. Share the repo link — the README is your pitch"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo ""
