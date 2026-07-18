"""Human feedback capture for answer quality improvement.

Feedback is persisted to Supabase (a `feedback_log` table) so it survives
redeploys; if the database is unavailable it falls back to a local CSV.
"""

import logging
import os
from datetime import datetime

import pandas as pd

from modules.supabase_logger import get_connection

logger = logging.getLogger("trustguard.feedback")

FEEDBACK_FILE = "reports/feedback_log.csv"


def _save_to_db(question: str, answer: str, feedback: str, corrected_answer: str) -> None:
    """Insert a feedback record into the feedback_log table."""
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO feedback_log
                    (question, answer, feedback, corrected_answer)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (question, answer, feedback, corrected_answer),
                )
    finally:
        conn.close()


def _save_to_csv(question: str, answer: str, feedback: str, corrected_answer: str) -> None:
    """Append a feedback record to the local CSV fallback."""
    os.makedirs(os.path.dirname(FEEDBACK_FILE), exist_ok=True)

    row = {
        "timestamp": datetime.now().isoformat(),
        "question": question,
        "answer": answer,
        "feedback": feedback,
        "corrected_answer": corrected_answer,
    }

    df = pd.DataFrame([row])

    if os.path.exists(FEEDBACK_FILE):
        df.to_csv(FEEDBACK_FILE, mode="a", header=False, index=False)
    else:
        df.to_csv(FEEDBACK_FILE, index=False)


def save_feedback(
    question: str,
    answer: str,
    feedback: str,
    corrected_answer: str = None,
) -> dict:
    """Record human feedback on a generated answer.

    Args:
        question: The question the answer responded to.
        answer: The generated answer being rated.
        feedback: The rating label (e.g. "Correct", "Incorrect").
        corrected_answer: Optional user-provided correction.

    Returns:
        A status dict confirming the save and where it was stored.
    """
    corrected = corrected_answer or ""

    try:
        _save_to_db(question, answer, feedback, corrected)
        storage = "supabase"
    except Exception:
        logger.warning("DB feedback save failed; falling back to CSV.")
        _save_to_csv(question, answer, feedback, corrected)
        storage = "csv"

    return {
        "status": "success",
        "message": "Feedback saved successfully",
        "storage": storage,
    }
