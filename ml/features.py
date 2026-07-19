"""Feature extraction for the answer-quality model.

Turns a single ``/analyze`` result (or an equivalently shaped record) into a
fixed, ordered numeric feature vector. Pure and dependency-free so it can be
unit-tested and reused identically at training and inference time — the same
function must produce the same features in both, or the model silently breaks.
"""

from __future__ import annotations

# Stable feature order. NEVER reorder or insert in the middle — append only,
# and retrain, otherwise saved models read the wrong columns.
FEATURE_NAMES = [
    "hallucination_score",   # 0 grounded .. 2 unsupported
    "risk_score",            # 0 Low .. 2 High
    "retrieved_context_count",
    "n_claims",
    "n_entailed",
    "n_baseless",
    "n_contradicted",
    "frac_entailed",         # entailed / claims
    "n_sources",
    "answer_len_words",
    "unverified_flag",       # answer says it could not verify
]

_RISK_LEVEL_TO_SCORE = {"low": 0, "medium": 1, "high": 2}


def _risk_score(result: dict) -> int:
    risk = result.get("risk_analysis", {}) or {}
    if "risk_score" in risk and risk["risk_score"] is not None:
        try:
            return int(risk["risk_score"])
        except (TypeError, ValueError):
            pass
    level = str(risk.get("risk_level", "")).strip().lower()
    return _RISK_LEVEL_TO_SCORE.get(level, 2)


def _hallucination_score(result: dict) -> int:
    analysis = result.get("hallucination_analysis", {}) or {}
    score = analysis.get("hallucination_score")
    try:
        return int(score)
    except (TypeError, ValueError):
        return 2  # unknown → assume worst


def extract_features(result: dict) -> dict:
    """Extract the named feature dict from an analysis result.

    Args:
        result: A dict shaped like the ``/analyze`` response (or a stored
            record with the same keys).

    Returns:
        A dict mapping every name in FEATURE_NAMES to a numeric value.
    """
    claims = result.get("claim_verification") or []
    verdicts = [str(c.get("verdict", "")).lower() for c in claims if isinstance(c, dict)]
    n_claims = len(verdicts)
    n_entailed = verdicts.count("entailed")
    n_baseless = verdicts.count("baseless")
    n_contradicted = verdicts.count("contradicted")

    sources = result.get("sources") or []
    answer = str(result.get("answer", ""))

    return {
        "hallucination_score": _hallucination_score(result),
        "risk_score": _risk_score(result),
        "retrieved_context_count": int(result.get("retrieved_context_count", len(sources)) or 0),
        "n_claims": n_claims,
        "n_entailed": n_entailed,
        "n_baseless": n_baseless,
        "n_contradicted": n_contradicted,
        "frac_entailed": (n_entailed / n_claims) if n_claims else 0.0,
        "n_sources": len(sources),
        "answer_len_words": len(answer.split()),
        "unverified_flag": 1 if "could not verify" in answer.lower() else 0,
    }


def feature_vector(result: dict) -> list:
    """Return features as a list ordered by FEATURE_NAMES (model input row)."""
    feats = extract_features(result)
    return [feats[name] for name in FEATURE_NAMES]


# Feedback strings map to a binary quality label: was the answer acceptable?
_POSITIVE_FEEDBACK = {"correct"}


def label_from_feedback(feedback: str) -> int:
    """Map a human feedback string to a binary label (1 = correct, 0 = not).

    "Partially Correct" and "Incorrect" both count as not-correct: for a
    governance tool, "mostly right" still isn't trustworthy.
    """
    return 1 if str(feedback).strip().lower() in _POSITIVE_FEEDBACK else 0
