"""Tests for audit log reporting and statistics."""

import pandas as pd

import modules.audit_reader as audit_reader
from modules.audit_reader import get_stats, get_top_questions


class TestTopQuestions:
    def test_counts_and_orders_questions(self):
        df = pd.DataFrame({"query": ["a", "b", "a", "a", "b", "c"]})
        top = get_top_questions(df, limit=2)
        assert top[0] == {"question": "a", "count": 3}
        assert len(top) == 2

    def test_missing_column_returns_empty(self):
        assert get_top_questions(pd.DataFrame({"other": [1]})) == []

    def test_blank_queries_are_ignored(self):
        df = pd.DataFrame({"query": ["", "  ", "real question"]})
        top = get_top_questions(df)
        assert len(top) == 1


class TestGetStats:
    def _patch_df(self, monkeypatch, df):
        monkeypatch.setattr(audit_reader, "_load_audit_df", lambda: df)

    def test_stats_from_risk_levels(self, monkeypatch):
        df = pd.DataFrame({"risk_level": ["Low", "Low", "Medium", "High"]})
        self._patch_df(monkeypatch, df)
        stats = get_stats()
        assert stats["total_queries"] == 4
        assert stats["grounded_pct"] == 50.0
        assert stats["risk_counts"] == {"Low": 2, "Medium": 1, "High": 1}

    def test_empty_log_is_safe(self, monkeypatch):
        self._patch_df(monkeypatch, pd.DataFrame())
        stats = get_stats()
        assert stats["total_queries"] == 0
        assert stats["grounded_pct"] is None

    def test_db_failure_is_safe(self, monkeypatch):
        def boom():
            raise RuntimeError("db down")

        monkeypatch.setattr(audit_reader, "_load_audit_df", boom)
        stats = get_stats()
        assert stats["total_queries"] == 0
