import json
import pytest
from statusline.formatting import visible_len


class TestProgressDisplayPassthrough:
    def test_no_session_id_passes_through(self):
        from statusline.progress_display import run
        lines = ["line1", "line2"]
        assert run({}, lines) == lines

    def test_no_progress_file_passes_through(self):
        from statusline.progress_display import run
        lines = ["line1", "line2"]
        assert run({"session_id": "no-such-session"}, lines) == lines


class TestProgressDisplayRendering:
    def test_appends_six_lines(self, tmp_path, monkeypatch):
        sl_dir = tmp_path / ".claude-status-line" / "progress"
        sl_dir.mkdir(parents=True)
        (sl_dir / "test-sess.json").write_text(json.dumps({
            "title": "Building",
            "subtitle": "Step",
            "count": 3,
            "max": 10,
            "cols": 60,
            "session_id": "test-sess",
        }))
        monkeypatch.setenv("HOME", str(tmp_path))

        from statusline.progress_display import run
        result = run({"session_id": "test-sess"}, ["line1", "line2"])
        assert len(result) == 8  # 2 original + 6 box lines

    def test_progress_bar_percentage(self, tmp_path, monkeypatch):
        sl_dir = tmp_path / ".claude-status-line" / "progress"
        sl_dir.mkdir(parents=True)
        (sl_dir / "sess.json").write_text(json.dumps({
            "title": "Test", "subtitle": "Working",
            "count": 5, "max": 10, "cols": 60, "session_id": "sess",
        }))
        monkeypatch.setenv("HOME", str(tmp_path))

        from statusline.progress_display import run
        result = run({"session_id": "sess"}, [])
        text = " ".join(result)
        assert "50%" in text

    def test_count_clamped_to_max(self, tmp_path, monkeypatch):
        sl_dir = tmp_path / ".claude-status-line" / "progress"
        sl_dir.mkdir(parents=True)
        (sl_dir / "sess.json").write_text(json.dumps({
            "title": "Test", "subtitle": "Done",
            "count": 15, "max": 10, "cols": 60, "session_id": "sess",
        }))
        monkeypatch.setenv("HOME", str(tmp_path))

        from statusline.progress_display import run
        result = run({"session_id": "sess"}, [])
        text = " ".join(result)
        assert "100%" in text
