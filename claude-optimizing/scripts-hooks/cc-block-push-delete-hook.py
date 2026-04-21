#!/usr/bin/env python3
"""PreToolUse:Bash hook — block `git push ... --delete <branch>` when the
branch is still the head of an open PR (deleting it would auto-close the PR).

Rationale: `cc-merge-worktree` has at least once resolved a PR number to the
wrong head branch via `gh pr view`, then executed `git push origin --delete
<wrong-branch>`. GitHub auto-closed the collateral PR as a side-effect. This
hook is the broadest backstop — it blocks the destructive `git push --delete`
call itself whenever the target branch is still open-PR'd.

Matches:
  * `git push [remote] --delete <branch>` (modern form)
  * `git push origin :<branch>`            (colon-syntax form)

Behavior:
  * Not Bash, or not a delete-push            → exit 0 (allow)
  * Command contains CC_ALLOW_BRANCH_DELETE=1 → exit 0 (override)
  * gh check says any open PR has this head   → exit 2 (block)
  * gh check fails (no gh, no repo, timeout)  → exit 2 (fail-closed)
  * gh check says no open PR uses this head   → exit 0 (allow)

Exits:
  0 — allow
  2 — block; stderr message is fed back to Claude
"""
from __future__ import annotations

import json
import re
import subprocess
import sys


# `git push` forms that delete a remote branch.
#
#   git push [flags] <remote> --delete <branch>
#   git push [flags] --delete <remote> <branch>
#   git push [flags] <remote> :<branch>
#
# We conservatively grab the last token after --delete, and for the colon
# form the token immediately after the colon. Remote name is variable
# (origin, upstream, fork, ...), so we don't pin it.
_DELETE_FLAG_RE = re.compile(
    r"\bgit\s+push\b[^|;&]*?\s--delete\s+(\S+)(?:\s+(\S+))?",
)
_COLON_RE = re.compile(
    r"\bgit\s+push\s+\S+\s+:(\S+)",
)
_OVERRIDE_RE = re.compile(r"\bCC_ALLOW_BRANCH_DELETE=1\b")


def _extract_branches(cmd: str) -> list[str]:
    """Return branch name(s) targeted by a delete-push, or [] if none."""
    branches: list[str] = []

    for m in _DELETE_FLAG_RE.finditer(cmd):
        # `--delete <a> [<b>]` — if two tokens follow, the second is the
        # branch (remote-first form); otherwise the only token is the branch.
        a, b = m.group(1), m.group(2)
        branches.append(b if b else a)

    for m in _COLON_RE.finditer(cmd):
        branches.append(m.group(1))

    # Strip any trailing shell noise (quotes, semicolons) from captured names.
    cleaned: list[str] = []
    for b in branches:
        b = b.strip().strip("'\"").rstrip(";&|")
        if b and not b.startswith("-"):
            cleaned.append(b)
    return cleaned


def _open_prs_for_branch(branch: str) -> tuple[list[int], str]:
    """Return (list of open PR numbers whose head is `branch`, error message).

    Non-empty error message means the gh query itself failed and we can't
    confirm safety — caller should fail-closed.
    """
    try:
        r = subprocess.run(
            ["gh", "pr", "list", "--head", branch, "--state", "open",
             "--limit", "10", "--json", "number"],
            capture_output=True, text=True, timeout=15,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return [], f"gh query failed: {e}"

    if r.returncode != 0:
        return [], (r.stderr.strip() or r.stdout.strip() or "gh non-zero exit")

    try:
        entries = json.loads(r.stdout or "[]")
    except json.JSONDecodeError as e:
        return [], f"gh returned non-JSON: {e}"

    return [e["number"] for e in entries if "number" in e], ""


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return 0

    if data.get("tool_name") != "Bash":
        return 0

    cmd = (data.get("tool_input") or {}).get("command", "")
    if not isinstance(cmd, str):
        return 0

    branches = _extract_branches(cmd)
    if not branches:
        return 0

    if _OVERRIDE_RE.search(cmd):
        return 0

    blocking: list[tuple[str, list[int]]] = []
    errors: list[tuple[str, str]] = []
    for branch in branches:
        prs, err = _open_prs_for_branch(branch)
        if err:
            errors.append((branch, err))
        elif prs:
            blocking.append((branch, prs))

    if not blocking and not errors:
        return 0

    msg_lines = ["Blocked: `git push --delete` would close an open PR."]
    for branch, prs in blocking:
        refs = ", ".join(f"#{n}" for n in prs)
        msg_lines.append(f"  branch {branch!r} is still the head of open PR(s): {refs}")
    for branch, err in errors:
        msg_lines.append(f"  branch {branch!r}: gh check failed — {err}")
    msg_lines.append("")
    msg_lines.append("  Merge the PR first (gh pr merge), or — if you truly want to")
    msg_lines.append("  delete the branch anyway — prefix the command with")
    msg_lines.append("  CC_ALLOW_BRANCH_DELETE=1.")
    print("\n".join(msg_lines), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
