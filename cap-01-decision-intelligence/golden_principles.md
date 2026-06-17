# Golden Principles — cap-01-decision-intelligence
# Machine-enforced anti-drift rules for agent-generated artifacts.
# See: docs/adr/ADR-002-harness-engineering.md
#
# Format: YAML front-matter, one principle per block.
# Severity: blocking (fails CI) | warning (flags PR)
# Test: shell command that returns exit 1 if principle violated

---
principle_id: GP-01
name: No hardcoded model strings
rule: Model strings must be read from settings, never hardcoded in agent or tool code.
test: grep -rn "claude-\|gpt-" cap-01-decision-intelligence/agents/ cap-01-decision-intelligence/tools/ --include="*.py" | grep -v "settings\|test\|#" | grep -v ".pyc"
severity: blocking

---
principle_id: GP-02
name: Every LLM call logged
rule: Every function that calls an LLM must log model, tokens_in, tokens_out, latency_ms.
test: python3 -c "
import ast, sys, pathlib
missing = []
for f in pathlib.Path('cap-01-decision-intelligence/agents').glob('*.py'):
    src = f.read_text()
    if 'invoke' in src or 'ainvoke' in src or 'generate' in src:
        if 'record_llm_call' not in src and 'log_llm' not in src:
            missing.append(str(f))
if missing:
    print('Missing LLM logging:', missing)
    sys.exit(1)
"
severity: blocking

---
principle_id: GP-03
name: No direct tool calls from model
rule: Model proposes structured action; harness validates and executes. Never model.tool_call().
test: grep -rn "\.invoke_tool\|\.call_tool\|requests\.get\|requests\.post" cap-01-decision-intelligence/agents/ --include="*.py" | grep -v "harness\|mcp\|test\|#"
severity: blocking

---
principle_id: GP-04
name: Human gate not bypassable
rule: Human approval gates must use LangGraph interrupt(). No conditional-skip logic.
test: grep -rn "skip.*gate\|bypass.*gate\|if.*approved.*skip" cap-01-decision-intelligence/agents/ --include="*.py"
severity: blocking

---
principle_id: GP-05
name: State must be JSON-serialisable
rule: LangGraph state TypedDicts must contain only JSON-serialisable types (no Python objects).
test: python3 -c "
import sys, pathlib, ast
for f in pathlib.Path('cap-01-decision-intelligence/agents').glob('*.py'):
    src = f.read_text()
    if 'datetime' in src and 'TypedDict' in src and 'isoformat' not in src:
        print(f'Possible non-serialisable datetime in {f}')
        sys.exit(1)
"
severity: warning
