from typing import Optional
import math

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents.orchestrator import run_agentic_workflow
from modules.url_ingestor import ingest_url
from modules.feedback_logger import save_feedback
from modules.audit_reader import get_audit_logs

app = FastAPI(title="TrustGuard AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    question: str


class UrlIngestRequest(BaseModel):
    url: str


class FeedbackRequest(BaseModel):
    question: str
    answer: str
    feedback: str
    corrected_answer: Optional[str] = None


def clean_json(value):
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value

    if isinstance(value, dict):
        return {
            str(k): clean_json(v)
            for k, v in value.items()
        }

    if isinstance(value, list):
        return [
            clean_json(item)
            for item in value
        ]

    return value


@app.get("/")
def home():
    return {
        "message": "TrustGuard AI API is running",
        "status": "healthy",
        "architecture": "multi-agent RAG governance workflow"
    }


@app.post("/analyze")
def analyze_query(request: QueryRequest):
    result = run_agentic_workflow(request.question)

    response = {
        "question": result["query"],
        "rewritten_query": result.get("rewritten_query", ""),
        "answer": result["answer"],
        "hallucination_analysis": result["hallucination_analysis"],
        "risk_analysis": result["risk_analysis"],
        "workflow": result.get("workflow", {}),
        "retrieved_context_count": result.get("retrieved_context_count", 0),
        "sources": [
            {
                "title": source.get("source_title", "No Title"),
                "url": source.get("source_url", "")
            }
            for source in result["sources"]
        ]
    }

    return clean_json(response)


@app.post("/ingest-url")
def ingest_source(request: UrlIngestRequest):
    return clean_json(ingest_url(request.url))


@app.post("/feedback")
def submit_feedback(request: FeedbackRequest):
    return clean_json(
        save_feedback(
            question=request.question,
            answer=request.answer,
            feedback=request.feedback,
            corrected_answer=request.corrected_answer
        )
    )


@app.get("/audit-logs")
def audit_logs():
    return clean_json(get_audit_logs())