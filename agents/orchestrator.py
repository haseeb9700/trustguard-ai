from agents.retrieval_agent import run_retrieval_agent
from agents.answer_agent import run_answer_agent
from agents.evaluation_agent import run_evaluation_agent
from agents.risk_agent import run_risk_agent
from agents.audit_agent import run_audit_agent
from agents.query_rewrite_agent import run_query_rewrite_agent


def get_unique_sources(contexts, limit=3):
    unique_sources = []
    seen_urls = set()

    for source in contexts:
        url = source.get("source_url", "")

        if url and url not in seen_urls:
            clean_source = {
                "text": str(source.get("text", "")),
                "source_title": str(source.get("source_title", "No Title")),
                "source_url": str(source.get("source_url", ""))
            }

            unique_sources.append(clean_source)
            seen_urls.add(url)

        if len(unique_sources) >= limit:
            break

    return unique_sources


def run_agentic_workflow(query):
    rewritten_query = run_query_rewrite_agent(query)

    contexts = run_retrieval_agent(rewritten_query)

    answer = run_answer_agent(
        query,
        contexts
    )

    hallucination_analysis = run_evaluation_agent(
        query,
        answer,
        contexts
    )

    risk_analysis = run_risk_agent(
        hallucination_analysis,
        answer
    )

    unique_sources = get_unique_sources(
        contexts,
        limit=3
    )

    result = {
        "query": query,
        "rewritten_query": rewritten_query,
        "answer": answer,
        "sources": unique_sources,
        "retrieved_context_count": len(contexts),
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