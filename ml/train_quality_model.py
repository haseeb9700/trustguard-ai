"""Train the answer-quality model.

Learns to predict whether a human will mark an answer "Correct" from the
pipeline's own signals (hallucination score, risk, claim verdicts, retrieval
count). This gives TrustGuard a data-driven quality estimate that improves as
real feedback accumulates — complementing the rule-based risk score.

Data: a JSONL of result-shaped records, each with a "feedback" label
(see ml/quality_dataset.jsonl). Retrain on exported production feedback once
you have enough labeled examples.

Usage:
    python -m ml.train_quality_model                    # logistic regression
    python -m ml.train_quality_model --model gbdt       # gradient boosting
    python -m ml.train_quality_model --data path.jsonl
"""

from __future__ import annotations

import argparse
import json
import os

import joblib
import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml.features import FEATURE_NAMES, feature_vector, label_from_feedback

HERE = os.path.dirname(__file__)
DATA_PATH = os.path.join(HERE, "quality_dataset.jsonl")
MODEL_PATH = os.path.join(HERE, "quality_model.joblib")
METRICS_PATH = os.path.join(HERE, "quality_metrics.json")
REPORT_PATH = os.path.join(HERE, "quality_report.md")


def load_xy(path: str):
    X, y = [], []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            X.append(feature_vector(rec))
            y.append(label_from_feedback(rec.get("feedback", "")))
    return np.array(X, dtype=float), np.array(y, dtype=int)


def build_model(name: str):
    if name == "gbdt":
        return GradientBoostingClassifier(random_state=42)
    # Default: scaled logistic regression — interpretable coefficients matter
    # for a governance tool (you can explain why an answer was flagged).
    return Pipeline(
        [
            ("scale", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ]
    )


def _coefficients(model) -> dict:
    """Return per-feature weights if the model exposes them (logreg)."""
    clf = model.named_steps["clf"] if isinstance(model, Pipeline) else model
    if hasattr(clf, "coef_"):
        return {
            name: round(float(w), 4)
            for name, w in zip(FEATURE_NAMES, clf.coef_[0], strict=True)
        }
    if hasattr(clf, "feature_importances_"):
        return {
            name: round(float(w), 4)
            for name, w in zip(FEATURE_NAMES, clf.feature_importances_, strict=True)
        }
    return {}


def train(data_path: str, model_name: str) -> dict:
    X, y = load_xy(data_path)
    n = len(y)

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    model = build_model(model_name)
    model.fit(X_tr, y_tr)

    proba = model.predict_proba(X_te)[:, 1]
    pred = (proba >= 0.5).astype(int)

    baseline = DummyClassifier(strategy="most_frequent").fit(X_tr, y_tr)
    baseline_acc = accuracy_score(y_te, baseline.predict(X_te))

    cv = cross_val_score(build_model(model_name), X, y, cv=5, scoring="roc_auc")

    metrics = {
        "n_total": int(n),
        "n_train": int(len(y_tr)),
        "n_test": int(len(y_te)),
        "positive_rate": round(float(y.mean()), 4),
        "model": model_name,
        "accuracy": round(float(accuracy_score(y_te, pred)), 4),
        "baseline_accuracy": round(float(baseline_acc), 4),
        "roc_auc": round(float(roc_auc_score(y_te, proba)), 4),
        "precision": round(float(precision_score(y_te, pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_te, pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_te, pred, zero_division=0)), 4),
        "cv_roc_auc_mean": round(float(cv.mean()), 4),
        "cv_roc_auc_std": round(float(cv.std()), 4),
        "confusion_matrix": confusion_matrix(y_te, pred).tolist(),
        "feature_weights": _coefficients(model),
    }

    # Retrain on ALL data before saving — the split was only for evaluation.
    final = build_model(model_name)
    final.fit(X, y)
    joblib.dump(
        {"model": final, "feature_names": FEATURE_NAMES, "metrics": metrics},
        MODEL_PATH,
    )
    return metrics


def format_report(m: dict) -> str:
    lines = ["## TrustGuard Answer-Quality Model\n"]
    lines.append(
        f"**Model:** {m['model']}  |  **Examples:** {m['n_total']} "
        f"({m['positive_rate']:.0%} correct)\n"
    )
    lines.append("### Held-out performance\n")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Accuracy | {m['accuracy']:.3f} |")
    lines.append(f"| Baseline (majority) | {m['baseline_accuracy']:.3f} |")
    lines.append(f"| ROC-AUC | {m['roc_auc']:.3f} |")
    lines.append(f"| Precision | {m['precision']:.3f} |")
    lines.append(f"| Recall | {m['recall']:.3f} |")
    lines.append(f"| F1 | {m['f1']:.3f} |")
    lines.append(
        f"| 5-fold CV ROC-AUC | {m['cv_roc_auc_mean']:.3f} ± {m['cv_roc_auc_std']:.3f} |"
    )

    if m["feature_weights"]:
        lines.append("\n### Feature influence\n")
        lines.append("| Feature | Weight |")
        lines.append("|---|---|")
        for name, w in sorted(m["feature_weights"].items(), key=lambda kv: -abs(kv[1])):
            lines.append(f"| {name} | {w:+.3f} |")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Train the answer-quality model")
    parser.add_argument("--data", default=DATA_PATH)
    parser.add_argument("--model", choices=["logreg", "gbdt"], default="logreg")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    metrics = train(args.data, args.model)
    report = format_report(metrics)
    print(report)

    if not args.no_write:
        with open(METRICS_PATH, "w", encoding="utf-8") as fh:
            json.dump(metrics, fh, indent=2)
        with open(REPORT_PATH, "w", encoding="utf-8") as fh:
            fh.write(report)
        print(f"Saved model  -> {MODEL_PATH}")
        print(f"Wrote report -> {REPORT_PATH}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
