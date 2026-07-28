"""Maximal marginal relevance: stop the context window filling with duplicates.

Chunks are cut with an 80-word overlap, and the same policy is often published
across several documents. So the highest-scoring chunks for a query are
frequently near-copies of one another: on the retrieval benchmark two pairs of
gold chunks are near-identical text from different sources, and adjacent chunks
share eighty words verbatim by construction.

Ranking purely by relevance spends the whole context window restating one
passage. MMR (Carbonell & Goldstein, 1998) scores each remaining candidate as::

    lambda * relevance  -  (1 - lambda) * max_similarity_to_already_selected

so a candidate is penalised for repeating something already chosen. The first
pick is always the most relevant one — diversity only affects what follows.

**Similarity is lexical, not embedding-based.** The redundancy being removed is
literal repetition: shared word-for-word overlap from the chunker, and the same
sentences republished across sources. Token overlap detects that exactly and
costs nothing, where cosine over embeddings would need the vectors carried
through the pipeline and would also score two *distinct* passages on one topic
as redundant. The tradeoff is that a genuine paraphrase is not caught; if that
turns out to matter, ``similarity`` is injectable.
"""

from __future__ import annotations

import re

# Alphanumeric runs, lower-cased. No stemming: "student's" tokenises to
# {student, s}, so morphological variants are not matched. That is adequate
# here because the redundancy being detected is literal repetition, where the
# duplicated spans are identical rather than merely inflected.
_TOKEN_RE = re.compile(r"[a-z0-9]+")

DEFAULT_LAMBDA = 0.7


def _tokens(text: str) -> set:
    return set(_TOKEN_RE.findall(str(text).lower()))


def jaccard(a: str, b: str) -> float:
    """Token overlap between two texts, 0.0 (disjoint) to 1.0 (identical)."""
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    union = ta | tb
    return len(ta & tb) / len(union) if union else 0.0


def mmr_select(
    contexts: list,
    top_k: int,
    lambda_: float = DEFAULT_LAMBDA,
    score_key: str = "rerank_score",
    similarity=jaccard,
) -> list:
    """Pick ``top_k`` contexts balancing relevance against redundancy.

    Args:
        contexts: Context dicts, already scored and sorted by relevance.
        top_k: How many to select.
        lambda_: 1.0 is pure relevance (identical to plain ranking), 0.0 is pure
            diversity. Between those it trades one against the other.
        score_key: Which key holds the relevance score.
        similarity: Redundancy function over two texts.

    Returns:
        The selected contexts in selection order, each annotated with
        ``mmr_score`` and ``max_redundancy`` so a ranking can be explained
        after the fact rather than being an opaque reordering.
    """
    if not contexts or top_k <= 0:
        return []
    if lambda_ >= 1.0:
        return contexts[:top_k]

    remaining = list(contexts)
    selected = []

    # Normalise relevance to [0, 1]. Cross-encoder logits are unbounded and can
    # be negative, so subtracting a raw similarity from a raw score would let
    # whichever quantity happens to have the larger magnitude dominate, and
    # lambda would no longer mean what it says.
    scores = [float(c.get(score_key, 0.0)) for c in contexts]
    lo, hi = min(scores), max(scores)
    span = hi - lo
    norm = {
        id(c): (1.0 if span == 0 else (float(c.get(score_key, 0.0)) - lo) / span)
        for c in contexts
    }

    while remaining and len(selected) < top_k:
        best, best_score, best_redundancy = None, None, 0.0

        for candidate in remaining:
            redundancy = max(
                (similarity(candidate["text"], s["text"]) for s in selected),
                default=0.0,
            )
            value = lambda_ * norm[id(candidate)] - (1 - lambda_) * redundancy
            if best_score is None or value > best_score:
                best, best_score, best_redundancy = candidate, value, redundancy

        selected.append(
            {
                **best,
                "mmr_score": round(best_score, 4),
                "max_redundancy": round(best_redundancy, 4),
            }
        )
        remaining.remove(best)

    return selected
