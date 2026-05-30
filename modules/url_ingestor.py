import os
import json
import requests
import psycopg2
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

embedding_model = SentenceTransformer("BAAI/bge-small-en-v1.5")


def get_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


def scrape_url(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
    }

    response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")

    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    title_tag = soup.find("h1") or soup.find("title")
    title = title_tag.get_text(" ", strip=True) if title_tag else "No Title"

    content_tags = soup.find_all(["h1", "h2", "h3", "p", "li"])

    text_blocks = []

    for tag in content_tags:
        text = tag.get_text(" ", strip=True)

        if len(text) > 40:
            text_blocks.append(text)

    full_text = "\n".join(text_blocks)

    return title, full_text


def chunk_text(text, chunk_size=400, overlap=80):
    words = str(text).split()
    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])

        if len(chunk.strip()) > 50:
            chunks.append(chunk)

        start += chunk_size - overlap

    return chunks


def save_chunks_to_supabase(title, url, chunks, embeddings):
    conn = get_connection()
    cur = conn.cursor()

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
            (
                title,
                url,
                chunk,
                json.dumps(embedding)
            )
        )

    conn.commit()
    cur.close()
    conn.close()


def ingest_url(url):
    title, full_text = scrape_url(url)

    chunks = chunk_text(full_text)

    if not chunks:
        return {
            "status": "failed",
            "message": "No usable text found on this URL.",
            "url": url
        }

    embeddings = embedding_model.encode(
        chunks,
        batch_size=32,
        show_progress_bar=True
    ).tolist()

    save_chunks_to_supabase(
        title=title,
        url=url,
        chunks=chunks,
        embeddings=embeddings
    )

    return {
        "status": "success",
        "source_title": title,
        "source_url": url,
        "chunks_added": len(chunks),
        "storage": "supabase"
    }