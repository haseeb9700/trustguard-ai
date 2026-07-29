"""Lexical (BM25) retrieval and rank fusion, to complement dense embeddings.

Dense embeddings are good at meaning and bad at exact strings. They place
"H-1B" and "F-1" near each other because both are visa classifications, which
is precisely wrong when a user asks about one of them. This corpus is full of
such tokens — 597 identifier occurrences across 93 chunks: ``Form I-983``,
``8 CFR 214.2(f)(10)``, ``INA 101(a)(3)``, ``81 FR 13040``. BM25 matches them
exactly, which is the capability the embedding model structurally lacks.

**Tokenisation is the whole game here.** The usual ``[a-z0-9]+`` pattern splits
``H-1B`` into ``h`` and ``1b`` and ``8 CFR 214.2(f)`` into five meaningless
fragments, destroying exactly the signal lexical search is being added for. The
tokeniser below keeps internal hyphens and dots so identifiers survive whole.

**Fusion is by rank, not score.** BM25 scores are unbounded sums of IDF terms;
cosine similarities sit in [-1, 1]. Adding them requires inventing a
normalisation, and whichever quantity happens to have the larger spread then
dominates for reasons unrelated to retrieval quality. Reciprocal rank fusion
(Cormack et al., 2009) uses only the position of a document in each ranking, so
the two systems can be combined without their scores ever being compared.

Note on deployment: this implementation scores every document in Python, which
is fine for the benchmark but would compound the existing full-table-scan
problem in ``retrieve_context``. In production the lexical half belongs in
Postgres as a ``tsvector`` column with a GIN index, with fusion done over the
two result sets.
"""

from __future__ import annotations

import math
import re
from collections import Counter

# Alphanumeric runs that may contain internal hyphens or dots, so "h-1b",
# "i-983" and "214.2" survive as single tokens instead of being shredded.
_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-.][a-z0-9]+)*")

# Okapi defaults. k1 controls how fast term-frequency saturates; b controls how
# strongly long documents are penalised. These are the standard values and are not
# tuned here — tuning them on the eval corpus would be fitting to the test set.
BM25_K1 = 1.5
BM25_B = 0.75

# RRF damping. 60 is the value from the original paper and the de-facto default;
# it decides how sharply top ranks are favoured over deeper ones.
RRF_K = 60


def tokenize(text: str) -> list:
    """Lower-case and split text, preserving identifier-shaped tokens."""
    return _TOKEN_RE.findall(str(text).lower())


class BM25:
    """Okapi BM25 over a fixed document collection.

    Args:
        documents: list of (doc_id, text) pairs.
    """

    def __init__(self, documents: list, k1: float = BM25_K1, b: float = BM25_B):
        self.k1 = k1
        self.b = b
        self.doc_ids = [doc_id for doc_id, _ in documents]

        self.tokens = [tokenize(text) for _, text in documents]
        self.lengths = [len(t) for t in self.tokens]
        self.avg_length = sum(self.lengths) / len(self.lengths) if self.lengths else 0.0
        self.frequencies = [Counter(t) for t in self.tokens]

        # Document frequency, then IDF with the +0.5 smoothing that keeps a
        # term appearing in every document from going negative.
        n_docs = len(documents)
        doc_freq = Counter()
        for tokens in self.tokens:
            doc_freq.update(set(tokens))
        self.idf = {
            term: math.log(1 + (n_docs - freq + 0.5) / (freq + 0.5))
            for term, freq in doc_freq.items()
        }

    def scores(self, query: str) -> dict:
        """Return {doc_id: bm25 score} for a query."""
        query_terms = tokenize(query)
        results = {}

        for i, doc_id in enumerate(self.doc_ids):
            freqs = self.frequencies[i]
            length = self.lengths[i]
            norm = self.k1 * (
                1
                - self.b
                + self.b * (length / self.avg_length if self.avg_length else 0)
            )

            score = 0.0
            for term in query_terms:
                tf = freqs.get(term, 0)
                if tf == 0:
                    continue
                score += self.idf.get(term, 0.0) * (tf * (self.k1 + 1)) / (tf + norm)
            results[doc_id] = score

        return results

    def rank(self, query: str) -> list:
        """Return doc ids ordered by descending BM25 score."""
        scored = self.scores(query)
        return sorted(scored, key=lambda d: scored[d], reverse=True)


def reciprocal_rank_fusion(
    rankings: list, k: int = RRF_K, weights: list = None
) -> list:
    """Fuse several ranked id lists into one.

    Each list contributes ``weight / (k + rank)`` to every document it ranks,
    with rank counted from 1. Because only positions are used, rankings from
    systems with entirely incomparable score scales can be combined directly.

    Args:
        rankings: ranked lists of document ids, best first.
        k: damping constant; larger values flatten the contribution of top ranks.
        weights: optional per-ranking weights, defaulting to equal.

    Returns:
        A single ranked list of every id appearing in any input.
    """
    if not rankings:
        return []
    if weights is None:
        weights = [1.0] * len(rankings)

    fused = {}
    for ranking, weight in zip(rankings, weights, strict=True):
        for position, doc_id in enumerate(ranking, start=1):
            fused[doc_id] = fused.get(doc_id, 0.0) + weight / (k + position)

    # Ties broken by best position achieved in any ranking, so the ordering is
    # deterministic rather than dependent on dict insertion order.
    best_rank = {}
    for ranking in rankings:
        for position, doc_id in enumerate(ranking, start=1):
            if doc_id not in best_rank or position < best_rank[doc_id]:
                best_rank[doc_id] = position

    return sorted(fused, key=lambda d: (-fused[d], best_rank[d], str(d)))
