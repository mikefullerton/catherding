"""Tests for session tracking integrated into base_info module."""
import json
import os
import time
import pytest
from unittest.mock import patch

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "custom-status-line", "references"))

from statusline.base_info import run


STALE_THRESHOLD = 3600


def make_claude_data():
    return {
        "model": {"display_name": "Test", "id": "test"},
        "context_window": {
            "remaining_percentage": 96,
            "context_window_size": 200000,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "current_usage": {},
        },
        "cost": {
            "total_duration_ms": 0,
            "total_api_duration_ms": 0,
            "total_lines_added": 0,
            "total_lines_removed": 0,
            "total_cost_usd": 0,
        },
        "cwd": "/tmp/test",
        "session_id": "test-session",
        "session_name": "",
        "rate_limits": {
            "five_hour": {"used_percentage": 0, "resets_at": 0},
            "seven_day": {"used_percentage": 0, "resets_at": 0},
        },
        "version": "1.0.0",
        "workspace": {"project_dir": "/tmp/test"},
        "transcript_path": "",
    }


@pytest.fixture
def sessions_dir(tmp_path, monkeypatch):
    d = tmp_path / "sessions"
    d.mkdir()
    # Patch the sessions dir path constructed inside base_info.run
    original_expanduser = os.path.expanduser
    def patched_expanduser(path):
        if path == "~/.claude-status-line/sessions":
            return str(d)
        return original_expanduser(path)
    monkeypatch.setattr("os.path.expanduser", patched_expanduser)
    return d


def write_session(sessions_dir, name, state="waiting", age_s=0):
    path = sessions_dir / f"{name}.json"
    path.write_text(json.dumps({"state": state, "ts": time.time() - age_s}))
    if age_s > 0:
        mtime = time.time() - age_s
        os.utime(path, (mtime, mtime))


@patch("statusline.base_info.git_cmd", return_value="")
@patch("statusline.base_info.log_to_db")
def test_counts_thinking_and_waiting(mock_log, mock_git, sessions_dir):
    write_session(sessions_dir, "s1", "thinking")
    write_session(sessions_dir, "s2", "waiting")
    write_session(sessions_dir, "s3", "thinking")

    lines = run(make_claude_data(), [])
    session_line = lines[2]
    assert "3 active" in session_line
    assert "2 thinking" in session_line
    assert "1 waiting" in session_line


@patch("statusline.base_info.git_cmd", return_value="")
@patch("statusline.base_info.log_to_db")
def test_session_line_at_position_2(mock_log, mock_git, sessions_dir):
    write_session(sessions_dir, "s1", "thinking")

    lines = run(make_claude_data(), [])
    assert len(lines) == 3
    assert "all sessions" in lines[2]


@patch("statusline.base_info.git_cmd", return_value="")
@patch("statusline.base_info.log_to_db")
def test_stale_sessions_removed(mock_log, mock_git, sessions_dir):
    write_session(sessions_dir, "fresh", "thinking")
    write_session(sessions_dir, "stale", "thinking", age_s=STALE_THRESHOLD + 60)

    lines = run(make_claude_data(), [])
    assert "1 active" in lines[2]
    assert not (sessions_dir / "stale.json").exists()
    assert (sessions_dir / "fresh.json").exists()


@patch("statusline.base_info.git_cmd", return_value="")
@patch("statusline.base_info.log_to_db")
def test_ignores_non_json_files(mock_log, mock_git, sessions_dir):
    write_session(sessions_dir, "s1", "thinking")
    (sessions_dir / "readme.txt").write_text("ignore me")

    lines = run(make_claude_data(), [])
    assert "1 active" in lines[2]


@patch("statusline.base_info.git_cmd", return_value="")
@patch("statusline.base_info.log_to_db")
def test_handles_corrupt_json(mock_log, mock_git, sessions_dir):
    write_session(sessions_dir, "s1", "thinking")
    (sessions_dir / "bad.json").write_text("not json{{{")

    lines = run(make_claude_data(), [])
    assert "1 active" in lines[2]


@patch("statusline.base_info.git_cmd", return_value="")
@patch("statusline.base_info.log_to_db")
def test_columns_aligned(mock_log, mock_git, sessions_dir):
    """Session line columns align with model and usage lines."""
    from statusline.formatting import visible_len
    write_session(sessions_dir, "s1", "thinking")

    lines = run(make_claude_data(), [])
    # Find pipe positions in each line (skip the leading border pipe)
    def pipe_positions(line):
        # Strip ANSI, find | positions after the first one
        import re
        plain = re.sub(r"\033\[[0-9;]*m", "", line)
        positions = [i for i, c in enumerate(plain) if c == "|"]
        return positions[1:]  # skip leading border

    model_pipes = pipe_positions(lines[1])
    session_pipes = pipe_positions(lines[2])

    # First few pipe positions should match
    for i in range(min(len(model_pipes), len(session_pipes))):
        assert model_pipes[i] == session_pipes[i], (
            f"Pipe {i} misaligned: model={model_pipes[i]}, session={session_pipes[i]}"
        )
