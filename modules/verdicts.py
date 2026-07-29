"""The claim-verification verdict taxonomy — one definition, used everywhere.

The three labels are only useful if "contradicted" and "baseless" have a sharp
boundary, and originally they did not. The eval dataset labelled a claim
``baseless`` whenever the *specific detail* it asserted was unsupported, even
when the context explicitly refuted it — "the Act does not name specific
auditing firms" was filed as baseless against a claim naming an auditing firm.
Structurally identical cases were then graded inconsistently, and all ten
``baseless`` cases turned out to have contexts that addressed and refuted the
claim. The class contained no genuine examples at all.

That is not a model failure, it is an under-specified label. So the boundary is
stated once, here, and the dataset, the verifier prompts and the docs all refer
back to it.

The test is **what the context does**, not how wrong the claim is:

``entailed``
    The context supports the claim.

``contradicted``
    The context asserts something incompatible with the claim. This includes
    explicit denial ("does not guarantee approval" against "guaranteed
    approval") and mutually exclusive assertions ("selection is random"
    against "conducted alphabetically"). The source engages with the claim
    and says otherwise.

``baseless``
    The context is *silent*. It neither supports nor refutes the claim because
    it does not address the subject at all.

The deciding question: **does the source say anything that bears on this
claim?** If yes and it agrees, entailed. If yes and it disagrees, contradicted.
Only if the source is genuinely silent is the claim baseless.

Why this cut and not another: it matches what a compliance reader needs to
know. "The source refutes this" and "the source doesn't cover this" call for
different responses — the first means the answer is wrong, the second means the
knowledge base has a gap. Grading by how specific the false detail was would
tell nobody anything actionable.

Both labels are failures; ``contradicted`` is the more severe, which is why
risk scoring escalates on it.
"""

from __future__ import annotations

ENTAILED = "entailed"
CONTRADICTED = "contradicted"
BASELESS = "baseless"

VERDICTS = (ENTAILED, CONTRADICTED, BASELESS)

# Worst-first precedence, used when collapsing per-claim verdicts into a single
# answer-level verdict: one contradicted claim makes the whole answer
# contradicted.
PRECEDENCE = (CONTRADICTED, BASELESS, ENTAILED)

DEFINITIONS = {
    ENTAILED: "The context supports the claim.",
    CONTRADICTED: (
        "The context asserts something incompatible with the claim — either "
        "explicit denial, or a statement that cannot both be true with it."
    ),
    BASELESS: (
        "The context is silent on the claim. It does not address the subject, "
        "so it neither supports nor refutes it."
    ),
}

# Dropped into the verifier prompts so the model is judged against the same
# boundary the dataset is labelled with.
PROMPT_RUBRIC = """\
- "entailed": the window supports the claim.
- "contradicted": the window asserts something incompatible with the claim.
  This covers BOTH explicit denial and mutually exclusive statements.
    * "does not guarantee approval" vs "approval is guaranteed" -> contradicted
    * "sets no fixed schedule" vs "requires retraining every 30 days" -> contradicted
    * "the selection is random" vs "conducted alphabetically" -> contradicted
    * "penalties vary by tier" vs "always exactly one million" -> contradicted
- "baseless": the window is SILENT on the claim — it does not discuss the
  subject at all, so it neither supports nor refutes it.
    * a window about encryption safeguards, against a claim about which
      country servers sit in -> baseless
    * a window about risk-management functions, against a claim about a
      model's parameter count -> baseless

Decide by asking: does this window say anything bearing on the claim?
  Yes, and it agrees      -> entailed
  Yes, and it disagrees   -> contradicted
  No, it never addresses it -> baseless

A claim being wrong is not enough to make it "contradicted" — the window must
actually say something that conflicts with it.\
"""
