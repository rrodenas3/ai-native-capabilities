from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("cap02_library_test", ROOT / "memory" / "briefing_library.py")
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def test_store_and_search_similar_briefings() -> None:
    library = module.BriefingLibrary()
    supply = module.minimal_valid_briefing(
        briefing_id="BRIEF-supply",
        goal_and_why={
            "goal": "Add supply chain risk dashboard",
            "why": "Track supplier risk",
            "business_value": "Improves resilience",
        },
    )
    commerce = module.minimal_valid_briefing(
        briefing_id="BRIEF-commerce",
        goal_and_why={
            "goal": "Add commerce checkout recommendations",
            "why": "Improve conversion",
            "business_value": "Increases revenue",
        },
    )

    library.store_briefing(supply, "DONE", "shipped")
    library.store_briefing(commerce, "ARCHIVED", "pattern retained")
    results = library.search_similar("supplier risk dashboard", k=1)

    assert results[0].briefing.briefing_id == "BRIEF-supply"
    assert results[0].similarity > 0
    assert library.briefing_reuse_rate == 1.0
