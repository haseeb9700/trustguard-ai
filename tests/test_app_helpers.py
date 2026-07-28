"""Tests for API response helpers in app.py."""

import math

from app import clean_json, get_unique_sources, parse_json_if_string


class TestCleanJson:
    def test_nan_becomes_none(self):
        assert clean_json(float("nan")) is None

    def test_inf_becomes_none(self):
        assert clean_json(float("inf")) is None

    def test_nested_structures_are_cleaned(self):
        data = {"a": [1.0, float("nan")], "b": {"c": float("inf")}}
        cleaned = clean_json(data)
        assert cleaned == {"a": [1.0, None], "b": {"c": None}}

    def test_normal_values_pass_through(self):
        assert clean_json({"x": 1, "y": "text"}) == {"x": 1, "y": "text"}
        assert math.isclose(clean_json(0.5), 0.5)


class TestParseJsonIfString:
    def test_dict_passes_through(self):
        assert parse_json_if_string({"hallucination_score": 0}) == {
            "hallucination_score": 0
        }

    def test_json_string_is_parsed(self):
        result = parse_json_if_string('{"hallucination_score": 1, "reason": "x"}')
        assert result["hallucination_score"] == 1

    def test_non_json_string_becomes_reason(self):
        result = parse_json_if_string("free text verdict")
        assert result["hallucination_score"] is None
        assert result["reason"] == "free text verdict"

    def test_none_returns_placeholder(self):
        result = parse_json_if_string(None)
        assert result["hallucination_score"] is None


class TestGetUniqueSources:
    def test_deduplicates_by_url(self):
        sources = [
            {"source_title": "A", "source_url": "http://x.com"},
            {"source_title": "A2", "source_url": "http://x.com"},
            {"source_title": "B", "source_url": "http://y.com"},
        ]
        unique = get_unique_sources(sources)
        assert len(unique) == 2

    def test_respects_max_sources(self):
        sources = [
            {"source_title": f"T{i}", "source_url": f"http://s{i}.com"}
            for i in range(10)
        ]
        assert len(get_unique_sources(sources, max_sources=3)) == 3

    def test_skips_missing_urls(self):
        sources = [{"source_title": "No URL", "source_url": ""}]
        assert get_unique_sources(sources) == []
