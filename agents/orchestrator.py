"""Orchestrator for the TrustGuard multi-agent governance workflow.

Pipeline: query rewrite → retrieval → answer generation →
hallucination evaluation → risk scoring → audit logging.
"""

from agents.answer_agent import run_answer_agent
from agents.audit_agent import run_audit_agent
from agents.evaluation_agent import run_evaluation_agent
from agents.query_rewrite_agent import run_query_rewrite_agent
from agents.retrieval_agent import run_retrieval_agent
from agents.risk_agent import run_risk_agent
from modules.claim_verifier import verify_claims
from modules.risk_score import apply_claim_escalation

AGENTS_USED = [
    "query_rewrite_agent",
    "retrieval_agent",
    "answer_agent",
    "evaluation_agent",
    "risk_agent",
    "audit_agent",
]

WORKFLOW_METADATA = {
    "type": "multi_agent_rag_governance",
    "agents_used": AGENTS_USED,
}


def run_agentic_workflow(query: str) -> dict:
    """Execute the full governance workflow for a user query.

    Args:
        query: The raw user question.

    Returns:
        A result dict containing the answer, retrieved sources,
        hallucination analysis, risk analysis, and workflow metadata.
        Every result is persisted to the audit log before returning.
    """
    rewritten_query = run_query_rewrite_agent(query)
    contexts = run_retrieval_agent(rewritten_query)

    if not contexts:
        result = {
            "query": query,
            "rewritten_query": rewritten_query,
            "answer": (
                "No knowledge sources have been ingested yet. "
                "Please add a source URL first."
            ),
            "sources": [],
            "hallucination_analysis": {
                "hallucination_score": 0,
                "reason": "No retrieved context was available.",
            },
            "risk_analysis": {
                "risk_level": "Low",
                "risk_status": "No Context",
                "risk_reason": "The knowledge base is empty.",
            },
            "workflow": WORKFLOW_METADATA,
        }

        run_audit_agent(result)
        return result

    answer = run_answer_agent(query, contexts)
    hallucination_analysis = run_evaluation_agent(query, answer, contexts)
    claim_verification = verify_claims(answer, contexts)
    risk_analysis = apply_claim_escalation(
        run_risk_agent(hallucination_analysis, answer),
        claim_verification,
    )

    result = {
        "query": query,
        "rewritten_query": rewritten_query,
        "answer": answer,
        "sources": contexts,
        "hallucination_analysis": hallucination_analysis,
        "risk_analysis": risk_analysis,
        "claim_verification": claim_verification,
        "workflow": WORKFLOW_METADATA,
    }

    run_audit_agent(result)
    return result
