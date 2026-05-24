import uuid
import requests
import chromadb
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer

DB_PATH = "data/chroma_db"
COLLECTION_NAME = "uscis_policy_docs"

embedding_model = SentenceTransformer("BAAI/bge-small-en-v1.5")


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


def ingest_url(url):
    title, full_text = scrape_url(url)

    chunks = chunk_text(full_text)

    if not chunks:
        return {
            "status": "failed",
            "message": "No usable text found on this URL.",
            "url": url
        }

    client = chromadb.PersistentClient(path=DB_PATH)
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    ids = []
    documents = []
    metadatas = []

    for index, chunk in enumerate(chunks):
        ids.append(str(uuid.uuid4()))
        documents.append(chunk)
        metadatas.append({
            "source_title": title,
            "source_url": url,
            "chunk_index": index
        })

    embeddings = embedding_model.encode(
        documents,
        batch_size=32,
        show_progress_bar=True
    ).tolist()

    collection.add(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas
    )

    return {
        "status": "success",
        "source_title": title,
        "source_url": url,
        "chunks_added": len(chunks)
    }