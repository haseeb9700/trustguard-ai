"""Audit logging — persists every workflow result for governance traceability."""

import logging

from modules.supabase_logger import save_audit_log

logger = logging.getLogger("trustguard.audit")


def log_audit(result: dict) -> None:
    """Persist a workflow result to the audit log store."""
    save_audit_log(
        query=result["query"],
        rewritten_query=result.get("rewritten_query", ""),
        answer=result["answer"],
        hallucination_analysis=result["hallucination_analysis"],
        risk_level=result["risk_analysis"]["risk_level"],
        risk_reason=result["risk_analysis"]["risk_reason"],
    )

    logger.info("Audit log entry saved.")
