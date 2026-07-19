"""Inference for the answer-quality model.

Loads the trained model once and scores an analysis result with the
probability a human would mark it correct. Degrades gracefully: if the model
has not been trained yet, ``predict_quality`` returns ``None`` so callers can
skip the feature rather than error.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from ml.features import feature_vector

logger = logging.getLogger("trustguard.quality")

MODEL_PATH = os.path.join(os.path.dirname(__file__), "quality_model.joblib")

_bundle = None
_load_attempted = False


def _load():
    global _bundle, _load_attempted
    if _load_attempted:
        return _bundle
    _load_attempted = True
    if not os.path.exists(MODEL_PATH):
        logger.info("Quality model not found at %s — run ml.train_quality_model.", MODEL_PATH)
        return None
    try:
        import joblib

        _bundle = joblib.load(MODEL_PATH)
    except Exception:
        logger.exception("Failed to load the quality model.")
        _bundle = None
    return _bundle


def predict_quality(result: dict) -> Optional[dict]:
    """Estimate answer quality for an analysis result.

    Returns:
        {"quality_score": float 0..1, "label": str, "model": str} or None if
        the model is unavailable.
    """
    bundle = _load()
    if bundle is None:
        return None

    model = bundle["model"]
    row = [feature_vector(result)]
    try:
        score = float(model.predict_proba(row)[0][1])
    except Exception:
        logger.exception("Quality prediction failed.")
        return None

    if score >= 0.66:
        label = "Likely correct"
    elif score >= 0.4:
        label = "Needs review"
    else:
        label = "Likely unreliable"

    return {
        "quality_score": round(score, 4),
        "label": label,
        "model": bundle.get("metrics", {}).get("model", "unknown"),
    }
