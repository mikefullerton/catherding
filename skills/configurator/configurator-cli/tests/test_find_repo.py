"""Tests for _find_repo — directory search up to 2 levels deep."""

from configurator.cli import _find_repo


class TestFindRepo:
    def test_direct_child(self, tmp_path):
        (tmp_path / "my-project").mkdir()
        result = _find_repo(str(tmp_path), "my-project")
        assert result == (tmp_path / "my-project").resolve()

    def test_nested_one_level(self, tmp_path):
        (tmp_path / "active" / "my-project").mkdir(parents=True)
        result = _find_repo(str(tmp_path), "my-project")
        assert result == (tmp_path / "active" / "my-project").resolve()

    def test_not_found(self, tmp_path):
        (tmp_path / "other-project").mkdir()
        assert _find_repo(str(tmp_path), "my-project") is None

    def test_prefers_direct_child(self, tmp_path):
        """Direct child should be found before nested match."""
        (tmp_path / "my-project").mkdir()
        (tmp_path / "sub" / "my-project").mkdir(parents=True)
        result = _find_repo(str(tmp_path), "my-project")
        assert result == (tmp_path / "my-project").resolve()

    def test_skips_hidden_dirs(self, tmp_path):
        (tmp_path / ".hidden" / "my-project").mkdir(parents=True)
        assert _find_repo(str(tmp_path), "my-project") is None

    def test_empty_dir(self, tmp_path):
        assert _find_repo(str(tmp_path), "anything") is None

    def test_file_not_dir(self, tmp_path):
        """A file with the repo name should not match."""
        (tmp_path / "my-project").write_text("not a directory")
        assert _find_repo(str(tmp_path), "my-project") is None
