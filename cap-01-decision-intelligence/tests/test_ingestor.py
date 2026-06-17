from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from time import perf_counter

import pytest

from core.memory import Document

MODULE_PATH = Path(__file__).parents[1] / "tools" / "ingestor.py"
SPEC = importlib.util.spec_from_file_location("cap01_ingestor", MODULE_PATH)
assert SPEC and SPEC.loader
ingestor_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ingestor_module
SPEC.loader.exec_module(ingestor_module)

DocumentIngestor = ingestor_module.DocumentIngestor
IngestMetadata = ingestor_module.IngestMetadata


class FakeSemanticMemory:
    def __init__(self) -> None:
        self.documents: list[Document] = []

    def index(self, documents: list[Document]) -> None:
        self.documents.extend(documents)

    def search(self, query: str, k: int = 10, filters=None):
        return [document for document in self.documents if query.lower() in document.content.lower()][:k]


def test_ingest_txt_writes_document_with_metadata(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    path = tmp_path / "strategy.txt"
    path.write_text("Supply chain risk is elevated.", encoding="utf-8")
    memory = FakeSemanticMemory()

    doc_id = DocumentIngestor(memory).ingest_file(
        path,
        metadata=IngestMetadata(
            title="Strategy",
            author="Ops",
            date="2026-06-01",
            doc_type="strategy",
            access_tier="restricted",
            source="fixture",
        ),
    )

    assert doc_id == "strategy"
    assert memory.documents[0].access_tier == "restricted"
    assert memory.documents[0].metadata["title"] == "Strategy"
    assert memory.documents[0].metadata["embedding_model"] == "text-embedding-3-large"


def test_ingest_html_strips_tags(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    path = tmp_path / "page.html"
    path.write_text("<html><body><h1>Decision</h1><p>Evidence base</p></body></html>", encoding="utf-8")
    memory = FakeSemanticMemory()

    DocumentIngestor(memory).ingest_file(path)

    assert memory.documents[0].content == "Decision Evidence base"


def test_unsupported_format_is_rejected(tmp_path) -> None:
    path = tmp_path / "image.png"
    path.write_text("not supported", encoding="utf-8")

    with pytest.raises(ValueError):
        DocumentIngestor(FakeSemanticMemory()).ingest_file(path)


def test_ingest_directory_indexes_100_documents_under_30s(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    for index in range(100):
        (tmp_path / f"doc-{index}.txt").write_text(
            f"document {index} supply chain evidence",
            encoding="utf-8",
        )
    memory = FakeSemanticMemory()

    start = perf_counter()
    doc_ids = DocumentIngestor(memory).ingest_directory(tmp_path)
    elapsed = perf_counter() - start

    assert len(doc_ids) == 100
    assert len(memory.documents) == 100
    assert elapsed < 30


def test_search_returns_indexed_result_under_2s(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    path = tmp_path / "risk.md"
    path.write_text("supplier concentration creates supply risk", encoding="utf-8")
    memory = FakeSemanticMemory()
    DocumentIngestor(memory).ingest_file(path)

    start = perf_counter()
    results = memory.search("supplier", k=1)
    elapsed = perf_counter() - start

    assert results[0].doc_id == "risk"
    assert elapsed < 2
