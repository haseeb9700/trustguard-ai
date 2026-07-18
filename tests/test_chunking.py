"""Tests for text chunking and section-aware chunking."""

from modules.url_ingestor import chunk_sections, chunk_text


class TestChunkText:
    def test_short_text_yields_single_chunk(self):
        text = " ".join(["word"] * 100)
        chunks = chunk_text(text, chunk_size=400, overlap=80)
        assert len(chunks) == 1

    def test_long_text_yields_overlapping_chunks(self):
        text = " ".join(f"w{i}" for i in range(1000))
        chunks = chunk_text(text, chunk_size=400, overlap=80)
        assert len(chunks) > 1
        # Overlap: the last words of chunk 1 appear at the start of chunk 2.
        assert chunks[1].split()[0] == "w320"

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
