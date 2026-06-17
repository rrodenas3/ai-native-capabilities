"""L0-L3 AI proficiency assessment for Cap-02 BriefingScript templates."""

from __future__ import annotations

import argparse
from dataclasses import dataclass


@dataclass(frozen=True)
class Question:
    prompt: str
    weight: int


QUESTIONS = (
    Question("Can you read a SPEC.md and explain the requested outcome?", 1),
    Question("Can you run project evals and interpret a failing metric?", 1),
    Question("Have you submitted a PR that passed CI?", 1),
    Question("Have you written a BriefingScript from scratch?", 2),
    Question("Can you run and interpret a security gate such as bandit or semgrep?", 2),
    Question("Can you debug agent traces in LangSmith or LangGraph Studio?", 2),
    Question("Can you implement a LangGraph state machine from a spec?", 3),
    Question("Can you design an MCP connector contract and mock implementation?", 3),
    Question("Can you author a capability SPEC from a business problem?", 4),
    Question("Can you make architecture decisions balancing capability, governance, and cost?", 4),
)


LEVELS = {
    "L0": "Aware: start with simple retrieval and question-raising tasks.",
    "L1": "User: implement well-scoped tasks and review generated output.",
    "L2": "Builder: write BriefingScripts, agents, evals, and connectors.",
    "L3": "Architect: author capability specs and review system architecture.",
}


def assess(answers: list[bool]) -> dict[str, str | int]:
    if len(answers) != len(QUESTIONS):
        raise ValueError(f"Expected {len(QUESTIONS)} answers")
    score = sum(question.weight for question, answer in zip(QUESTIONS, answers, strict=True) if answer)
    if score >= 18:
        level = "L3"
    elif score >= 9:
        level = "L2"
    elif score >= 4:
        level = "L1"
    else:
        level = "L0"
    return {"level": level, "score": score, "explanation": LEVELS[level], "template": template_for_level(level)}


def template_for_level(level: str) -> str:
    templates = {
        "L0": _template("Retrieve and summarize one project SPEC section", "Read one file and produce questions", "No code changes; cite file paths."),
        "L1": _template("Implement one small validated utility", "Change one module and add one focused test", "Run pytest for the touched capability."),
        "L2": _template("Build a capability agent or eval", "Implement agent logic, tests, and metric reporting", "Use graph/schema patterns already in the repo."),
        "L3": _template("Design a governed agentic capability", "Author SPEC, architecture, eval gates, and rollout plan", "Justify human gates, cost model, and failure modes."),
    }
    if level not in templates:
        raise ValueError("level must be L0, L1, L2, or L3")
    return templates[level]


def run_interactive() -> dict[str, str | int]:
    answers = []
    for index, question in enumerate(QUESTIONS, start=1):
        raw = input(f"{index}. {question.prompt} [y/N] ").strip().lower()
        answers.append(raw in {"y", "yes"})
    return assess(answers)


def _template(goal: str, scope: str, constraints: str) -> str:
    return f"""briefing_id: BRIEF-YYYYMMDD-your-task
version: 1
status: APPROVED
author: agent-coach
agent: codex
goal_and_why:
  goal: {goal}
  why: Build proficiency with SASE workflows.
  business_value: Improves safe agent delegation.
what_and_success:
  scope: {scope}
  acceptance_criteria:
    - id: AC-01
      description: Outcome is verifiable and documented.
      testable: true
      test_command: pytest
all_needed_context:
  constraints:
    - {constraints}
implementation_tasks:
  - id: TASK-01
    description: Complete the scoped work.
    estimated_complexity: S
failure_modes:
  - Ambiguous scope should raise a CRP.
codex_instructions: Work on a branch, validate, and produce a Merge-Readiness Pack.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Assess Cap-02 AI proficiency using docs/playbooks/RAMP_L0_L3.md")
    parser.add_argument("--answers", help="Comma-separated y/n answers for non-interactive mode")
    args = parser.parse_args()
    if args.answers:
        values = [item.strip().lower() in {"y", "yes", "true", "1"} for item in args.answers.split(",")]
        result = assess(values)
    else:
        result = run_interactive()
    print(f"Level: {result['level']}")
    print(f"Score: {result['score']}")
    print(f"Explanation: {result['explanation']}")
    print("Recommended BriefingScript template:")
    print(result["template"])


if __name__ == "__main__":
    main()
