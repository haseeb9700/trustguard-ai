"""Tests for the reranked ranker, BGE instruction plumbing, and comparison report.

The production retrieval path is embedding recall followed by cross-encoder
reranking, but both stages need heavyweight models that cannot run in CI. So
the models are stubbed with deterministic fakes and the tests assert on the
*wiring* — that the pool is sized correctly, that the reranker's ordering is
respected, that the tail below the pool is preserved, and that the instruction
prefix reaches the query and only the query. Those are exactly the things that
break silently and would otherwise make the benchmark quietly wrong.
"""

import math

import numpy as np

import eval.run_retrieval_eval as rre
from eval.retrieval_metrics import format_comparison_report

# Each chunk is placed at a known angle from the query on the unit circle, so
# cosine similarity is exactly cos(angle) and the expected ranking follows by
# construction. Encoding term *counts* would not work: cosine normalises away
# magnitude, so "contains the word more often" does not imply "ranks higher".
_ANGLES = {
    "query text": 0.0,
    "nearest chunk": 0.1,
    "second chunk": 0.2,
    "third chunk": 0.3,
    "far chunk": 1.5,
}
_UNKNOWN_ANGLE = 1.5


class _StubModel:
    """Encodes known text to a unit 2-vector at a fixed angle."""

    def __init__(self):
        self.encoded = []

    def encode(self, texts):
        self.encoded.extend(texts)
        vectors = [
            [
                math.cos(_ANGLES.get(t, _UNKNOWN_ANGLE)),
                math.sin(_ANGLES.get(t, _UNKNOWN_ANGLE)),
            ]
            for t in texts
        ]
        # ndarray, not list — callers do .tolist(), so the fake must match the
        # real SentenceTransformer return type or the test proves nothing.
        return np.array(vectors)


def _corpus():
    return [
        {"id": "c0", "text": "nearest chunk"},
        {"id": "c1", "text": "second chunk"},
        {"id": "c2", "text": "third chunk"},
        {"id": "c3", "text": "far chunk"},
    ]


def _patch_model(monkeypatch, model):
    # Patch the shared loader every caller now routes through. It accepts an
    # optional model-name override, so the stub must take one too.
    monkeypatch.setattr(
        "modules.embeddings.get_embedding_model",
        lambda name=None: model,
        raising=False,
    )


# --- embedding ranker ------------------------------------------------------


def test_embedding_ranker_orders_by_similarity(monkeypatch):
    _patch_model(monkeypatch, _StubModel())
    ranked = rre.embedding_ranker(_corpus())("query text")
    assert ranked[0] == "c0"
    assert ranked[-1] == "c3"


def test_query_instruction_prefixes_query_only(monkeypatch):
    model = _StubModel()
    _patch_model(monkeypatch, model)

    rank = rre.embedding_ranker(_corpus(), instruction=rre.BGE_QUERY_INSTRUCTION)
    corpus_texts = list(model.encoded)  # captured at build time
    rank("what matches?")

    # Passages must stay bare — prefixing them too would defeat the asymmetry.
    assert not any(t.startswith(rre.BGE_QUERY_INSTRUCTION) for t in corpus_texts)
    # ...and the query must carry the instruction.
    assert model.encoded[-1] == rre.BGE_QUERY_INSTRUCTION + "what matches?"


def test_no_instruction_by_default(monkeypatch):
    model = _StubModel()
    _patch_model(monkeypatch, model)
    rre.embedding_ranker(_corpus())("plain query")
    assert model.encoded[-1] == "plain query"


# --- reranked ranker -------------------------------------------------------


def test_reranked_ranker_applies_reranker_over_pool(monkeypatch):
    _patch_model(monkeypatch, _StubModel())

    def fake_rerank(query, contexts, top_k, mmr_lambda=None):
        # Reverse the pool, so a passive pass-through cannot fake success.
        return list(reversed(contexts))[:top_k]

    monkeypatch.setattr("modules.reranker.rerank_contexts", fake_rerank)

    ranked = rre.reranked_ranker(_corpus(), pool_size=2)("query text")

    # Pool was [c0, c1] by embedding score; the reranker flipped it.
    assert ranked[:2] == ["c1", "c0"]
    # Everything below the pool keeps its embedding order and is preserved.
    assert ranked[2:] == ["c2", "c3"]
    assert sorted(ranked) == ["c0", "c1", "c2", "c3"]


def test_reranked_ranker_passes_mmr_lambda_through(monkeypatch):
    # The eval must be able to score the MMR variant; if the flag silently
    # stopped reaching the reranker, a sweep would report identical numbers
    # for every lambda and look like "MMR does nothing".
    _patch_model(monkeypatch, _StubModel())
    seen = {}

    def fake_rerank(query, contexts, top_k, mmr_lambda=None):
        seen["lambda"] = mmr_lambda
        return contexts[:top_k]

    monkeypatch.setattr("modules.reranker.rerank_contexts", fake_rerank)
    rre.reranked_ranker(_corpus(), pool_size=2, mmr_lambda=0.6)("query text")
    assert seen["lambda"] == 0.6


def test_reranked_ranker_pool_matches_production_default():
    # If these drift apart the eval silently measures a different pipeline.
    from agents.retrieval_agent import CANDIDATE_POOL_SIZE

    assert rre.CANDIDATE_POOL_SIZE == CANDIDATE_POOL_SIZE


def test_build_ranker_knows_every_compare_ranker():
    # --compare iterates COMPARE_ORDER, so an unrecognised name there would
    # only surface as a crash partway through a long benchmark run.
    known = {
        "lexical",
        "bm25",
        "embedding",
        "hybrid",
        "reranked",
        "hybrid_reranked",
        "oracle",
    }
    for name in rre.COMPARE_ORDER:
        assert name in known


# --- comparison report -----------------------------------------------------


def _metrics(mrr, ndcg):
    return {
        "queries": 3,
        "mrr": mrr,
        "at_k": {1: {"hit_rate": 1.0, "recall": 1.0, "precision": 1.0, "ndcg": ndcg}},
    }


def test_comparison_report_shows_deltas():
    report = format_comparison_report(
        [("lexical", _metrics(0.5, 0.5)), ("embedding", _metrics(0.8, 0.8))],
        ks=[1],
        corpus_size=42,
    )
    assert "lexical" in report and "embedding" in report
    assert "+0.300" in report  # improvement over the previous stage
    assert "42 chunks" in report
    assert "off" in report  # instruction defaults to off


def test_comparison_report_notes_instruction():
    report = format_comparison_report(
        [("embedding", _metrics(0.8, 0.8))], ks=[1], instruction=True
    )
    assert "on" in report


def test_comparison_report_handles_no_runs():
    assert "No runs" in format_comparison_report([])
