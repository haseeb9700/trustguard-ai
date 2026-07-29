"""Hierarchical claim-level verification for context faithfulness.

Inspired by RT4CHART (Yu et al., arXiv:2603.27752): the answer is
decomposed into atomic claims WITHOUT showing the context (to avoid
bias), each claim is screened locally against every retrieved chunk,
chunk verdicts are merged with an OR-join, and unresolved claims are
re-verified globally against the full context (evidence distributed
across chunks gets caught here).

Label taxonomy is defined once in ``modules/verdicts`` and shared with the eval
dataset, so the model is judged against the same boundary the data is labelled
with. In short: contradicted means the context says something incompatible with
the claim, baseless means the context is silent on it.
"""

import json
import logging
import os
import re

from dotenv import load_dotenv
from openai import OpenAI

from modules.verdicts import PROMPT_RUBRIC

load_dotenv()

logger = logging.getLogger("trustguard.claims")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

VERIFICATION_MODEL = "gpt-4o-mini"

VALID_VERDICTS = {"entailed", "contradicted", "baseless"}

MAX_CLAIMS = 6


def _chat(system: str, prompt: str) -> str:
    """Single deterministic chat completion."""
    response = client.chat.completions.create(
        model=VERIFICATION_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )
    return response.choices[0].message.content


def _parse_json(raw: str):
    """Parse model JSON output, tolerating code fences. Returns None on failure."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        logger.warning("Model returned non-JSON output.")
        return None


def _normalize_verdict(verdict: str) -> str:
    verdict = str(verdict).lower().strip()
    return verdict if verdict in VALID_VERDICTS else "baseless"


def decompose_claims(answer: str) -> list:
    """Split the answer into atomic, self-contained factual claims.

    The model sees ONLY the answer (not the context), so claim formation
    stays faithful to the answer itself rather than being biased by the
    retrieved evidence (decompose-then-verify).
    """
    prompt = f"""
Split the ANSWER below into its individual atomic factual claims (maximum {MAX_CLAIMS}).

Rules:
- Each claim must be self-contained: no unresolved pronouns or missing subjects.
- Preserve qualifiers: negation, quantities, dates, and modality.
- Skip meta statements like "I could not verify this from the provided sources."

ANSWER:
{answer}

Return STRICT JSON only — a list of claim strings:
["claim 1", "claim 2"]
"""
    parsed = _parse_json(
        _chat("You decompose text into atomic factual claims.", prompt)
    )

    if not isinstance(parsed, list):
        return []

    return [str(c) for c in parsed if isinstance(c, str) and c.strip()][:MAX_CLAIMS]


def _or_join(verdicts: list) -> str:
    """Merge chunk-level verdicts: contradiction dominates, one supporting
    chunk suffices, otherwise no local chunk was decisive."""
    if "contradicted" in verdicts:
        return "contradicted"
    if "entailed" in verdicts:
        return "entailed"
    return "baseless"


def _local_verify(claims: list, contexts: list) -> list:
    """Screen every claim against every context chunk independently.

    Returns one record per claim: {"verdicts": [per-chunk labels],
    "evidence": str, "source_title": str}.
    """
    chunk_text = "\n\n".join(
        f"WINDOW {k}: (Source: {c['source_title']})\n{c['text']}"
        for k, c in enumerate(contexts)
    )
    claims_text = "\n".join(f"{i}: {claim}" for i, claim in enumerate(claims))

    prompt = f"""
You are a strict context-faithfulness verifier.

For EACH claim, assess it against EACH context window INDEPENDENTLY:

{PROMPT_RUBRIC}

Judge only from the window text. Do not use outside knowledge.

CLAIMS:
{claims_text}

CONTEXT WINDOWS:
{chunk_text}

Return STRICT JSON only — one entry per claim, in claim order:

