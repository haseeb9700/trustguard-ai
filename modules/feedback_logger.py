"""Human feedback capture for answer quality improvement."""

import os
from datetime import datetime

import pandas as pd

FEEDBACK_FILE = "reports/feedback_log.csv"


def save_feedback(
    question: str,
    answer: str,
    feedback: str,
    corrected_answer: str = None,
) -> dict:
    """Append a feedback record to the feedback log CSV.

    Args:
        question: The question the answer responded to.
        answer: The generated answer being rated.
        feedback: The rating label (e.g. "Correct", "Incorrect").
        corrected_answer: Optional user-provided correction.

    Returns:
        A status dict confirming the save.
    """
    os.makedirs(os.path.dirname(FEEDBACK_FILE), exist_ok=True)

    row = {
        "timestamp": datetime.now().isoformat(),
        "question": question,
        "answer": answer,
        "feedback": feedback,
        "corrected_answer": corrected_answer or "",
    }

    df = pd.DataFrame([row])

    if os.path.exists(FEEDBACK_FILE):
        df.to_csv(FEEDBACK_FILE, mode="a", header=False, index=False)
    else:
        df.to_csv(FEEDBACK_FILE, index=False)

    return {
        "status": "success",
        "message": "Feedback saved successfully",
    }
