## TrustGuard Claim-Verification Eval

**Cases:** 40  |  **Accuracy:** 92.5%  |  **Macro-F1:** 0.928  |  **Weighted-F1:** 0.927

### Per-class metrics

| Verdict | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| entailed | 1.000 | 1.000 | 1.000 | 11 |
| baseless | 0.769 | 1.000 | 0.870 | 10 |
| contradicted | 1.000 | 0.842 | 0.914 | 19 |

### Confusion matrix (rows = gold, cols = predicted)

| gold \ pred | entailed | baseless | contradicted |
|---|---|---|---|
| entailed | 11 | 0 | 0 |
| baseless | 0 | 10 | 0 |
| contradicted | 0 | 3 | 16 |
