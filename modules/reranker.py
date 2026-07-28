"""Cross-encoder reranking to improve retrieval precision."""

RERANKER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

_reranker_model = None


def _get_model():
    """Lazy-load the cross-encoder on first use (keeps startup fast)."""
    global _reranker_model
    if _reranker_model is None:
        from sentence_transformers import CrossEncoder

        _reranker_model = CrossEncoder(RERANKER_MODEL_NAME)
    return _reranker_model


def rerank_contexts(query: str, contexts: list, top_k: int = 10) -> list:
    """Re-score retrieved contexts against the query with a cross-encoder.

    Args:
        query: The search query.
        contexts: Context dicts, each with a "text" key.
        top_k: Number of top-ranked contexts to return.

    Returns:
        The top_k contexts sorted by "rerank_score" (descending).
    """
    pairs = [[query, context["text"]] for context in contexts]

    scores = _get_model().predict(pairs)

    scored_contexts = [
        {**context, "rerank_score": float(score)}
        for context, score in zip(contexts, scores, strict=True)
    ]

    scored_contexts.sort(key=lambda item: item["rerank_score"], reverse=True)

    return scored_contexts[:top_k]
