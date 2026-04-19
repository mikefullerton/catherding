import subprocess
from .conftest import run_cc, MAIN_REPO


def _remote_tracking_refs(cwd):
    """Local view of remote branches: `git for-each-ref refs/remotes/origin/` minus HEAD pointer."""
    out = subprocess.run(
        ["git", "-C", str(cwd), "for-each-ref",
         "--format=%(refname:short)", "refs/remotes/origin/"],
        check=True, capture_output=True, text=True,
    ).stdout
    return [l.strip() for l in out.splitlines()
            if l.strip() and not l.endswith("/HEAD")]


def test_merges_pr_and_cleans_local_and_remote(test_pr):
    """Happy path: draft PR -> ready -> squash-merged -> local branch gone,
    remote branch gone, AND no stale tracking ref left behind."""
    pr_number, wt, branch = test_pr
    out, err, rc = run_cc("cc-merge-worktree", [str(pr_number), "--branch", branch], cwd=MAIN_REPO)
    assert rc == 0, f"out={out!r} err={err!r}"
    assert "done:" in out

    local = subprocess.run(
        ["git", "-C", str(MAIN_REPO), "branch", "--list", branch],
        capture_output=True, text=True,
    ).stdout
    assert branch not in local, "local branch still present"

    remote_live = subprocess.run(
        ["git", "ls-remote", "--heads", "origin", branch],
        cwd=MAIN_REPO, capture_output=True, text=True,
    ).stdout
    assert not remote_live.strip(), "remote branch still present on origin"

    # The bug we're guarding against: tracking ref lingers locally even
    # though the remote branch is gone.
    assert f"origin/{branch}" not in _remote_tracking_refs(MAIN_REPO), \
        "stale refs/remotes/origin/<branch> tracking ref not pruned"


def test_caller_inside_worktree_resets_to_merge_base(test_pr):
    """When invoked from inside the worktree (Claude's normal case),
    the script must reset the worktree branch to the merge-base so that
    a subsequent ExitWorktree action:remove succeeds without
    discard_changes=true."""
    pr_number, wt, branch = test_pr
    out, err, rc = run_cc("cc-merge-worktree", [str(pr_number), "--branch", branch], cwd=wt)
    assert rc == 0, err
    assert "Worktree branch reset to branch-creation point" in out

    branch_head = subprocess.run(
        ["git", "-C", str(wt), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    main_parent = subprocess.run(
        ["git", "-C", str(MAIN_REPO), "rev-parse", "main^"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert branch_head == main_parent


def test_dirty_main_blocks_merge(test_pr):
    """Gate must refuse to proceed when main has uncommitted tracked
    changes that don't match origin (data-loss guard)."""
    pr_number, wt, branch = test_pr
    readme = MAIN_REPO / "README.md"
    original = readme.read_text()
    readme.write_text(original + "\nlocal-only mod that doesn't match origin\n")
    try:
        out, err, rc = run_cc("cc-merge-worktree", [str(pr_number), "--branch", branch], cwd=wt)
        assert rc != 0
        assert "uncommitted" in (out + err).lower()
    finally:
        readme.write_text(original)


def test_already_merged_pr_is_idempotent(test_pr):
    """Re-running on an already-MERGED PR cleans up local/remote state
    without re-attempting the merge."""
    pr_number, wt, branch = test_pr
    run_cc("cc-merge-worktree", [str(pr_number), "--branch", branch], cwd=wt)
    out, err, rc = run_cc("cc-merge-worktree", [str(pr_number), "--branch", branch], cwd=MAIN_REPO)
    # Either a clean noop (rc==0) or a controlled gate failure - but never
    # an exception or a re-merge attempt.
    assert "done:" in out or "MERGED" in (out + err)
