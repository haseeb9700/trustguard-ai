"""Knowledge-source ingestion: scrape (HTML or PDF) → chunk → embed → store."""

import io
import json
import logging
import os
import re
from urllib.parse import urljoin

import psycopg2
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from modules.content_filter import filter_chunks, is_boilerplate
from modules.embeddings import get_embedding_model
from modules.source_manager import delete_source
from modules.trick_questions import generate_trick_questions
from modules.url_guard import pin_validated_host, validate_public_url

load_dotenv()

logger = logging.getLogger("trustguard.ingest")

REQUEST_TIMEOUT_SECONDS = 30
MIN_BLOCK_LENGTH = 40
MIN_CHUNK_LENGTH = 50
MAX_CHUNKS_PER_SOURCE = 300

# Dotted forms that must not be mistaken for the end of a sentence: titles,
# regulation cites (8 CFR 214.2), month abbreviations, and single initials.
_ABBREV_RE = re.compile(
    r"\b(?:[A-Z]|No|Nos|Mr|Mrs|Ms|Dr|Sr|Jr|St|vs|etc|e\.g|i\.e|approx|Fig"
    r"|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept?|Oct|Nov|Dec|U\.S|Sec|Pub|Reg)\."
    r"|\b\d+\.\d+(?:\.\d+)*"
)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
MAX_REDIRECTS = 5
MAX_RESPONSE_BYTES = 15 * 1024 * 1024  # 15 MB cap on a fetched document
_REDIRECT_STATUSES = {301, 302, 303, 307, 308}

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}


def _get_embedding_model():
    """Lazy-load the shared embedding model.

    Must be the same model that embeds queries in ``rag_pipeline``, or stored
    vectors and query vectors are not comparable.
    """
    return get_embedding_model()


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
        elif len(text) > MIN_BLOCK_LENGTH and not is_boilerplate(text):
            # Drop banners and cookie notices here, before they are merged into
            # a section and become indistinguishable from the prose around them.
            current_blocks.append(text)

    if current_blocks:
        sections.append((current_heading, "\n".join(current_blocks)))

    return title, sections


def _read_capped(response: requests.Response) -> requests.Response:
    """Stream a response body, aborting if it exceeds MAX_RESPONSE_BYTES.

    Guards against memory exhaustion from a very large (or unbounded) remote
    document. A declared Content-Length is rejected up front; the streamed
    body is also capped in case the header lies or is absent.
    """
    declared = response.headers.get("Content-Length")
    if declared and declared.isdigit() and int(declared) > MAX_RESPONSE_BYTES:
        response.close()
        raise ValueError("Remote document exceeds the size limit.")

    body = bytearray()
    for chunk in response.iter_content(8192):
        body.extend(chunk)
        if len(body) > MAX_RESPONSE_BYTES:
            response.close()
            raise ValueError("Remote document exceeds the size limit.")

    response._content = bytes(body)
    response._content_consumed = True
    return response


def _safe_get(url: str) -> requests.Response:
    """GET a URL safely against SSRF, following redirects manually.

    ``requests`` follows redirects automatically, which would defeat the
    pre-flight SSRF check: a public URL can respond with a 302 to an internal
    address (localhost, 169.254.169.254, private hosts). Each hop is therefore
    validated AND its host is pinned to the validated IP (closing the DNS
    rebinding window) before the request is made. The response body is size-capped.
    """
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        validate_public_url(current)
        with pin_validated_host(current):
            response = requests.get(
                current,
                headers=REQUEST_HEADERS,
                timeout=REQUEST_TIMEOUT_SECONDS,
                allow_redirects=False,
                stream=True,
            )

            if response.status_code in _REDIRECT_STATUSES:
                location = response.headers.get("Location")
                response.close()
                if not location:
                    raise ValueError("Redirect response had no Location header.")
                current = urljoin(current, location)
                continue

            return _read_capped(response)

    raise ValueError("Too many redirects while fetching the URL.")


def scrape_url(url: str) -> tuple:
    """Fetch a URL (HTML page or PDF) and extract its content by section.

    Args:
        url: The document to scrape.

    Returns:
        A (title, sections) tuple, where sections is a list of
        (section_heading, text) pairs.
    """
    response = _safe_get(url)
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "").lower()

    if "application/pdf" in content_type or url.lower().endswith(".pdf"):
        return _extract_pdf(response.content, url)

    return _extract_html(response.text)


