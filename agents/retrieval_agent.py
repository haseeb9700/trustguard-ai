"""Retrieval agent — fetches relevant context chunks from the vector store.

Retrieves a wide candidate set by embedding similarity, then narrows it
with a cross-encoder reranker for higher precision.
"""

import logging

from modules.rag_pipeline import retrieve_context
from modules.reranker import rerank_contexts

logger = logging.getLogger("trustguard.retrieval")

CANDIDATE_POOL_SIZE = 15
FINAL_TOP_K = 6

# Diversity weight for MMR, chosen by sweeping lambda on the retrieval
# benchmark rather than by taste (see eval/README.md). At 0.8 every ranking
# metric is at least as good as pure relevance (MRR 0.743 vs 0.739,
# hit-rate@3 0.852 vs 0.815) while the share of queries returning a
# near-duplicate pair falls from 15/54 to 10/54. Lower values keep cutting
# redundancy but start costing recall: by 0.5, hit-rate@3 drops to 0.778.
MMR_LAMBDA = 0.8


def run_retrieval_agent(query: str, top_k: int = FINAL_TOP_K) -> list:
    """Retrieve and rerank the most relevant context chunks for a query.

    Args:
        query: The (rewritten) search query.
        top_k: Number of chunks to return after reranking.

    Returns:
        A list of scored context dicts (with "similarity_score" and
        "rerank_score"), or an empty list on failure.
    """
    try:
        candidates = retrieve_context(query, top_k=CANDIDATE_POOL_SIZE)
    except Exception:
        logger.exception("Retrieval failed for query: %r", query)
        return []

    if not candidates:
        return []

    try:
        return rerank_contexts(query, candidates, top_k=top_k, mmr_lambda=MMR_LAMBDA)
    except Exception:
        logger.exception("Reranking failed; falling back to similarity order.")
        return candidates[:top_k]
