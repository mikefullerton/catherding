"""Tests for the Stop hook (cc-repo-hygiene-hook.py).

Focus: the squash-merged orphan remote branch case. The sandbox repo
has `delete_branch_on_merge: true`, which auto-deletes the head branch
on merge. Real project repos (e.g. `catherding` itself) ship with
`delete_branch_on_merge: false`, so after a squash-merge the remote
branch lingers on origin. If the user's exit ritual is
`ExitWorktree action:remove` (skipping cc-merge-worktree), nothing
cleans the orphan up. The Stop hook must catch it.
"""
import json
import subprocess
from pathlib import Path

from .conftest import MAIN_REPO, GH_REPO

HOOK_PATH = (
    Path(__file__).resolve().parent.parent / "scripts-hooks" / "cc-repo-hygiene-hook.py"
)


def _invoke_hook(cwd, stop_hook_active=False):
    payload = json.dumps({"cwd": str(cwd), "stop_hook_active": stop_hook_active})
    r = subprocess.run(
        [str(HOOK_PATH)], input=payload,
        capture_output=True, text=True, timeout=30,
    )
    return r.stdout, r.stderr, r.returncode


def _decision(stdout):
    """Parse the hook's JSON decision output. None if hook did not block."""
    stdout = stdout.strip()
    if not stdout:
        return None
    return json.loads(stdout)


def test_hook_flags_squash_merged_orphan_remote_branch(test_pr):
    """Squash-merge a PR, then re-push the head branch to origin to
    simulate a `delete_branch_on_merge: false` repo where the orphan
    remote branch stays after merge. The Stop hook must detect it."""
    pr_number, wt, branch = test_pr

    subprocess.run(
        ["gh", "pr", "ready", str(pr_number), "--repo", GH_REPO],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["gh", "pr", "merge", str(pr_number), "--squash", "--repo", GH_REPO],
        check=True, capture_output=True,
    )

    # Sandbox auto-deletes the remote branch on merge; re-push to simulate
    # the delete_branch_on_merge=false case where origin keeps the branch.
    subprocess.run(
        ["git", "-C", str(wt), "push", "origin", branch],
        check=True, capture_output=True,
    )

    # Simulate `ExitWorktree action:remove`: remove the worktree directory
    # and the local branch. This leaves the remote branch as an orphan —
    # the exact state the Stop hook needs to catch.
    subprocess.run(
        ["git", "-C", str(MAIN_REPO), "worktree", "remove", str(wt), "--force"],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(MAIN_REPO), "branch", "-D", branch],
        check=True, capture_output=True,
    )

    # Sync MAIN_REPO main so the hook doesn't also block on "main behind
    # origin" — we want to isolate the orphan-detection signal.
    subprocess.run(
        ["git", "-C", str(MAIN_REPO), "pull", "origin", "main"],
        check=True, capture_output=True,
    )

    out, err, rc = _invoke_hook(MAIN_REPO)
    assert rc == 0, f"hook exited non-zero: err={err!r}"
    decision = _decision(out)
    assert decision is not None, (
        f"hook did not block but orphan remote branch {branch!r} exists; "
        f"stdout={out!r} stderr={err!r}"
    )
    assert decision.get("decision") == "block"
    reason = decision.get("reason", "")
    assert branch in reason, (
        f"orphan branch {branch!r} not named in hook reason: {reason!r}"
    )
