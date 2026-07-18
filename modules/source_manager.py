"""Knowledge-source management — list and delete ingested sources."""

import logging

from modules.supabase_logger import get_connection

logger = logging.getLogger("trustguard.sources")


def list_sources() -> list:
    """Return all ingested sources with their chunk counts.

    Returns:
        A list of dicts: {"source_title", "source_url", "chunks"}.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT source_title, source_url, COUNT(*) AS chunks
                FROM knowledge_sources
                GROUP BY source_title, source_url
                ORDER BY source_title
                """
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    return [
        {"source_title": title, "source_url": url, "chunks": int(count)}
        for title, url, count in rows
    ]


def delete_source(url: str) -> int:
    """Delete all chunks belonging to a source URL.

    Args:
        url: The source URL whose chunks should be removed.

    Returns:
        The number of chunks deleted.
    """
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM knowledge_sources WHERE source_url = %s", (url,)
                )
                deleted = cur.rowcount
    finally:
        conn.close()

    logger.info("Deleted %d chunks for source: %s", deleted, url)
    return deleted
