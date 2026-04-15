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


class TestComputeWarningText:
    @patch("statusline.repo_cleanup.git_cmd")
    def test_no_git_repo_returns_empty(self, mock_git):
        mock_git.return_value = ""
        from statusline.repo_cleanup import compute_warning_text
        assert compute_warning_text() == ""

    @patch("statusline.repo_cleanup.git_cmd")
    def test_no_issues_returns_empty(self, mock_git):
        mock_git.side_effect = mock_side_effect(make_git_responses())
        from statusline.repo_cleanup import compute_warning_text
        assert compute_warning_text() == ""

    @patch("statusline.repo_cleanup.git_cmd")
    def test_stale_branches_detected(self, mock_git):
        mock_git.side_effect = mock_side_effect(make_git_responses({
            ("branch", "-vv"): "  stale abc [origin/stale: gone] old\n  main def [origin/main] ok",
        }))
        from statusline.repo_cleanup import compute_warning_text
        text = compute_warning_text()
        assert "1 stale" in text
        assert "\u26a0" in text

    @patch("statusline.repo_cleanup.git_cmd")
    def test_merged_branches_detected(self, mock_git):
        mock_git.side_effect = mock_side_effect(make_git_responses({
            ("branch", "--merged", "main"): "* main\n  feature-done\n",
        }))
        from statusline.repo_cleanup import compute_warning_text
        assert "1 merged" in compute_warning_text()


class TestRunLegacy:
    def test_run_returns_lines_unchanged(self):
        from statusline.repo_cleanup import run
        assert run({}, ["a", "b"]) == ["a", "b"]
        assert run({}, ["a", "b"], []) == ["a", "b"]
