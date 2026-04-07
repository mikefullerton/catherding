import json
import pytest


class TestWriteProgress:
    def test_writes_progress_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        from statusline.update_progress import write_progress
        write_progress("sess-1", "Building", "Step", 3, 10, 80)

        pfile = tmp_path / ".claude-status-line" / "progress" / "sess-1.json"
        assert pfile.exists()
        data = json.loads(pfile.read_text())
        assert data["title"] == "Building"
        assert data["count"] == 3
        assert data["max"] == 10


class TestClearProgress:
    def test_clear_removes_file(self, tmp_path, monkeypatch):
        progress_dir = tmp_path / ".claude-status-line" / "progress"
        progress_dir.mkdir(parents=True)
        pfile = progress_dir / "sess-1.json"
        pfile.write_text("{}")
        monkeypatch.setenv("HOME", str(tmp_path))

        from statusline.update_progress import clear_progress
        clear_progress("sess-1")
        assert not pfile.exists()

    def test_clear_missing_file_is_ok(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        from statusline.update_progress import clear_progress
        clear_progress("no-such-session")  # should not raise
