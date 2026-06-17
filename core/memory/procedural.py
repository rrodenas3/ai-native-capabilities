"""Procedural memory backed by Redis."""

from __future__ import annotations

import json
import os
from typing import Any, Protocol

import redis
from redis.exceptions import RedisError


class RedisClient(Protocol):
    def set(self, name: str, value: str, ex: int | None = None) -> Any: ...
    def get(self, name: str) -> bytes | str | None: ...
    def ttl(self, name: str) -> int: ...
    def config_set(self, name: str, value: str) -> Any: ...


class ProceduralMemory:
    """Learned patterns and routing rules stored as JSON in Redis."""

    DEFAULT_TTL_SECONDS = 7 * 24 * 60 * 60

    def __init__(
        self,
        redis_client: RedisClient | None = None,
        *,
        redis_url: str | None = None,
        namespace: str = "procedural",
        default_ttl: int = DEFAULT_TTL_SECONDS,
    ) -> None:
        self.namespace = namespace
        self.default_ttl = default_ttl
        self.client = redis_client or redis.Redis.from_url(
            redis_url or os.getenv("REDIS_URL", "redis://localhost:6379"),
            decode_responses=False,
        )
        self._configure_lru_policy()

    def store_pattern(self, key: str, pattern: dict[str, Any], ttl: int | None = None) -> None:
        payload = self._payload(pattern=pattern, usage_count=self._usage_count(key))
        self.client.set(self._key(key), json.dumps(payload), ex=ttl or self.default_ttl)

    def get_pattern(self, key: str) -> dict[str, Any] | None:
        raw = self.client.get(self._key(key))
        if raw is None:
            return None
        return json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)

    def increment_usage(self, key: str) -> None:
        existing = self.get_pattern(key)
        if existing is None:
            self.client.set(
                self._key(key),
                json.dumps(self._payload(pattern={}, usage_count=1)),
                ex=self.default_ttl,
            )
            return

        ttl = self.client.ttl(self._key(key))
        usage_count = int(existing.get("usage_count", 0)) + 1
        payload = self._payload(pattern=existing.get("pattern", {}), usage_count=usage_count)
        self.client.set(self._key(key), json.dumps(payload), ex=ttl if ttl > 0 else self.default_ttl)

    def _usage_count(self, key: str) -> int:
        existing = self.get_pattern(key)
        if existing is None:
            return 0
        return int(existing.get("usage_count", 0))

    def _key(self, key: str) -> str:
        if not key:
            raise ValueError("procedural memory key must not be empty")
        return f"{self.namespace}:{key}"

    def _configure_lru_policy(self) -> None:
        try:
            self.client.config_set("maxmemory-policy", "allkeys-lru")
        except RedisError:
            # Hosted Redis and fakeredis-compatible clients may reject CONFIG.
            # Runtime correctness does not depend on this command succeeding.
            return

    @staticmethod
    def _payload(pattern: dict[str, Any], usage_count: int) -> dict[str, Any]:
        return {"pattern": pattern, "usage_count": usage_count}

