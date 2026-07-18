"""Rule-based governance risk scoring derived from hallucination analysis."""

import json


def calculate_risk(hallucination_analysis, answer: str = None) -> dict:
    """Map a hallucination analysis to a governance risk rating.

    Args:
        hallucination_analysis: Dict (or JSON string) containing
            "hallucination_score" (0, 1, or 2).
        answer: The generated answer text, used to detect unverified responses.

    Returns:
        A dict with "risk_score", "risk_level", "risk_status", and "risk_reason".
    """
    try:
        if isinstance(hallucination_analysis, str):
            analysis = json.loads(hallucination_analysis)
        else:
            analysis = hallucination_analysis

        hallucination_score = analysis.get("hallucination_score", 2)

    except (json.JSONDecodeError, ValueError, AttributeError):
        hallucination_score = 2

    answer_text = answer.lower() if answer else ""

    if "i could not verify" in answer_text:
        return {
            "risk_score": 1,
            "risk_level": "Medium",
            "risk_status": "Unverified",
            "risk_reason": (
                "The system could not verify the answer from retrieved sources."
            ),
        }

    if hallucination_score == 0:
        return {
            "risk_score": 0,
            "risk_level": "Low",
            "risk_status": "Grounded",
            "risk_reason": "Answer is fully supported by retrieved sources.",
        }

    if hallucination_score == 1:
        return {
            "risk_score": 1,
            "risk_level": "Medium",
            "risk_status": "Partially Supported",
            "risk_reason": (
                "Answer contains partially unsupported or uncertain claims."
            ),
        }

    return {
        "risk_score": 2,
        "risk_level": "High",
        "risk_status": "Unsupported",
        "risk_reason": (
            "Answer contains major unsupported claims or hallucination risk."
        ),
    }
