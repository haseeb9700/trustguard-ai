import os
import pandas as pd
from datetime import datetime

FEEDBACK_FILE = "reports/feedback_log.csv"


def save_feedback(question, answer, feedback, corrected_answer=None):
    os.makedirs("reports", exist_ok=True)

    row = {
        "timestamp": datetime.now().isoformat(),
        "question": question,
        "answer": answer,
        "feedback": feedback,
        "corrected_answer": corrected_answer or ""
    }

    df = pd.DataFrame([row])

    if os.path.exists(FEEDBACK_FILE):
        df.to_csv(FEEDBACK_FILE, mode="a", header=False, index=False)
    else:
        df.to_csv(FEEDBACK_FILE, index=False)

    return {
        "status": "success",
        "message": "Feedback saved successfully"
    }