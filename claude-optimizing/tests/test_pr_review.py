from .conftest import run_cc


def test_basic_output(test_pr):
    pr_number, wt, branch = test_pr
    out, err, rc = run_cc("cc-pr-review", [str(pr_number)], cwd=wt)
    assert rc == 0, err
    assert f"#{pr_number}" in out
    assert branch in out


def test_shows_draft_state(test_pr):
    pr_number, wt, _ = test_pr
    out, err, rc = run_cc("cc-pr-review", [str(pr_number)], cwd=wt)
    assert rc == 0, err
    assert "draft=True" in out


def test_bad_pr_number(repo_worktree):
    wt, _ = repo_worktree
    out, err, rc = run_cc("cc-pr-review", ["99999"], cwd=wt)
    assert rc != 0
