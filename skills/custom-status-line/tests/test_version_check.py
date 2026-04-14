"""Tests for the database-backed version_check pipeline module."""
import pytest
from unittest.mock import patch

from statusline import version_check
from statusline.db import get_db, insert_version
from statusline.formatting import Row, visible_len


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Point version_check at a temporary DB and reset cache state."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(version_check, "DB_PATH", db_path)
    monkeypatch.setattr(version_check, "_last_check_time", 0)
    monkeypatch.setattr(version_check, "_cached_version_rows", None)
    return db_path


def claude_data(version, extra_fields=None):
    """Build a minimal claude_data dict with optional extra fields."""
    data = {
        "version": version,
        "session_id": "s1",
        "model": {"id": "opus", "display_name": "Opus"},
        "context_window": {"context_window_size": 200000},
    }
    if extra_fields:
        data.update(extra_fields)
    return data


class TestVersionSeeding:
    def test_inserts_current_version_if_new(self, tmp_db):
        data = claude_data("2.1.105")
        version_check._check_version(data)

        db = get_db(tmp_db)
        row = db.execute(
            "SELECT claude_version FROM claude_versions"
        ).fetchone()
        assert row[0] == "2.1.105"
        db.close()

    def test_does_not_duplicate_existing_version(self, tmp_db):
        data = claude_data("2.1.105")
        version_check._check_version(data)
        version_check._check_version(data)

        db = get_db(tmp_db)
        count = db.execute("SELECT count(*) FROM claude_versions").fetchone()[0]
        assert count == 1
        db.close()

    def test_missing_version_returns_empty(self, tmp_db):
        rows = version_check._check_version({"session_id": "s1"})
        assert rows == []


class TestNoUpgrade:
    def test_returns_empty_when_no_newer_versions(self, tmp_db, monkeypatch):
        monkeypatch.setattr(version_check, "BUILT_FOR_VERSION", "2.1.105")
        rows = version_check._check_version(claude_data("2.1.105"))
        assert rows == []

    def test_returns_empty_when_current_is_older(self, tmp_db, monkeypatch):
        monkeypatch.setattr(version_check, "BUILT_FOR_VERSION", "2.1.200")
        rows = version_check._check_version(claude_data("2.1.105"))
        assert rows == []


class TestUpgradeDisplay:
    def test_shows_row_for_newer_version(self, tmp_db, monkeypatch):
        monkeypatch.setattr(version_check, "BUILT_FOR_VERSION", "2.1.100")
        # Pre-seed the BUILT_FOR_VERSION in DB so diff has a reference
        db = get_db(tmp_db)
        insert_version(db, "2.1.100", claude_data("2.1.100"), 5)
        db.close()

        rows = version_check._check_version(claude_data("2.1.101"))
        assert len(rows) == 1
        assert isinstance(rows[0], Row)
        assert "2.1.101" in rows[0].columns[0]

    def test_one_row_per_newer_version(self, tmp_db, monkeypatch):
        monkeypatch.setattr(version_check, "BUILT_FOR_VERSION", "2.1.100")
        db = get_db(tmp_db)
        insert_version(db, "2.1.100", claude_data("2.1.100"), 5)
        insert_version(db, "2.1.101", claude_data("2.1.101"), 5)
        insert_version(db, "2.1.102", claude_data("2.1.102"), 5)
        db.close()

        rows = version_check._check_version(claude_data("2.1.103"))
        # 2.1.101, 2.1.102, 2.1.103 — three newer than BUILT_FOR_VERSION
        assert len(rows) == 3
        versions_shown = [r.columns[0] for r in rows]
        assert "2.1.101" in versions_shown[0]
        assert "2.1.102" in versions_shown[1]
        assert "2.1.103" in versions_shown[2]


