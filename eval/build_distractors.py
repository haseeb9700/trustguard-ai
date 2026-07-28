"""Expand the retrieval eval corpus with real, unlabeled distractor chunks.

A benchmark is only as hard as the haystack. With 18 hand-written chunks the
gold answer is nearly always in the top few by construction, so scores sit
near the ceiling and real changes to the retriever vanish into noise. Adding
genuine chunks scraped from the live sources makes the ranking task realistic
without anyone having to label new query/chunk pairs.

The catch is false negatives: if an unlabeled distractor is *actually* relevant
to an existing query, the harness counts a correct retrieval as a miss and the
benchmark silently lies. Filtering by source title would be guesswork, so this
screens with the retriever itself.

Screening rule — a candidate is rejected if, for any query, it scores at least
as high as that query's weakest gold chunk. That is exactly the condition under
which it could displace a gold chunk in the ranking, so survivors are provably
incapable of manufacturing a false negative at any k. No arbitrary threshold is
involved.

Usage:
    python -m eval.build_distractors            # write eval/retrieval_corpus.jsonl
    python -m eval.build_distractors --dry-run  # report only, change nothing
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HERE = os.path.dirname(__file__)
CORPUS_PATH = os.path.join(HERE, "retrieval_corpus.jsonl")
QUERIES_PATH = os.path.join(HERE, "retrieval_queries.jsonl")
CHUNKS_CSV = os.path.join(os.path.dirname(HERE), "data", "rag_chunks.csv")

# Distractors are prefixed so they are obvious in reports and can never
# collide with a hand-written gold id (g1, g2, ...).
DISTRACTOR_PREFIX = "d"

MIN_WORDS = 25


def _load_jsonl(path: str) -> list:
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def load_gold_corpus() -> list:
    """Return only the hand-written gold chunks, dropping any prior distractors.

    Makes the script idempotent: re-running rebuilds the distractor set from
    scratch instead of stacking a second copy on top of the first.
    """
    return [
        c
        for c in _load_jsonl(CORPUS_PATH)
        if not str(c["id"]).startswith(DISTRACTOR_PREFIX)
    ]


def load_candidates() -> list:
    """Read scraped chunks from the RAG chunk CSV, deduped and length-filtered."""
    if not os.path.exists(CHUNKS_CSV):
        raise SystemExit(f"Missing {CHUNKS_CSV} — run the ingestion scripts first.")

    seen = set()
    candidates = []
    with open(CHUNKS_CSV, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            text = (row.get("chunk_text") or "").strip()
            if len(text.split()) < MIN_WORDS:
                continue
            key = text[:200]
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                {
                    "source_title": (row.get("source_title") or "").strip()
                    or "Unknown Source",
                    "text": text,
                }
            )
    return candidates


def screen(gold: list, queries: list, candidates: list) -> tuple:
    """Split candidates into (safe, rejected) using the gold-displacement rule.

    Args:
        gold: hand-written corpus chunks, each with "id" and "text".
        queries: eval queries, each with "query" and "relevant_ids".
        candidates: scraped chunks to screen.

    Returns:
        (safe, rejected) where rejected entries carry the query they collide
        with and the margin by which they beat the weakest gold chunk.
    """
    from modules.rag_pipeline import _get_embedding_model, cosine_similarity

    model = _get_embedding_model()

    gold_by_id = {c["id"]: c for c in gold}
    gold_ids = list(gold_by_id)
    gold_emb = dict(
        zip(
            gold_ids,
            model.encode([gold_by_id[i]["text"] for i in gold_ids]).tolist(),
            strict=True,
        )
    )
    query_emb = model.encode([q["query"] for q in queries]).tolist()
    cand_emb = model.encode([c["text"] for c in candidates]).tolist()

    # Per query, the weakest gold similarity is the bar a distractor must stay
    # under. Beat it and the distractor could outrank a gold chunk.
    bars = []
    for q, q_emb in zip(queries, query_emb, strict=True):
        rel = [r for r in q["relevant_ids"] if r in gold_emb]
        if not rel:
            continue
        bars.append((q, q_emb, min(cosine_similarity(q_emb, gold_emb[r]) for r in rel)))

    safe, rejected = [], []
    for cand, c_emb in zip(candidates, cand_emb, strict=True):
        worst = None
        for q, q_emb, bar in bars:
            score = cosine_similarity(q_emb, c_emb)
            if score >= bar and (worst is None or score - bar > worst[1]):
                worst = (q, score - bar, score, bar)
        if worst is None:
            safe.append(cand)
        else:
            q, margin, score, bar = worst
            rejected.append(
                {
                    **cand,
                    "collides_with": q.get("id"),
                    "query": q["query"],
                    "score": round(score, 4),
                    "gold_bar": round(bar, 4),
                    "margin": round(margin, 4),
                }
            )
    return safe, rejected


def main() -> int:
    parser = argparse.ArgumentParser(description="Build retrieval eval distractors")
    parser.add_argument(
        "--dry-run", action="store_true", help="Report only; do not write the corpus."
    )
    parser.add_argument(
        "--max", type=int, default=None, help="Cap the number of distractors kept."
    )
    args = parser.parse_args()

    gold = load_gold_corpus()
    queries = _load_jsonl(QUERIES_PATH)
    candidates = load_candidates()

    print(
        f"Gold chunks: {len(gold)}  |  Queries: {len(queries)}  "
        f"|  Candidate distractors: {len(candidates)}\n"
    )

    safe, rejected = screen(gold, queries, candidates)

    print(f"Rejected {len(rejected)} candidate(s) that could displace a gold chunk:")
    for r in sorted(rejected, key=lambda x: -x["margin"])[:15]:
        print(
            f"  {r['collides_with']:<4} margin=+{r['margin']:.3f} "
            f"(score {r['score']:.3f} vs gold bar {r['gold_bar']:.3f})  "
            f"{r['source_title'][:45]}"
        )
    if len(rejected) > 15:
        print(f"  ... and {len(rejected) - 15} more")

    if args.max:
        safe = safe[: args.max]

    corpus = list(gold)
    for i, cand in enumerate(safe, start=1):
        corpus.append(
            {
                "id": f"{DISTRACTOR_PREFIX}{i}",
                "source_title": cand["source_title"],
                "text": cand["text"],
                "distractor": True,
            }
        )

    print(
        f"\nKept {len(safe)} distractor(s). "
        f"Corpus: {len(gold)} gold + {len(safe)} distractors = {len(corpus)} chunks."
    )

    if args.dry_run:
        print("Dry run — corpus not written.")
        return 0

    with open(CORPUS_PATH, "w", encoding="utf-8") as fh:
        for row in corpus:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote {CORPUS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
