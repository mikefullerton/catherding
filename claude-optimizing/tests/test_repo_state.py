import subprocess
from .conftest import run_cc


def test_clean_repo(repo_worktree):
    wt, _ = repo_worktree
    out, err, rc = run_cc("cc-repo-state", cwd=wt)
    assert rc == 0
    assert "status:  clean" in out


def test_modified_file(repo_worktree):
    wt, _ = repo_worktree
    (wt / "README.md").write_text("changed\n")
    out, err, rc = run_cc("cc-repo-state", cwd=wt)
    assert rc == 0
    assert "1 changed" in out


def test_untracked_file(repo_worktree):
    wt, _ = repo_worktree
    (wt / "new.txt").write_text("hello\n")
    out, err, rc = run_cc("cc-repo-state", cwd=wt)
    assert rc == 0
    assert "1 untracked" in out


def test_not_a_git_repo(tmp_path):
    out, err, rc = run_cc("cc-repo-state", cwd=tmp_path)
    assert rc != 0
    assert "not a git repo" in err


def test_shows_branch(repo_worktree):
    wt, branch = repo_worktree
    out, err, rc = run_cc("cc-repo-state", cwd=wt)
    assert rc == 0
    assert branch in out


def test_ahead_of_remote(pushed_worktree):
    wt, branch = pushed_worktree
    (wt / "extra.txt").write_text("extra\n")
    subprocess.run(["git", "-C", str(wt), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(wt), "commit", "-m", "extra"],
                   check=True, capture_output=True)
    out, err, rc = run_cc("cc-repo-state", cwd=wt)
    assert rc == 0
    assert "1 ahead" in out
