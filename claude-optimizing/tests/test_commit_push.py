import subprocess
from .conftest import run_cc


def test_commit_and_push(repo_worktree):
    wt, _ = repo_worktree
    (wt / "new.txt").write_text("hello\n")
    out, err, rc = run_cc("cc-commit-push", ["add new file"], cwd=wt)
    assert rc == 0, err
    assert "did:" in out
    assert "1" in out


def test_nothing_to_commit(repo_worktree):
    wt, _ = repo_worktree
    out, err, rc = run_cc("cc-commit-push", ["empty"], cwd=wt)
    assert rc != 0
    assert "nothing to commit" in err


def test_commit_specific_file(repo_worktree):
    wt, _ = repo_worktree
    (wt / "a.txt").write_text("a\n")
    (wt / "b.txt").write_text("b\n")
    out, err, rc = run_cc("cc-commit-push", ["only a", "--files", "a.txt"], cwd=wt)
    assert rc == 0, err
    assert "did:" in out
    status = subprocess.run(
        ["git", "-C", str(wt), "status", "--porcelain"],
        capture_output=True, text=True,
    ).stdout
    assert "b.txt" in status


def test_tracked_only_skips_untracked(repo_worktree):
    wt, _ = repo_worktree
    (wt / "README.md").write_text("modified\n")
    (wt / "untracked.txt").write_text("new\n")
    out, err, rc = run_cc("cc-commit-push", ["tracked only", "--tracked-only"], cwd=wt)
    assert rc == 0, err
    status = subprocess.run(
        ["git", "-C", str(wt), "status", "--porcelain"],
        capture_output=True, text=True,
    ).stdout
    assert "untracked.txt" in status
