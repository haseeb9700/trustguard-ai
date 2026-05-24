from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from modules.rag_pipeline import generate_answer
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


@app.get("/")
def home():
    return {
        "message": "TrustGuard AI API is running",
        "status": "healthy"
    }


@app.post("/analyze")
def analyze_query(request: QueryRequest):

    result = generate_answer(request.question)

    return {
        "question": result["query"],
        "answer": result["answer"],
        "hallucination_analysis": result["hallucination_analysis"],
        "risk_analysis": result["risk_analysis"],
        "sources": [
            {
                "title": source["source_title"],
                "url": source["source_url"]
            }
            for source in result["sources"]
        ]
    }


@app.post("/ingest-url")
def ingest_source(request: UrlIngestRequest):

    result = ingest_url(request.url)

    return result


@app.post("/feedback")
def submit_feedback(request: FeedbackRequest):

    return save_feedback(
        question=request.question,
        answer=request.answer,
        feedback=request.feedback,
        corrected_answer=request.corrected_answer
    )


@app.get("/audit-logs")
def audit_logs():

    return get_audit_logs()