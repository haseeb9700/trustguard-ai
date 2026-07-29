"""Tests that queries and passages can never be embedded by different models.

Dense retrieval compares a query vector against stored passage vectors. If the
two came from different models the comparison is meaningless — cosine
similarity still returns a number, so nothing raises and nothing logs; search
quality just quietly collapses. These tests pin the invariants that make that
state unreachable.
"""

import pytest

from modules import cache, embeddings


@pytest.fixture(autouse=True)
def _clear_model_cache():
    embeddings._model = None
    embeddings._loaded_name = None
    yield
    embeddings._model = None
    embeddings._loaded_name = None


def test_query_and_ingest_paths_share_one_loader():
    # The failure this prevents: each module holding its own hardcoded model
    # name, one gets updated, the other does not, and retrieval silently breaks.
    from modules import rag_pipeline, url_ingestor

    assert (
        rag_pipeline.get_embedding_model
        is url_ingestor.get_embedding_model
        is embeddings.get_embedding_model
    )


def test_only_the_shared_module_names_a_model():
    # Anywhere else naming a model is a second source of truth waiting to drift
    # out of sync with the one that embedded the stored passages.
    # Matches the identifier form ("BAAI/bge-..."), not prose mentioning it.
    import pathlib
    import re

    root = pathlib.Path(__file__).resolve().parent.parent
    pattern = re.compile(r"""["']BAAI/[\w.-]+["']""")

    offenders = []
    for folder in ("modules", "agents", "scripts"):
        for path in (root / folder).glob("*.py"):
            if path.name == "embeddings.py":
                continue
            if pattern.search(path.read_text()):
                offenders.append(f"{folder}/{path.name}")

    assert not offenders, (
        f"embedding model hardcoded outside modules/embeddings.py: {offenders}"
    )


def test_model_name_is_env_overridable(monkeypatch):
    monkeypatch.setenv("TRUSTGUARD_EMBEDDING_MODEL", "some/other-model")
    assert embeddings.embedding_model_name() == "some/other-model"


def test_default_model_when_env_unset(monkeypatch):
    monkeypatch.delenv("TRUSTGUARD_EMBEDDING_MODEL", raising=False)
    assert embeddings.embedding_model_name() == embeddings.DEFAULT_EMBEDDING_MODEL


# --- cache namespacing -----------------------------------------------------


def test_cached_embedding_is_namespaced_by_model(monkeypatch):
    # The bug this prevents: switching models and being served the previous
    # model's vector, which has the wrong meaning and possibly the wrong width.
    monkeypatch.setattr(cache, "CACHE_ENABLED", True)
    cache.embedding_cache.clear() if hasattr(cache.embedding_cache, "clear") else None

    monkeypatch.setenv("TRUSTGUARD_EMBEDDING_MODEL", "model/small")
    cache.set_cached_embedding("a query", [0.1, 0.2])
    assert cache.get_cached_embedding("a query") == [0.1, 0.2]

    monkeypatch.setenv("TRUSTGUARD_EMBEDDING_MODEL", "model/large")
    assert cache.get_cached_embedding("a query") is None, (
        "a different model must miss the cache, not inherit stale vectors"
    )

    cache.set_cached_embedding("a query", [0.3, 0.4, 0.5])
    assert cache.get_cached_embedding("a query") == [0.3, 0.4, 0.5]

    # ...and the original model's entry is untouched.
    monkeypatch.setenv("TRUSTGUARD_EMBEDDING_MODEL", "model/small")
    assert cache.get_cached_embedding("a query") == [0.1, 0.2]


def test_cache_key_still_normalises_text(monkeypatch):
    monkeypatch.setattr(cache, "CACHE_ENABLED", True)
    monkeypatch.setenv("TRUSTGUARD_EMBEDDING_MODEL", "model/small")
    cache.set_cached_embedding("  Some   Query  ", [1.0])
    assert cache.get_cached_embedding("some query") == [1.0]
