"""Tests for the PreToolUse:Bash hook that blocks `git push --delete`
when the target branch is still the head of an open PR.

Pure-pattern tests (no gh) use arbitrary input. Live tests create a real
draft PR in `catherdingtests` via the `test_pr` fixture and invoke the hook
with cwd set to that repo so gh resolves to the correct remote.
"""
import json
import subprocess
from pathlib import Path

from .conftest import GH_REPO

HOOK_PATH = (
    Path(__file__).resolve().parent.parent / "scripts-hooks" / "cc-block-push-delete-hook.py"
)


def _invoke(command, tool_name="Bash", cwd=None):
    payload = json.dumps({"tool_name": tool_name, "tool_input": {"command": command}})
    r = subprocess.run(
        [str(HOOK_PATH)], input=payload,
        capture_output=True, text=True, timeout=30, cwd=cwd,
    )
    return r.stdout, r.stderr, r.returncode


# -------- Pure-pattern tests (no gh interaction) --------

def test_ignores_non_bash_tools():
    _, err, rc = _invoke("git push origin --delete whatever", tool_name="Read")
    assert rc == 0
    assert not err.strip()


def test_ignores_unrelated_bash_commands():
    _, err, rc = _invoke("ls -la")
    assert rc == 0
    assert not err.strip()


def test_ignores_non_delete_push():
    _, err, rc = _invoke("git push origin main")
    assert rc == 0
    assert not err.strip()


def test_ignores_malformed_input():
    r = subprocess.run(
        [str(HOOK_PATH)], input="not json",
        capture_output=True, text=True, timeout=10,
    )
    assert r.returncode == 0


def test_override_prefix_allows_without_gh_check():
    # Override must short-circuit before any gh call — this branch doesn't
    # exist, but the hook should still exit 0 because of the env-var prefix.
    _, err, rc = _invoke(
        "CC_ALLOW_BRANCH_DELETE=1 git push origin --delete bogus-branch-abc"
    )
    assert rc == 0, f"override should allow; got rc={rc} err={err!r}"


# -------- Live tests against a real open PR --------

def test_blocks_delete_of_branch_with_open_pr(test_pr):
    """Concrete safeguard: `git push origin --delete <head>` must be blocked
    while PR is open, else GitHub auto-closes the PR on delete."""
    pr_number, wt, branch = test_pr

    cmd = f"git push origin --delete {branch}"
    _, err, rc = _invoke(cmd, cwd=wt)
    assert rc == 2, f"expected block; got rc={rc} err={err!r}"
    assert branch in err
    assert f"#{pr_number}" in err
    assert "CC_ALLOW_BRANCH_DELETE=1" in err


def test_blocks_colon_syntax_delete(test_pr):
    pr_number, wt, branch = test_pr

    cmd = f"git push origin :{branch}"
    _, err, rc = _invoke(cmd, cwd=wt)
    assert rc == 2, f"expected block; got rc={rc} err={err!r}"
    assert branch in err
    assert f"#{pr_number}" in err


def test_override_allows_even_with_open_pr(test_pr):
    """User-asserted bypass: prefix must allow even when we'd otherwise block."""
    pr_number, wt, branch = test_pr

    cmd = f"CC_ALLOW_BRANCH_DELETE=1 git push origin --delete {branch}"
    _, err, rc = _invoke(cmd, cwd=wt)
    assert rc == 0, f"override should allow; got rc={rc} err={err!r}"


def test_allows_delete_of_branch_with_no_open_pr(pushed_worktree):
    """A pushed branch with no PR → no auto-close risk → allow."""
    wt, branch = pushed_worktree

    cmd = f"git push origin --delete {branch}"
    _, err, rc = _invoke(cmd, cwd=wt)
    assert rc == 0, f"no-PR delete should allow; got rc={rc} err={err!r}"
