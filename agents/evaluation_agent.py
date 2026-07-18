"""Evaluation agent — scores answers for hallucination risk."""

from modules.hallucination_checker import evaluate_hallucination


def run_evaluation_agent(query: str, answer: str, contexts: list) -> dict:
    """Evaluate how well an answer is grounded in the retrieved context."""
    return evaluate_hallucination(query, answer, contexts)
