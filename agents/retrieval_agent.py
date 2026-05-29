from modules.rag_pipeline import retrieve_context


def run_retrieval_agent(query):
    try:
        contexts = retrieve_context(query, top_k=15)
        return contexts
    except Exception as e:
        print(f"Retrieval agent error: {e}")
        return []