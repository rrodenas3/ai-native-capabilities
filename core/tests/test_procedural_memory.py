from __future__ import annotations

import json
import os
import time

import fakeredis
import pytest

from core.memory import ProceduralMemory


def make_memory(default_ttl: int = 60) -> ProceduralMemory:
    return ProceduralMemory(redis_client=fakeredis.FakeRedis(), default_ttl=default_ttl)


def test_store_and_get_pattern_as_json_payload() -> None:
    memory = make_memory()

    memory.store_pattern("routing:brief", {"agent": "retrieval", "confidence": 0.91})

    assert memory.get_pattern("routing:brief") == {
        "pattern": {"agent": "retrieval", "confidence": 0.91},
        "usage_count": 0,
    }


def test_pattern_expires_after_ttl() -> None:
    memory = make_memory()

    memory.store_pattern("temporary", {"value": True}, ttl=1)
    time.sleep(1.1)

    assert memory.get_pattern("temporary") is None


def test_default_ttl_is_applied() -> None:
    client = fakeredis.FakeRedis()
    memory = ProceduralMemory(redis_client=client, default_ttl=123)

    memory.store_pattern("ttl-default", {"value": True})

    assert 0 < client.ttl("procedural:ttl-default") <= 123


def test_increment_usage_tracks_count_alongside_pattern() -> None:
    memory = make_memory()
    memory.store_pattern("repeat", {"agent": "analysis"})

    memory.increment_usage("repeat")
    memory.increment_usage("repeat")

    assert memory.get_pattern("repeat") == {
        "pattern": {"agent": "analysis"},
        "usage_count": 2,
    }


def test_increment_usage_creates_empty_pattern_when_missing() -> None:
    memory = make_memory()

    memory.increment_usage("new")

    assert memory.get_pattern("new") == {"pattern": {}, "usage_count": 1}


def test_empty_key_is_rejected() -> None:
    memory = make_memory()

    with pytest.raises(ValueError):
        memory.store_pattern("", {"invalid": True})


def test_patterns_are_json_serialized() -> None:
    client = fakeredis.FakeRedis()
    memory = ProceduralMemory(redis_client=client)

    memory.store_pattern("json", {"nested": {"ok": True}})
    raw = client.get("procedural:json")

    assert raw is not None
    assert json.loads(raw) == {"pattern": {"nested": {"ok": True}}, "usage_count": 0}


def test_default_connection_uses_redis_url_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/15")

    memory = ProceduralMemory(redis_client=fakeredis.FakeRedis())

    assert os.environ["REDIS_URL"] == "redis://localhost:6379/15"
    assert memory.namespace == "procedural"

