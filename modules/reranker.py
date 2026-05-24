from sentence_transformers import CrossEncoder

reranker_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")


def rerank_contexts(query, contexts, top_k=10):
    pairs = []

    for context in contexts:
        pairs.append([
            query,
            context["text"]
        ])

    scores = reranker_model.predict(pairs)

    scored_contexts = []

    for context, score in zip(contexts, scores):
        scored_contexts.append({
            **context,
            "rerank_score": float(score)
        })

    scored_contexts = sorted(
        scored_contexts,
        key=lambda x: x["rerank_score"],
        reverse=True
    )

    return scored_contexts[:top_k]