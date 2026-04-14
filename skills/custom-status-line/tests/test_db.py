import sqlite3
import pytest
from statusline.db import (
    get_db, upsert_session, append_weekly_usage, DB_VERSION,
    get_version, insert_version, get_versions_after, _extract_paths,
)


class TestGetDb:
    def test_creates_tables(self, tmp_path):
        db = get_db(str(tmp_path / "test.db"))
        cursor = db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor]
        assert "sessions" in tables
        assert "weekly_usage" in tables
        assert "claude_versions" in tables
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


class TestExtractPaths:
    def test_flat_object(self):
        paths = _extract_paths({"a": 1, "b": 2})
        assert set(paths) == {"a", "b"}

    def test_nested_object(self):
        paths = _extract_paths({"a": {"b": 1, "c": 2}})
        assert set(paths) == {"a", "a.b", "a.c"}

    def test_deeply_nested(self):
        paths = _extract_paths({"a": {"b": {"c": {"d": 1}}}})
        assert set(paths) == {"a", "a.b", "a.b.c", "a.b.c.d"}

    def test_list_sample(self):
        paths = _extract_paths({"items": [{"x": 1, "y": 2}]})
        assert set(paths) == {"items", "items[].x", "items[].y"}

    def test_empty_list_ignored(self):
        paths = _extract_paths({"items": []})
        assert set(paths) == {"items"}

    def test_primitive_values(self):
        paths = _extract_paths({"a": "hello", "b": 42, "c": True, "d": None})
        assert set(paths) == {"a", "b", "c", "d"}

    def test_empty_dict(self):
        assert _extract_paths({}) == []


SAMPLE_CLAUDE_DATA = {
    "version": "2.1.105",
    "model": {"id": "claude-opus-4-6", "display_name": "Claude Opus 4.6"},
    "context_window": {"context_window_size": 200000},
}


class TestInsertVersion:
    def test_inserts_new_version(self, tmp_path):
        db = get_db(str(tmp_path / "test.db"))
        insert_version(db, "2.1.105", SAMPLE_CLAUDE_DATA, 5)
        row = db.execute("SELECT claude_version, fields_count FROM claude_versions").fetchone()
        assert row[0] == "2.1.105"
        assert row[1] == 5
        db.close()

    def test_stores_blob_as_json(self, tmp_path):
        import json
        db = get_db(str(tmp_path / "test.db"))
        insert_version(db, "2.1.105", SAMPLE_CLAUDE_DATA, 5)
        raw = db.execute("SELECT fields FROM claude_versions").fetchone()[0]
        # Must be self-contained, valid JSON of the full blob (not a bare list)
        parsed = json.loads(raw)
        assert isinstance(parsed, dict)
        assert parsed == SAMPLE_CLAUDE_DATA
        db.close()

    def test_ignores_duplicate(self, tmp_path):
        db = get_db(str(tmp_path / "test.db"))
        insert_version(db, "2.1.105", SAMPLE_CLAUDE_DATA, 5)
        # Insert again with different data — should be ignored
        insert_version(db, "2.1.105", {"version": "changed"}, 99)
        row = db.execute("SELECT fields_count FROM claude_versions").fetchone()
        assert row[0] == 5
        assert db.execute("SELECT count(*) FROM claude_versions").fetchone()[0] == 1
        db.close()


class TestGetVersion:
    def test_returns_none_for_missing(self, tmp_path):
        db = get_db(str(tmp_path / "test.db"))
        assert get_version(db, "2.1.999") is None
        db.close()

    def test_returns_parsed_row(self, tmp_path):
        db = get_db(str(tmp_path / "test.db"))
        insert_version(db, "2.1.105", SAMPLE_CLAUDE_DATA, 5)
        result = get_version(db, "2.1.105")
        assert result["claude_version"] == "2.1.105"
        assert result["fields_count"] == 5
        assert result["blob"] == SAMPLE_CLAUDE_DATA
        assert result["first_seen"]
        db.close()

    def test_extracts_field_paths(self, tmp_path):
        db = get_db(str(tmp_path / "test.db"))
        insert_version(db, "2.1.105", SAMPLE_CLAUDE_DATA, 5)
        result = get_version(db, "2.1.105")
        # field_paths should include all dotted paths from the blob
        assert "version" in result["field_paths"]
        assert "model" in result["field_paths"]
        assert "model.id" in result["field_paths"]
        assert "context_window.context_window_size" in result["field_paths"]
        # Must be sorted
        assert result["field_paths"] == sorted(result["field_paths"])
        db.close()


class TestGetVersionsAfter:
    def test_empty_when_none_after(self, tmp_path):
        db = get_db(str(tmp_path / "test.db"))
        insert_version(db, "2.1.100", SAMPLE_CLAUDE_DATA, 5)
        assert get_versions_after(db, "2.1.100") == []
        assert get_versions_after(db, "2.1.200") == []
        db.close()

    def test_returns_newer_versions(self, tmp_path):
        db = get_db(str(tmp_path / "test.db"))
        insert_version(db, "2.1.100", SAMPLE_CLAUDE_DATA, 5)
        insert_version(db, "2.1.101", SAMPLE_CLAUDE_DATA, 5)
        insert_version(db, "2.1.102", SAMPLE_CLAUDE_DATA, 5)
        result = get_versions_after(db, "2.1.100")
        assert [v["claude_version"] for v in result] == ["2.1.101", "2.1.102"]
        db.close()

    def test_ordered_ascending(self, tmp_path):
        db = get_db(str(tmp_path / "test.db"))
        # Insert out of order
        insert_version(db, "2.1.103", SAMPLE_CLAUDE_DATA, 5)
        insert_version(db, "2.1.101", SAMPLE_CLAUDE_DATA, 5)
        insert_version(db, "2.1.102", SAMPLE_CLAUDE_DATA, 5)
        result = get_versions_after(db, "2.1.100")
        versions = [v["claude_version"] for v in result]
        assert versions == ["2.1.101", "2.1.102", "2.1.103"]
        db.close()

    def test_exclusive_boundary(self, tmp_path):
        db = get_db(str(tmp_path / "test.db"))
        insert_version(db, "2.1.100", SAMPLE_CLAUDE_DATA, 5)
        insert_version(db, "2.1.101", SAMPLE_CLAUDE_DATA, 5)
        result = get_versions_after(db, "2.1.100")
        # Should NOT include 2.1.100 itself
        assert [v["claude_version"] for v in result] == ["2.1.101"]
        db.close()
