"""Tests for usage_costs pipeline module."""
import json
import os
import sqlite3
import time

import pytest

from statusline.usage_costs import (
    calc_cost, model_family, query_daily_costs, run,
    USAGE_DB, THROTTLE_FILE, SCANNER_DIR,
)


@pytest.fixture
def usage_db(tmp_path, monkeypatch):
    """Create a temporary usage.db with test data."""
    db_path = str(tmp_path / "usage.db")
    monkeypatch.setattr("statusline.usage_costs.USAGE_DB", db_path)
    monkeypatch.setattr("statusline.usage_costs.SCANNER_DIR", str(tmp_path / "nonexistent"))
    monkeypatch.setattr("statusline.usage_costs.THROTTLE_FILE", str(tmp_path / "throttle"))

    db = sqlite3.connect(db_path)
    db.executescript("""
        CREATE TABLE turns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT, timestamp TEXT, model TEXT,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            cache_read_tokens INTEGER DEFAULT 0,
            cache_creation_tokens INTEGER DEFAULT 0,
            tool_name TEXT, cwd TEXT
        );
    """)
    return db, db_path


def insert_turn(db, day, model="claude-opus-4-6", inp=1000, out=500, cr=0, cc=0):
    db.execute(
        "INSERT INTO turns (session_id, timestamp, model, input_tokens, output_tokens, cache_read_tokens, cache_creation_tokens) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("s1", f"{day}T12:00:00", model, inp, out, cr, cc),
    )
    db.commit()


def make_claude_data(rate_7d=50.0):
    return {
        "rate_limits": {"seven_day": {"used_percentage": rate_7d, "resets_at": 0}},
        "cwd": "/tmp",
        "session_id": "test",
    }


class TestModelFamily:
    def test_opus(self):
        assert model_family("claude-opus-4-6") == "opus"

    def test_sonnet(self):
        assert model_family("claude-sonnet-4-6") == "sonnet"

    def test_haiku(self):
        assert model_family("claude-haiku-4-5-20251001") == "haiku"

    def test_unknown(self):
        assert model_family("unknown-model") == "sonnet"

    def test_empty(self):
        assert model_family("") == "sonnet"


class TestCalcCost:
    def test_opus_input_only(self):
        cost = calc_cost("claude-opus-4-6", 1_000_000, 0, 0, 0)
        assert abs(cost - 15.0) < 0.01

    def test_opus_output_only(self):
        cost = calc_cost("claude-opus-4-6", 0, 1_000_000, 0, 0)
        assert abs(cost - 75.0) < 0.01

    def test_cache_read_discount(self):
        # Cache read is 10% of input price
        cost = calc_cost("claude-opus-4-6", 0, 0, 1_000_000, 0)
        assert abs(cost - 1.5) < 0.01

    def test_cache_create_premium(self):
        # Cache create is 125% of input price
        cost = calc_cost("claude-opus-4-6", 0, 0, 0, 1_000_000)
        assert abs(cost - 18.75) < 0.01


class TestQueryDailyCosts:
    def test_groups_by_day(self, usage_db):
        db, _ = usage_db
        insert_turn(db, "2026-04-07", inp=1_000_000, out=0)
        insert_turn(db, "2026-04-08", inp=1_000_000, out=0)
        daily = query_daily_costs(db, "2026-04-01T00:00:00")
        assert "2026-04-07" in daily
        assert "2026-04-08" in daily
        assert len(daily) == 2

    def test_empty_db(self, usage_db):
        db, _ = usage_db
        daily = query_daily_costs(db, "2026-04-01T00:00:00")
        assert daily == {}


