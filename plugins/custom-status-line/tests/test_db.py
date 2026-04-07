import sqlite3
import pytest
from statusline.db import get_db, upsert_session, append_weekly_usage, DB_VERSION


class TestGetDb:
    def test_creates_tables(self, tmp_path):
        db = get_db(str(tmp_path / "test.db"))
        cursor = db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor]
        assert "sessions" in tables
        assert "weekly_usage" in tables
        db.close()

    def test_sets_user_version(self, tmp_path):
        db = get_db(str(tmp_path / "test.db"))
        version = db.execute("PRAGMA user_version").fetchone()[0]
        assert version == DB_VERSION
        db.close()

    def test_migration_is_idempotent(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        db1 = get_db(db_path)
        db1.close()
        db2 = get_db(db_path)
        version = db2.execute("PRAGMA user_version").fetchone()[0]
        assert version == DB_VERSION
        db2.close()


SESSION_KWARGS = dict(
    session_id="sess-1", session_name="test", model_id="opus-4",
    model_display="Opus 4", claude_version="1.0", cwd="/tmp",
    project_dir="/tmp", transcript_path="/tmp/t.json",
    context_window_size=200000, duration_s=60, api_duration_ms=5000,
    lines_added=10, lines_removed=5, total_cost_usd="0.50",
    total_input_tokens=1000, total_output_tokens=500,
    cache_create_tokens=100, cache_read_tokens=200,
    context_used_pct=15,
)


class TestUpsertSession:
    def test_insert_new_session(self, tmp_path):
        db = get_db(str(tmp_path / "test.db"))
        upsert_session(db, **SESSION_KWARGS)
        row = db.execute("SELECT session_id, model_id FROM sessions").fetchone()
        assert row[0] == "sess-1"
        assert row[1] == "opus-4"
        db.close()

    def test_upsert_updates_existing(self, tmp_path):
        db = get_db(str(tmp_path / "test.db"))
        upsert_session(db, **SESSION_KWARGS)
        upsert_session(db, **{**SESSION_KWARGS, "duration_s": 120, "lines_added": 20})
        row = db.execute("SELECT duration_s, lines_added FROM sessions").fetchone()
        assert row[0] == 120
        assert row[1] == 20
        assert db.execute("SELECT count(*) FROM sessions").fetchone()[0] == 1
        db.close()


WEEKLY_KWARGS = dict(
    session_id="sess-1", week_start="2026-04-02",
    elapsed_hours=48, elapsed_day=2.0,
    weekly_pct=28.5, daily_avg_pct=14.3,
    five_hour_pct=5.0, five_hour_resets_at=0,
    seven_day_resets_at=0, projected_pct=100.0,
)


class TestAppendWeeklyUsage:
    def test_appends_new_row(self, tmp_path):
        db = get_db(str(tmp_path / "test.db"))
        append_weekly_usage(db, **WEEKLY_KWARGS)
        count = db.execute("SELECT count(*) FROM weekly_usage").fetchone()[0]
        assert count == 1
        db.close()

    def test_dedup_skips_unchanged(self, tmp_path):
        db = get_db(str(tmp_path / "test.db"))
        append_weekly_usage(db, **WEEKLY_KWARGS)
        append_weekly_usage(db, **WEEKLY_KWARGS)
        count = db.execute("SELECT count(*) FROM weekly_usage").fetchone()[0]
        assert count == 1
        db.close()

    def test_appends_when_values_change(self, tmp_path):
        db = get_db(str(tmp_path / "test.db"))
        append_weekly_usage(db, **WEEKLY_KWARGS)
        append_weekly_usage(db, **{**WEEKLY_KWARGS, "weekly_pct": 30.0})
        count = db.execute("SELECT count(*) FROM weekly_usage").fetchone()[0]
        assert count == 2
        db.close()
