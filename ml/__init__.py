"""Learned answer-quality model for TrustGuard.

Predicts whether a human will judge an answer correct, from signals the RAG
pipeline already produces (hallucination score, risk, claim verdicts,
retrieval count). Trained on captured feedback to augment the rule-based
risk score with a data-driven quality estimate.
"""
