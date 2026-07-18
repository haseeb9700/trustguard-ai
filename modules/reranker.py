"""Cross-encoder reranking to improve retrieval precision."""

from sentence_transformers import CrossEncoder

RERANKER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

reranker_model = CrossEncoder(RERANKER_MODEL_NAME)


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

    scores = reranker_model.predict(pairs)

    scored_contexts = [
        {**context, "rerank_score": float(score)}
        for context, score in zip(contexts, scores)
    ]

    scored_contexts.sort(key=lambda item: item["rerank_score"], reverse=True)

    return scored_contexts[:top_k]