[
  {{
    "claim_index": 0,
    "window_verdicts": ["baseless", "entailed", ...],
    "evidence": "shortest quote (max 25 words) from the strongest window that supports or contradicts the claim, else empty",
    "source_title": "source of that quote, else empty"
  }}
]
"""
    parsed = _parse_json(
        _chat("You are a strict, literal context-faithfulness verifier.", prompt)
    )

    results = [
        {"verdicts": ["baseless"], "evidence": "", "source_title": ""} for _ in claims
    ]

    if not isinstance(parsed, list):
        return results

    for item in parsed:
        if not isinstance(item, dict):
            continue
        try:
            idx = int(item.get("claim_index", -1))
        except (TypeError, ValueError):
            continue
        if 0 <= idx < len(claims):
            verdicts = item.get("window_verdicts", [])
            if not isinstance(verdicts, list) or not verdicts:
                verdicts = ["baseless"]
            results[idx] = {
                "verdicts": [_normalize_verdict(v) for v in verdicts],
                "evidence": str(item.get("evidence", "")),
                "source_title": str(item.get("source_title", "")),
            }

    return results


def _global_verify(
    claims: list, indices: list, local_labels: dict, contexts: list
) -> dict:
    """Re-verify unresolved claims against the FULL context.

    Local screening can miss evidence distributed across chunk boundaries
    and can flag contradictions that surrounding text resolves. The global
    pass reads the whole context, using local labels only as hints.

    Returns {claim_index: {"verdict", "evidence", "source_title"}}.
    """
    full_context = "\n\n".join(
        f"(Source: {c['source_title']})\n{c['text']}" for c in contexts
    )
    claims_text = "\n".join(
        f"{i}: {claims[i]}  [local screening said: {local_labels[i]}]" for i in indices
    )

    prompt = f"""
You are a strict context-faithfulness verifier performing a FINAL global check.

Each claim below was screened chunk-by-chunk; the local result is shown as a hint
only. Now read the FULL context — evidence may be spread across passages, and an
apparent local contradiction may be resolved by surrounding text.

Final verdicts — read "window" below as the FULL context:

{PROMPT_RUBRIC}

Evidence may be spread across passages, so a claim unsupported by any single
passage may still be entailed by the whole.

Judge only from the context. Do not use outside knowledge.

CLAIMS:
{claims_text}

FULL CONTEXT:
{full_context}

Return STRICT JSON only:

[
  {{
    "claim_index": 0,
    "verdict": "entailed",
    "evidence": "shortest supporting or contradicting quote (max 25 words), empty if baseless",
    "source_title": "source of the quote, else empty"
  }}
]
"""
    parsed = _parse_json(
        _chat("You are a strict, literal context-faithfulness verifier.", prompt)
    )

    results = {}

    if not isinstance(parsed, list):
        return results

    for item in parsed:
        if not isinstance(item, dict):
            continue
        try:
            idx = int(item.get("claim_index", -1))
        except (TypeError, ValueError):
            continue
        if idx in indices:
            results[idx] = {
                "verdict": _normalize_verdict(item.get("verdict", "baseless")),
                "evidence": str(item.get("evidence", "")),
                "source_title": str(item.get("source_title", "")),
            }

    return results


def verify_claims(answer: str, contexts: list) -> list:
    """Run hierarchical claim verification for an answer.

    Args:
        answer: The generated answer text.
        contexts: Retrieved chunks, each with "source_title" and "text".

    Returns:
        A list of dicts: {"claim", "verdict" (entailed | contradicted |
        baseless), "evidence", "source_title"}. Empty list on any failure —
        claim verification is supplementary and must never break the
        main workflow.
    """
    try:
        claims = decompose_claims(answer)
        if not claims:
            return []

        # Stage 1 — local: screen each claim against each chunk, OR-join.
        local = _local_verify(claims, contexts)
        local_labels = {i: _or_join(rec["verdicts"]) for i, rec in enumerate(local)}

        # Stage 2 — global: re-verify claims that were not locally entailed.
        # Baseless claims may have cross-chunk evidence; contradictions are
        # double-checked against the full context.
        unresolved = [i for i, lbl in local_labels.items() if lbl != "entailed"]
        global_results = (
            _global_verify(claims, unresolved, local_labels, contexts)
            if unresolved
            else {}
        )

        final = []
        for i, claim in enumerate(claims):
            if i in global_results:
                verdict = global_results[i]["verdict"]
                evidence = global_results[i]["evidence"]
                source = global_results[i]["source_title"]
            else:
                verdict = local_labels[i]
                evidence = local[i]["evidence"]
                source = local[i]["source_title"]

            # Baseless claims must not carry evidence (RT4CHART Eq. 1).
            if verdict == "baseless":
                evidence, source = "", ""

            final.append(
                {
                    "claim": claim,
                    "verdict": verdict,
                    "evidence": evidence,
                    "source_title": source,
                }
            )

        return final

    except Exception:
        logger.exception("Claim verification failed.")
        return []
