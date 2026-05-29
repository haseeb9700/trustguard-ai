from modules.supabase_logger import save_audit_log


def log_audit(result):
    save_audit_log(
        query=result["query"],
        rewritten_query=result.get("rewritten_query", ""),
        answer=result["answer"],
        hallucination_analysis=result["hallucination_analysis"],
        risk_level=result["risk_analysis"]["risk_level"],
        risk_reason=result["risk_analysis"]["risk_reason"]
    )

    print("Audit log saved to Supabase")