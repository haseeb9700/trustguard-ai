"""Scoring for the TrustGuard claim-verification eval harness.

Pure functions with no external dependencies so they can be unit-tested
in CI without an API key. The verdict taxonomy mirrors the production
verifier (modules/claim_verifier.py): entailed | contradicted | baseless.
"""

from __future__ import annotations

# Answer-level severity, worst first. A single contradicted claim condemns
# the whole answer; a single baseless claim floors it at baseless. This is
# the same AND-join precedence used by modules/risk_score.apply_claim_escalation,
# so the eval measures the system exactly as it behaves in production.
LABELS = ["entailed", "baseless", "contradicted"]
_SEVERITY = {"entailed": 0, "baseless": 1, "contradicted": 2}


def aggregate_verdict(claim_verification: list) -> str:
    """Collapse per-claim verdicts into a single answer-level verdict.

    Precedence: contradicted > baseless > entailed. An empty list (the
    verifier produced no claims / failed) is treated as ``baseless`` — the
    answer could not be grounded, which is the conservative governance call.
    """
    if not claim_verification:
        return "baseless"

    worst = "entailed"
    for claim in claim_verification:
        verdict = claim.get("verdict", "baseless")
        if verdict not in _SEVERITY:
            verdict = "baseless"
        if _SEVERITY[verdict] > _SEVERITY[worst]:
            worst = verdict
    return worst


def confusion_matrix(pairs: list, labels: list | None = None) -> dict:
    """Build a nested confusion matrix.

    Args:
        pairs: list of (gold, pred) verdict strings.
        labels: label order; defaults to LABELS.

    Returns:
        {gold_label: {pred_label: count}} covering every label pair.
    """
    labels = labels or LABELS
    matrix = {g: {p: 0 for p in labels} for g in labels}
    for gold, pred in pairs:
        if gold in matrix and pred in matrix[gold]:
            matrix[gold][pred] += 1
    return matrix


def _prf(tp: int, fp: int, fn: int) -> tuple:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall)
        else 0.0
    )
    return precision, recall, f1


def compute_metrics(pairs: list, labels: list | None = None) -> dict:
    """Compute per-class and aggregate classification metrics.

    Args:
        pairs: list of (gold, pred) verdict strings.
        labels: label order; defaults to LABELS.

    Returns:
        A dict with per_class precision/recall/f1/support, macro_f1,
        weighted_f1, accuracy, total, and the confusion matrix.
    """
    labels = labels or LABELS
    matrix = confusion_matrix(pairs, labels)
    total = len(pairs)

    per_class = {}
    correct = 0
    for label in labels:
        tp = matrix[label][label]
        fp = sum(matrix[g][label] for g in labels if g != label)
        fn = sum(matrix[label][p] for p in labels if p != label)
        support = sum(matrix[label][p] for p in labels)
        precision, recall, f1 = _prf(tp, fp, fn)
        per_class[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": support,
        }
        correct += tp

    macro_f1 = (
        sum(per_class[l]["f1"] for l in labels) / len(labels) if labels else 0.0
    )
    weighted_f1 = (
        sum(per_class[l]["f1"] * per_class[l]["support"] for l in labels) / total
        if total
        else 0.0
    )
    accuracy = correct / total if total else 0.0

    return {
        "total": total,
        "accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        "per_class": per_class,
        "confusion_matrix": matrix,
        "labels": labels,
    }


def format_report(metrics: dict) -> str:
    """Render metrics as a Markdown report (per-class table + confusion matrix)."""
    labels = metrics["labels"]
    lines = []
    lines.append("## TrustGuard Claim-Verification Eval\n")
    lines.append(
        f"**Cases:** {metrics['total']}  |  "
        f"**Accuracy:** {metrics['accuracy']:.1%}  |  "
        f"**Macro-F1:** {metrics['macro_f1']:.3f}  |  "
        f"**Weighted-F1:** {metrics['weighted_f1']:.3f}\n"
    )

    lines.append("### Per-class metrics\n")
    lines.append("| Verdict | Precision | Recall | F1 | Support |")
    lines.append("|---|---|---|---|---|")
    for label in labels:
        m = metrics["per_class"][label]
        lines.append(
            f"| {label} | {m['precision']:.3f} | {m['recall']:.3f} | "
            f"{m['f1']:.3f} | {m['support']} |"
        )

    lines.append("\n### Confusion matrix (rows = gold, cols = predicted)\n")
    header = "| gold \\ pred | " + " | ".join(labels) + " |"
    sep = "|---" * (len(labels) + 1) + "|"
    lines.append(header)
    lines.append(sep)
    matrix = metrics["confusion_matrix"]
    for gold in labels:
        row = " | ".join(str(matrix[gold][pred]) for pred in labels)
        lines.append(f"| {gold} | {row} |")

    return "\n".join(lines) + "\n"
