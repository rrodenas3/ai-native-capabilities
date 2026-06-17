from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

CORPUS_DIR = Path(__file__).parent / "fixtures" / "corpus"


def test_seed_corpus_contains_100_documents_with_required_metadata() -> None:
    documents = sorted(CORPUS_DIR.glob("*.md"))

    assert len(documents) == 100
    tiers: Counter[str] = Counter()
    contradiction_pairs: defaultdict[str, int] = defaultdict(int)
    for path in documents:
        metadata, body = _parse_frontmatter(path)
        assert {"doc_id", "title", "domain", "doc_type", "access_tier", "date"} <= set(metadata)
        assert 300 <= len(body.split()) <= 800
        tiers[metadata["access_tier"]] += 1
        if "contradiction_pair" in metadata:
            contradiction_pairs[metadata["contradiction_pair"]] += 1

    assert all(tiers[tier] >= 10 for tier in ("public", "internal", "restricted"))
    assert len(contradiction_pairs) >= 5
    assert all(count == 2 for count in contradiction_pairs.values())


def _parse_frontmatter(path: Path) -> tuple[dict[str, str], str]:
    raw = path.read_text(encoding="utf-8")
    assert raw.startswith("---")
    _start, meta_text, body = raw.split("---", 2)
    metadata = {}
    for line in meta_text.splitlines():
        key, sep, value = line.partition(":")
        if sep:
            metadata[key.strip()] = value.strip()
    return metadata, body
