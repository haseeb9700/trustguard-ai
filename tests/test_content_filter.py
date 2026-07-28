"""Tests for boilerplate detection.

The costly mistake here is a false positive: rejecting real policy text means
the system can no longer answer questions about it, and nothing downstream will
reveal that the content was silently discarded at ingest. So the substantive
tests are the negative ones — legitimate prose full of lists, citations and
short sentences must survive.
"""

from modules.content_filter import (
    filter_chunks,
    is_boilerplate,
    score_block,
)

# --- must be rejected ------------------------------------------------------


def test_rejects_gov_security_banner():
    assert is_boilerplate(
        "Official websites use .gov A .gov website belongs to an official "
        "government organization in the United States. Secure .gov websites "
        "use HTTPS A lock ( Lock Locked padlock ) or https:// means you've "
        "safely connected to the .gov website."
    )


def test_rejects_cookie_notice():
    assert is_boilerplate("This site uses cookies to improve your experience.")


def test_rejects_citation_dump():
    text = (
        "[^ 49] See the DHS STEM OPT Hub webpage for more information. "
        "[^ 51] See 8 CFR 214.2(f)(10)(ii)(A)(3). [^ 52] See 8 CFR "
        "214.2(f)(10)(ii)(C)(9)(i). [^ 53] See 81 FR 13040 (PDF). "
        "[^ 54] See 8 CFR 214.2(f)(11). [^ 55] See USCIS-PM Volume 2. "
    ) * 3
    assert is_boilerplate(text)


def test_rejects_navigation_link_list():
    # No sentence structure at all: a menu flattened into text.
    text = (
        "Session Dates Extending the F-1 Form I-20 Extending the M-1 Form I-20 "
        "Reduced Course Load Shorten Program Cancel SEVIS Record in Initial "
        "Status Understanding SEVIS Program and Session Dates Transfers "
        "Complete Travel and Identity Documents Financial Information "
        "Personal Information Program Information Report School Action"
    )
    assert is_boilerplate(text)


# --- must be kept ----------------------------------------------------------


def test_keeps_ordinary_policy_prose():
    assert not is_boilerplate(
        "When more registrations are received than the cap allows, USCIS uses "
        "a random selection process, commonly called the H-1B lottery, to "
        "choose registrations. Petitions that are not selected are returned."
    )


def test_keeps_prose_containing_some_citations():
    # Real policy text cites regulations constantly. Only a dump should fail.
    text = (
        "Practical training is employment directly related to a student's "
        "major area of study. [1] F-1 students may engage in three types of "
        "practical training. The student must be enrolled full time at an "
        "SEVP-certified institution and must have completed one full academic "
        "year before applying. See 8 CFR 214.2(f)(10) for the full rule."
    )
    assert not is_boilerplate(text), score_block(text)


def test_keeps_legitimate_requirement_list():
    # Eligibility criteria are exactly what this product answers questions
    # about; a naive "looks like a list" rule would throw them away.
    text = (
        "The student must report the following to their designated school "
        "official within 10 days of any change. Their legal name. Their "
        "residential or mailing address. Their email address. Their "
        "employer's name. Their employer's address. Failure to report may "
        "result in the termination of the student's record."
    )
    assert not is_boilerplate(text), score_block(text)


def test_short_blocks_only_checked_for_chrome():
    # Too little text for the statistical signals to mean anything, so a bare
    # heading-like fragment is kept rather than guessed at.
    assert not is_boilerplate("Eligibility Requirements for STEM OPT")
    # ...but a short chrome phrase is still caught.
    assert is_boilerplate("Skip to main content")


def test_empty_text_is_boilerplate():
    assert is_boilerplate("")
    assert is_boilerplate("   ")


# --- filter_chunks ---------------------------------------------------------


def test_filter_chunks_splits_and_explains():
    good = (
        "The agency uses a random selection process when more registrations "
        "are received than the annual cap permits. Unselected petitions are "
        "returned to the petitioner without prejudice."
    )
    kept, dropped = filter_chunks([good, "This site uses cookies.", good])

    assert kept == [good, good]
    assert len(dropped) == 1
    # Callers need to be able to log *why* content was discarded.
    assert dropped[0]["reasons"]
    assert dropped[0]["text"] == "This site uses cookies."


def test_score_block_reports_signals():
    info = score_block("A sentence. Another sentence. A third one here now.")
    assert info["words"] > 0
    assert info["sentence_density"] > 0
    assert info["reasons"] == []
