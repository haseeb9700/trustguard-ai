"""Knowledge-source ingestion: scrape → chunk → embed → store."""

import json
import os

import psycopg2
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"
REQUEST_TIMEOUT_SECONDS = 20
MIN_BLOCK_LENGTH = 40
MIN_CHUNK_LENGTH = 50

embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)


def get_connection():
    """Open a new PostgreSQL connection using the DATABASE_URL env var."""
    return psycopg2.connect(os.getenv("DATABASE_URL"))


def scrape_url(url: str) -> tuple:
    """Fetch a URL and extract its title and readable text content.

    Args:
        url: The page to scrape.

    Returns:
        A (title, full_text) tuple. Navigation, scripts, and styling
        are stripped; only substantive text blocks are kept.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
    }

    response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")

    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    title_tag = soup.find("h1") or soup.find("title")
    title = title_tag.get_text(" ", strip=True) if title_tag else "Untitled Source"

    content_tags = soup.find_all(["h1", "h2", "h3", "p", "li"])

    text_blocks = [
        text
        for tag in content_tags
        if len(text := tag.get_text(" ", strip=True)) > MIN_BLOCK_LENGTH
    ]

    return title, "\n".join(text_blocks)


def chunk_text(text: str, chunk_size: int = 400, overlap: int = 80) -> list:
    """Split text into overlapping word-based chunks.

    Args:
        text: The full text to chunk.
        chunk_size: Number of words per chunk.
        overlap: Number of words shared between consecutive chunks.

    Returns:
        A list of chunk strings.
    """
    words = str(text).split()
    chunks = []
    start = 0

    while start < len(words):
        chunk = " ".join(words[start : start + chunk_size])

        if len(chunk.strip()) > MIN_CHUNK_LENGTH:
            chunks.append(chunk)

        start += chunk_size - overlap

    return chunks


def save_chunks_to_supabase(title: str, url: str, chunks: list, embeddings: list) -> None:
    """Insert chunk/embedding pairs into the knowledge_sources table."""
    conn = get_connection()

    try:
        with conn:
            with conn.cursor() as cur:
                for chunk, embedding in zip(chunks, embeddings):
                    cur.execute(
                        """
                        INSERT INTO knowledge_sources
                        (
                            source_title,
                            source_url,
                            chunk_text,
                            embedding
                        )
                        VALUES (%s, %s, %s, %s)
                        """,
                        (title, url, chunk, json.dumps(embedding)),
                    )
    finally:
        conn.close()


def ingest_url(url: str) -> dict:
    """Ingest a URL as a trusted knowledge source.

    Scrapes the page, chunks its text, generates embeddings, and stores
    everything in the vector store.

    Args:
        url: The page to ingest.

    Returns:
        A status dict describing the outcome.
    """
    title, full_text = scrape_url(url)

    chunks = chunk_text(full_text)

    if not chunks:
        return {
            "status": "failed",
            "message": "No usable text content was found at this URL.",
            "url": url,
        }

    embeddings = embedding_model.encode(
        chunks,
        batch_size=32,
        show_progress_bar=False,
    ).tolist()

    save_chunks_to_supabase(title=title, url=url, chunks=chunks, embeddings=embeddings)

    return {
        "status": "success",
        "source_title": title,
        "source_url": url,
        "chunks_added": len(chunks),
        "storage": "supabase",
    }
