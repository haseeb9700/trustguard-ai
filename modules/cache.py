"""In-memory LRU + TTL caches for the TrustGuard pipeline.

Two process-local caches cut repeated work without an external service:

* ``embedding_cache`` — query text → embedding vector. Independent of the
  knowledge base, so it never needs invalidation.
* ``answer_cache`` — user query → full workflow result. Depends on the
  knowledge base, so ingesting or deleting a source clears it.

Everything is thread-safe. Set ``CACHE_ENABLED=false`` to disable entirely
(e.g. for load tests or debugging). Sizes and TTL are configurable via env:
``EMBED_CACHE_SIZE``, ``ANSWER_CACHE_SIZE``, ``ANSWER_CACHE_TTL`` (seconds).

The cache is per-process. On a multi-worker deployment each worker keeps its
own cache; point ``REDIS_URL`` at a shared store only if you later need
cross-worker sharing (not required for a single Render/uvicorn instance).
"""

from __future__ import annotations

import os
import threading
import time
from collections import OrderedDict
from typing import Any, Optional


def _env_bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


CACHE_ENABLED = _env_bool("CACHE_ENABLED", True)
EMBED_CACHE_SIZE = _env_int("EMBED_CACHE_SIZE", 512)
ANSWER_CACHE_SIZE = _env_int("ANSWER_CACHE_SIZE", 256)
ANSWER_CACHE_TTL = _env_int("ANSWER_CACHE_TTL", 3600)


class LRUCache:
    """A thread-safe LRU cache with optional per-entry TTL."""

    def __init__(self, maxsize: int = 256, ttl: Optional[int] = None):
        self.maxsize = max(1, maxsize)
        self.ttl = ttl
        self._data: "OrderedDict[str, tuple]" = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            item = self._data.get(key)
            if item is None:
                self.misses += 1
                return None

            value, expires = item
            if expires is not None and expires < time.time():
                del self._data[key]
                self.misses += 1
                return None

            self._data.move_to_end(key)
            self.hits += 1
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            expires = time.time() + self.ttl if self.ttl else None
            self._data[key] = (value, expires)
            self._data.move_to_end(key)
            while len(self._data) > self.maxsize:
                self._data.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def stats(self) -> dict:
        with self._lock:
            total = self.hits + self.misses
            return {
                "size": len(self._data),
                "maxsize": self.maxsize,
                "ttl_seconds": self.ttl,
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": round(self.hits / total, 4) if total else 0.0,
            }


embedding_cache = LRUCache(maxsize=EMBED_CACHE_SIZE)
answer_cache = LRUCache(maxsize=ANSWER_CACHE_SIZE, ttl=ANSWER_CACHE_TTL)


def _norm(text: str) -> str:
    """Normalize a key so trivial whitespace/case differences share a slot."""
    return " ".join(str(text).strip().lower().split())


def get_cached_embedding(text: str) -> Optional[list]:
    if not CACHE_ENABLED:
        return None
    return embedding_cache.get(_norm(text))


def set_cached_embedding(text: str, vector: list) -> None:
    if not CACHE_ENABLED:
        return
    embedding_cache.set(_norm(text), vector)


def get_cached_answer(query: str) -> Optional[dict]:
    if not CACHE_ENABLED:
        return None
    return answer_cache.get(_norm(query))


def set_cached_answer(query: str, result: dict) -> None:
    if not CACHE_ENABLED:
        return
    answer_cache.set(_norm(query), result)


def invalidate_answers() -> None:
    """Drop all cached answers. Call whenever the knowledge base changes."""
    answer_cache.clear()


def cache_stats() -> dict:
    """Return cache configuration and hit/miss statistics for observability."""
    return {
        "enabled": CACHE_ENABLED,
        "embedding_cache": embedding_cache.stats(),
        "answer_cache": answer_cache.stats(),
    }
