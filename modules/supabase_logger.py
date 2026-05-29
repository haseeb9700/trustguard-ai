import os
import psycopg2


def get_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


def save_audit_log(query, rewritten_query, answer, hallucination_analysis, risk_level, risk_reason):
    conn = get_connection()
    cur = conn.cursor()

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
            risk_reason
        )
    )

    conn.commit()
    cur.close()
    conn.close()