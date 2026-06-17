"""CLI demo for Cap-01 Decision Intelligence."""

from __future__ import annotations

import argparse
import importlib.util
import os
import re
import sys
from pathlib import Path
from uuid import uuid4

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.schemas import CapabilityID, DocumentChunk, RetrievalResult  # noqa: E402
from core.utils.settings import get_settings  # noqa: E402

ROOT = Path(__file__).resolve().parent
CORPUS_DIR = ROOT / "tests" / "fixtures" / "corpus"


class DemoCorpusRetriever:
    """Small local retriever for the committed demo corpus."""

    def __init__(self, corpus_dir: Path = CORPUS_DIR) -> None:
        self.documents = [_load_document(path) for path in sorted(corpus_dir.glob("*.md"))]

    def hybrid_search(self, query: str, k: int = 10, filters=None, access_tier: str = "internal") -> list[RetrievalResult]:
        allowed = {"public"} if access_tier == "public" else {"public", "internal"}
        if access_tier == "restricted":
            allowed.add("restricted")
        query_terms = _terms(query)
        scored = []
        for metadata, content in self.documents:
            if metadata.get("access_tier", "internal") not in allowed:
                continue
            haystack = _terms(content + " " + " ".join(metadata.values()))
            overlap = len(query_terms & haystack)
            score = overlap + (0.15 if metadata.get("contradiction_pair") else 0.0)
            if score > 0:
                scored.append((score, metadata, content))
        scored.sort(key=lambda item: item[0], reverse=True)
        results: list[RetrievalResult] = []
        for rank, (score, metadata, content) in enumerate(scored[:k], start=1):
            combined = round(min(0.55 + score / 20, 0.98), 3)
            results.append(
                RetrievalResult(
                    chunk=DocumentChunk(
                        capability=CapabilityID.DECISION_INTELLIGENCE,
                        doc_id=metadata["doc_id"],
                        chunk_index=0,
                        content=_body_excerpt(content),
                        metadata=metadata,
                        access_tier=metadata.get("access_tier", "internal"),
                    ),
                    semantic_score=combined,
                    lexical_score=score,
                    combined_score=combined,
                    rank=rank,
                )
            )
        return results


class DemoBriefMemory:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def store_brief(self, brief, session_id: str, run_id: str, **kwargs) -> str:
        event_id = f"demo-memory-{len(self.events) + 1}"
        self.events.append({"event_id": event_id, "brief": brief, "session_id": session_id, "run_id": run_id, **kwargs})
        return event_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a strategic query through the Cap-01 decision brief graph.")
    parser.add_argument("--query", help="Strategic question to brief.")
    parser.add_argument("--access-tier", choices=["public", "internal", "restricted"], default="internal")
    parser.add_argument("--auto-approve", action="store_true", help="Approve the human gate without prompting.")
    args = parser.parse_args()

    os.environ.setdefault("LLM_MODE", "mock")
    if args.auto_approve:
        os.environ["EVAL_MODE"] = "ci"
        os.environ["HUMAN_GATE_MOCK_APPROVED"] = "true"
    get_settings.cache_clear()

    console = Console()
    query = args.query or console.input("[bold]Strategic query:[/] ").strip()
    if not query:
        query = "What are our three biggest supply chain risks entering Q3?"

    graph_module = _load_graph_module()
    graph = graph_module.build_graph(
        DemoCorpusRetriever(),
        checkpointer=MemorySaver(),
        episodic_memory=DemoBriefMemory(),
    )
    run_id = f"demo-{uuid4()}"
    config = {"configurable": {"thread_id": run_id}}
    state = graph_module.initial_state(query, run_id=run_id, session_id="demo-session")
    state["access_tier"] = args.access_tier
    output = graph.invoke(state, config=config)

    if "__interrupt__" in output:
        approved = args.auto_approve or console.input("[bold]Approve brief for memory storage? [y/N][/] ").strip().lower() == "y"
        output = graph.invoke(
            Command(
                resume={
                    "status": "approved" if approved else "rejected",
                    "approver_id": "cli-demo",
                    "rationale": "CLI demo decision",
                }
            ),
            config=config,
        )

    console.print(format_brief(output))


def format_brief(output: dict) -> Panel:
    brief = output.get("brief")
    summary = getattr(brief, "executive_summary", output.get("executive_summary", "No summary produced."))
    table = Table.grid(padding=(0, 1))
    table.add_column(style="bold")
    table.add_column()
    table.add_row("Summary", summary)
    table.add_row("Confidence", f"{float(output.get('overall_confidence', 0.0)):.2f}")
    table.add_row("Cost", f"${float(output.get('cost_usd_total', 0.0)):.6f}")
    table.add_row("Tokens", str(output.get("cost_tokens", 0)))
    table.add_row("Human gate", str(output.get("human_gate_status", "pending")))
    findings = getattr(brief, "key_findings", output.get("key_findings", [])) or []
    for index, finding in enumerate(findings[:3], start=1):
        citation = finding.citations[0] if getattr(finding, "citations", None) else None
        source = f" [{citation.source_title}]" if citation is not None else ""
        table.add_row(f"Finding {index}", f"{finding.claim}{source}")
    return Panel(table, title="Cap-01 Board-Ready Brief", expand=False)


def _load_graph_module():
    module_path = ROOT / "agents" / "graph.py"
    spec = importlib.util.spec_from_file_location("cap01_demo_graph", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load graph module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_document(path: Path) -> tuple[dict[str, str], str]:
    raw = path.read_text(encoding="utf-8")
    metadata: dict[str, str] = {}
    body = raw
    if raw.startswith("---"):
        _start, meta_text, body = raw.split("---", 2)
        for line in meta_text.splitlines():
            key, sep, value = line.partition(":")
            if sep:
                metadata[key.strip()] = value.strip()
    metadata.setdefault("doc_id", path.stem)
    metadata.setdefault("title", path.stem)
    metadata.setdefault("access_tier", "internal")
    return metadata, body.strip()


def _body_excerpt(content: str) -> str:
    return " ".join(content.split()[:220])


def _terms(text: str) -> set[str]:
    stopwords = {"and", "are", "for", "the", "our", "what", "with", "into", "from"}
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 3 and token not in stopwords}


if __name__ == "__main__":
    main()
