"""Audit log reporting — reads and summarizes the audit log.

Prefers the live Supabase audit_logs table; falls back to the local
CSV export if the database is unavailable.
"""

import logging
import os

import pandas as pd

from modules.supabase_logger import get_connection

logger = logging.getLogger("trustguard.audit_reader")

AUDIT_LOG = "reports/audit_log.csv"


def _load_audit_df_from_db(limit: int = 500) -> pd.DataFrame:
    """Load recent audit rows from Supabase into a DataFrame (newest first)."""
    conn = get_connection()
    try:
        return pd.read_sql_query(
            "SELECT * FROM audit_logs ORDER BY id DESC LIMIT %(limit)s",
            conn,
            params={"limit": limit},
        )
    finally:
        conn.close()


def _load_audit_df() -> pd.DataFrame:
    """Load audit data from Supabase, falling back to the local CSV."""
    try:
        df = _load_audit_df_from_db()
        if not df.empty:
            return df
    except Exception:
        logger.warning("Could not read audit logs from database; using CSV fallback.")

    if os.path.exists(AUDIT_LOG):
        return pd.read_csv(AUDIT_LOG)

    return pd.DataFrame()

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


def get_stats() -> dict:
    """Compute aggregate accuracy statistics from the audit log.

    Returns:
        A dict with "total_queries", "grounded_pct" (share of Low-risk
        answers), and per-level "risk_counts". Empty-log-safe.
    """
    empty = {
        "total_queries": 0,
        "grounded_pct": None,
        "risk_counts": {"Low": 0, "Medium": 0, "High": 0},
    }

    try:
        df = _load_audit_df()

        if df.empty or "risk_level" not in df.columns:
            return empty

        levels = df["risk_level"].dropna().astype(str).str.strip()
        counts = levels.value_counts().to_dict()
        total = int(len(levels))

        risk_counts = {
            "Low": int(counts.get("Low", 0)),
            "Medium": int(counts.get("Medium", 0)),
            "High": int(counts.get("High", 0)),
        }

        grounded_pct = (
            round(100 * risk_counts["Low"] / total, 1) if total else None
        )

        return {
            "total_queries": total,
            "grounded_pct": grounded_pct,
            "risk_counts": risk_counts,
        }

    except Exception:
        return empty


def get_audit_logs(limit: int = 20) -> dict:
    """Return the most recent audit log entries plus summary statistics.

    Args:
        limit: Maximum number of log entries to return.

    Returns:
        A dict with "status", total "count", the "logs" list (newest first),
        and "top_questions" — or an error payload if the log cannot be read.
    """
    try:
        df = _load_audit_df()

        if df.empty:
            return dict(EMPTY_RESPONSE)

        # Normalize the timestamp column name (DB uses created_at).
        if "timestamp" not in df.columns and "created_at" in df.columns:
            df = df.rename(columns={"created_at": "timestamp"})

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
