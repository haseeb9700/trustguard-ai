"""Tests for hierarchical claim verification logic (pure functions only)."""

from modules.claim_verifier import _normalize_verdict, _or_join, _parse_json


class TestOrJoin:
    def test_contradiction_dominates(self):
        assert _or_join(["entailed", "contradicted", "baseless"]) == "contradicted"

    def test_one_supporting_chunk_suffices(self):
        assert _or_join(["baseless", "entailed", "baseless"]) == "entailed"

    def test_no_decisive_evidence_is_baseless(self):
        assert _or_join(["baseless", "baseless"]) == "baseless"

    def test_empty_verdicts_are_baseless(self):
        assert _or_join([]) == "baseless"


class TestNormalizeVerdict:
    def test_valid_verdicts_pass_through(self):
        assert _normalize_verdict("entailed") == "entailed"
        assert _normalize_verdict("CONTRADICTED") == "contradicted"

    def test_unknown_verdicts_default_to_baseless(self):
        assert _normalize_verdict("supported") == "baseless"
        assert _normalize_verdict("") == "baseless"


class TestParseJson:
    def test_plain_json(self):
        assert _parse_json('["a", "b"]') == ["a", "b"]

    def test_fenced_json(self):
        assert _parse_json('```json\n["a"]\n```') == ["a"]

    def test_invalid_json_returns_none(self):
        assert _parse_json("this is not json") is None
