import json
import os

import numpy as np
import psycopg2
from dotenv import load_dotenv
from openai import OpenAI

from modules.audit_logger import log_audit
from modules.cache import get_cached_embedding, set_cached_embedding
from modules.hallucination_checker import evaluate_hallucination
from modules.reranker import rerank_contexts
from modules.risk_score import calculate_risk

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"

_embedding_model = None


def _get_embedding_model():
    """Lazy-load the embedding model on first use (keeps startup fast)."""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer

        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedding_model


def get_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


def cosine_similarity(a, b):
    a = np.array(a, dtype=float)
    b = np.array(b, dtype=float)

    denominator = np.linalg.norm(a) * np.linalg.norm(b)

    if denominator == 0:
        return 0

    return float(np.dot(a, b) / denominator)


def retrieve_context(query, top_k=10):
    # Query embedding is knowledge-base independent, so cache it by text.
    query_embedding = get_cached_embedding(query)
    if query_embedding is None:
        query_embedding = _get_embedding_model().encode([query]).tolist()[0]
        set_cached_embedding(query, query_embedding)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            source_title,
            source_url,
            chunk_text,
            embedding
        FROM knowledge_sources
        """
    )

    rows = cur.fetchall()

    cur.close()
    conn.close()

    if not rows:
        return []

    scored_contexts = []

    for source_title, source_url, chunk_text, embedding in rows:
        if isinstance(embedding, str):
            embedding = json.loads(embedding)

        score = cosine_similarity(query_embedding, embedding)

        scored_contexts.append(
            {
                "text": chunk_text,
                "source_title": source_title or "Unknown Source",
                "source_url": source_url or "",
                "similarity_score": score,
            }
        )

    scored_contexts.sort(key=lambda item: item["similarity_score"], reverse=True)

    return scored_contexts[:top_k]


def generate_answer(query):
    contexts = retrieve_context(query, top_k=15)

    if not contexts:
        result = {
            "query": query,
            "answer": (
                "No knowledge sources have been ingested yet. "
                "Please add a source URL first."
            ),
            "sources": [],
            "hallucination_analysis": {
                "hallucination_score": 0,
                "reason": "No retrieved context was available.",
            },
            "risk_analysis": {
                "risk_level": "Low",
                "risk_status": "No Context",
                "risk_reason": "The knowledge base is empty.",
            },
        }

        log_audit(result)
        return result

    contexts = rerank_contexts(query, contexts, top_k=6)

    context_text = "\n\n".join(
        [f"Source: {c['source_title']}\nText: {c['text']}" for c in contexts]
    )

    prompt = f"""
You are an AI assistant answering only from the provided official source context.

Rules:
- Use only the provided context.
- If the answer is not in the context, say:
  "I could not verify this from the provided sources."
- Do not guess.
- Keep the answer concise and factual.

USER QUESTION:
{query}

OFFICIAL SOURCE CONTEXT:
{context_text}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a careful enterprise RAG assistant "
                    "for policy and compliance documents."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )

    answer = response.choices[0].message.content

    hallucination_result = evaluate_hallucination(query, answer, contexts)

    risk_result = calculate_risk(hallucination_result, answer)

    result = {
        "query": query,
        "answer": answer,
        "sources": contexts,
        "hallucination_analysis": hallucination_result,
        "risk_analysis": risk_result,
    }

    log_audit(result)

    return result
