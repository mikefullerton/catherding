#!/usr/bin/env python3
"""PostToolUse hook for ExitWorktree — block if worktree exit left dangling state.

Fires right after Claude runs ExitWorktree. Detects two flavors of the
"I exited the worktree but forgot to run cc-merge-worktree" bug:

  1. A non-default-branch worktree is still on disk and its branch is
     already merged into origin/<default> (action:keep without follow-up).
  2. A remote branch on origin corresponds to a merged PR but the local
     branch is gone (action:remove shortcut on a repo with
     `delete_branch_on_merge: false`).

Exit codes:
  0  — nothing dangling, proceed
  2  — blocking; prints a diagnostic to stderr that the harness surfaces
       back to Claude as a tool-use error

This is the flip-side of the Stop hygiene hook: Stop catches the problem at
turn-end; this one catches it the moment ExitWorktree returns, so Claude has
to resolve it before the next tool call rather than at turn-end.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys


def _git(args: list[str], cwd: str) -> tuple[str, int]:
    try:
        r = subprocess.run(
            ["git", "-C", cwd, *args],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ("", 1)
    return (r.stdout.strip(), r.returncode)


def _default_branch(cwd: str) -> str:
    out, rc = _git(["symbolic-ref", "--short", "refs/remotes/origin/HEAD"], cwd)
    if rc == 0 and out.startswith("origin/"):
        return out[len("origin/"):]
    # Fallbacks
    for candidate in ("main", "master"):
        _, rc = _git(["rev-parse", "--verify", candidate], cwd)
        if rc == 0:
            return candidate
    return "main"


def _parse_worktrees(cwd: str) -> list[tuple[str, str | None]]:
    out, rc = _git(["worktree", "list", "--porcelain"], cwd)
    if rc != 0:
        return []
    entries: list[tuple[str, str | None]] = []
    path: str | None = None
    branch: str | None = None
    for line in out.splitlines():
        if line.startswith("worktree "):
            if path is not None:
                entries.append((path, branch))
            path = line[len("worktree "):]
            branch = None
        elif line.startswith("branch refs/heads/"):
            branch = line[len("branch refs/heads/"):]
    if path is not None:
        entries.append((path, branch))
    return entries


def _merged_into(branch: str, target: str, cwd: str) -> bool:
    """True iff `branch` is reachable from origin/<target>."""
    # `git merge-base --is-ancestor branch origin/target` → exit 0 if merged
    _, rc = _git(["merge-base", "--is-ancestor", branch, f"origin/{target}"], cwd)
    return rc == 0


def _find_squash_merged_orphans(cwd: str, default_branch: str) -> list[str]:
    """Remote branches that correspond to a merged PR but still exist on origin.

    Mirrors the Stop hook's Check 5b. We fetch with --prune first so
    tombstone tracking refs (remote deleted, local still cached) don't
    surface as false orphans.
    """
    _git(["fetch", "origin", "--prune", "--quiet"], cwd)

    refs_out, _ = _git(
        ["for-each-ref", "--format=%(refname:short)", "refs/remotes/origin/"], cwd
    )
    local_out, _ = _git(
        ["for-each-ref", "--format=%(refname:short)", "refs/heads/"], cwd
    )
    local_branches = {b.strip() for b in local_out.splitlines() if b.strip()}

    remote_only: list[str] = []
    for ref in refs_out.splitlines():
        ref = ref.strip()
        if not ref.startswith("origin/"):
            continue
        name = ref[len("origin/"):]
        if not name or name in ("HEAD", default_branch):
            continue
        if name in local_branches:
            continue
        remote_only.append(name)

    if not remote_only:
        return []

    try:
        r = subprocess.run(
            ["gh", "pr", "list", "--state", "merged", "--limit", "100",
             "--json", "headRefName"],
            capture_output=True, text=True, timeout=15, cwd=cwd,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if r.returncode != 0 or not r.stdout.strip():
        return []
    try:
        merged_heads = {pr["headRefName"] for pr in json.loads(r.stdout)}
    except (json.JSONDecodeError, KeyError, TypeError):
        return []

    return [name for name in remote_only if name in merged_heads]


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return 0  # malformed input — don't block

    if data.get("tool_name") != "ExitWorktree":
        return 0

    cwd = data.get("cwd") or os.getcwd()
    if not cwd:
        return 0

    # Only enforce under ~/projects/ — matches the rest of the hygiene rules.
    if "/projects/" not in cwd:
        return 0

    # Be quiet when the action was "remove" and succeeded: cc-merge-worktree
    # is a no-op because there's nothing left to clean up.
    # (We still scan in case there's ANOTHER stale worktree.)

    default = _default_branch(cwd)
    worktrees = _parse_worktrees(cwd)

    stale: list[tuple[str, str]] = []
    for path, branch in worktrees:
        if not branch or branch in (default, "main", "master"):
            continue
        if _merged_into(branch, default, cwd):
            stale.append((path, branch))

    orphans = _find_squash_merged_orphans(cwd, default)

    if not stale and not orphans:
        return 0

    # Try to suggest concrete PR numbers so Claude has a one-call fix.
    def _pr_number(branch: str) -> str:
        try:
            r = subprocess.run(
                ["gh", "pr", "list", "--head", branch, "--state", "merged",
                 "--json", "number", "-q", ".[0].number"],
                capture_output=True, text=True, timeout=8, cwd=cwd,
            )
            return r.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return ""

    lines = [
        "ExitWorktree completed but the exit ritual left dangling state.",
        "You MUST run cc-merge-worktree to finish the ritual (see the",
        "'Exiting a Worktree' section of the global CLAUDE.md).",
        "",
    ]
    # Always emit --branch <name> in the suggested command. When multiple
    # worktrees coexist (e.g. concurrent sessions), `cc-merge-worktree <pr>`
    # alone would rely on cc-merge-worktree to resolve headRefName — which
    # it now does, but passing --branch makes the caller's intent explicit
    # and exercises the mismatch gate as a safety net.
    for path, branch in stale:
        pr = _pr_number(branch)
        suffix = f"  →  cc-merge-worktree {pr} --branch {branch}" if pr else \
                 f"  →  cc-merge-worktree <pr-number> --branch {branch}"
        lines.append(f"  stale: {path}  (branch {branch}, merged into {default}){suffix}")
    for branch in orphans:
        pr = _pr_number(branch)
        suffix = f"  →  cc-merge-worktree {pr} --branch {branch}" if pr else \
                 f"  →  git push origin --delete {branch}"
        lines.append(
            f"  orphan: origin/{branch}  (PR merged, remote branch not deleted){suffix}"
        )

    print("\n".join(lines), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
