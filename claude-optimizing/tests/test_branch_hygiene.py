import subprocess
from .conftest import run_cc


def test_no_problems(local_git_repo):
    out, err, rc = run_cc("cc-branch-hygiene", cwd=local_git_repo)
    assert rc == 0
    assert "clean" in out


def test_reports_merged_branch(local_git_repo):
    r = local_git_repo

    subprocess.run(["git", "-C", str(r), "checkout", "-b", "feature-x"],
                   check=True, capture_output=True)
    (r / "f.txt").write_text("x\n")
    subprocess.run(["git", "-C", str(r), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(r), "commit", "-m", "feature x"],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(r), "checkout", "main"],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(r), "merge", "--no-ff", "feature-x"],
                   check=True, capture_output=True)

    out, err, rc = run_cc("cc-branch-hygiene", cwd=r)
    assert rc == 0
    assert "feature-x" in out
    assert "merged" in out


def test_cleanup_deletes_merged_branch(local_git_repo):
    r = local_git_repo

    subprocess.run(["git", "-C", str(r), "checkout", "-b", "delete-me"],
                   check=True, capture_output=True)
    (r / "d.txt").write_text("d\n")
    subprocess.run(["git", "-C", str(r), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(r), "commit", "-m", "to delete"],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(r), "checkout", "main"],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(r), "merge", "--no-ff", "delete-me"],
                   check=True, capture_output=True)

    out, err, rc = run_cc("cc-branch-hygiene", ["--cleanup"], cwd=r)
    assert rc == 0
    assert "deleted" in out

    branches = subprocess.run(
        ["git", "-C", str(r), "branch"], capture_output=True, text=True,
    ).stdout
    assert "delete-me" not in branches


def test_not_a_git_repo(tmp_path):
    out, err, rc = run_cc("cc-branch-hygiene", cwd=tmp_path)
    assert rc != 0
    assert "not a git repo" in err


def _stale_tracking_ref(repo):
    """Set up a tombstone: push a branch, fetch it, then delete it from
    the remote without pruning so the local refs/remotes/origin/<branch>
    lingers as a stale tracking ref."""
    git = lambda *a: subprocess.run(["git", "-C", str(repo), *a],
                                    check=True, capture_output=True)
    git("checkout", "-b", "feature-tomb")
    (repo / "tomb.txt").write_text("x\n")
    git("add", ".")
    git("commit", "-m", "tomb")
    git("push", "-u", "origin", "feature-tomb")
    git("checkout", "main")
    git("branch", "-D", "feature-tomb")
    # Delete the remote ref directly, bypassing the push --delete
    # auto-prune side effect, so the local tracking ref remains.
    remote_url, _ = subprocess.run(
        ["git", "-C", str(repo), "remote", "get-url", "origin"],
        check=True, capture_output=True, text=True,
    ).stdout, None
    subprocess.run(
        ["git", "-C", remote_url.strip(), "branch", "-D", "feature-tomb"],
        check=True, capture_output=True,
    )


def test_reports_tombstone_tracking_refs(local_git_repo):
    _stale_tracking_ref(local_git_repo)

    out, err, rc = run_cc("cc-branch-hygiene", cwd=local_git_repo)
    assert rc == 0
    assert "tombstone tracking refs" in out
    assert "feature-tomb" in out


def test_cleanup_prunes_tombstone_tracking_refs(local_git_repo):
    _stale_tracking_ref(local_git_repo)

    out, err, rc = run_cc("cc-branch-hygiene", ["--cleanup"], cwd=local_git_repo)
    assert rc == 0
    assert "pruned 1 tombstone tracking refs" in out

    refs = subprocess.run(
        ["git", "-C", str(local_git_repo), "for-each-ref",
         "--format=%(refname:short)", "refs/remotes/origin/"],
        capture_output=True, text=True, check=True,
    ).stdout
    assert "origin/feature-tomb" not in refs
