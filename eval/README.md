# TrustGuard Eval Harness

A reproducible benchmark for the claim-level hallucination detector
(`modules/claim_verifier.py`). It turns "I rebuilt verification" into a
concrete, defensible number: **precision / recall / F1 per verdict class**
plus a confusion matrix.

## What it measures

Each labeled case in `dataset.jsonl` has an `answer`, its retrieved
`contexts`, and a gold verdict:

- **entailed** — the context supports the answer
- **baseless** — the context has no evidence for it
- **contradicted** — the context states the opposite

The verifier's per-claim verdicts are collapsed to one answer-level verdict
using the same AND-join precedence as production risk scoring
(`contradicted > baseless > entailed`), then compared to gold. So the eval
scores the system exactly as it behaves live.

## Run it

```bash
# Real production verifier (needs OPENAI_API_KEY, makes API calls)
python -m eval.run_eval

# Offline word-overlap baseline — no key, no cost. This is the "holistic
# scorer" floor your claim verifier should beat, especially on contradictions.
python -m eval.run_eval --verifier lexical

# Sanity check the scoring math (should print macro-F1 = 1.000)
python -m eval.run_eval --verifier oracle

# Quick smoke run
python -m eval.run_eval --limit 5 --verifier lexical
```

Each run writes `results.json` (full per-case detail) and `report.md`
(the Markdown table below).

## Baseline result

The offline lexical baseline over the 30-case set:

| Verifier | Accuracy | Macro-F1 | Contradicted F1 |
|---|---|---|---|
| lexical (word overlap) | 70.0% | 0.549 | **0.000** |
| oracle (upper bound) | 100.0% | 1.000 | 1.000 |

The baseline never detects a single contradiction — the exact failure mode
the hierarchical claim verifier is built to fix. Run `--verifier llm` to fill
in the production number and quote the lift over this baseline.

## Files

- `dataset.jsonl` — 30 labeled cases across AI governance, immigration,
  finance, and healthcare (balanced across the three verdict classes).
- `metrics.py` — pure scoring functions (aggregation, P/R/F1, confusion
  matrix, Markdown report). Unit-tested in `tests/test_eval_metrics.py`.
- `run_eval.py` — CLI runner with `llm` / `lexical` / `oracle` verifiers.

## Retrieval eval

RAG answers are only as good as what gets retrieved, so retrieval is
benchmarked on its own against a labeled corpus and query-relevance set.

```bash
python -m eval.run_retrieval_eval                     # bge-small + cosine (real path)
python -m eval.run_retrieval_eval --ranker lexical    # offline word-overlap baseline
python -m eval.run_retrieval_eval --ranker oracle     # verify metric math (MRR/nDCG = 1.0)
```

Reports hit-rate@k, recall@k, precision@k, MRR, and nDCG@k over `k = 1,3,5`
and writes `retrieval_results.json` + `retrieval_report.md`.

Baseline (lexical word-overlap, 15 paraphrased queries):

| k | Hit-rate@k | Recall@k | MRR |
|---|---|---|---|
| 1 | 0.60 | 0.57 | 0.74 |
| 5 | 0.93 | 0.93 | — |

Queries are paraphrased with synonyms so surface-term overlap alone can't solve
them — the embedding retriever should beat this baseline, especially at k=1.

Files: `retrieval_corpus.jsonl` (18 labeled chunks), `retrieval_queries.jsonl`
(15 queries with relevant ids), `retrieval_metrics.py`, `run_retrieval_eval.py`.
Metrics and rankers are unit-tested in `tests/test_retrieval_metrics.py`.

## Extending the dataset

Append JSONL rows in the same shape:

```json
{"id": "gov-07", "domain": "ai_governance", "gold": "contradicted",
 "answer": "…", "contexts": [{"source_title": "…", "text": "…"}]}
```

Keep contexts short and self-contained so the benchmark stays independent of
the live vector store.
