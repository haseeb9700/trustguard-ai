"""Audit log reporting — reads and summarizes the local audit log."""

import os

import pandas as pd

AUDIT_LOG = "reports/audit_log.csv"

EMPTY_RESPONSE = {
    "status": "empty",
    "count": 0,
    "logs": [],
    "top_questions": [],
}


def get_top_questions(df: pd.DataFrame, limit: int = 8) -> list:
    """Return the most frequently asked questions with their counts."""
    if "query" not in df.columns:
        return []

    questions = df["query"].dropna().astype(str).str.strip()
    questions = questions[questions != ""]

    if questions.empty:
        return []

    top_questions = questions.value_counts().head(limit).reset_index()
    top_questions.columns = ["question", "count"]

    return top_questions.to_dict(orient="records")


def get_audit_logs(limit: int = 20) -> dict:
    """Return the most recent audit log entries plus summary statistics.

    Args:
        limit: Maximum number of log entries to return.

    Returns:
        A dict with "status", total "count", the "logs" list (newest first),
        and "top_questions" — or an error payload if the log cannot be read.
    """
    if not os.path.exists(AUDIT_LOG):
        return dict(EMPTY_RESPONSE)

    try:
        df = pd.read_csv(AUDIT_LOG)

        if df.empty:
            return dict(EMPTY_RESPONSE)

        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
            df = df.sort_values(by="timestamp", ascending=False)

        logs = df.head(limit).fillna("").to_dict(orient="records")

        return {
            "status": "success",
            "count": len(df),
            "returned": len(logs),
            "logs": logs,
            "top_questions": get_top_questions(df),
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Could not read audit log: {e}",
            "logs": [],
            "top_questions": [],
        }
