import pytest
from unittest.mock import patch


def make_git_responses(overrides=None):
    """Return a dict of git command args -> response for mocking."""
    defaults = {
        ("rev-parse", "--git-dir"): ".git",
        ("symbolic-ref", "refs/remotes/origin/HEAD"): "refs/remotes/origin/main",
        ("branch", "-vv"): "  main abc1234 [origin/main] latest",
        ("branch", "--merged", "main"): "* main\n",
        ("worktree", "prune", "--dry-run"): "",
        ("branch", "-r"): "  origin/HEAD -> origin/main\n  origin/main\n",
        ("branch",): "* main\n",
        ("worktree", "list"): "/repo abc1234 [main]\n",
        ("rev-parse", "--show-toplevel"): "/repo",
    }
    if overrides:
        defaults.update(overrides)
    return defaults


def mock_side_effect(responses):
    def side_effect(*args):
        return responses.get(args, "")
    return side_effect


class TestRepoCleanupPassthrough:
    @patch("statusline.repo_cleanup.git_cmd")
    def test_no_git_repo_passes_through(self, mock_git):
        mock_git.return_value = ""
        from statusline.repo_cleanup import run
        lines = ["line1", "line2"]
        rows = []
        result = run({}, lines, rows)
        assert result == lines
        assert rows == []

    @patch("statusline.repo_cleanup.git_cmd")
    def test_no_issues_emits_no_row(self, mock_git):
        mock_git.side_effect = mock_side_effect(make_git_responses())
        from statusline.repo_cleanup import run
        lines = ["line1", "line2"]
        rows = []
        result = run({}, lines, rows)
        assert result == lines
        assert rows == []

    @patch("statusline.repo_cleanup.git_cmd")
    def test_line_zero_untouched_when_warnings_present(self, mock_git):
        """Warnings no longer splice into line 0 — they emit a standalone row."""
        mock_git.side_effect = mock_side_effect(make_git_responses({
            ("branch", "-vv"): "  stale abc [origin/stale: gone] old\n  main def [origin/main] ok",
        }))
        from statusline.repo_cleanup import run
        lines = ["path-line"]
        rows = []
        result = run({}, lines, rows)
        assert result[0] == "path-line"


class TestRepoCleanupWarnings:
    @patch("statusline.repo_cleanup.git_cmd")
    def test_stale_branches_detected(self, mock_git):
        mock_git.side_effect = mock_side_effect(make_git_responses({
            ("branch", "-vv"): "  stale abc [origin/stale: gone] old\n  main def [origin/main] ok",
        }))
        from statusline.repo_cleanup import run
        rows = []
        run({}, ["line1"], rows)
        assert len(rows) == 1
        assert rows[0].heading is True
        assert "1 stale" in rows[0].columns[0]

    @patch("statusline.repo_cleanup.git_cmd")
    def test_merged_branches_detected(self, mock_git):
        mock_git.side_effect = mock_side_effect(make_git_responses({
            ("branch", "--merged", "main"): "* main\n  feature-done\n",
        }))
        from statusline.repo_cleanup import run
        rows = []
        run({}, ["line1"], rows)
        assert len(rows) == 1
        assert "1 merged" in rows[0].columns[0]
