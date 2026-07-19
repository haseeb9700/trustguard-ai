"""Tests for the answer-quality model.

Feature extraction is pure and always tested. The training/prediction tests
require scikit-learn and are skipped if it is unavailable.
"""

import pytest

from ml.features import (
    FEATURE_NAMES,
    extract_features,
    feature_vector,
    label_from_feedback,
)

SAMPLE_GOOD = {
    "answer": "The regular H-1B cap is 65,000 visas.",
    "hallucination_analysis": {"hallucination_score": 0},
    "risk_analysis": {"risk_level": "Low", "risk_score": 0},
    "claim_verification": [{"verdict": "entailed"}, {"verdict": "entailed"}],
    "retrieved_context_count": 5,
    "sources": [{"title": "A", "url": ""}, {"title": "B", "url": ""}],
}

SAMPLE_BAD = {
    "answer": "I could not verify this from the provided sources.",
    "hallucination_analysis": {"hallucination_score": 2},
    "risk_analysis": {"risk_level": "High", "risk_score": 2},
    "claim_verification": [{"verdict": "contradicted"}, {"verdict": "baseless"}],
    "retrieved_context_count": 1,
    "sources": [],
}


# --- feature extraction ----------------------------------------------------

def test_feature_vector_length_matches_names():
    assert len(feature_vector(SAMPLE_GOOD)) == len(FEATURE_NAMES)


def test_extract_good_example():
    f = extract_features(SAMPLE_GOOD)
    assert f["hallucination_score"] == 0
    assert f["risk_score"] == 0
    assert f["n_claims"] == 2
    assert f["n_entailed"] == 2
    assert f["frac_entailed"] == 1.0
    assert f["n_sources"] == 2
    assert f["unverified_flag"] == 0


def test_extract_bad_example():
    f = extract_features(SAMPLE_BAD)
    assert f["risk_score"] == 2
    assert f["n_contradicted"] == 1
    assert f["n_baseless"] == 1
    assert f["frac_entailed"] == 0.0
    assert f["unverified_flag"] == 1
    assert f["n_sources"] == 0


def test_risk_level_fallback_when_no_score():
    f = extract_features({"risk_analysis": {"risk_level": "Medium"}})
    assert f["risk_score"] == 1


def test_missing_fields_default_safely():
    f = extract_features({})
    assert f["hallucination_score"] == 2  # unknown → worst
    assert f["n_claims"] == 0
    assert f["frac_entailed"] == 0.0


def test_label_from_feedback():
    assert label_from_feedback("Correct") == 1
    assert label_from_feedback("correct") == 1
    assert label_from_feedback("Partially Correct") == 0
    assert label_from_feedback("Incorrect") == 0


# --- training + prediction (need scikit-learn) -----------------------------

def test_training_beats_baseline_and_predicts():
    pytest.importorskip("sklearn")
    from ml import predict
    from ml.train_quality_model import DATA_PATH, train

    metrics = train(DATA_PATH, "logreg")
    assert metrics["roc_auc"] >= 0.7
    assert metrics["accuracy"] >= metrics["baseline_accuracy"]
    assert metrics["confusion_matrix"]

    # Force a fresh load of the model just written by train().
    predict._bundle = None
    predict._load_attempted = False

    good = predict.predict_quality(SAMPLE_GOOD)
    bad = predict.predict_quality(SAMPLE_BAD)
    assert good is not None and bad is not None
    assert 0.0 <= good["quality_score"] <= 1.0
    # A clean, fully-entailed answer should score higher than a contradicted one.
    assert good["quality_score"] > bad["quality_score"]
