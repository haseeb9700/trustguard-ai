"""Information-retrieval metrics for the TrustGuard retrieval eval.

Pure functions, no external dependencies, so they run in CI without a model
or database. Given a ranked list of retrieved chunk ids and the set of
relevant ids for a query, they compute the standard RAG-retrieval measures:
hit-rate@k, recall@k, precision@k, MRR, and nDCG@k.
"""

from __future__ import annotations

import math

DEFAULT_KS = [1, 3, 5]


def hit_at_k(ranked_ids: list, relevant: set, k: int) -> float:
    """1.0 if any relevant id appears in the top k, else 0.0 (a.k.a. success@k)."""
    return 1.0 if any(rid in relevant for rid in ranked_ids[:k]) else 0.0


def recall_at_k(ranked_ids: list, relevant: set, k: int) -> float:
    """Fraction of the relevant ids that appear in the top k."""
    if not relevant:
        return 0.0
    found = sum(1 for rid in ranked_ids[:k] if rid in relevant)
    return found / len(relevant)


def precision_at_k(ranked_ids: list, relevant: set, k: int) -> float:
    """Fraction of the top k that are relevant."""
    if k <= 0:
        return 0.0
    found = sum(1 for rid in ranked_ids[:k] if rid in relevant)
    return found / k


def reciprocal_rank(ranked_ids: list, relevant: set) -> float:
    """1 / rank of the first relevant id (0 if none retrieved)."""
    for i, rid in enumerate(ranked_ids, start=1):
        if rid in relevant:
            return 1.0 / i
    return 0.0


def ndcg_at_k(ranked_ids: list, relevant: set, k: int) -> float:
    """Binary-relevance normalized discounted cumulative gain at k."""
    dcg = 0.0
    for i, rid in enumerate(ranked_ids[:k], start=1):
        if rid in relevant:
            dcg += 1.0 / math.log2(i + 1)

    ideal_hits = min(len(relevant), k)
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_hits + 1))
    return dcg / idcg if idcg else 0.0


def compute_metrics(results: list, ks: list | None = None) -> dict:
    """Aggregate per-query metrics into dataset-level averages.

    Args:
        results: list of (ranked_ids, relevant_set) per query.
        ks: cutoff values for @k metrics (default [1, 3, 5]).

    Returns:
        A dict with mrr and, for each k, mean hit_rate / recall / precision / ndcg.
    """
    ks = ks or DEFAULT_KS
    n = len(results)
    if n == 0:
        return {"queries": 0, "mrr": 0.0, "at_k": {}}

    mrr = sum(reciprocal_rank(r, rel) for r, rel in results) / n

    at_k = {}
    for k in ks:
        at_k[k] = {
            "hit_rate": round(sum(hit_at_k(r, rel, k) for r, rel in results) / n, 4),
            "recall": round(sum(recall_at_k(r, rel, k) for r, rel in results) / n, 4),
            "precision": round(
                sum(precision_at_k(r, rel, k) for r, rel in results) / n, 4
            ),
            "ndcg": round(sum(ndcg_at_k(r, rel, k) for r, rel in results) / n, 4),
        }

    return {"queries": n, "mrr": round(mrr, 4), "at_k": at_k}


def format_comparison_report(
    runs: list,
    ks: list | None = None,
    corpus_size: int | None = None,
    instruction: bool = False,
) -> str:
    """Render several rankers side by side, cheapest first.

    A single ranker's scores are hard to read: is MRR 0.74 good? The answer is
    only visible in comparison — against the lexical floor below it and the
    next pipeline stage above it. Each row also carries its delta against the
    previous row, which is the actual quantity of interest when deciding
    whether a stage earns its latency.

    Args:
        runs: ordered list of (ranker_name, metrics) pairs.
        ks: cutoffs to tabulate (defaults to those present in the first run).
        corpus_size: number of chunks ranked, noted in the header.
        instruction: whether the BGE query instruction was applied.
    """
    if not runs:
        return "## TrustGuard Retrieval Eval\n\nNo runs.\n"

    ks = ks or sorted(runs[0][1]["at_k"])
    lines = ["## TrustGuard Retrieval Eval — Ranker Comparison\n"]

    header = f"**Queries:** {runs[0][1]['queries']}"
    if corpus_size:
        header += f"  |  **Corpus:** {corpus_size} chunks"
    header += f"  |  **BGE query instruction:** {'on' if instruction else 'off'}"
    lines.append(header + "\n")

    lines.append(
        "| Ranker | MRR | Δ MRR | " + " | ".join(f"nDCG@{k}" for k in ks) + " |"
    )
    lines.append("|---|---|---|" + "---|" * len(ks))

    prev_mrr = None
    for name, m in runs:
        delta = "—" if prev_mrr is None else f"{m['mrr'] - prev_mrr:+.3f}"
        ndcgs = " | ".join(f"{m['at_k'][k]['ndcg']:.3f}" for k in ks)
        lines.append(f"| {name} | {m['mrr']:.3f} | {delta} | {ndcgs} |")
        prev_mrr = m["mrr"]

    lines.append("\n### Hit-rate / Recall / Precision\n")
    lines.append("| Ranker | k | Hit-rate@k | Recall@k | Precision@k | nDCG@k |")
    lines.append("|---|---|---|---|---|---|")
    for name, m in runs:
        for k in ks:
            s = m["at_k"][k]
            lines.append(
                f"| {name} | {k} | {s['hit_rate']:.3f} | {s['recall']:.3f} | "
                f"{s['precision']:.3f} | {s['ndcg']:.3f} |"
            )

    return "\n".join(lines) + "\n"


def format_report(metrics: dict, ranker: str = "") -> str:
    """Render retrieval metrics as a Markdown report."""
    lines = []
    lines.append("## TrustGuard Retrieval Eval\n")
    header = f"**Queries:** {metrics['queries']}  |  **MRR:** {metrics['mrr']:.3f}"
    if ranker:
        header += f"  |  **Ranker:** {ranker}"
    lines.append(header + "\n")

    lines.append("| k | Hit-rate@k | Recall@k | Precision@k | nDCG@k |")
    lines.append("|---|---|---|---|---|")
    for k, m in metrics["at_k"].items():
        lines.append(
            f"| {k} | {m['hit_rate']:.3f} | {m['recall']:.3f} | "
            f"{m['precision']:.3f} | {m['ndcg']:.3f} |"
        )

    return "\n".join(lines) + "\n"
