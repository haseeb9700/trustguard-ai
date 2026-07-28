"""Reject non-prose blocks before they reach the vector store.

Stripping ``<nav>``/``<footer>``/``<header>`` tags removes site chrome that is
*marked up* as chrome. It does nothing about the rest: cookie and security
banners sitting in ordinary ``<p>`` tags, link menus built from ``<li>``, and
footnote blocks that are legitimately body text but carry no facts.

Those blocks are not harmless filler. They embed to plausible-looking vectors
and compete for slots in the candidate pool — on the retrieval benchmark, two
pure footnote-index chunks outranked the chunk that actually quoted the statute
a query asked about. Every such slot is one the real answer does not get.

Three signals, each independently sufficient, because these are different kinds
of junk and a single blended score would need a threshold that suits none of
them:

``chrome``
    Known banner phrasing ("this site is secure", cookie notices). Matched as
    fixed phrases — high precision, and unlike the other two it fires on short
    text where the statistical signals have too little to work with.

``citations``
    Footnote and cross-reference markers as a share of tokens. Bibliography
    blocks are almost entirely "[^ 51] See 8 CFR 214.2(f)(10)".

``fragmented``
    Sentence-ending punctuation per hundred words. Navigation menus and link
    lists are long runs of noun phrases with almost no sentence structure.

Deliberately *not* included: a "does it look like a list" check based on line
count or bullet characters. Genuine policy text is full of legitimate lists —
eligibility criteria, required documents — and rejecting those would discard
exactly the content this system exists to answer questions about.
"""

from __future__ import annotations

import re

# Fixed phrases from site furniture. Lower-cased substring matches, so they
# survive whitespace and markup variation.
CHROME_PHRASES = (
    "official website of the united states government",
    "a .gov website belongs to an official government organization",
    ".gov website belongs to an official government",
    "secure .gov websites use https",
    "means you've safely connected",
    "means you have safely connected",
    "locked padlock",
    "lock a locked padlock",
    "skip to main content",
    "this site uses cookies",
    "we use cookies",
    "accept all cookies",
    "javascript is disabled",
    "enable javascript",
    "browser is out of date",
    "sign up for email updates",
    "subscribe to our newsletter",
    "share this page",
    "was this page helpful",
    "return to top",
)

# Footnote markers ([^ 51], [24]), regulation cites (8 CFR 214.2, 81 FR 13040),
# and "See ..." cross-references.
_CITATION_PATTERNS = (
    r"\[\^?\s*\d+\s*\]",
    r"\b\d+\s+CFR\s+[\d.]+",
    r"\b\d+\s+FR\s+\d+",
    r"\bSee\s+(?:also\s+)?(?:the\s+)?[A-Z0-9]",
    r"\(PDF\)",
    r"\bUSCIS-PM\b",
)
_CITATION_RE = re.compile("|".join(_CITATION_PATTERNS))

_SENTENCE_END_RE = re.compile(r"[.!?](?:\s|$)")
_WORD_RE = re.compile(r"\S+")

# A block is rejected when it crosses any of these.
MAX_CITATION_DENSITY = 0.08  # citation markers per word
MIN_SENTENCE_DENSITY = 1.2  # sentence enders per 100 words

# Below this, the statistical signals are too noisy to trust, so only the
# fixed-phrase check applies. Short blocks are cheap to keep and expensive to
# wrongly discard.
MIN_WORDS_FOR_STATS = 40


def _chrome_hits(text: str) -> list:
    lowered = " ".join(text.lower().split())
    return [p for p in CHROME_PHRASES if p in lowered]


def score_block(text: str) -> dict:
    """Return the signal breakdown for a block of text.

    Exposed separately from :func:`is_boilerplate` so the thresholds can be
    inspected and tuned against real pages rather than guessed at.
    """
    words = _WORD_RE.findall(text or "")
    n_words = len(words)
    if n_words == 0:
        return {
            "words": 0,
            "chrome": [],
            "citation_density": 0.0,
            "sentence_density": 0.0,
            "reasons": ["empty"],
        }

    chrome = _chrome_hits(text)
    citations = len(_CITATION_RE.findall(text))
    sentences = len(_SENTENCE_END_RE.findall(text))

    citation_density = citations / n_words
    sentence_density = sentences / n_words * 100

    reasons = []
    if chrome:
        reasons.append(f"chrome:{chrome[0]}")
    if n_words >= MIN_WORDS_FOR_STATS:
        if citation_density > MAX_CITATION_DENSITY:
            reasons.append(f"citations:{citation_density:.3f}")
        if sentence_density < MIN_SENTENCE_DENSITY:
            reasons.append(f"fragmented:{sentence_density:.2f}")

    return {
        "words": n_words,
        "chrome": chrome,
        "citation_density": round(citation_density, 4),
        "sentence_density": round(sentence_density, 2),
        "reasons": reasons,
    }


def is_boilerplate(text: str) -> bool:
    """True if a block is site furniture, a citation dump, or a link list."""
    return bool(score_block(text)["reasons"])


def filter_chunks(chunks: list) -> tuple:
    """Split chunks into (kept, dropped).

    Returns both halves rather than only the survivors so callers can log and
    audit what ingestion discarded — silently dropping source content in a
    governance product would be its own kind of bug.
    """
    kept, dropped = [], []
    for chunk in chunks:
        info = score_block(chunk)
        if info["reasons"]:
            dropped.append({"text": chunk, **info})
        else:
            kept.append(chunk)
    return kept, dropped
