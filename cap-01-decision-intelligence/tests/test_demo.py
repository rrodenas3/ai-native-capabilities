from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from rich.panel import Panel

MODULE_PATH = Path(__file__).parents[1] / "demo.py"
SPEC = importlib.util.spec_from_file_location("cap01_demo", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)

DemoCorpusRetriever = module.DemoCorpusRetriever
format_brief = module.format_brief


def test_demo_corpus_retriever_returns_ranked_results() -> None:
    retriever = DemoCorpusRetriever()

    results = retriever.hybrid_search("supply chain supplier concentration risk", k=3, access_tier="internal")

    assert len(results) == 3
    assert [result.rank for result in results] == [1, 2, 3]
    assert results[0].combined_score >= results[-1].combined_score
    assert results[0].chunk.metadata["title"]


def test_format_brief_returns_rich_panel() -> None:
    panel = format_brief(
        {
            "executive_summary": "Summary",
            "overall_confidence": 0.82,
            "cost_usd_total": 0.01,
            "cost_tokens": 123,
            "human_gate_status": "approved",
            "key_findings": [],
        }
    )

    assert isinstance(panel, Panel)
