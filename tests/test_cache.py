"""Unit tests for the pipeline cache (modules/cache.py).

Pure and dependency-free: covers LRU eviction, TTL expiry, key
normalization, invalidation, and the module-level helper functions.
"""

import time

import pytest

from modules import cache
from modules.cache import LRUCache

# --- LRUCache core ---------------------------------------------------------


def test_get_miss_returns_none_and_counts():
    c = LRUCache(maxsize=2)
    assert c.get("absent") is None
    assert c.misses == 1
    assert c.hits == 0


def test_set_then_get_hit():
    c = LRUCache(maxsize=2)
    c.set("k", [1, 2, 3])
    assert c.get("k") == [1, 2, 3]
    assert c.hits == 1


def test_lru_evicts_least_recently_used():
    c = LRUCache(maxsize=2)
    c.set("a", 1)
    c.set("b", 2)
    c.get("a")  # touch "a" so "b" becomes LRU
    c.set("c", 3)  # evicts "b"
    assert c.get("a") == 1
    assert c.get("c") == 3
    assert c.get("b") is None


def test_ttl_expiry():
    c = LRUCache(maxsize=4, ttl=1)
    c.set("k", "v")
    assert c.get("k") == "v"
    # Force expiry without sleeping a full second.
    c._data["k"] = ("v", time.time() - 5)
    assert c.get("k") is None


def test_clear_empties_cache():
    c = LRUCache(maxsize=2)
    c.set("a", 1)
    c.clear()
    assert c.get("a") is None
    assert c.stats()["size"] == 0


def test_stats_hit_rate():
    c = LRUCache(maxsize=2)
    c.set("a", 1)
    c.get("a")  # hit
    c.get("b")  # miss
    stats = c.stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["hit_rate"] == 0.5


# --- module helpers --------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_caches():
    cache.embedding_cache.clear()
    cache.answer_cache.clear()
    yield
    cache.embedding_cache.clear()
    cache.answer_cache.clear()


def test_key_normalization_collapses_whitespace_and_case():
    cache.set_cached_answer("  What IS   Basel III? ", {"answer": "x"})
    assert cache.get_cached_answer("what is basel iii?") == {"answer": "x"}


def test_embedding_roundtrip():
    cache.set_cached_embedding("hello world", [0.1, 0.2])
    assert cache.get_cached_embedding("Hello World") == [0.1, 0.2]


def test_invalidate_answers_clears_answers_but_not_embeddings():
    cache.set_cached_answer("q", {"answer": "a"})
    cache.set_cached_embedding("q", [0.5])
    cache.invalidate_answers()
    assert cache.get_cached_answer("q") is None
    assert cache.get_cached_embedding("q") == [0.5]


def test_cache_stats_shape():
    stats = cache.cache_stats()
    assert "enabled" in stats
    assert "embedding_cache" in stats
    assert "answer_cache" in stats


def test_disabled_cache_is_a_noop(monkeypatch):
    monkeypatch.setattr(cache, "CACHE_ENABLED", False)
    cache.set_cached_answer("q", {"answer": "a"})
    assert cache.get_cached_answer("q") is None
