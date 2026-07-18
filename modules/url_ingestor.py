"""Knowledge-source ingestion: scrape (HTML or PDF) → chunk → embed → store."""

import io
import json
import logging
import os

import psycopg2
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from modules.source_manager import delete_source
from modules.trick_questions import generate_trick_questions

load_dotenv()

logger = logging.getLogger("trustguard.ingest")

EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"
REQUEST_TIMEOUT_SECONDS = 30
MIN_BLOCK_LENGTH = 40
MIN_CHUNK_LENGTH = 50
MAX_CHUNKS_PER_SOURCE = 300

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

_embedding_model = None


def _get_embedding_model():
    """Lazy-load the embedding model on first use (keeps startup fast)."""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer

        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedding_model


def get_connection():
    """Open a new PostgreSQL connection using the DATABASE_URL env var."""
    return psycopg2.connect(os.getenv("DATABASE_URL"))


def _extract_pdf(content: bytes, url: str) -> tuple:
    """Extract title and section-tagged text blocks from PDF bytes.

    Returns:
        A (title, sections) tuple, where sections is a list of
        (section_heading, text) pairs.
    """
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(content))

    title = None
    if reader.metadata and reader.metadata.title:
        title = str(reader.metadata.title).strip()
    if not title:
        title = url.rstrip("/").split("/")[-1] or "PDF Document"

    sections = []
    for page_num, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if len(text) > MIN_BLOCK_LENGTH:
            sections.append((f"Page {page_num}", text))

    return title, sections


def _extract_html(html: str) -> tuple:
    """Extract title and section-tagged text blocks from HTML.

    Text is grouped under its nearest preceding heading so that chunks
    can carry section context.

    Returns:
        A (title, sections) tuple, where sections is a list of
        (section_heading, text) pairs.
    """
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    title_tag = soup.find("h1") or soup.find("title")
    title = title_tag.get_text(" ", strip=True) if title_tag else "Untitled Source"

    sections = []
    current_heading = ""
    current_blocks = []

    for tag in soup.find_all(["h1", "h2", "h3", "p", "li"]):
        text = tag.get_text(" ", strip=True)

        if tag.name in ("h1", "h2", "h3"):
            if current_blocks:
                sections.append((current_heading, "\n".join(current_blocks)))
                current_blocks = []
            current_heading = text
        elif len(text) > MIN_BLOCK_LENGTH:
            current_blocks.append(text)

    if current_blocks:
        sections.append((current_heading, "\n".join(current_blocks)))

    return title, sections


def scrape_url(url: str) -> tuple:
    """Fetch a URL (HTML page or PDF) and extract its content by section.

    Args:
        url: The document to scrape.

    Returns:
        A (title, sections) tuple, where sections is a list of
        (section_heading, text) pairs.
    """
    response = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "").lower()

    if "application/pdf" in content_type or url.lower().endswith(".pdf"):
        return _extract_pdf(response.content, url)

    return _extract_html(response.text)


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


def chunk_sections(sections: list, chunk_size: int = 400, overlap: int = 80) -> list:
    """Chunk each section separately, prefixing chunks with their heading.

    Section-aware chunking keeps chunks topically coherent and carries the
    heading as retrieval context, which improves both embedding quality
    and answer grounding.

    Args:
        sections: List of (section_heading, text) pairs.
        chunk_size: Number of words per chunk.
        overlap: Number of words shared between consecutive chunks.

    Returns:
        A list of chunk strings.
    """
    chunks = []

    for heading, text in sections:
        prefix = f"[{heading}] " if heading else ""
        for chunk in chunk_text(text, chunk_size=chunk_size, overlap=overlap):
            chunks.append(f"{prefix}{chunk}")

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
    """Ingest a URL (HTML page or PDF) as a trusted knowledge source.

    Scrapes the document, chunks its text section by section, generates
    embeddings, and stores everything in the vector store.

    Args:
        url: The document to ingest.

    Returns:
        A status dict describing the outcome, including generated
        trick questions for the demo.
    """
    title, sections = scrape_url(url)

    chunks = chunk_sections(sections)[:MAX_CHUNKS_PER_SOURCE]

    if not chunks:
        return {
            "status": "failed",
            "message": "No usable text content was found at this URL.",
            "url": url,
        }

    embeddings = _get_embedding_model().encode(
        chunks,
        batch_size=32,
        show_progress_bar=False,
    ).tolist()

    # Refresh semantics: re-ingesting a URL replaces its old chunks
    # instead of duplicating them.
    refreshed = delete_source(url) > 0

    save_chunks_to_supabase(title=title, url=url, chunks=chunks, embeddings=embeddings)

    return {
        "status": "success",
        "source_title": title,
        "source_url": url,
        "chunks_added": len(chunks),
        "refreshed": refreshed,
        "storage": "supabase",
        "trick_questions": generate_trick_questions(chunks, title),
    }