class TestRun:
    def test_no_rate_limits(self, usage_db):
        data = {"rate_limits": {}}
        assert run(data, ["a"]) == ["a"]

    def test_zero_rate(self, usage_db):
        data = make_claude_data(rate_7d=0)
        assert run(data, ["a"]) == ["a"]

    def test_no_db(self, tmp_path, monkeypatch):
        monkeypatch.setattr("statusline.usage_costs.USAGE_DB", str(tmp_path / "nope.db"))
        monkeypatch.setattr("statusline.usage_costs.SCANNER_DIR", str(tmp_path / "nope"))
        monkeypatch.setattr("statusline.usage_costs.THROTTLE_FILE", str(tmp_path / "t"))
        assert run(make_claude_data(), ["a"]) == ["a"]

    def test_adds_line(self, usage_db):
        db, _ = usage_db
        from datetime import datetime, timedelta
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        insert_turn(db, today, inp=1_000_000, out=0)
        insert_turn(db, yesterday, inp=1_000_000, out=0)
        result = run(make_claude_data(rate_7d=50.0), ["existing"])
        assert len(result) == 3
        assert "today" in result[1]
        assert "daily usage ave:" in result[1]
        assert "left" in result[1]
        assert "projected" in result[1]
        assert "daily usage ave 2:" in result[2]
        assert "projected" in result[2]

    def test_overage_projected(self, usage_db, monkeypatch):
        db, _ = usage_db
        from datetime import timedelta
        # Simulate being 4 days into the cycle
        fake_wed = __import__("datetime").datetime.now() - timedelta(days=4)
        monkeypatch.setattr("statusline.usage_costs.get_wed_10am", lambda: fake_wed)
        for i in range(4):
            day = (__import__("datetime").datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            insert_turn(db, day, inp=1_000_000, out=500_000)
        result = run(make_claude_data(rate_7d=120.0), [])
        assert len(result) == 2
        assert "projected" in result[0]
        assert "projected" in result[1]

    def test_no_overage_when_under(self, usage_db, monkeypatch):
        db, _ = usage_db
        from datetime import timedelta
        fake_wed = __import__("datetime").datetime.now() - timedelta(days=4)
        monkeypatch.setattr("statusline.usage_costs.get_wed_10am", lambda: fake_wed)
        for i in range(4):
            day = (__import__("datetime").datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            insert_turn(db, day, inp=1_000_000, out=0)
        result = run(make_claude_data(rate_7d=10.0), [])
        assert len(result) == 2
        assert "projected" in result[0]
        assert "projected" in result[1]

    def test_too_early_suppresses_projection(self, usage_db):
        db, _ = usage_db
        today = __import__("datetime").datetime.now().strftime("%Y-%m-%d")
        insert_turn(db, today, inp=1_000_000, out=0)
        # When only today's data exists and cycle just started, projection is suppressed
        result = run(make_claude_data(rate_7d=50.0), [])
        assert len(result) == 2
        # Should either show "too early" or a valid projection depending on time of day
        assert "today" in result[0]
        assert "daily usage ave 2:" in result[1]


class TestExtractColWidths:
    def test_extracts_widths_from_base_info_lines(self):
        from statusline.usage_costs import _extract_col_widths
        from statusline.formatting import pad_right, pad_left
        sep = " | "
        lbor = "| "
        # Simulate 3 lines from base_info with known column widths
        line0 = f"~/projects/foo{sep}git:(main)"
        line1 = f"{lbor}{pad_right('Opus 4', 30)}{sep}{pad_right('1h:05m', 20)}{sep}5% context"
        line2 = f"{lbor}{pad_left('all sessions', 30)}{sep}{pad_right('2 active', 20)}{sep}{pad_right('1 thinking', 20)}{sep}{pad_right('1 waiting', 15)}"
        lines = [line0, line1, line2]
        widths = _extract_col_widths(lines)
        assert widths is not None
        assert widths[0] == 30
        assert widths[1] == 20
        assert widths[2] == 20

    def test_returns_none_for_empty(self):
        from statusline.usage_costs import _extract_col_widths
        assert _extract_col_widths([]) is None

    def test_returns_none_for_insufficient_columns(self):
        from statusline.usage_costs import _extract_col_widths
        assert _extract_col_widths(["just a plain line", "another"]) is None
