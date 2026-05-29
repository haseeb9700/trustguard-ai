from agents.query_rewrite_agent import run_query_rewrite_agent
from agents.retrieval_agent import run_retrieval_agent
from agents.answer_agent import run_answer_agent
from agents.evaluation_agent import run_evaluation_agent
from agents.risk_agent import run_risk_agent
from agents.audit_agent import run_audit_agent


def run_agentic_workflow(query):
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
                "reason": "No retrieved context was available."
            },
            "risk_analysis": {
                "risk_level": "Low",
                "risk_status": "No Context",
                "risk_reason": "The knowledge base is empty."
            },
            "workflow": {
                "type": "multi_agent_rag_governance",
                "agents_used": [
                    "query_rewrite_agent",
                    "retrieval_agent",
                    "answer_agent",
                    "evaluation_agent",
                    "risk_agent",
                    "audit_agent"
                ]
            }
        }

        run_audit_agent(result)
        return result

    answer = run_answer_agent(query, contexts)

    hallucination_analysis = run_evaluation_agent(
        query,
        answer,
        contexts
    )

    risk_analysis = run_risk_agent(
        hallucination_analysis,
        answer
    )

    result = {
        "query": query,
        "rewritten_query": rewritten_query,
        "answer": answer,
        "sources": contexts,
        "hallucination_analysis": hallucination_analysis,
        "risk_analysis": risk_analysis,
        "workflow": {
            "type": "multi_agent_rag_governance",
            "agents_used": [
                "query_rewrite_agent",
                "retrieval_agent",
                "answer_agent",
                "evaluation_agent",
                "risk_agent",
                "audit_agent"
            ]
        }
    }

    run_audit_agent(result)

    return result