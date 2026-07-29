"""Guards on the claim-verification dataset's labelling.

The dataset once contained ten cases labelled ``baseless`` whose contexts
explicitly refuted the claim ("does not guarantee approval" against "approval
is guaranteed"). Structurally identical cases were graded inconsistently, and
the class held no genuine examples at all — so the eval was scoring the
verifier against a boundary that did not exist.

Nothing failed when that happened. The suite passed, the harness ran, and the
only symptom was a confusion matrix that looked like a model problem. These
tests make the labelling itself checkable, because a benchmark that quietly
disagrees with its own definitions is worse than no benchmark.
"""

import json
import pathlib
import re

import pytest

from modules.verdicts import BASELESS, CONTRADICTED, ENTAILED, VERDICTS

DATASET = pathlib.Path(__file__).resolve().parent.parent / "eval" / "dataset.jsonl"


def _cases():
    return [
        json.loads(line) for line in DATASET.read_text().splitlines() if line.strip()
    ]


# Phrasings where the context engages with the claim and denies it. A context
# doing this is asserting something incompatible, which is "contradicted".
_DENIAL = re.compile(
    r"\b(?:does not|do not|did not|is not|are not|was not|were not|cannot|"
    r"can't|doesn't|don't|no fixed|sets no|not guarantee|never|"
    r"rather than|instead of)\b",
    re.IGNORECASE,
)


def test_dataset_is_well_formed():
    for case in _cases():
        assert case["gold"] in VERDICTS, case["id"]
        assert case["answer"].strip(), case["id"]
        assert case["contexts"], case["id"]
        for ctx in case["contexts"]:
            assert ctx["text"].strip(), case["id"]


def test_every_verdict_class_has_examples():
    # The bug this catches: a class silently emptying out, so metrics for it
    # become meaningless while still being reported.
    golds = {c["gold"] for c in _cases()}
    for verdict in VERDICTS:
        assert verdict in golds, f"no {verdict} cases left in the dataset"


def test_baseless_contexts_do_not_refute_the_claim():
    # The original defect, made unrepeatable: "baseless" means the context is
    # silent, so a context that explicitly denies something is mislabelled.
    offenders = []
    for case in _cases():
        if case["gold"] != BASELESS:
            continue
        for ctx in case["contexts"]:
            found = _DENIAL.findall(ctx["text"])
            if found:
                offenders.append((case["id"], found[:2]))

    assert not offenders, (
        "cases labelled 'baseless' whose context refutes the claim — these are "
        f"contradictions under the taxonomy in modules/verdicts.py: {offenders}"
    )


def test_relabelled_cases_carry_their_reason():
    # Relabelling a benchmark by hand is how benchmarks rot. Anything moved
    # must record why, so the decision stays auditable.
    for case in _cases():
        if "relabel_note" in case:
            assert case["gold"] == CONTRADICTED, case["id"]
            assert len(case["relabel_note"]) > 20, case["id"]


@pytest.mark.parametrize("verdict", [ENTAILED, CONTRADICTED, BASELESS])
def test_classes_are_not_wildly_imbalanced(verdict):
    # Not a strict balance requirement — just a floor, so a class cannot dwindle
    # to a handful of cases where a single flip swings its F1 by a third.
    cases = _cases()
    count = sum(1 for c in cases if c["gold"] == verdict)
    assert count >= 5, f"only {count} {verdict} cases; metrics would be unstable"
