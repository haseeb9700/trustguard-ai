from modules.risk_score import calculate_risk


def run_risk_agent(hallucination_analysis, answer):
    return calculate_risk(
        hallucination_analysis,
        answer
    )