import json
import os
import time
import pytest
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "custom-status-line", "references"))

from statusline.session_tracker import run, STALE_THRESHOLD
from statusline.formatting import visible_len


@pytest.fixture
def sessions_dir(tmp_path, monkeypatch):
    """Create a temp sessions directory and patch the module to use it."""
    d = tmp_path / "sessions"
    d.mkdir()
    monkeypatch.setattr("statusline.session_tracker.SESSIONS_DIR", str(d))
    return d


def write_session(sessions_dir, name, state="waiting", age_s=0):
    path = sessions_dir / f"{name}.json"
    path.write_text(json.dumps({"state": state, "ts": time.time() - age_s}))
    if age_s > 0:
        mtime = time.time() - age_s
        os.utime(path, (mtime, mtime))


def test_no_sessions_dir(monkeypatch):
    """Returns lines unchanged when sessions dir doesn't exist."""
    monkeypatch.setattr("statusline.session_tracker.SESSIONS_DIR", "/nonexistent")
    lines = ["line1", "line2", "line3"]
    result = run({}, lines.copy())
    assert result == lines


def test_empty_sessions_dir(sessions_dir):
    """Returns lines unchanged when no session files exist."""
    lines = ["line1", "line2", "line3"]
    result = run({}, lines.copy())
    # Still adds line showing 0 active
    assert len(result) == 4
    assert "0 active" in result[2]


def test_counts_thinking_and_waiting(sessions_dir):
    """Correctly counts thinking and waiting sessions."""
    write_session(sessions_dir, "s1", "thinking")
    write_session(sessions_dir, "s2", "waiting")
    write_session(sessions_dir, "s3", "thinking")

    lines = ["line1", "line2", "line3"]
    result = run({}, lines)

    session_line = result[2]
    assert "3 active" in session_line
    assert "2 thinking" in session_line
    assert "1 waiting" in session_line


def test_inserts_at_position_2(sessions_dir):
    """Line is inserted between line 2 (model) and line 3 (usage)."""
    write_session(sessions_dir, "s1", "thinking")

    lines = ["project", "model", "usage"]
    result = run({}, lines)

    assert result[0] == "project"
    assert result[1] == "model"
    assert "all sessions" in result[2]
    assert result[3] == "usage"


def test_appends_when_fewer_than_3_lines(sessions_dir):
    """Appends to end when lines list is short."""
    write_session(sessions_dir, "s1", "waiting")

    lines = ["only"]
    result = run({}, lines)

    assert result[0] == "only"
    assert "all sessions" in result[1]


def test_stale_sessions_removed(sessions_dir):
    """Sessions older than threshold are removed and not counted."""
    write_session(sessions_dir, "fresh", "thinking")
    write_session(sessions_dir, "stale", "thinking", age_s=STALE_THRESHOLD + 60)

    lines = ["line1", "line2", "line3"]
    result = run({}, lines)

    assert "1 active" in result[2]
    assert not (sessions_dir / "stale.json").exists()
    assert (sessions_dir / "fresh.json").exists()


def test_ignores_non_json_files(sessions_dir):
    """Non-.json files are ignored."""
    write_session(sessions_dir, "s1", "thinking")
    (sessions_dir / "readme.txt").write_text("ignore me")

    lines = ["line1", "line2", "line3"]
    result = run({}, lines)

    assert "1 active" in result[2]


def test_handles_corrupt_json(sessions_dir):
    """Corrupt JSON files are silently skipped."""
    write_session(sessions_dir, "s1", "thinking")
    (sessions_dir / "bad.json").write_text("not json{{{")

    lines = ["line1", "line2", "line3"]
    result = run({}, lines)

    assert "1 active" in result[2]
