#!/usr/bin/env python3
"""PostToolUse hook for ExitWorktree — block if a merged worktree is stale.

Fires right after Claude runs ExitWorktree. Detects the "I exited the worktree
but forgot to run cc-merge-worktree" case: a non-default-branch worktree is
still on disk and its branch is already merged into origin/<default>. That's
exactly the ritual cc-merge-worktree automates.

Exit codes:
  0  — nothing stale, proceed
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

    if not stale:
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
        "ExitWorktree completed but a merged worktree is still on disk.",
        "You MUST run cc-merge-worktree to finish the ritual (see the",
        "'Exiting a Worktree' section of the global CLAUDE.md).",
        "",
    ]
    for path, branch in stale:
        pr = _pr_number(branch)
        suffix = f"  →  cc-merge-worktree {pr}" if pr else \
                 "  →  cc-merge-worktree <pr-number>"
        lines.append(f"  stale: {path}  (branch {branch}, merged into {default}){suffix}")

    print("\n".join(lines), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
