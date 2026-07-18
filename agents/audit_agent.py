"""Audit agent — persists workflow results for governance traceability."""

from modules.audit_logger import log_audit


def run_audit_agent(result: dict) -> None:
    """Record a completed workflow result in the audit log."""
    log_audit(result)
