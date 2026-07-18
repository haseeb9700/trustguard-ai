"""Unit tests for the eval harness scoring (eval/metrics.py).

These run in CI with no API key: they cover the aggregation precedence and
the precision/recall/F1 math, and use the offline lexical + oracle verifiers
to smoke-test the runner end-to-end.
"""

from eval.metrics import aggregate_verdict, compute_metrics, confusion_matrix
from eval.run_eval import lexical_verifier, load_dataset, run, DATASET_PATH


# --- aggregate_verdict: AND-join precedence --------------------------------

def test_aggregate_empty_is_baseless():
    assert aggregate_verdict([]) == "baseless"


def test_aggregate_all_entailed():
    claims = [{"verdict": "entailed"}, {"verdict": "entailed"}]
    assert aggregate_verdict(claims) == "entailed"


def test_aggregate_one_baseless_floors_to_baseless():
    claims = [{"verdict": "entailed"}, {"verdict": "baseless"}]
    assert aggregate_verdict(claims) == "baseless"


def test_aggregate_one_contradicted_dominates():
    claims = [{"verdict": "entailed"}, {"verdict": "baseless"}, {"verdict": "contradicted"}]
    assert aggregate_verdict(claims) == "contradicted"


def test_aggregate_unknown_verdict_treated_as_baseless():
    assert aggregate_verdict([{"verdict": "???"}]) == "baseless"


# --- confusion matrix + metrics math ---------------------------------------

def test_confusion_matrix_counts():
    pairs = [("entailed", "entailed"), ("entailed", "baseless"), ("baseless", "baseless")]
    matrix = confusion_matrix(pairs)
    assert matrix["entailed"]["entailed"] == 1
    assert matrix["entailed"]["baseless"] == 1
    assert matrix["baseless"]["baseless"] == 1
    assert matrix["contradicted"]["contradicted"] == 0


def test_perfect_predictions_give_macro_f1_one():
    pairs = [
        ("entailed", "entailed"),
        ("baseless", "baseless"),
        ("contradicted", "contradicted"),
    ]
    metrics = compute_metrics(pairs)
    assert metrics["accuracy"] == 1.0
    assert metrics["macro_f1"] == 1.0
    for label in metrics["labels"]:
        assert metrics["per_class"][label]["f1"] == 1.0


def test_precision_recall_known_values():
    # entailed: TP=1, FP=1 (a baseless predicted entailed), FN=1 (an entailed
    # predicted baseless) -> precision = recall = 0.5, f1 = 0.5
    pairs = [
        ("entailed", "entailed"),
        ("entailed", "baseless"),
        ("baseless", "entailed"),
        ("baseless", "baseless"),
    ]
    metrics = compute_metrics(pairs)
    ent = metrics["per_class"]["entailed"]
    assert ent["precision"] == 0.5
    assert ent["recall"] == 0.5
    assert ent["f1"] == 0.5
    assert metrics["accuracy"] == 0.5


def test_empty_pairs_do_not_crash():
    metrics = compute_metrics([])
    assert metrics["total"] == 0
    assert metrics["accuracy"] == 0.0


# --- runner smoke tests (offline verifiers) --------------------------------

def test_oracle_verifier_scores_perfectly():
    result = run(DATASET_PATH, "oracle", limit=None)
    assert result["metrics"]["accuracy"] == 1.0
    assert result["metrics"]["macro_f1"] == 1.0


def test_lexical_baseline_runs_and_never_predicts_contradicted():
    # The lexical baseline should complete over the whole dataset and, by
    # construction, never emit "contradicted" (illustrating why it is weak).
    result = run(DATASET_PATH, "lexical", limit=None)
    preds = {c["pred"] for c in result["cases"]}
    assert "contradicted" not in preds
    assert result["metrics"]["total"] == len(result["cases"])


def test_lexical_verifier_entails_high_overlap():
    answer = "Basel III sets a minimum CET1 ratio of 4.5 percent."
    contexts = [{"source_title": "x", "text": "Basel III sets the minimum CET1 ratio at 4.5 percent of risk-weighted assets."}]
    assert aggregate_verdict(lexical_verifier(answer, contexts)) == "entailed"


def test_dataset_is_well_formed():
    cases = load_dataset(DATASET_PATH)
    assert len(cases) >= 20
    for case in cases:
        assert case["gold"] in {"entailed", "baseless", "contradicted"}
        assert case["answer"]
        assert isinstance(case.get("contexts", []), list)
