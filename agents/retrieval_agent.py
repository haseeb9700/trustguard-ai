from modules.rag_pipeline import retrieve_context
from modules.reranker import rerank_contexts


def run_retrieval_agent(query):
    contexts = retrieve_context(query, top_k=15)
    reranked_contexts = rerank_contexts(query, contexts, top_k=6)

    return reranked_contexts