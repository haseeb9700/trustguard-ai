## TrustGuard Retrieval Eval — Ranker Comparison

**Queries:** 54  |  **Corpus:** 93 chunks  |  **BGE query instruction:** on

| Ranker | MRR | Δ MRR | nDCG@1 | nDCG@3 | nDCG@5 |
|---|---|---|---|---|---|
| lexical | 0.348 | — | 0.204 | 0.307 | 0.386 |
| embedding | 0.668 | +0.320 | 0.537 | 0.652 | 0.697 |
| reranked | 0.740 | +0.072 | 0.648 | 0.724 | 0.756 |

### Hit-rate / Recall / Precision

| Ranker | k | Hit-rate@k | Recall@k | Precision@k | nDCG@k |
|---|---|---|---|---|---|
| lexical | 1 | 0.204 | 0.185 | 0.204 | 0.204 |
| lexical | 3 | 0.407 | 0.389 | 0.148 | 0.307 |
| lexical | 5 | 0.611 | 0.579 | 0.133 | 0.386 |
| embedding | 1 | 0.537 | 0.518 | 0.537 | 0.537 |
| embedding | 3 | 0.759 | 0.741 | 0.278 | 0.652 |
| embedding | 5 | 0.889 | 0.843 | 0.193 | 0.697 |
| reranked | 1 | 0.648 | 0.597 | 0.648 | 0.648 |
| reranked | 3 | 0.833 | 0.792 | 0.302 | 0.724 |
| reranked | 5 | 0.889 | 0.870 | 0.204 | 0.756 |
