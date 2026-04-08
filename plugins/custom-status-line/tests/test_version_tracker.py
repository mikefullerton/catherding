"""Tests for version_tracker pipeline module."""
import json
import os

import pytest

from statusline.version_tracker import extract_paths, run, VERSION_FILE


@pytest.fixture
def version_file(tmp_path, monkeypatch):
    """Create a temporary version file and patch VERSION_FILE."""
    path = tmp_path / "claude_version.json"
    baseline = {
        "built_against": "2.1.96",
        "acknowledged": True,
        "fields": [
            "cwd",
            "model",
            "model.id",
            "model.display_name",
            "session_id",
            "version",
        ],
    }
    path.write_text(json.dumps(baseline))
    monkeypatch.setattr("statusline.version_tracker.VERSION_FILE", str(path))
    return path


class TestExtractPaths:
    def test_flat(self):
        assert sorted(extract_paths({"a": 1, "b": "x"})) == ["a", "b"]

    def test_nested(self):
        paths = extract_paths({"a": {"b": 1, "c": {"d": 2}}})
        assert sorted(paths) == ["a", "a.b", "a.c", "a.c.d"]

    def test_list_with_objects(self):
        paths = extract_paths({"items": [{"x": 1}]})
        assert "items" in paths
        assert "items[].x" in paths

    def test_empty_list(self):
        paths = extract_paths({"items": []})
        assert paths == ["items"]

    def test_empty_dict(self):
        assert extract_paths({}) == []


class TestRun:
    def test_same_version_no_output(self, version_file):
        data = {"version": "2.1.96", "cwd": "/tmp", "session_id": "s"}
        result = run(data, ["existing"])
        assert result == ["existing"]

    def test_new_version_no_new_fields(self, version_file):
        data = {"version": "2.2.0", "cwd": "/tmp", "session_id": "s"}
        result = run(data, [])
        assert len(result) == 1
        assert "2.2.0" in result[0]
        assert "2.1.96" in result[0]
        assert "no new fields" in result[0]

    def test_new_version_with_new_fields(self, version_file):
        data = {
            "version": "2.2.0",
            "cwd": "/tmp",
            "session_id": "s",
            "model": {"id": "opus", "display_name": "Opus"},
            "brand_new": "hello",
        }
        result = run(data, ["line1"])
        assert len(result) == 2
        assert "line1" == result[0]
        assert "2.2.0" in result[1]
        assert "brand_new" in result[1]

    def test_missing_version_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "statusline.version_tracker.VERSION_FILE",
            str(tmp_path / "nonexistent.json"),
        )
        data = {"version": "2.2.0"}
        result = run(data, ["a"])
        assert result == ["a"]

    def test_no_version_in_input(self, version_file):
        result = run({"cwd": "/tmp"}, [])
        assert result == []

    def test_many_new_fields_truncated(self, version_file):
        data = {"version": "3.0.0"}
        for i in range(12):
            data[f"field_{i:02d}"] = "val"
        result = run(data, [])
        assert len(result) == 1
        assert "+4 more" in result[0] or "more" in result[0]
