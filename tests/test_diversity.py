"""Tests for MMR diversity selection.

MMR is easy to write in a way that looks right and silently does nothing — or
that quietly drops the best result. The properties worth pinning down are:
the top pick is never sacrificed to diversity, lambda=1.0 is exactly the old
behaviour, redundant candidates actually get demoted, and nothing is lost or
duplicated along the way.
"""

import pytest

from modules.diversity import jaccard, mmr_select


def _ctx(cid, text, score):
    return {"id": cid, "text": text, "rerank_score": score}


# Two near-identical passages plus a distinct one. Relevance order is a, b, c,
# but b merely restates a.
NEAR_DUPES = [
    _ctx("a", "The agency uses a random selection process called the lottery", 9.0),
    _ctx("b", "The agency uses a random selection lottery process", 8.0),
    _ctx("c", "Applicants must hold a bachelor degree or its equivalent", 7.0),
]


# --- jaccard ---------------------------------------------------------------


def test_jaccard_identical_and_disjoint():
    assert jaccard("alpha beta", "alpha beta") == 1.0
    assert jaccard("alpha beta", "gamma delta") == 0.0


def test_jaccard_is_case_insensitive():
    assert jaccard("Random Selection Process.", "random selection process") == 1.0


def test_jaccard_splits_possessives_rather_than_stemming():
    # No stemming: "student's" becomes {student, s}, so this is 2/3 not 1.0.
    # Fine for detecting literal repetition, which is what MMR needs here, but
    # worth pinning down so nobody assumes morphological matching exists.
    assert jaccard("Student's Record.", "student record") == pytest.approx(2 / 3)


def test_jaccard_handles_empty():
    assert jaccard("", "anything") == 0.0


# --- selection behaviour ---------------------------------------------------


def test_top_result_is_never_sacrificed():
    # The first pick has nothing to be redundant against, so it must always be
    # the most relevant candidate no matter how aggressive lambda is.
    for lam in (0.0, 0.3, 0.5, 0.9):
        assert mmr_select(NEAR_DUPES, top_k=3, lambda_=lam)[0]["id"] == "a"


def test_demotes_the_near_duplicate():
    # b is more relevant than c but says the same thing as a, so c should come
    # second once redundancy is priced in.
    picked = [c["id"] for c in mmr_select(NEAR_DUPES, top_k=3, lambda_=0.5)]
    assert picked == ["a", "c", "b"]


def test_lambda_one_is_plain_relevance_ordering():
    picked = [c["id"] for c in mmr_select(NEAR_DUPES, top_k=3, lambda_=1.0)]
    assert picked == ["a", "b", "c"]


def test_high_lambda_keeps_relevance_order():
    # With diversity weighted lightly, a 1.0-point relevance gap outweighs the
    # redundancy penalty and the original order survives.
    picked = [c["id"] for c in mmr_select(NEAR_DUPES, top_k=3, lambda_=0.95)]
    assert picked == ["a", "b", "c"]


def test_returns_requested_count_without_loss_or_duplication():
    picked = mmr_select(NEAR_DUPES, top_k=2, lambda_=0.5)
    assert len(picked) == 2
    ids = [c["id"] for c in picked]
    assert len(set(ids)) == 2


def test_preserves_original_fields_and_annotates():
    picked = mmr_select(NEAR_DUPES, top_k=1, lambda_=0.5)[0]
    assert picked["id"] == "a"
    assert picked["rerank_score"] == 9.0
    # Annotated so a ranking can be explained rather than just accepted.
    assert "mmr_score" in picked
    assert picked["max_redundancy"] == 0.0


NEGATIVE_SCORED = [
    _ctx("a", "random selection lottery process for petitions", -2.0),
    _ctx("b", "random selection lottery process for petitions filed", -3.0),
    _ctx("c", "an entirely unrelated passage about capital ratios", -11.0),
]


def test_negative_scores_are_normalised_not_dropped():
    # Cross-encoder logits are routinely negative. After normalisation the
    # spread is what matters: a=1.0, b=0.89, c=0.0. At lambda 0.5, b is so
    # much more relevant than c that it survives its own redundancy.
    picked = [c["id"] for c in mmr_select(NEGATIVE_SCORED, top_k=3, lambda_=0.5)]
    assert picked == ["a", "b", "c"]


def test_lower_lambda_overrides_a_large_relevance_gap():
    # Same candidates, more weight on diversity: now b's near-duplication of a
    # costs more than its relevance advantage over c.
    picked = [c["id"] for c in mmr_select(NEGATIVE_SCORED, top_k=3, lambda_=0.3)]
    assert picked == ["a", "c", "b"]


def test_identical_scores_do_not_crash():
    contexts = [_ctx(str(i), f"passage number {i} here", 5.0) for i in range(4)]
    assert len(mmr_select(contexts, top_k=3, lambda_=0.5)) == 3


# --- edge cases ------------------------------------------------------------


@pytest.mark.parametrize("top_k", [0, -1])
def test_non_positive_top_k_returns_empty(top_k):
    assert mmr_select(NEAR_DUPES, top_k=top_k, lambda_=0.5) == []


def test_empty_input_returns_empty():
    assert mmr_select([], top_k=5, lambda_=0.5) == []


def test_top_k_larger_than_input():
    assert len(mmr_select(NEAR_DUPES, top_k=99, lambda_=0.5)) == 3
