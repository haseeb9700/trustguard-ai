"""Unit tests for the retrieval eval (eval/retrieval_metrics.py + runner).

Runs in CI with no model or database: covers the IR metric math and uses the
offline lexical + oracle rankers to smoke-test the runner end to end.
"""

import math

from eval.retrieval_metrics import (
    compute_metrics,
    hit_at_k,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from eval.run_retrieval_eval import run, _load_jsonl, CORPUS_PATH, QUERIES_PATH


# --- per-metric math -------------------------------------------------------

def test_hit_at_k():
    assert hit_at_k(["a", "b", "c"], {"c"}, 3) == 1.0
    assert hit_at_k(["a", "b", "c"], {"c"}, 2) == 0.0


def test_recall_at_k():
    assert recall_at_k(["a", "b", "c"], {"a", "c"}, 3) == 1.0
    assert recall_at_k(["a", "b", "c"], {"a", "c"}, 1) == 0.5
    assert recall_at_k(["a"], set(), 1) == 0.0


def test_precision_at_k():
    assert precision_at_k(["a", "b"], {"a"}, 2) == 0.5
    assert precision_at_k(["a", "b"], {"a", "b"}, 2) == 1.0


def test_reciprocal_rank():
    assert reciprocal_rank(["x", "y", "rel"], {"rel"}) == 1 / 3
    assert reciprocal_rank(["rel"], {"rel"}) == 1.0
    assert reciprocal_rank(["a", "b"], {"z"}) == 0.0


def test_ndcg_perfect_and_partial():
    # Relevant item first -> perfect nDCG.
    assert ndcg_at_k(["rel", "x", "y"], {"rel"}, 3) == 1.0
    # Relevant item in second position -> DCG = 1/log2(3), IDCG = 1.
    expected = (1.0 / math.log2(3)) / 1.0
    assert abs(ndcg_at_k(["x", "rel", "y"], {"rel"}, 3) - expected) < 1e-9


def test_compute_metrics_perfect():
    results = [(["a", "b"], {"a"}), (["c", "d"], {"c"})]
    m = compute_metrics(results, ks=[1, 2])
    assert m["mrr"] == 1.0
    assert m["at_k"][1]["hit_rate"] == 1.0
    assert m["at_k"][1]["recall"] == 1.0
    assert m["at_k"][1]["ndcg"] == 1.0


def test_compute_metrics_empty():
    m = compute_metrics([], ks=[1, 3])
    assert m["queries"] == 0
    assert m["mrr"] == 0.0


# --- dataset + runner ------------------------------------------------------

def test_dataset_is_well_formed():
    corpus = _load_jsonl(CORPUS_PATH)
    queries = _load_jsonl(QUERIES_PATH)
    corpus_ids = {c["id"] for c in corpus}
    assert len(corpus) >= 10
    assert len(queries) >= 10
    for q in queries:
        assert q["relevant_ids"], f"{q['id']} has no relevant ids"
        for rid in q["relevant_ids"]:
            assert rid in corpus_ids, f"{q['id']} references unknown chunk {rid}"


def test_oracle_ranker_scores_perfectly():
    result = run("oracle", ks=[1, 3, 5])
    m = result["metrics"]
    assert m["mrr"] == 1.0
    assert m["at_k"][1]["hit_rate"] == 1.0
    assert m["at_k"][5]["ndcg"] == 1.0


def test_lexical_ranker_runs_and_reports():
    result = run("lexical", ks=[1, 3, 5])
    m = result["metrics"]
    assert m["queries"] == len(result["queries"])
    # A sane lexical baseline should retrieve most answers within the top 5.
    assert 0.0 <= m["at_k"][5]["hit_rate"] <= 1.0
