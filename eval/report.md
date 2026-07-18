## TrustGuard Claim-Verification Eval

**Cases:** 30  |  **Accuracy:** 70.0%  |  **Macro-F1:** 0.549  |  **Weighted-F1:** 0.577

### Per-class metrics

| Verdict | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| entailed | 0.688 | 1.000 | 0.815 | 11 |
| baseless | 0.714 | 1.000 | 0.833 | 10 |
| contradicted | 0.000 | 0.000 | 0.000 | 9 |

### Confusion matrix (rows = gold, cols = predicted)

| gold \ pred | entailed | baseless | contradicted |
|---|---|---|---|
| entailed | 11 | 0 | 0 |
| baseless | 0 | 10 | 0 |
| contradicted | 5 | 4 | 0 |
