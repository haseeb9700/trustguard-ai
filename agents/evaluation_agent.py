from modules.hallucination_checker import evaluate_hallucination


def run_evaluation_agent(query, answer, contexts):
    return evaluate_hallucination(
        query,
        answer,
        contexts
    )