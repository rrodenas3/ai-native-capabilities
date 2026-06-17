"""Minimal CLI helpers for expert review queue workflows."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cap05_loader import load_attr  # noqa: E402

ExpertReviewGate = load_attr("cap05_expert_gate_cli", "agents/expert_gate.py", "ExpertReviewGate")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--obligations", type=Path, required=True)
    parser.add_argument("--reviewer", default="legal-reviewer")
    args = parser.parse_args()
    gate = ExpertReviewGate()
    obligations = json.loads(args.obligations.read_text(encoding="utf-8"))
    reviewed = []
    for obligation in obligations:
        gate.queue_for_review(obligation)
        reviewed.append(gate.submit_review(obligation["id"], "CONFIRM", args.reviewer))
    print(json.dumps({"reviewed": len(reviewed), "pending": len(gate.get_pending())}, indent=2))


if __name__ == "__main__":
    main()