def split_sentences(text: str) -> list:
    """Split text into sentences, keeping their terminating punctuation.

    Not a general-purpose sentence tokenizer — it only needs to avoid the
    abbreviations that actually occur in this corpus, where a naive split on
    "." would cut "8 CFR 214.2(f)" or "Mar. 11, 2016" into pieces.
    """
    protected = _ABBREV_RE.sub(lambda m: m.group(0).replace(".", "\x00"), text)
    parts = _SENTENCE_SPLIT_RE.split(protected)
    return [p.replace("\x00", ".").strip() for p in parts if p.strip()]


def chunk_text(text: str, chunk_size: int = 400, overlap: int = 80) -> list:
    """Split text into overlapping chunks that begin at sentence boundaries.

    An earlier version sliced on a fixed word count. That routinely cut through
    the middle of a sentence, so a chunk could open with a dangling clause and
    no subject — one such chunk, whose text plainly contained the answer to a
    benchmark query, was retrieved at rank 28 of 93 because its opening words
    referred to something named in the *previous* chunk. Packing whole
    sentences instead keeps every chunk independently readable, which is what
    the embedding model is being asked to represent.

    A "sentence" longer than ``chunk_size`` is split on words as a fallback.
    That is not hypothetical: badly-extracted PDFs and flattened link menus can
    run for hundreds of words without a full stop, and emitting them whole
    would hand the embedding model a chunk past its 512-token limit, which it
    truncates silently — losing content with nothing to show for it.

    Args:
        text: The full text to chunk.
        chunk_size: Target words per chunk; a chunk may overshoot to finish
            the sentence it is in.
        overlap: Approximate words of trailing context repeated at the start of
            the next chunk, rounded to whole sentences.

    Returns:
        A list of chunk strings.
    """
    sentences = []
    for sentence in split_sentences(str(text)):
        words = sentence.split()
        if len(words) <= chunk_size:
            sentences.append(sentence)
            continue
        # Oversized run with no sentence break — fall back to word slices.
        for i in range(0, len(words), chunk_size):
            sentences.append(" ".join(words[i : i + chunk_size]))

    if not sentences:
        return []

    lengths = [len(s.split()) for s in sentences]
    chunks = []
    start = 0

    while start < len(sentences):
        end, total = start, 0
        while end < len(sentences) and (
            total == 0 or total + lengths[end] <= chunk_size
        ):
            total += lengths[end]
            end += 1

        chunk = " ".join(sentences[start:end])
        if len(chunk.strip()) > MIN_CHUNK_LENGTH:
            chunks.append(chunk)

        if end >= len(sentences):
            break

        # Step back over whole sentences until roughly `overlap` words of
        # context are repeated, so consecutive chunks still share ground.
        back, carried = end, 0
        while back > start + 1 and carried + lengths[back - 1] <= overlap:
            back -= 1
            carried += lengths[back]
        start = back

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


def save_chunks_to_supabase(
    title: str, url: str, chunks: list, embeddings: list
) -> None:
    """Insert chunk/embedding pairs into the knowledge_sources table."""
    conn = get_connection()

    try:
        with conn:
            with conn.cursor() as cur:
                for chunk, embedding in zip(chunks, embeddings, strict=True):
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

    # Second pass, now at chunk level. Block filtering cannot catch link menus:
    # each <li> is a few words, too short for the statistical signals to be
    # meaningful, and only becomes recognisable as a list once assembled.
    chunks, dropped = filter_chunks(chunk_sections(sections))
    chunks = chunks[:MAX_CHUNKS_PER_SOURCE]

    if dropped:
        logger.info(
            "Filtered %d non-prose chunk(s) from %s: %s",
            len(dropped),
            url,
            ", ".join(sorted({r for d in dropped for r in d["reasons"]}))[:200],
        )

    if not chunks:
        return {
            "status": "failed",
            "message": "No usable text content was found at this URL.",
            "url": url,
        }

    embeddings = (
        _get_embedding_model()
        .encode(
            chunks,
            batch_size=32,
            show_progress_bar=False,
        )
        .tolist()
    )

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
