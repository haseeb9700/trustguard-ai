"""Quality checks on the retrieval query set, for human review.

Two failure modes make a retrieval benchmark quietly worthless:

1. **Lexical transparency.** If a query reuses its gold chunk's distinctive
   wording, word overlap alone finds it and the benchmark stops measuring
   semantic retrieval.

2. **Ambiguous labels.** If some *other* chunk answers the query at least as
   well as the labelled one, a correct retrieval is scored as a miss.

For (1) the obvious approach — flagging queries whose token overlap with their
gold chunk exceeds some threshold — does not survive contact with the data. Any
threshold low enough to catch real leaks also flags hand-written paraphrases,
because short questions share function words with everything. So transparency
is measured with the lexical ranker instead: if word overlap puts the gold
chunk first, overlap solves that query, by definition and with no threshold to
argue about.

That is reported as a corpus-level difficulty statistic, not a pass/fail gate.
Some questions legitimately share vocabulary with their answer, and real IR
benchmarks do not exclude them. The per-query list is a shortlist of rewording
candidates for a human, nothing more.

**This script deliberately prunes nothing.** It is tempting to drop every query
the retriever gets wrong, but that is exactly backwards: it would delete the
hard cases the benchmark exists to expose and leave a set the retriever passes
by construction. Only a human can tell "this label is wrong" from "the
retriever is wrong", and the second kind must be kept.

Usage:
    python -m eval.validate_queries              # difficulty report, no model
    python -m eval.validate_queries --rank       # add the embedding review pass
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eval.run_retrieval_eval import (  # noqa: E402
    CORPUS_PATH,
    QUERIES_PATH,
    _load_jsonl,
    _tokens,
    lexical_ranker,
)


def check_transparency(queries: list, corpus: list) -> list:
    """Return queries the lexical ranker solves outright, worst first.

    "Solved" means a gold chunk lands at rank 1 on word overlap alone. The
    reported share of shared content words is context for a human deciding
    whether to reword — it is not what determines the flag.
    """
    rank = lexical_ranker(corpus)
    by_id = {c["id"]: c for c in corpus}

    solved = []
    for q in queries:
        ranked = rank(q["query"])
        relevant = set(q["relevant_ids"])
        if not ranked or ranked[0] not in relevant:
            continue

        q_tok = _tokens(q["query"])
        gold_tok = _tokens(by_id[ranked[0]]["text"])
        shared = q_tok & gold_tok
        solved.append(
            {
                "id": q["id"],
                "gold": ranked[0],
                "overlap": round(len(shared) / len(q_tok), 3) if q_tok else 0.0,
                "shared": sorted(shared),
                "query": q["query"],
            }
        )
    return sorted(solved, key=lambda x: -x["overlap"])


def check_ranking(queries: list, corpus: list) -> list:
    """Return queries whose gold chunk is not ranked first by the embedder.

    Each hit needs a human verdict: an unlabelled chunk that genuinely answers
    the query is a labelling bug, but a chunk that merely *looks* similar is a
    real retrieval failure and belongs in the benchmark.
    """
    from eval.run_retrieval_eval import embedding_ranker

    rank = embedding_ranker(corpus)
    by_id = {c["id"]: c for c in corpus}

    flagged = []
    for q in queries:
        ranked = rank(q["query"])
        relevant = set(q["relevant_ids"])
        if ranked and ranked[0] in relevant:
            continue
        position = next((i for i, r in enumerate(ranked, 1) if r in relevant), None)
        flagged.append(
            {
                "id": q["id"],
                "query": q["query"],
                "gold": sorted(relevant),
                "gold_rank": position,
                "beaten_by": [
                    {
                        "id": cid,
                        "title": by_id[cid]["source_title"],
                        "text": " ".join(by_id[cid]["text"].split())[:160],
                    }
                    for cid in ranked[:3]
                    if cid not in relevant
                ],
            }
        )
    return flagged


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate retrieval eval queries")
    parser.add_argument(
        "--rank",
        action="store_true",
        help="Also run the embedding review pass (loads the model).",
    )
    parser.add_argument(
        "--show",
        type=int,
        default=10,
        help="How many lexically-transparent queries to list (default 10).",
    )
    args = parser.parse_args()

    queries = _load_jsonl(QUERIES_PATH)
    corpus = _load_jsonl(CORPUS_PATH)
    print(f"Queries: {len(queries)}  |  Corpus: {len(corpus)} chunks\n")

    solved = check_transparency(queries, corpus)
    share = len(solved) / len(queries) if queries else 0.0
    print("— Corpus difficulty: solvable by word overlap alone")
    print(
        f"  {len(solved)}/{len(queries)} ({share:.0%}) have their gold chunk "
        f"ranked first by the lexical baseline."
    )
    print("  Lower is harder. These are reword candidates, not errors:\n")
    for f in solved[: args.show]:
        print(f"  {f['id']} -> {f['gold']}  shares {f['overlap']:.0%} of its words")
        print(f"      {', '.join(f['shared'])}")
        print(f"      {f['query']}")
    if len(solved) > args.show:
        print(f"  ... and {len(solved) - args.show} more")
    print()

    if args.rank:
        print("— Gold chunk not ranked first (REVIEW, not auto-fix)")
        flagged = check_ranking(queries, corpus)
        if not flagged:
            print("  none.\n")
        for f in flagged:
            print(f"  {f['id']}  gold={f['gold']}  gold_rank={f['gold_rank']}")
            print(f"      {f['query']}")
            for b in f["beaten_by"]:
                print(
                    f"      beaten by [{b['id']}] ({b['title'][:34]}) {b['text'][:110]}"
                )
            print()
        print(
            "  For each: does the competing chunk actually answer the question?\n"
            "  If yes, add it to relevant_ids — the label was incomplete.\n"
            "  If no, leave it alone. That is a real retrieval failure and it is\n"
            "  the signal this benchmark exists to capture."
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
