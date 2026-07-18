"""Retrieval agent — fetches relevant context chunks from the vector store."""

import logging

from modules.rag_pipeline import retrieve_context

logger = logging.getLogger("trustguard.retrieval")

DEFAULT_TOP_K = 15


def run_retrieval_agent(query: str, top_k: int = DEFAULT_TOP_K) -> list:
    """Retrieve the most relevant context chunks for a query.

    Args:
        query: The (rewritten) search query.
        top_k: Maximum number of chunks to return.

    Returns:
        A list of scored context dicts, or an empty list on failure.
    """
    try:
        return retrieve_context(query, top_k=top_k)
    except Exception:
        logger.exception("Retrieval failed for query: %r", query)
        return []
