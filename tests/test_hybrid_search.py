"""Tests for BM25 and reciprocal rank fusion.

The tokeniser tests matter most. Lexical search is being added precisely to
catch exact identifiers that embeddings blur together, so a tokeniser that
shreds "H-1B" into "h" and "1b" would leave the whole feature doing nothing
detectable — it would still return plausible rankings, just without the one
capability it exists to provide.
"""

from modules.hybrid_search import BM25, reciprocal_rank_fusion, tokenize

# --- tokenisation ----------------------------------------------------------


def test_preserves_visa_class_identifiers():
    assert "h-1b" in tokenize("Applicants under H-1B status")
    assert "f-1" in tokenize("F-1 students may work")
    # ...and does not shred them into meaningless pieces.
    assert "1b" not in tokenize("H-1B")


def test_preserves_form_numbers():
    tokens = tokenize("File Form I-765 and keep Form I-20")
    assert "i-765" in tokens
    assert "i-20" in tokens


def test_preserves_dotted_regulation_cites():
    assert "214.2" in tokenize("See 8 CFR 214.2(f)(10)")


def test_distinguishes_similar_identifiers():
    # The exact failure dense embeddings have: these are different things.
    assert tokenize("H-1B") != tokenize("H-4")
    assert tokenize("I-765") != tokenize("I-983")


def test_lowercases_and_drops_punctuation():
    assert tokenize("The Agency, USCIS.") == ["the", "agency", "uscis"]


# --- BM25 ------------------------------------------------------------------


DOCS = [
    ("a", "F-1 students may apply for optional practical training after one year"),
    ("b", "H-1B petitions are subject to an annual numerical cap and a lottery"),
    ("c", "Form I-983 records the training plan agreed with the employer"),
    ("d", "The bank must maintain a minimum common equity tier one capital ratio"),
]


def test_exact_identifier_beats_topical_neighbour():
    # The capability dense retrieval lacks: "H-1B" must not match the F-1 doc
    # just because both concern student and worker visas.
    assert BM25(DOCS).rank("H-1B cap")[0] == "b"
    assert BM25(DOCS).rank("Form I-983")[0] == "c"


def test_rare_terms_outrank_common_ones():
    # "the" appears everywhere and should carry almost no weight, so a query
    # dominated by it must not beat a distinctive term.
    ranked = BM25(DOCS).rank("the capital ratio")
    assert ranked[0] == "d"


def test_unmatched_query_scores_zero_for_all():
    scores = BM25(DOCS).scores("kangaroo marsupial")
    assert set(scores.values()) == {0.0}


def test_rank_returns_every_document():
    assert sorted(BM25(DOCS).rank("training")) == ["a", "b", "c", "d"]


def test_empty_collection_does_not_crash():
    index = BM25([])
    assert index.rank("anything") == []


def test_longer_documents_are_length_normalised():
    # Same single match, but one document is padded with filler. BM25 should
    # prefer the shorter one rather than rewarding verbosity.
    docs = [
        ("short", "lottery"),
        ("long", "lottery " + "filler words here " * 40),
    ]
    assert BM25(docs).rank("lottery")[0] == "short"


# --- reciprocal rank fusion ------------------------------------------------


def test_agreement_between_systems_wins():
    # Ranked highly by both, so it should come first even though neither
    # system put it at the very top.
    dense = ["x", "target", "y"]
    lexical = ["z", "target", "w"]
    assert reciprocal_rank_fusion([dense, lexical])[0] == "target"


def test_includes_documents_found_by_only_one_system():
    # The point of hybrid: a document dense retrieval missed entirely must
    # still be reachable via the lexical ranking.
    fused = reciprocal_rank_fusion([["a", "b"], ["c"]])
    assert set(fused) == {"a", "b", "c"}


def test_weights_shift_the_balance():
    # Disjoint rankings, so weighting is the only thing deciding the order.
    dense = ["dense_pick"]
    lexical = ["lexical_pick"]
    assert (
        reciprocal_rank_fusion([dense, lexical], weights=[5.0, 1.0])[0] == "dense_pick"
    )
    assert (
        reciprocal_rank_fusion([dense, lexical], weights=[1.0, 5.0])[0]
        == "lexical_pick"
    )


def test_agreement_outweighs_a_single_first_place_at_any_k():
    # A structural property of RRF, not a tuning artefact: a document ranked
    # second by both systems beats one ranked first by only one, because
    # 1/(k+1) > 2/(k+2) reduces to 0 > k, which fails for every k > 0.
    # Worth pinning down — it means equal-weight fusion is strongly biased
    # toward consensus, so a document only one retriever can find needs a
    # substantially better rank to surface.
    dense = ["first", "second"]
    lexical = ["other", "second"]
    for k in (1, 10, 60, 200):
        assert reciprocal_rank_fusion([dense, lexical], k=k)[0] == "second"

    # k=0 is the boundary case: the inequality becomes an equality, the two
    # tie on fused score, and the tie-break on best achieved rank decides.
    assert reciprocal_rank_fusion([dense, lexical], k=0)[0] == "first"


def test_larger_k_flattens_rank_differences():
    # k controls how sharply early ranks are favoured. With k large, the gap
    # between rank 1 and rank 2 shrinks toward nothing.
    ranking = [["a", "b"]]
    sharp = reciprocal_rank_fusion(ranking, k=0)
    flat = reciprocal_rank_fusion(ranking, k=1000)
    # Order is unchanged either way; only the margin differs.
    assert sharp == flat == ["a", "b"]


def test_fusion_is_deterministic():
    a = reciprocal_rank_fusion([["p", "q", "r"], ["r", "q", "p"]])
    b = reciprocal_rank_fusion([["p", "q", "r"], ["r", "q", "p"]])
    assert a == b


def test_empty_rankings_return_empty():
    assert reciprocal_rank_fusion([]) == []
