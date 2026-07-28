"""Evaluate the TrustGuard claim verifier against a labeled dataset.

Runs each labeled case through a verifier, aggregates the per-claim verdicts
to an answer-level verdict, and reports precision / recall / F1 and a confusion
matrix — giving a concrete, reproducible accuracy number for the hallucination
detector instead of a vibes-based claim.

Verifiers (``--verifier``):
    llm      production hierarchical verifier (modules/claim_verifier). Needs
             OPENAI_API_KEY and makes API calls (default).
    lexical  offline word-overlap baseline. No API key, no cost — use it as
             the "holistic scorer" baseline the claim verifier should beat,
             and to smoke-test the harness in CI.
    oracle   returns the gold label; verifies the scoring math (macro-F1 = 1.0).

Examples:
    python -m eval.run_eval                       # real LLM verifier
    python -m eval.run_eval --verifier lexical    # offline baseline
    python -m eval.run_eval --limit 5 --verifier oracle
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time

# Allow "python eval/run_eval.py" as well as "python -m eval.run_eval".
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eval.metrics import aggregate_verdict, compute_metrics, format_report

DATASET_PATH = os.path.join(os.path.dirname(__file__), "dataset.jsonl")
RESULTS_JSON = os.path.join(os.path.dirname(__file__), "results.json")
REPORT_MD = os.path.join(os.path.dirname(__file__), "report.md")

_STOPWORDS = {
    "the",
    "a",
    "an",
    "of",
    "to",
    "in",
    "on",
    "for",
    "and",
    "or",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "by",
    "as",
    "at",
    "it",
    "its",
    "that",
    "this",
    "with",
    "from",
    "than",
    "into",
    "under",
    "over",
    "their",
    "they",
    "them",
    "which",
    "who",
    "whom",
    "whose",
    "not",
    "no",
    "any",
    "all",
    "each",
    "per",
}


def _tokens(text: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOPWORDS}


def lexical_verifier(answer: str, contexts: list) -> list:
    """Offline baseline: label the whole answer by token overlap with context.

    Deliberately naive — it cannot detect contradiction (it never predicts it),
    which is exactly why a holistic/lexical scorer is weak and the LLM
    claim verifier is expected to win on the contradicted class.
    """
    answer_tokens = _tokens(answer)
    if not answer_tokens:
        return [{"claim": answer, "verdict": "baseless"}]

    context_tokens = set()
    for chunk in contexts:
        context_tokens |= _tokens(chunk.get("text", ""))

    overlap = len(answer_tokens & context_tokens) / len(answer_tokens)
    verdict = "entailed" if overlap >= 0.6 else "baseless"
    return [{"claim": answer, "verdict": verdict, "overlap": round(overlap, 3)}]


def load_dataset(path: str, limit: int | None = None) -> list:
    cases = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases[:limit] if limit else cases


def build_verifier(name: str):
    """Return a callable (answer, contexts, gold) -> answer_level_verdict."""
    if name == "lexical":
        return lambda answer, contexts, gold: aggregate_verdict(
            lexical_verifier(answer, contexts)
        )

    if name == "oracle":
        return lambda answer, contexts, gold: gold

    if name == "llm":
        from modules.claim_verifier import verify_claims

        return lambda answer, contexts, gold: aggregate_verdict(
            verify_claims(answer, contexts)
        )

    raise ValueError(f"Unknown verifier: {name!r}")


def run(dataset_path: str, verifier_name: str, limit: int | None) -> dict:
    cases = load_dataset(dataset_path, limit)
    verify = build_verifier(verifier_name)

    pairs = []
    per_case = []
    started = time.time()

    for case in cases:
        gold = case["gold"]
        pred = verify(case["answer"], case.get("contexts", []), gold)
        correct = pred == gold
        pairs.append((gold, pred))
        per_case.append(
            {
                "id": case.get("id"),
                "domain": case.get("domain"),
                "gold": gold,
                "pred": pred,
                "correct": correct,
            }
        )
        flag = "ok " if correct else "MISS"
        print(f"  [{flag}] {case.get('id'):<10} gold={gold:<12} pred={pred}")

    metrics = compute_metrics(pairs)
    elapsed = round(time.time() - started, 2)

    return {
        "verifier": verifier_name,
        "dataset": os.path.basename(dataset_path),
        "elapsed_seconds": elapsed,
        "metrics": metrics,
        "cases": per_case,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="TrustGuard claim-verification eval")
    parser.add_argument(
        "--verifier",
        choices=["llm", "lexical", "oracle"],
        default="llm",
        help="Which verifier to score (default: llm).",
    )
    parser.add_argument("--dataset", default=DATASET_PATH, help="Path to dataset.jsonl")
    parser.add_argument(
        "--limit", type=int, default=None, help="Only run first N cases"
    )
    parser.add_argument(
        "--no-write", action="store_true", help="Do not write results.json / report.md"
    )
    args = parser.parse_args()

    print(f"Running eval — verifier={args.verifier}\n")
    result = run(args.dataset, args.verifier, args.limit)

    report = format_report(result["metrics"])
    print("\n" + report)

    if not args.no_write:
        with open(RESULTS_JSON, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2)
        with open(REPORT_MD, "w", encoding="utf-8") as fh:
            fh.write(report)
        print(f"Wrote {RESULTS_JSON}")
        print(f"Wrote {REPORT_MD}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
