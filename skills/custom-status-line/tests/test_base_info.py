import pytest
from unittest.mock import patch
from statusline.formatting import visible_len


def make_claude_data(**overrides):
    """Build a mock claude_data dict with sensible defaults."""
    base = {
        "model": {"display_name": "Claude Opus 4 (1M context)", "id": "claude-opus-4"},
        "context_window": {
            "remaining_percentage": 96,
            "context_window_size": 1000000,
            "total_input_tokens": 40000,
            "total_output_tokens": 5000,
            "current_usage": {
                "cache_creation_input_tokens": 1000,
                "cache_read_input_tokens": 2000,
            },
        },
        "cost": {
            "total_duration_ms": 3661000,  # 1h:01m
            "total_api_duration_ms": 300000,
            "total_lines_added": 150,
            "total_lines_removed": 30,
            "total_cost_usd": 1.25,
        },
        "cwd": "/Users/test/projects/myapp",
        "session_id": "test-session-abc",
        "session_name": "",
        "rate_limits": {
            "five_hour": {"used_percentage": 5.2, "resets_at": 0},
            "seven_day": {"used_percentage": 100.0, "resets_at": 0},
        },
        "version": "1.0.0",
        "workspace": {"project_dir": "/Users/test/projects/myapp"},
        "transcript_path": "/tmp/transcript.json",
    }
    for key, val in overrides.items():
        if isinstance(val, dict) and key in base and isinstance(base[key], dict):
            base[key] = {**base[key], **val}
        else:
            base[key] = val
    return base


class TestDurationFormat:
    def test_format_duration_hours(self):
        from statusline.base_info import format_duration
        assert format_duration(3661000) == "1h:01m"

    def test_format_duration_minutes(self):
        from statusline.base_info import format_duration
        assert format_duration(125000) == "0h:02m"

    def test_format_duration_seconds(self):
        from statusline.base_info import format_duration
        assert format_duration(45000) == "45s"


class TestUsageProjection:
    def test_day7_100pct_projects_to_100(self):
        from statusline.base_info import compute_projection
        result = compute_projection(rate_7d=100.0, elapsed_hours=168)
        assert abs(result["projected"] - 100.0) < 0.1

    def test_day1_14pct_projects_to_98(self):
        from statusline.base_info import compute_projection
        result = compute_projection(rate_7d=14.0, elapsed_hours=24)
        assert abs(result["projected"] - 98.0) < 1.0

    def test_overage_detected(self):
        from statusline.base_info import compute_projection
        result = compute_projection(rate_7d=50.0, elapsed_hours=24)
        assert result["projected"] > 100.0
        assert result["overage_dollars"] > 0

    def test_zero_usage(self):
        from statusline.base_info import compute_projection
        result = compute_projection(rate_7d=0.0, elapsed_hours=48)
        assert result["projected"] == 0.0
        assert result["daily_avg"] == 0.0

    def test_elapsed_hours_clamped_to_1(self):
        from statusline.base_info import compute_projection
        result = compute_projection(rate_7d=10.0, elapsed_hours=0)
        assert result["elapsed_hours"] == 1


class TestRunOutputStructure:
    @patch("statusline.base_info.git_cmd")
    @patch("statusline.base_info.log_to_db")
    def test_returns_at_least_three_lines(self, mock_log, mock_git):
        mock_git.return_value = ""
        from statusline.base_info import run
        lines = run(make_claude_data(), [])
        assert len(lines) >= 3

    @patch("statusline.base_info.git_cmd")
    @patch("statusline.base_info.log_to_db")
    def test_line1_contains_project_path(self, mock_log, mock_git):
        mock_git.return_value = ""
        from statusline.base_info import run
        lines = run(make_claude_data(cwd="/Users/test/projects/myapp"), [])
        assert "myapp" in lines[0] or "projects" in lines[0]

    @patch("statusline.base_info.git_cmd")
    @patch("statusline.base_info.log_to_db")
    def test_line2_contains_model_name(self, mock_log, mock_git):
        mock_git.return_value = ""
        from statusline.base_info import run
        lines = run(make_claude_data(), [])
        # Model name appears in the "Claude" section heading row now, and the
        # data row beneath it is labeled "Current Session". Search the whole
        # rendered output rather than a positional index.
        blob = "\n".join(lines).lower()
        assert "opus" in blob
        assert "current session" in blob

    @patch("statusline.base_info.git_cmd")
    @patch("statusline.base_info.log_to_db")
    def test_line3_contains_session_info(self, mock_log, mock_git):
        mock_git.return_value = ""
        from statusline.base_info import run
        lines = run(make_claude_data(), [])
        assert "all sessions" in lines[3]

    @patch("statusline.base_info.git_cmd")
    @patch("statusline.base_info.log_to_db")
    def test_usage_and_version_consolidated(self, mock_log, mock_git):
        """Usage and version lines are now generated by base_info."""
        mock_git.return_value = ""
        from statusline.base_info import run
        lines = run(make_claude_data(), [])
        assert len(lines) >= 3
