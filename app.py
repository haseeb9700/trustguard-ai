"""TrustGuard AI — FastAPI backend.

Exposes the multi-agent RAG governance workflow over HTTP:
query analysis, knowledge-source ingestion, feedback capture,
and audit-log retrieval.
"""

import json
import logging
import math
import os
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# Optional error tracking: set SENTRY_DSN in the environment to enable.
if os.getenv("SENTRY_DSN"):
    try:
        import sentry_sdk

        sentry_sdk.init(dsn=os.getenv("SENTRY_DSN"), traces_sample_rate=0.1)
    except ImportError:
        pass

from agents.orchestrator import run_agentic_workflow
from modules.audit_reader import get_audit_logs, get_stats
from modules.cache import cache_stats, invalidate_answers
from modules.feedback_logger import save_feedback
from modules.source_manager import delete_source, list_sources
from modules.url_guard import validate_public_url
from modules.url_ingestor import ingest_url

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("trustguard")

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="TrustGuard AI",
    description=(
        "Enterprise AI governance API: retrieval-augmented answers with "
        "hallucination detection, risk scoring, and audit logging."
    ),
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Restrict CORS via env, e.g. ALLOWED_ORIGINS=https://your-frontend.vercel.app
# Defaults to "*" for local development.
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",")
    if origin.strip()
]

# Credentials must never be combined with a wildcard origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials="*" not in ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    """A user question to analyze against the knowledge base."""

    question: str = Field(
        ..., min_length=1, max_length=2000, description="The user's question."
    )


class UrlIngestRequest(BaseModel):
    """A URL to scrape, chunk, embed, and store as a knowledge source."""

    url: str = Field(
        ..., min_length=1, max_length=2048, description="Publicly accessible URL."
    )


class FeedbackRequest(BaseModel):
    """Human feedback on a generated answer."""

    question: str = Field(..., max_length=2000)
    answer: str = Field(..., max_length=10000)
    feedback: str = Field(..., max_length=100)
    corrected_answer: str | None = Field(None, max_length=10000)


def clean_json(value: Any) -> Any:
    """Recursively replace NaN/Inf floats with None so responses are valid JSON."""
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value

    if isinstance(value, dict):
        return {str(k): clean_json(v) for k, v in value.items()}

    if isinstance(value, list):
        return [clean_json(item) for item in value]

    return value


def parse_json_if_string(value: Any) -> dict:
    """Normalize the hallucination analysis into a dict.

    The evaluator model may return a JSON string; parse it defensively and
    fall back to a well-formed placeholder when parsing fails.
    """
    if isinstance(value, dict):
        return value

    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass
        return {"hallucination_score": None, "reason": value}

    return {
        "hallucination_score": None,
        "reason": "No hallucination analysis returned.",
    }


def get_unique_sources(sources: list, max_sources: int = 5) -> list:
    """Deduplicate retrieved sources by URL, preserving retrieval order."""
    unique_sources = []
    seen_urls = set()

    for source in sources:
        url = source.get("source_url", "")

        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_sources.append(
                {
                    "title": source.get("source_title", "Untitled Source"),
                    "url": url,
                }
            )

        if len(unique_sources) >= max_sources:
            break

    return unique_sources


@app.get("/")
def home() -> dict:
    """Health check and service metadata."""
    return {
        "message": "TrustGuard AI API is running",
        "status": "healthy",
        "architecture": "multi-agent RAG governance workflow",
    }


@app.post("/analyze")
@limiter.limit("10/minute")
def analyze_query(request: Request, query: QueryRequest) -> dict:
    """Run the full governance workflow for a question.

    Returns the grounded answer along with hallucination analysis,
    risk assessment, and deduplicated source citations.
    Rate limited to 10 requests/minute per IP.
    """
    try:
        result = run_agentic_workflow(query.question)
    except Exception:
        logger.exception("Analysis workflow failed for question: %r", query.question)
        raise HTTPException(
            status_code=500,
            detail="Analysis failed. Please try again shortly.",
        ) from None

    response = {
        "question": result["query"],
        "rewritten_query": result.get("rewritten_query", ""),
        "answer": result["answer"],
        "hallucination_analysis": parse_json_if_string(
            result.get("hallucination_analysis", {})
        ),
        "risk_analysis": result.get("risk_analysis", {}),
        "claim_verification": result.get("claim_verification", []),
        "workflow": result.get("workflow", {}),
        "retrieved_context_count": result.get("retrieved_context_count", 0),
        "sources": get_unique_sources(result.get("sources", []), max_sources=5),
        "cached": result.get("cache_hit", False),
    }

    return clean_json(response)


