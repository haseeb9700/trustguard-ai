"""Cross-encoder reranking to improve retrieval precision."""

from modules.diversity import mmr_select

RERANKER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

_reranker_model = None


def _get_model():
    """Lazy-load the cross-encoder on first use (keeps startup fast)."""
    global _reranker_model
    if _reranker_model is None:
        from sentence_transformers import CrossEncoder

        _reranker_model = CrossEncoder(RERANKER_MODEL_NAME)
    return _reranker_model


def rerank_contexts(
    query: str,
    contexts: list,
    top_k: int = 10,
    mmr_lambda: float | None = None,
) -> list:
    """Re-score retrieved contexts against the query with a cross-encoder.

    Args:
        query: The search query.
        contexts: Context dicts, each with a "text" key.
        top_k: Number of top-ranked contexts to return.
        mmr_lambda: If set, apply maximal marginal relevance after scoring so
            near-duplicate chunks do not fill the context window. ``None``
            (the default) keeps pure relevance ordering.

    Returns:
        The top_k contexts sorted by "rerank_score" (descending), or in MMR
        selection order when ``mmr_lambda`` is given.
    """
    pairs = [[query, context["text"]] for context in contexts]

    scores = _get_model().predict(pairs)

    scored_contexts = [
        {**context, "rerank_score": float(score)}
        for context, score in zip(contexts, scores, strict=True)
    ]

    scored_contexts.sort(key=lambda item: item["rerank_score"], reverse=True)

    if mmr_lambda is not None:
        return mmr_select(scored_contexts, top_k=top_k, lambda_=mmr_lambda)

    return scored_contexts[:top_k]
