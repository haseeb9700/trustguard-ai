import os
import pandas as pd

AUDIT_LOG = "reports/audit_log.csv"


def get_top_questions(df, limit=8):
    if "query" not in df.columns:
        return []

    questions = (
        df["query"]
        .dropna()
        .astype(str)
        .str.strip()
    )

    questions = questions[questions != ""]

    if questions.empty:
        return []

    top_questions = (
        questions
        .value_counts()
        .head(limit)
        .reset_index()
    )

    top_questions.columns = ["question", "count"]

    return top_questions.to_dict(orient="records")


def get_audit_logs(limit=20):
    if not os.path.exists(AUDIT_LOG):
        return {
            "status": "empty",
            "count": 0,
            "logs": [],
            "top_questions": []
        }

    try:
        df = pd.read_csv(AUDIT_LOG)

        if df.empty:
            return {
                "status": "empty",
                "count": 0,
                "logs": [],
                "top_questions": []
            }

        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(
                df["timestamp"],
                errors="coerce"
            )

            df = df.sort_values(
                by="timestamp",
                ascending=False
            )

        logs = (
            df
            .head(limit)
            .fillna("")
            .to_dict(orient="records")
        )

        return {
            "status": "success",
            "count": len(df),
            "returned": len(logs),
            "logs": logs,
            "top_questions": get_top_questions(df)
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "logs": [],
            "top_questions": []
        }