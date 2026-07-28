# Answer-Quality Model

A learned model that predicts whether a human will judge an answer **correct**,
from the signals the RAG pipeline already produces. It complements the
rule-based risk score with a data-driven quality estimate that **improves as
real feedback accumulates** — the "learn and improve" loop for a governance
system, without fine-tuning the generator (which would reintroduce
hallucination risk).

## Why this and not fine-tuning the LLM

In a grounded RAG system, answer quality is dominated by retrieval and
grounding, not the model's parametric memory. So instead of teaching a model
the answers, we learn a **quality/reward model** over pipeline features — the
credible, low-risk way to make the system improve from feedback.

## Features

Extracted by `features.py` from an `/analyze` result (identical at train and
inference time):

`hallucination_score`, `risk_score`, `retrieved_context_count`, `n_claims`,
`n_entailed`, `n_baseless`, `n_contradicted`, `frac_entailed`, `n_sources`,
`answer_len_words`, `unverified_flag`.

Label: the human feedback (`Correct` → 1; `Partially Correct` / `Incorrect` → 0).

## Train

```bash
python -m ml.train_quality_model                 # scaled logistic regression
python -m ml.train_quality_model --model gbdt    # gradient boosting
python -m ml.train_quality_model --data path.jsonl
```

Reports held-out accuracy, ROC-AUC, precision/recall/F1, a 5-fold CV AUC, a
confusion matrix, and per-feature weights; saves the model to
`quality_model.joblib` and writes `quality_report.md` + `quality_metrics.json`.

On the bundled bootstrap dataset (150 records), scaled logistic regression
reaches ~0.90 accuracy / ~0.86 ROC-AUC vs a 0.63 majority baseline, and the
weights are sensible: `frac_entailed` pushes quality up, while `n_contradicted`
and `unverified_flag` push it down.

## Predict

```python
from ml.predict import predict_quality

predict_quality(analyze_result)
# -> {"quality_score": 0.91, "label": "Likely correct", ...}
```

Returns `None` if the model hasn't been trained yet. Also exposed as
`POST /predict-quality` (runs the workflow, then attaches a `quality` block).

## From bootstrap data to real feedback

`quality_dataset.jsonl` is a labeled **bootstrap** sample so the pipeline is
reproducible and testable today. To learn from production:

1. Capture the pipeline features alongside each `feedback_log` entry (the
   `/analyze` result carries them all).
2. Export those labeled rows to a JSONL of the same shape.
3. `python -m ml.train_quality_model --data your_feedback.jsonl` and redeploy
   the refreshed `quality_model.joblib`.

Retraining on a schedule as feedback grows is the improvement loop.

## Files

- `features.py` — feature extraction (pure, unit-tested).
- `quality_dataset.jsonl` — bootstrap labeled data.
- `train_quality_model.py` — training + evaluation CLI.
- `predict.py` — inference with graceful fallback.
- Tested in `tests/test_quality_model.py`.
