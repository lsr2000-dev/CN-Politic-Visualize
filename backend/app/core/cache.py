"""Two-tier cache: process LRU + Redis.

Key design (see docs/performance.md):
    polvis:{dataset}:snap:{date}:{scope_hash}
    polvis:{dataset}:career:{officer_id}:{from}:{to}
    polvis:{dataset}:seat:{region}:{seat_key}
    polvis:{dataset}:meta
Redis 故障时自动降级到进程内缓存，接口不做硬依赖。
"""

from __future__ import annotations

import json
import logging
import time
from collections import OrderedDict
from typing import Any

import redis

from .config import Settings

log = logging.getLogger(__name__)


class MemoryLRU:
    def __init__(self, max_items: int = 512, ttl: int = 60) -> None:
        self.max_items = max_items
        self.ttl = ttl
        self._store: OrderedDict[str, tuple[float, str]] = OrderedDict()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> str | None:
        item = self._store.get(key)
        if item is None:
            self.misses += 1
            return None
        expires_at, payload = item
        if expires_at < time.monotonic():
            self._store.pop(key, None)
            self.misses += 1
            return None
        self._store.move_to_end(key)
        self.hits += 1
        return payload

    def set(self, key: str, payload: str, ttl: int | None = None) -> None:
        self._store[key] = (time.monotonic() + (ttl or self.ttl), payload)
        self._store.move_to_end(key)
        while len(self._store) > self.max_items:
            self._store.popitem(last=False)

    def clear(self) -> None:
        self._store.clear()


class CacheLayer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.memory = MemoryLRU(settings.cache_max_items, settings.memory_cache_ttl_seconds)
        self.redis: redis.Redis | None = None
        self.redis_disabled_until = 0.0
        if settings.redis_url:
            try:
                self.redis = redis.Redis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=0.6,
                    socket_timeout=0.6,
                )
                self.redis.ping()
                log.info("redis connected: %s", settings.redis_url)
            except Exception as exc:  # pragma: no cover - depends on environment
                log.warning("redis unavailable, falling back to memory cache: %s", exc)
                self.redis = None

    def get(self, key: str) -> str | None:
        cached = self.memory.get(key)
        if cached is not None:
            return cached
        if self.redis is not None and time.monotonic() > self.redis_disabled_until:
            try:
                value = self.redis.get(key)
                if value is not None:
                    self.memory.set(key, value)
                return value
            except Exception as exc:  # pragma: no cover
                log.warning("redis get failed, disabling for 30s: %s", exc)
                self.redis_disabled_until = time.monotonic() + 30
        return None

    def set(self, key: str, payload: str, ttl: int | None = None) -> None:
        ttl = ttl or self.settings.cache_ttl_seconds
        self.memory.set(key, payload, ttl=min(ttl, self.settings.memory_cache_ttl_seconds))
        if self.redis is not None and time.monotonic() > self.redis_disabled_until:
            try:
                # 抖动 0~120s，避免同一批 key 同时过期造成惊群
                jitter = int.from_bytes(key.encode()[-2:], "big") % 120
                self.redis.set(key, payload, ex=ttl + jitter)
            except Exception as exc:  # pragma: no cover
                log.warning("redis set failed: %s", exc)
                self.redis_disabled_until = time.monotonic() + 30

    def stats(self) -> dict[str, Any]:
        return {
            "layer": "memory+redis" if self.redis else "memory",
            "items": len(self.memory._store),
            "hits": self.memory.hits,
            "misses": self.memory.misses,
            "hit_rate": round(
                self.memory.hits / max(1, self.memory.hits + self.memory.misses), 4
            ),
        }


def dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str, separators=(",", ":"))
