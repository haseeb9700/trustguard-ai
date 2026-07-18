"""Risk agent — converts hallucination analysis into a governance risk rating."""

from modules.risk_score import calculate_risk


def run_risk_agent(hallucination_analysis: dict, answer: str) -> dict:
    """Assess governance risk for an answer based on its hallucination analysis."""
    return calculate_risk(hallucination_analysis, answer)