@app.post("/ingest-url")
@limiter.limit("5/minute")
def ingest_source(
    request: Request,
    ingest: UrlIngestRequest,
    x_api_key: str | None = Header(None),
) -> dict:
    """Scrape a URL (HTML or PDF), chunk and embed it as a trusted source.

    If ADMIN_API_KEY is set in the environment, this endpoint requires a
    matching X-API-Key header — ingestion modifies the knowledge base, so it
    should not be open to the public. Rate limited to 5 requests/minute per IP.
    """
    admin_key = os.getenv("ADMIN_API_KEY")
    if admin_key and x_api_key != admin_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")

    try:
        validate_public_url(ingest.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        result = ingest_url(ingest.url)
    except Exception:
        logger.exception("URL ingestion failed for: %s", ingest.url)
        raise HTTPException(
            status_code=502,
            detail="Could not ingest this URL. Verify it is reachable and try again.",
        ) from None

    # The knowledge base changed — cached answers may now be stale.
    invalidate_answers()
    logger.info("Knowledge source ingested: %s", ingest.url)

    return clean_json(result)


@app.post("/feedback")
def submit_feedback(request: FeedbackRequest) -> dict:
    """Record human feedback on a generated answer for future improvement."""
    try:
        result = save_feedback(
            question=request.question,
            answer=request.answer,
            feedback=request.feedback,
            corrected_answer=request.corrected_answer,
        )
    except Exception:
        logger.exception("Failed to save feedback")
        raise HTTPException(
            status_code=500, detail="Could not save feedback."
        ) from None

    return clean_json(result)


@app.get("/audit-logs")
def audit_logs() -> dict:
    """Return recent audit log entries and the most frequently asked questions."""
    return clean_json(get_audit_logs())


@app.get("/stats")
def stats() -> dict:
    """Return aggregate accuracy statistics computed from the audit log."""
    return clean_json(get_stats())


@app.get("/sources")
def sources() -> dict:
    """List all ingested knowledge sources with their chunk counts."""
    try:
        return clean_json({"status": "success", "sources": list_sources()})
    except Exception:
        logger.exception("Failed to list sources")
        return {"status": "error", "sources": []}


@app.delete("/sources")
def remove_source(url: str, x_api_key: str | None = Header(None)) -> dict:
    """Delete an ingested source (all its chunks) by URL.

    Requires a matching X-API-Key header when ADMIN_API_KEY is set —
    deletion modifies the knowledge base.
    """
    admin_key = os.getenv("ADMIN_API_KEY")
    if admin_key and x_api_key != admin_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")

    try:
        deleted = delete_source(url)
    except Exception:
        logger.exception("Failed to delete source: %s", url)
        raise HTTPException(
            status_code=500, detail="Could not delete this source."
        ) from None

    # The knowledge base changed — cached answers may now be stale.
    invalidate_answers()

    return {"status": "success", "deleted_chunks": deleted}


@app.get("/cache-stats")
def cache_statistics() -> dict:
    """Return cache hit/miss statistics for the answer and embedding caches."""
    return clean_json(cache_stats())


@app.post("/predict-quality")
def predict_quality_endpoint(request: Request, query: QueryRequest) -> dict:
    """Analyze a question, then attach a learned answer-quality estimate.

    The quality model predicts the probability a human would mark the answer
    correct, based on the pipeline's own signals. Returns the analysis plus a
    ``quality`` block, or ``quality: null`` if the model has not been trained.
    """
    from ml.predict import predict_quality

    try:
        result = run_agentic_workflow(query.question)
    except Exception:
        logger.exception("Quality prediction workflow failed.")
        raise HTTPException(
            status_code=500, detail="Analysis failed. Please try again shortly."
        ) from None

    return clean_json(
        {
            "question": result["query"],
            "answer": result["answer"],
            "risk_analysis": result.get("risk_analysis", {}),
            "quality": predict_quality(result),
        }
    )
