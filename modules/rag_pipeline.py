from modules.hallucination_checker import evaluate_hallucination
from modules.risk_score import calculate_risk
from modules.audit_logger import log_audit
from modules.reranker import rerank_contexts

import os
import chromadb
from dotenv import load_dotenv
from openai import OpenAI
from sentence_transformers import SentenceTransformer

load_dotenv()

DB_PATH = "data/chroma_db"
COLLECTION_NAME = "uscis_policy_docs"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
embedding_model = SentenceTransformer("BAAI/bge-small-en-v1.5")


def retrieve_context(query, top_k=10):
    db_client = chromadb.PersistentClient(path=DB_PATH)

    collection = db_client.get_collection(
        name=COLLECTION_NAME
    )

    query_embedding = embedding_model.encode(
        [query]
    ).tolist()[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )

    contexts = []

    for doc, meta in zip(
        results["documents"][0],
        results["metadatas"][0]
    ):
        contexts.append({
            "text": doc,
            "source_title": meta["source_title"],
            "source_url": meta["source_url"]
        })

    return contexts


def generate_answer(query):

    contexts = retrieve_context(query, top_k=15)
    contexts = rerank_contexts(query, contexts, top_k=6 )

    context_text = "\n\n".join([
        f"Source: {c['source_title']}\n"
        f"Text: {c['text']}"
        for c in contexts
    ])

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
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )

    answer = response.choices[0].message.content

    hallucination_result = evaluate_hallucination(
        query,
        answer,
        contexts
    )

    risk_result = calculate_risk(
        hallucination_result,
        answer
    )

    result = {
        "query": query,
        "answer": answer,
        "sources": contexts,
        "hallucination_analysis": hallucination_result,
        "risk_analysis": risk_result
    }

    log_audit(result)

    return result