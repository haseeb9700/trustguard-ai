"""Evaluate TrustGuard retrieval quality against a labeled corpus + qrels.

RAG lives or dies on retrieval: if the right chunk is never retrieved, no
amount of clever answering recovers it. This harness ranks a fixed labeled
corpus for each query and reports hit-rate@k, recall@k, precision@k, MRR, and
nDCG@k — the standard measures of retrieval quality.

Rankers (``--ranker``):
    reranked   the full production path: embedding recall to a candidate pool,
               then cross-encoder reranking. This is what actually serves users,
               so it is the number that matters.
    embedding  embedding model (BAAI/bge-small) + cosine similarity only. The
               first stage in isolation; the gap to ``reranked`` is the
               reranker's measured contribution.
    lexical    offline word-overlap baseline. No model, no network — the floor
               the embedding retriever should beat, and a CI smoke test.
    oracle     perfect ranking; verifies the scoring math (MRR / nDCG = 1.0).

The corpus is self-contained (eval/retrieval_corpus.jsonl), so the benchmark
is reproducible and independent of the live vector store.

Examples:
    python -m eval.run_retrieval_eval                       # production path
    python -m eval.run_retrieval_eval --compare             # all rankers, one table
    python -m eval.run_retrieval_eval --ranker embedding    # first stage only
    python -m eval.run_retrieval_eval --ranker lexical      # offline baseline

    # Does BGE's retrieval instruction actually help? Measure, don't assume:
    python -m eval.run_retrieval_eval --ranker embedding --query-instruction
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eval.retrieval_metrics import (
    compute_metrics,
    format_comparison_report,
    format_report,
)

HERE = os.path.dirname(__file__)
CORPUS_PATH = os.path.join(HERE, "retrieval_corpus.jsonl")
QUERIES_PATH = os.path.join(HERE, "retrieval_queries.jsonl")
RESULTS_JSON = os.path.join(HERE, "retrieval_results.json")
REPORT_MD = os.path.join(HERE, "retrieval_report.md")

# Must match agents/retrieval_agent.CANDIDATE_POOL_SIZE, or the eval measures a
# pipeline that differs from the one in production.
CANDIDATE_POOL_SIZE = 15

# BGE is trained asymmetrically: short queries get an instruction prefix, long
# passages do not. BAAI report the gain is smaller for v1.5 than v1 (v1.5 was
# trained to work without it), so this is opt-in and worth measuring rather
# than assuming — which is the whole point of having this harness.
BGE_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "

# Cheapest first, so a --compare run fails fast before loading any model.
COMPARE_ORDER = [
    "lexical",
    "bm25",
    "embedding",
    "hybrid",
    "reranked",
    "hybrid_reranked",
]

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


def embedding_ranker(
    corpus: list, instruction: str = "", model_name: str | None = None
):
    """Rank corpus ids by cosine similarity of the embedding model.

    Args:
        corpus: chunks to rank.
        instruction: optional prefix applied to the *query only*. BGE is
            trained asymmetrically, so passages stay bare.
        model_name: override the configured model, for benchmarking. The corpus
            is re-encoded here on every call, so a swap needs no re-indexing to
            *measure* — only to deploy.
    """
    from modules.embeddings import get_embedding_model
    from modules.rag_pipeline import cosine_similarity

    model = get_embedding_model(model_name)
    ids = [c["id"] for c in corpus]
    embeddings = model.encode([c["text"] for c in corpus]).tolist()

    def rank(query: str) -> list:
        q_emb = model.encode([instruction + query]).tolist()[0]
        scored = [
            (cid, cosine_similarity(q_emb, emb))
            for cid, emb in zip(ids, embeddings, strict=True)
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [cid for cid, _ in scored]

    return rank


def bm25_ranker(corpus: list):
    """Rank corpus ids by Okapi BM25 — exact-term matching, no model."""
    from modules.hybrid_search import BM25

    index = BM25([(c["id"], c["text"]) for c in corpus])
    return index.rank


def hybrid_ranker(
    corpus: list,
    instruction: str = "",
    model_name: str | None = None,
    rrf_k: int = None,
    dense_weight: float = 1.0,
    lexical_weight: float = 1.0,
):
    """Fuse dense and BM25 rankings with reciprocal rank fusion.

    Dense retrieval handles paraphrase; BM25 handles the exact identifiers
    ("Form I-983", "8 CFR 214.2(f)") that embeddings blur together. Fusing by
    rank avoids having to reconcile their incomparable score scales.
    """
    from modules.hybrid_search import RRF_K, reciprocal_rank_fusion

    rrf_k = RRF_K if rrf_k is None else rrf_k
    dense = embedding_ranker(corpus, instruction=instruction, model_name=model_name)
    lexical = bm25_ranker(corpus)

    def rank(query: str) -> list:
        return reciprocal_rank_fusion(
            [dense(query), lexical(query)],
            k=rrf_k,
            weights=[dense_weight, lexical_weight],
        )

    return rank


def reranked_ranker(
    corpus: list,
    instruction: str = "",
    pool_size: int = CANDIDATE_POOL_SIZE,
    mmr_lambda: float | None = None,
    model_name: str | None = None,
    first_stage: str = "embedding",
):
    """Rank as production does: first-stage recall, then cross-encoder rerank.

    ``run_retrieval_agent`` pulls a wide candidate pool by embedding similarity
    and hands it to the cross-encoder, which reads each query/chunk pair
    properly instead of comparing two independently-computed vectors. Scoring
    only the embedding stage therefore measures something the user never sees.

    The reranker is applied to the pool; everything below the pool keeps its
    embedding order and is appended. So for k <= pool_size this is exactly the
    production ordering, and the metrics stay well-defined for larger k.
    """
    from modules.reranker import rerank_contexts

    if first_stage == "hybrid":
        embed_rank = hybrid_ranker(
            corpus, instruction=instruction, model_name=model_name
        )
    else:
        embed_rank = embedding_ranker(
            corpus, instruction=instruction, model_name=model_name
        )
    by_id = {c["id"]: c for c in corpus}

    def rank(query: str) -> list:
        ranked = embed_rank(query)
        pool, tail = ranked[:pool_size], ranked[pool_size:]
        contexts = [{"id": cid, "text": by_id[cid]["text"]} for cid in pool]
        reranked = rerank_contexts(
            query, contexts, top_k=len(contexts), mmr_lambda=mmr_lambda
        )
        return [c["id"] for c in reranked] + tail

    return rank


def oracle_ranker(corpus: list):
    """Perfect ranker: relevant ids first. Used to verify the metric math."""
    all_ids = [c["id"] for c in corpus]

    def rank_for(relevant: set) -> list:
        rel = [i for i in all_ids if i in relevant]
        rest = [i for i in all_ids if i not in relevant]
        return rel + rest

    return rank_for


def build_ranker(
    name: str,
    corpus: list,
    instruction: str = "",
    mmr_lambda: float | None = None,
    model_name: str | None = None,
):
    if name == "lexical":
        return lexical_ranker(corpus), False
    if name == "embedding":
        return embedding_ranker(
            corpus, instruction=instruction, model_name=model_name
        ), False
    if name == "bm25":
        return bm25_ranker(corpus), False
    if name == "hybrid":
        return hybrid_ranker(
            corpus, instruction=instruction, model_name=model_name
        ), False
    if name in ("reranked", "hybrid_reranked"):
        return reranked_ranker(
            corpus,
            instruction=instruction,
            mmr_lambda=mmr_lambda,
            model_name=model_name,
            first_stage="hybrid" if name == "hybrid_reranked" else "embedding",
        ), False
    if name == "oracle":
        return oracle_ranker(corpus), True  # needs the relevant set, not the query
    raise ValueError(f"Unknown ranker: {name!r}")


def run(
    ranker_name: str,
    ks: list,
    limit: int | None = None,
    instruction: str = "",
    verbose: bool = True,
    mmr_lambda: float | None = None,
    model_name: str | None = None,
) -> dict:
    corpus = _load_jsonl(CORPUS_PATH)
    queries = _load_jsonl(QUERIES_PATH)
    if limit:
        queries = queries[:limit]

    ranker, is_oracle = build_ranker(
        ranker_name,
        corpus,
        instruction=instruction,
        mmr_lambda=mmr_lambda,
        model_name=model_name,
    )

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
        if verbose:
            flag = "ok " if per_query[-1]["hit"] else "MISS"
            print(
                f"  [{flag}] {q.get('id'):<5} top{top_k}={ranked[:top_k]}  "
                f"rel={sorted(relevant)}"
            )

    metrics = compute_metrics(results, ks)
    return {
        "ranker": ranker_name,
        "query_instruction": bool(instruction),
        "mmr_lambda": mmr_lambda,
        "embedding_model": model_name or "default",
        "corpus_size": len(corpus),
        "elapsed_seconds": round(time.time() - started, 2),
        "metrics": metrics,
        "queries": per_query,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="TrustGuard retrieval eval")
    parser.add_argument(
        "--ranker",
        choices=[
            "reranked",
            "hybrid_reranked",
            "hybrid",
            "embedding",
            "bm25",
            "lexical",
            "oracle",
        ],
        default="reranked",
        help="Which retriever to score (default: reranked, the production path).",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Score every ranker and write one side-by-side table.",
    )
    parser.add_argument(
        "--query-instruction",
        action="store_true",
        help="Prefix queries with BGE's retrieval instruction (queries only).",
    )
    parser.add_argument(
        "--embedding-model",
        default=None,
        metavar="NAME",
        help="Override the embedding model, e.g. BAAI/bge-base-en-v1.5",
    )
    parser.add_argument(
        "--embedding-sweep",
        default=None,
        metavar="NAMES",
        help="Comma-separated models to compare on the same corpus.",
    )
    parser.add_argument(
        "--mmr",
        type=float,
        default=None,
        metavar="LAMBDA",
        help="Apply MMR after reranking. 1.0 = pure relevance, 0.0 = pure diversity.",
    )
    parser.add_argument(
        "--mmr-sweep",
        default=None,
        metavar="LAMBDAS",
        help="Comma-separated lambdas to compare, e.g. 1.0,0.9,0.7,0.5",
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
    instruction = BGE_QUERY_INSTRUCTION if args.query_instruction else ""

    if args.embedding_sweep:
        names = [n.strip() for n in args.embedding_sweep.split(",") if n.strip()]
        runs = []
        for name in names:
            print(f"\n--- {name} ---")
            runs.append(
                run(
                    args.ranker,
                    ks,
                    args.limit,
                    instruction,
                    verbose=False,
                    mmr_lambda=args.mmr,
                    model_name=name,
                )
            )
            m = runs[-1]["metrics"]
            print(f"  MRR {m['mrr']:.3f}  |  {runs[-1]['elapsed_seconds']}s")
        report = format_comparison_report(
            [
                (n.split("/")[-1], r["metrics"])
                for n, r in zip(names, runs, strict=True)
            ],
            ks,
            corpus_size=runs[0]["corpus_size"],
            instruction=bool(instruction),
        )
        result = {"mode": "embedding_sweep", "models": names, "runs": runs}
        print("\n" + report)
        print(
            "\nNote: swapping the embedding model requires re-embedding the whole\n"
            "vector store. Stored vectors come from the old model and are not\n"
            "comparable to new query vectors — and the widths differ."
        )
        if not args.no_write:
            with open(RESULTS_JSON, "w", encoding="utf-8") as fh:
                json.dump(result, fh, indent=2)
            with open(REPORT_MD, "w", encoding="utf-8") as fh:
                fh.write(report)
        return 0

    if args.mmr_sweep:
        lambdas = [float(x) for x in args.mmr_sweep.split(",") if x.strip()]
        runs = []
        for lam in lambdas:
            print(f"\n--- reranked, mmr lambda={lam} ---")
            runs.append(
                run(
                    "reranked",
                    ks,
                    args.limit,
                    instruction,
                    verbose=False,
                    mmr_lambda=lam,
                )
            )
            m = runs[-1]["metrics"]
            print(f"  MRR {m['mrr']:.3f}  |  {runs[-1]['elapsed_seconds']}s")
        report = format_comparison_report(
            [
                (f"mmr λ={lam}", r["metrics"])
                for lam, r in zip(lambdas, runs, strict=True)
            ],
            ks,
            corpus_size=runs[0]["corpus_size"],
            instruction=bool(instruction),
        )
        result = {"mode": "mmr_sweep", "lambdas": lambdas, "runs": runs}
        print("\n" + report)
        if not args.no_write:
            with open(RESULTS_JSON, "w", encoding="utf-8") as fh:
                json.dump(result, fh, indent=2)
            with open(REPORT_MD, "w", encoding="utf-8") as fh:
                fh.write(report)
        return 0

    if args.compare:
        runs = []
        for name in COMPARE_ORDER:
            print(f"\n--- {name} ---")
            runs.append(
                run(
                    name,
                    ks,
                    args.limit,
                    instruction,
                    verbose=False,
                    mmr_lambda=args.mmr,
                )
            )
            m = runs[-1]["metrics"]
            print(f"  MRR {m['mrr']:.3f}  |  {runs[-1]['elapsed_seconds']}s")
        report = format_comparison_report(
            [(r["ranker"], r["metrics"]) for r in runs],
            ks,
            corpus_size=runs[0]["corpus_size"],
            instruction=bool(instruction),
        )
        result = {
            "mode": "compare",
            "query_instruction": bool(instruction),
            "corpus_size": runs[0]["corpus_size"],
            "runs": runs,
        }
    else:
        print(f"Running retrieval eval — ranker={args.ranker}, k={ks}\n")
        result = run(
            args.ranker,
            ks,
            args.limit,
            instruction,
            mmr_lambda=args.mmr,
            model_name=args.embedding_model,
        )
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
