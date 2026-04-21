"""Tests for the ExitWorktree PostToolUse hook.

The hook catches "exited the worktree without running cc-merge-worktree"
so the user gets immediate feedback on the next tool call, not just at
turn-end via the Stop hook. Two cases to cover:

1. Worktree still on disk with merged branch (existing behavior).
2. Worktree already removed but remote branch still on origin because
   the repo has `delete_branch_on_merge: false` (new coverage).
"""
import json
import subprocess
from pathlib import Path

from .conftest import MAIN_REPO, GH_REPO

HOOK_PATH = (
    Path(__file__).resolve().parent.parent / "scripts-hooks" / "cc-exit-worktree-hook.py"
)


def _invoke_hook(cwd, tool_name="ExitWorktree"):
    payload = json.dumps({"tool_name": tool_name, "cwd": str(cwd)})
    r = subprocess.run(
        [str(HOOK_PATH)], input=payload,
        capture_output=True, text=True, timeout=30,
    )
    return r.stdout, r.stderr, r.returncode


def test_hook_ignores_non_exit_worktree_events():
    """Unrelated tool events are no-ops."""
    out, err, rc = _invoke_hook(MAIN_REPO, tool_name="Bash")
    assert rc == 0
    assert not err.strip()


def test_hook_warns_on_squash_merged_orphan_after_action_remove(test_pr):
    """When a squash-merged PR leaves an orphan remote branch and the
    user's ExitWorktree removed the worktree+local branch, the hook
    must surface a non-blocking warning (exit 0) naming the orphan."""
    pr_number, wt, branch = test_pr

    subprocess.run(
        ["gh", "pr", "ready", str(pr_number), "--repo", GH_REPO],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["gh", "pr", "merge", str(pr_number), "--squash", "--repo", GH_REPO],
        check=True, capture_output=True,
    )

    # Simulate `delete_branch_on_merge: false`: re-push the head branch so
    # it lingers on origin after the merge.
    subprocess.run(
        ["git", "-C", str(wt), "push", "origin", branch],
        check=True, capture_output=True,
    )

    # Simulate `ExitWorktree action:remove`: remove worktree + local branch.
    subprocess.run(
        ["git", "-C", str(MAIN_REPO), "worktree", "remove", str(wt), "--force"],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(MAIN_REPO), "branch", "-D", branch],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(MAIN_REPO), "pull", "origin", "main"],
        check=True, capture_output=True,
    )

    out, err, rc = _invoke_hook(MAIN_REPO)
    assert rc == 0, f"hook should warn (rc=0) but got rc={rc} err={err!r}"
    assert branch in err, (
        f"orphan branch {branch!r} not mentioned in hook stderr: {err!r}"
    )
