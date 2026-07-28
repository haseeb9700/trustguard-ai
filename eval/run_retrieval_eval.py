"""Evaluate TrustGuard retrieval quality against a labeled corpus + qrels.

RAG lives or dies on retrieval: if the right chunk is never retrieved, no
amount of clever answering recovers it. This harness ranks a fixed labeled
corpus for each query and reports hit-rate@k, recall@k, precision@k, MRR, and
nDCG@k — the standard measures of retrieval quality.

Rankers (``--ranker``):
    embedding  production embedding model (BAAI/bge-small) + cosine similarity,
               the real retrieval path. Downloads the model on first run.
    lexical    offline word-overlap baseline. No model, no network — the floor
               the embedding retriever should beat, and a CI smoke test.
    oracle     perfect ranking; verifies the scoring math (MRR / nDCG = 1.0).

The corpus is self-contained (eval/retrieval_corpus.jsonl), so the benchmark
is reproducible and independent of the live vector store.

Examples:
    python -m eval.run_retrieval_eval                     # real embedding model
    python -m eval.run_retrieval_eval --ranker lexical    # offline baseline
    python -m eval.run_retrieval_eval --ranker oracle
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eval.retrieval_metrics import compute_metrics, format_report

HERE = os.path.dirname(__file__)
CORPUS_PATH = os.path.join(HERE, "retrieval_corpus.jsonl")
QUERIES_PATH = os.path.join(HERE, "retrieval_queries.jsonl")
RESULTS_JSON = os.path.join(HERE, "retrieval_results.json")
REPORT_MD = os.path.join(HERE, "retrieval_report.md")

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
    "does",
    "do",
    "what",
    "when",
    "how",
    "many",
    "own",
    "not",
    "any",
}


def _tokens(text: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOPWORDS}


def _load_jsonl(path: str) -> list:
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def lexical_ranker(corpus: list):
    """Rank corpus ids by query/chunk token overlap (offline baseline)."""
    chunk_tokens = {c["id"]: _tokens(c["text"]) for c in corpus}

    def rank(query: str) -> list:
        q = _tokens(query)
        scored = [
            (cid, len(q & toks) / len(q | toks) if (q | toks) else 0.0)
            for cid, toks in chunk_tokens.items()
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [cid for cid, _ in scored]

    return rank


def embedding_ranker(corpus: list):
    """Rank corpus ids by cosine similarity of bge-small embeddings."""
    from modules.rag_pipeline import _get_embedding_model, cosine_similarity

    model = _get_embedding_model()
    ids = [c["id"] for c in corpus]
    embeddings = model.encode([c["text"] for c in corpus]).tolist()

    def rank(query: str) -> list:
        q_emb = model.encode([query]).tolist()[0]
        scored = [
            (cid, cosine_similarity(q_emb, emb))
            for cid, emb in zip(ids, embeddings, strict=True)
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [cid for cid, _ in scored]

    return rank


def oracle_ranker(corpus: list):
    """Perfect ranker: relevant ids first. Used to verify the metric math."""
    all_ids = [c["id"] for c in corpus]

    def rank_for(relevant: set) -> list:
        rel = [i for i in all_ids if i in relevant]
        rest = [i for i in all_ids if i not in relevant]
        return rel + rest

    return rank_for


def build_ranker(name: str, corpus: list):
    if name == "lexical":
        return lexical_ranker(corpus), False
    if name == "embedding":
        return embedding_ranker(corpus), False
    if name == "oracle":
        return oracle_ranker(corpus), True  # needs the relevant set, not the query
    raise ValueError(f"Unknown ranker: {name!r}")


def run(ranker_name: str, ks: list, limit: int | None = None) -> dict:
    corpus = _load_jsonl(CORPUS_PATH)
    queries = _load_jsonl(QUERIES_PATH)
    if limit:
        queries = queries[:limit]

    ranker, is_oracle = build_ranker(ranker_name, corpus)

    results = []
    per_query = []
    started = time.time()

    for q in queries:
        relevant = set(q["relevant_ids"])
        ranked = ranker(relevant) if is_oracle else ranker(q["query"])
        results.append((ranked, relevant))
        top_k = max(ks)
        per_query.append(
            {
                "id": q.get("id"),
                "query": q["query"],
                "relevant": sorted(relevant),
                "top": ranked[:top_k],
                "hit": any(r in relevant for r in ranked[:top_k]),
            }
        )
        flag = "ok " if per_query[-1]["hit"] else "MISS"
        print(
            f"  [{flag}] {q.get('id'):<5} top{top_k}={ranked[:top_k]}  rel={sorted(relevant)}"
        )

    metrics = compute_metrics(results, ks)
    return {
        "ranker": ranker_name,
        "elapsed_seconds": round(time.time() - started, 2),
        "metrics": metrics,
        "queries": per_query,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="TrustGuard retrieval eval")
    parser.add_argument(
        "--ranker",
        choices=["embedding", "lexical", "oracle"],
        default="embedding",
        help="Which retriever to score (default: embedding).",
    )
    parser.add_argument(
        "--k", default="1,3,5", help="Comma-separated cutoffs, e.g. 1,3,5"
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Only run first N queries"
    )
    parser.add_argument(
        "--no-write", action="store_true", help="Skip writing result files"
    )
    args = parser.parse_args()

    ks = [int(x) for x in args.k.split(",") if x.strip()]
    print(f"Running retrieval eval — ranker={args.ranker}, k={ks}\n")
    result = run(args.ranker, ks, args.limit)

    report = format_report(result["metrics"], ranker=args.ranker)
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
