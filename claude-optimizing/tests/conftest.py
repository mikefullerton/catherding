import os
import subprocess
import time
import uuid
from pathlib import Path
import pytest

MAIN_REPO = Path.home() / "projects/tests/catherdingtests"
GH_REPO = "agentic-cookbook/catherdingtests"


@pytest.fixture
def repo_worktree(tmp_path):
    """Isolated worktree of the real catherdingtests repo on a fresh branch."""
    branch = f"test-{uuid.uuid4().hex[:8]}"
    wt = tmp_path / "wt"

    subprocess.run(
        ["git", "-C", str(MAIN_REPO), "worktree", "add", str(wt), "-b", branch],
        check=True, capture_output=True,
    )
    for k, v in [("user.email", "test@test.com"), ("user.name", "Test User"),
                 ("commit.gpgsign", "false")]:
        subprocess.run(["git", "-C", str(wt), "config", k, v],
                       check=True, capture_output=True)

    yield wt, branch

    subprocess.run(["git", "-C", str(MAIN_REPO), "worktree", "remove", str(wt), "--force"],
                   capture_output=True)
    subprocess.run(["git", "-C", str(MAIN_REPO), "branch", "-D", branch],
                   capture_output=True)
    subprocess.run(["git", "-C", str(MAIN_REPO), "push", "origin", "--delete", branch],
                   capture_output=True)


@pytest.fixture
def pushed_worktree(repo_worktree):
    """repo_worktree with one commit already pushed to origin."""
    wt, branch = repo_worktree
    (wt / f"test-{branch[:8]}.txt").write_text("test\n")
    subprocess.run(["git", "-C", str(wt), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(wt), "commit", "-m", f"test: {branch}"],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(wt), "push", "-u", "origin", branch],
                   check=True, capture_output=True)
    return wt, branch


@pytest.fixture
def test_pr(pushed_worktree):
    """Real draft PR in catherdingtests. Closed after test."""
    wt, branch = pushed_worktree
    result = subprocess.run(
        ["gh", "pr", "create", "--repo", GH_REPO,
         "--title", f"test: {branch}",
         "--body", "Automated test PR — safe to close",
         "--draft", "--base", "main", "--head", branch],
        capture_output=True, text=True, check=True,
    )
    pr_url = result.stdout.strip()
    pr_number = int(pr_url.rstrip("/").rsplit("/", 1)[-1])

    time.sleep(2)  # GitHub API needs a moment to index new PRs
    yield pr_number, wt, branch

    subprocess.run(["gh", "pr", "close", str(pr_number), "--repo", GH_REPO],
                   capture_output=True)


@pytest.fixture
def local_git_repo(tmp_path):
    """Standalone git repo with one commit on main — no GitHub remote needed."""
    repo = tmp_path / "repo"
    repo.mkdir()
    remote = tmp_path / "remote.git"

    def git(*args):
        subprocess.run(["git", "-C", str(repo)] + list(args), check=True, capture_output=True)

    subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
    git("config", "user.email", "test@test.com")
    git("config", "user.name", "Test User")
    git("config", "commit.gpgsign", "false")
    (repo / "README.md").write_text("# test\n")
    git("add", ".")
    git("commit", "-m", "Initial commit")

    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    git("remote", "add", "origin", str(remote))
    git("push", "-u", "origin", "main")
    return repo


def run_cc(script, args=(), cwd=None):
    # Propagate cwd into PWD so scripts that read os.environ["PWD"] (e.g.
    # cc-merge-worktree's caller-inside-worktree detection) see the
    # invocation directory, mirroring how a real shell sets PWD on chdir.
    env = None
    if cwd is not None:
        env = {**os.environ, "PWD": str(cwd)}
    result = subprocess.run(
        [script] + list(args), capture_output=True, text=True, cwd=cwd, env=env,
    )
    return result.stdout, result.stderr, result.returncode
