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
python -m eval.run_retrieval_eval                    # production path (embed + rerank)
python -m eval.run_retrieval_eval --compare         # every ranker, one table
python -m eval.run_retrieval_eval --ranker embedding # first stage alone
python -m eval.run_retrieval_eval --ranker lexical   # offline baseline, no model
python -m eval.run_retrieval_eval --ranker oracle    # verify math (MRR/nDCG = 1.0)
```

Reports hit-rate@k, recall@k, precision@k, MRR, and nDCG@k over `k = 1,3,5`
and writes `retrieval_results.json` + `retrieval_report.md`.

### Rankers

| Ranker | What it measures |
|---|---|
| `lexical` | Word-overlap floor. No model, no network — the number the embedding retriever must beat. |
| `embedding` | `bge-small` + cosine similarity: recall stage only. |
| `reranked` | **The production path.** Embedding recall to a 15-chunk pool, then cross-encoder rerank. |
| `oracle` | Perfect ranking; asserts the metric math is right. |

The gap between `embedding` and `reranked` *is* the reranker's contribution.
Measuring only the embedding stage scores a pipeline no user ever hits.

### Results (54 queries, 93 chunks)

| Ranker | MRR | Δ MRR | Hit-rate@1 | nDCG@5 |
|---|---|---|---|---|
| lexical | 0.348 | — | 0.204 | 0.386 |
| embedding | 0.665 | +0.318 | 0.537 | 0.682 |
| reranked | **0.739** | **+0.073** | **0.648** | 0.757 |

**The cross-encoder earns its latency.** +0.073 MRR and +0.111 hit-rate@1 over
embedding alone — six more queries out of 54 where the right chunk lands first.

That conclusion is the opposite of what an earlier version of this benchmark
reported. At 15 queries over 18 chunks the reranker appeared to *hurt*
(MRR 0.967 → 0.947), but the entire difference was two queries changing rank,
where one query is worth ~0.067 MRR. The effect was never resolvable at that
size. Worth remembering before acting on a small eval: the honest reading of an
underpowered result is "unresolved", not "no effect".

### Does the BGE instruction help? No.

`bge-small-en-v1.5` is trained asymmetrically — short queries take an
instruction prefix, long passages do not:

```bash
python -m eval.run_retrieval_eval --compare --query-instruction
```

Measured effect at 54 queries: MRR 0.665 → 0.668 (embedding), 0.739 → 0.740
(reranked), hit-rate@1 unchanged to three decimals. It is not applied in
production.

On the earlier saturated 15-query set it looked like a clear win
(MRR 0.967 → 1.000) — but that was one query moving on a benchmark with no
headroom left. BAAI themselves note the gain is smaller for v1.5 than v1, since
v1.5 was trained to work without it.

### Corpus difficulty

A benchmark that everything passes measures nothing. The first version of this
set (15 queries, 18 chunks) hit **MRR 1.000** once the BGE query instruction
was switched on — completely saturated, so no later change could register.

Difficulty comes from two places, and both are checked rather than assumed.

**Query wording.** Queries are paraphrased so surface-term overlap alone
cannot find the answer. `validate_queries.py` measures this by asking whether
the lexical ranker solves a query outright:

```bash
python -m eval.validate_queries          # difficulty report, no model needed
python -m eval.validate_queries --rank   # review pass over gold labels
```

An earlier version flagged queries whose token overlap with the gold chunk
crossed a threshold. That approach was dropped: any threshold low enough to
catch real leaks also flagged hand-written paraphrases, because short questions
share function words with everything. Using the lexical ranker replaces the
arbitrary threshold with a direct answer to the actual question — if word
overlap ranks the gold chunk first, word overlap solves it.

Current: **11/54 (20%)** solvable lexically, giving the lexical floor
**MRR 0.345** (down from 0.727 on the original 15). The report lists the
transparent queries as rewording candidates, not errors — some questions
legitimately share vocabulary with their answer, and real IR benchmarks keep
them.

`--rank` reports queries whose gold chunk is not ranked first by the embedder.
It **prunes nothing**. Dropping every query the retriever fails would delete
the hard cases the benchmark exists to expose and leave a set that passes by
construction. Each flagged query needs a human verdict: if the competing chunk
genuinely answers the question the label was incomplete and should be extended;
if it does not, that is a real retrieval failure and belongs in the benchmark.

**Corpus size.** A benchmark is only as hard as its haystack: with a handful of
gold chunks the answer is in the top few by construction. `build_distractors.py`
pads the corpus with genuine scraped chunks:

```bash
python -m eval.build_distractors --dry-run   # see what would be kept/rejected
python -m eval.build_distractors             # rewrite retrieval_corpus.jsonl
```

Unlabeled distractors risk false negatives — a distractor that is *actually*
relevant turns a correct retrieval into a recorded miss. Rather than guess from
source titles, each candidate is screened with the retriever itself and
rejected if it scores at least as high as that query's weakest gold chunk.
That is precisely the condition for displacing a gold chunk, so survivors
cannot manufacture a false negative at any k, and no arbitrary threshold is
involved. The script is idempotent: it rebuilds the distractor set from the
gold chunks each run rather than stacking copies.

### What the failures pointed at

Reviewing the 22 genuine retrieval failures surfaced three ingestion defects,
each since fixed:

- **Boilerplate outranked answers.** Two pure footnote-index chunks beat the
  chunk quoting the statute a query asked about. Across the benchmark, 8% of
  top-3 slots and 13/54 queries had site chrome or citation dumps in them.
  Fixed by `modules/content_filter.py`, applied at ingest.
- **Chunks began mid-sentence.** Fixed-width 400-word slicing left **59.5%** of
  chunks opening with a dangling clause whose subject was in the *previous*
  chunk. One such chunk contained a query's answer verbatim and was retrieved
  at rank 28 of 93. Sentence-aligned chunking brings that to **4.7%**.
- **Near-duplicate chunks split each other's signal**, from 80-word overlap
  plus overlapping source documents. Not yet addressed — MMR at the rerank
  step is the candidate fix.

**The benchmark corpus is frozen.** Ingestion changes are deliberately *not*
folded back into `retrieval_corpus.jsonl`: rebuilding it would renumber every
`d*` id and invalidate all 39 distractor-based labels, and a corpus that
shrinks whenever the filter improves would show rising scores purely from a
smaller haystack. Ingestion changes are measured on their own terms (fragment
rate, boilerplate share) rather than by moving the benchmark under itself.

Files: `retrieval_corpus.jsonl` (18 gold chunks + 75 `d*` distractors),
`retrieval_queries.jsonl` (54 queries with relevant ids),
`retrieval_metrics.py`, `run_retrieval_eval.py`, `build_distractors.py`,
`validate_queries.py`.
Metrics and rankers are unit-tested in `tests/test_retrieval_metrics.py` and
`tests/test_retrieval_eval_rankers.py` (models stubbed, so CI needs neither).

## Extending the dataset

Append JSONL rows in the same shape:

```json
{"id": "gov-07", "domain": "ai_governance", "gold": "contradicted",
 "answer": "…", "contexts": [{"source_title": "…", "text": "…"}]}
```

Keep contexts short and self-contained so the benchmark stays independent of
the live vector store.
