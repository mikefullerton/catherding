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


class TestComputeWarningRow:
    @patch("statusline.repo_cleanup.git_cmd")
    def test_no_git_repo_returns_none(self, mock_git):
        mock_git.return_value = ""
        from statusline.repo_cleanup import compute_warning_row
        assert compute_warning_row() is None

    @patch("statusline.repo_cleanup.git_cmd")
    def test_no_issues_returns_none(self, mock_git):
        mock_git.side_effect = mock_side_effect(make_git_responses())
        from statusline.repo_cleanup import compute_warning_row
        assert compute_warning_row() is None

    @patch("statusline.repo_cleanup.git_cmd")
    def test_stale_branches_detected(self, mock_git):
        mock_git.side_effect = mock_side_effect(make_git_responses({
            ("branch", "-vv"): "  stale abc [origin/stale: gone] old\n  main def [origin/main] ok",
        }))
        from statusline.repo_cleanup import compute_warning_row
        row = compute_warning_row()
        assert row is not None
        assert row.heading is True
        assert "1 stale" in row.columns[0]

    @patch("statusline.repo_cleanup.git_cmd")
    def test_merged_branches_detected(self, mock_git):
        mock_git.side_effect = mock_side_effect(make_git_responses({
            ("branch", "--merged", "main"): "* main\n  feature-done\n",
        }))
        from statusline.repo_cleanup import compute_warning_row
        row = compute_warning_row()
        assert row is not None
        assert "1 merged" in row.columns[0]


class TestRunLegacyPipeline:
    @patch("statusline.repo_cleanup.git_cmd")
    def test_run_without_rows_returns_lines(self, mock_git):
        mock_git.return_value = ""
        from statusline.repo_cleanup import run
        lines = ["line1"]
        assert run({}, lines) == lines

    @patch("statusline.repo_cleanup.git_cmd")
    def test_run_appends_warning_when_invoked_standalone(self, mock_git):
        mock_git.side_effect = mock_side_effect(make_git_responses({
            ("branch", "-vv"): "  stale abc [origin/stale: gone] old\n  main def [origin/main] ok",
        }))
        from statusline.repo_cleanup import run
        rows = []
        run({}, ["line1"], rows)
        assert len(rows) == 1
        assert "1 stale" in rows[0].columns[0]

    @patch("statusline.repo_cleanup.git_cmd")
    def test_run_skips_warning_when_base_info_already_emitted(self, mock_git):
        """Prevent double-emission when base_info and repo_cleanup both run."""
        mock_git.side_effect = mock_side_effect(make_git_responses({
            ("branch", "-vv"): "  stale abc [origin/stale: gone] old\n  main def [origin/main] ok",
        }))
        from statusline.repo_cleanup import run
        from statusline.formatting import Row
        rows = [Row("\u26a0 pre-existing", heading=True)]
        run({}, ["line1"], rows)
        # No duplicate appended
        assert len(rows) == 1