class TestFieldDiff:
    def test_counts_new_fields_vs_previous(self, tmp_db, monkeypatch):
        monkeypatch.setattr(version_check, "BUILT_FOR_VERSION", "2.1.100")
        db = get_db(tmp_db)
        insert_version(db, "2.1.100", claude_data("2.1.100"), 5)
        db.close()

        # Add two new top-level fields in 2.1.101
        new_data = claude_data("2.1.101", {"foo": 1, "bar": 2})
        rows = version_check._check_version(new_data)

        assert len(rows) == 1
        # Col 1 should mention "2 new fields"
        assert "2 new fields" in rows[0].columns[1]

    def test_no_new_fields_message(self, tmp_db, monkeypatch):
        monkeypatch.setattr(version_check, "BUILT_FOR_VERSION", "2.1.100")
        db = get_db(tmp_db)
        insert_version(db, "2.1.100", claude_data("2.1.100"), 5)
        db.close()

        # Same fields, just a new version
        rows = version_check._check_version(claude_data("2.1.101"))
        assert len(rows) == 1
        assert "no new fields" in rows[0].columns[1]

    def test_shows_removed_count(self, tmp_db, monkeypatch):
        monkeypatch.setattr(version_check, "BUILT_FOR_VERSION", "2.1.100")
        db = get_db(tmp_db)
        # Seed 2.1.100 with an extra field
        insert_version(
            db, "2.1.100",
            claude_data("2.1.100", {"old_field": "removed"}),
            6,
        )
        db.close()

        # 2.1.101 removes that field
        rows = version_check._check_version(claude_data("2.1.101"))
        assert len(rows) == 1
        # Col 1 should show (-1) for removed field
        assert "-1" in rows[0].columns[1]

    def test_diffs_against_previous_version_not_built_for(self, tmp_db, monkeypatch):
        """Each version row diffs against its predecessor in the DB."""
        monkeypatch.setattr(version_check, "BUILT_FOR_VERSION", "2.1.100")
        db = get_db(tmp_db)
        insert_version(db, "2.1.100", claude_data("2.1.100"), 5)
        # 2.1.101 adds field 'foo'
        insert_version(db, "2.1.101", claude_data("2.1.101", {"foo": 1}), 6)
        db.close()

        # 2.1.102 adds field 'bar' on top of 2.1.101
        rows = version_check._check_version(
            claude_data("2.1.102", {"foo": 1, "bar": 2})
        )
        assert len(rows) == 2
        # 2.1.101 diffs vs 2.1.100: 1 new field (foo)
        assert "1 new field" in rows[0].columns[1]
        # 2.1.102 diffs vs 2.1.101: 1 new field (bar), NOT 2
        assert "1 new field" in rows[1].columns[1]


class TestThrottling:
    def test_checks_on_first_invocation(self, tmp_db, monkeypatch):
        monkeypatch.setattr(version_check, "BUILT_FOR_VERSION", "2.1.100")
        monkeypatch.setattr(version_check, "_last_check_time", 0)

        lines = []
        rows = []
        version_check.run(claude_data("2.1.105"), lines, rows)

        # After first run, _last_check_time should be set
        assert version_check._last_check_time > 0

    def test_skips_check_if_recent(self, tmp_db, monkeypatch):
        import time
        monkeypatch.setattr(version_check, "BUILT_FOR_VERSION", "2.1.100")
        # Pretend we checked 1 second ago
        monkeypatch.setattr(version_check, "_last_check_time", time.time() - 1)
        monkeypatch.setattr(version_check, "_cached_version_rows", [])

        with patch.object(version_check, "_check_version") as mock_check:
            lines = []
            rows = []
            version_check.run(claude_data("2.1.105"), lines, rows)
            # Should not call _check_version because of throttle
            mock_check.assert_not_called()

    def test_rechecks_after_interval(self, tmp_db, monkeypatch):
        import time
        monkeypatch.setattr(version_check, "BUILT_FOR_VERSION", "2.1.100")
        # Pretend we checked longer than CHECK_INTERVAL ago
        monkeypatch.setattr(
            version_check, "_last_check_time",
            time.time() - version_check.CHECK_INTERVAL - 1,
        )
        monkeypatch.setattr(version_check, "_cached_version_rows", [])

        with patch.object(version_check, "_check_version", return_value=[]) as mock_check:
            lines = []
            rows = []
            version_check.run(claude_data("2.1.105"), lines, rows)
            mock_check.assert_called_once()


class TestRunIntegration:
    def test_appends_rows_when_upgrade(self, tmp_db, monkeypatch):
        monkeypatch.setattr(version_check, "BUILT_FOR_VERSION", "2.1.100")
        db = get_db(tmp_db)
        insert_version(db, "2.1.100", claude_data("2.1.100"), 5)
        db.close()

        lines = []
        rows = []
        version_check.run(claude_data("2.1.101"), lines, rows)
        assert len(rows) == 1
        assert isinstance(rows[0], Row)

    def test_does_not_append_when_no_upgrade(self, tmp_db, monkeypatch):
        monkeypatch.setattr(version_check, "BUILT_FOR_VERSION", "2.1.200")

        lines = []
        rows = []
        version_check.run(claude_data("2.1.105"), lines, rows)
        assert rows == []

    def test_returns_lines_unchanged(self, tmp_db, monkeypatch):
        monkeypatch.setattr(version_check, "BUILT_FOR_VERSION", "2.1.100")
        lines = ["existing line"]
        rows = []
        result = version_check.run(claude_data("2.1.105"), lines, rows)
        assert result == ["existing line"]

    def test_handles_none_rows(self, tmp_db, monkeypatch):
        monkeypatch.setattr(version_check, "BUILT_FOR_VERSION", "2.1.200")
        result = version_check.run(claude_data("2.1.105"), [], None)
        # Should not raise — creates an empty rows list internally
        assert result == []
