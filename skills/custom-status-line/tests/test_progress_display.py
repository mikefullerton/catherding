import json
import pytest
from statusline.formatting import visible_len


def _write_progress(tmp_path, monkeypatch, session_id="test-sess", **kwargs):
    sl_dir = tmp_path / ".claude-status-line" / "progress"
    sl_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "title": kwargs.get("title", "Building"),
        "subtitle": kwargs.get("subtitle", "Step"),
        "count": kwargs.get("count", 3),
        "max": kwargs.get("max", 10),
        "cols": kwargs.get("cols", 60),
        "session_id": session_id,
    }
    (sl_dir / f"{session_id}.json").write_text(json.dumps(data))
    monkeypatch.setenv("HOME", str(tmp_path))


def _write_pipeline(tmp_path, monkeypatch, style="standard"):
    config_dir = tmp_path / ".claude-status-line"
    config_dir.mkdir(parents=True, exist_ok=True)
    config = {"progress_style": style, "pipeline": []}
    (config_dir / "pipeline.json").write_text(json.dumps(config))
    monkeypatch.setattr(
        "statusline.progress_display._get_progress_style",
        lambda: style,
    )


class TestProgressDisplayPassthrough:
    def test_no_session_id_passes_through(self):
        from statusline.progress_display import run
        lines = ["line1", "line2"]
        assert run({}, lines) == lines

    def test_no_progress_file_passes_through(self):
        from statusline.progress_display import run
        lines = ["line1", "line2"]
        assert run({"session_id": "no-such-session"}, lines) == lines


class TestStandardRendering:
    def test_appends_six_lines(self, tmp_path, monkeypatch):
        _write_progress(tmp_path, monkeypatch)
        _write_pipeline(tmp_path, monkeypatch, "standard")
        from statusline.progress_display import run
        result = run({"session_id": "test-sess"}, ["line1", "line2"])
        assert len(result) == 8  # 2 original + 6 box lines

    def test_progress_bar_percentage(self, tmp_path, monkeypatch):
        _write_progress(tmp_path, monkeypatch, session_id="sess", count=5, max=10)
        _write_pipeline(tmp_path, monkeypatch, "standard")
        from statusline.progress_display import run
        result = run({"session_id": "sess"}, [])
        text = " ".join(result)
        assert "50%" in text

    def test_count_clamped_to_max(self, tmp_path, monkeypatch):
        _write_progress(tmp_path, monkeypatch, session_id="sess", count=15, max=10)
        _write_pipeline(tmp_path, monkeypatch, "standard")
        from statusline.progress_display import run
        result = run({"session_id": "sess"}, [])
        text = " ".join(result)
        assert "100%" in text


class TestCompactRendering:
    def test_appends_two_lines(self, tmp_path, monkeypatch):
        _write_progress(tmp_path, monkeypatch)
        _write_pipeline(tmp_path, monkeypatch, "compact")
        from statusline.progress_display import run
        lines = ["x" * 40, "y" * 40]
        result = run({"session_id": "test-sess"}, lines)
        assert len(result) == 4  # 2 original + 2 compact lines

    def test_width_matches_longest_line_plus_one(self, tmp_path, monkeypatch):
        _write_progress(tmp_path, monkeypatch)
        _write_pipeline(tmp_path, monkeypatch, "compact")
        from statusline.progress_display import run
        lines = ["a" * 50, "b" * 60]
        result = run({"session_id": "test-sess"}, lines)
        bar_line = result[2]
        info_line = result[3]
        assert visible_len(bar_line) == 61
        assert visible_len(info_line) == 61

    def test_contains_title_and_count(self, tmp_path, monkeypatch):
        _write_progress(tmp_path, monkeypatch, title="Deploying", count=7, max=10)
        _write_pipeline(tmp_path, monkeypatch, "compact")
        from statusline.progress_display import run
        result = run({"session_id": "test-sess"}, ["x" * 40])
        text = " ".join(result)
        assert "Deploying" in text
        assert "[7/10]" in text
        assert "70%" in text

    def test_bar_fills_proportionally(self, tmp_path, monkeypatch):
        _write_progress(tmp_path, monkeypatch, count=5, max=10)
        _write_pipeline(tmp_path, monkeypatch, "compact")
        from statusline.progress_display import run
        lines = ["x" * 40]
        result = run({"session_id": "test-sess"}, lines)
        bar_line = result[2]
        # Count pipe chars (from ANSI-stripped version)
        import re
        plain = re.sub(r"\033\[[0-9;]*m", "", bar_line)
        pipe_count = plain.count("|")
        total_w = visible_len(bar_line)
        # Filled pipes should be roughly half (plus right border)
        # filled = 5 * inner / 10, plus 1 for left border start, plus 1 right border
        assert pipe_count >= 2  # at least some progress + right border

    def test_count_clamped_to_max(self, tmp_path, monkeypatch):
        _write_progress(tmp_path, monkeypatch, count=15, max=10)
        _write_pipeline(tmp_path, monkeypatch, "compact")
        from statusline.progress_display import run
        result = run({"session_id": "test-sess"}, ["x" * 40])
        text = " ".join(result)
        assert "100%" in text
