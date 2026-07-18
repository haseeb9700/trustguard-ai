"""Supabase (PostgreSQL) persistence for audit log entries."""

import os

import psycopg2


def get_connection():
    """Open a new PostgreSQL connection using the DATABASE_URL env var."""
    return psycopg2.connect(os.getenv("DATABASE_URL"))


def save_audit_log(
    query: str,
    rewritten_query: str,
    answer: str,
    hallucination_analysis,
    risk_level: str,
    risk_reason: str,
) -> None:
    """Insert a single audit record into the audit_logs table."""
    conn = get_connection()

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO audit_logs
                    (
                        query,
                        rewritten_query,
                        answer,
                        hallucination_analysis,
                        risk_level,
                        risk_reason
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        query,
                        rewritten_query,
                        answer,
                        str(hallucination_analysis),
                        risk_level,
                        risk_reason,
                    ),
                )
    finally:
        conn.close()
