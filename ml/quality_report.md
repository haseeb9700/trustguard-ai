## TrustGuard Answer-Quality Model

**Model:** logreg  |  **Examples:** 150 (63% correct)

### Held-out performance

| Metric | Value |
|---|---|
| Accuracy | 0.895 |
| Baseline (majority) | 0.632 |
| ROC-AUC | 0.860 |
| Precision | 0.917 |
| Recall | 0.917 |
| F1 | 0.917 |
| 5-fold CV ROC-AUC | 0.859 ± 0.053 |

### Feature influence

| Feature | Weight |
|---|---|
| frac_entailed | +1.108 |
| n_contradicted | -1.103 |
| unverified_flag | -0.670 |
| risk_score | +0.536 |
| n_claims | -0.509 |
| n_baseless | -0.386 |
| answer_len_words | -0.354 |
| n_entailed | +0.300 |
| retrieved_context_count | -0.293 |
| hallucination_score | -0.168 |
| n_sources | +0.091 |
