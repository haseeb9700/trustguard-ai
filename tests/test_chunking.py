"""Tests for text chunking and section-aware chunking."""

from modules.url_ingestor import chunk_sections, chunk_text


class TestChunkText:
    def test_short_text_yields_single_chunk(self):
        text = " ".join(["word"] * 100)
        chunks = chunk_text(text, chunk_size=400, overlap=80)
        assert len(chunks) == 1

    def test_long_text_yields_overlapping_chunks(self):
        text = " ".join(
            f"Sentence {i} carries a few words along with it." for i in range(200)
        )
        chunks = chunk_text(text, chunk_size=400, overlap=80)
        assert len(chunks) > 1
        # Consecutive chunks share trailing context.
        assert set(chunks[0].split()) & set(chunks[1].split())

    def test_chunks_begin_at_sentence_boundaries(self):
        # The point of sentence alignment: no chunk opens mid-clause, so every
        # chunk is readable (and embeddable) on its own.
        text = " ".join(
            f"Rule {i} states that the applicant must file the form on time."
            for i in range(120)
        )
        chunks = chunk_text(text, chunk_size=60, overlap=15)
        assert len(chunks) > 1
        assert all(c.startswith("Rule ") for c in chunks)

    def test_abbreviations_do_not_end_a_sentence(self):
        text = (
            "See 8 CFR 214.2(f)(10) for the rule. The student may then work. "
            "Dr. Smith signed it on Mar. 11, 2016 without objection."
        )
        chunks = chunk_text(text, chunk_size=400, overlap=80)
        assert len(chunks) == 1
        assert "8 CFR 214.2(f)(10)" in chunks[0]

    def test_oversized_sentence_is_split_on_words(self):
        # No full stop anywhere: must still be broken up, or the embedding
        # model would silently truncate at its token limit.
        text = " ".join(f"w{i}" for i in range(1000))
        chunks = chunk_text(text, chunk_size=400, overlap=80)
        assert len(chunks) > 1
        assert all(len(c.split()) <= 400 for c in chunks)

    def test_tiny_text_is_dropped(self):
        assert chunk_text("too short", chunk_size=400, overlap=80) == []

    def test_empty_text(self):
        assert chunk_text("", chunk_size=400, overlap=80) == []


class TestChunkSections:
    def test_heading_is_prefixed(self):
        sections = [("Eligibility", " ".join(["word"] * 100))]
        chunks = chunk_sections(sections)
        assert chunks[0].startswith("[Eligibility] ")

    def test_no_heading_no_prefix(self):
        sections = [("", " ".join(["word"] * 100))]
        chunks = chunk_sections(sections)
        assert chunks[0].startswith("word")

    def test_multiple_sections_stay_separate(self):
        sections = [
            ("A", " ".join(["alpha"] * 100)),
            ("B", " ".join(["beta"] * 100)),
        ]
        chunks = chunk_sections(sections)
        assert len(chunks) == 2
        assert "beta" not in chunks[0]
