#!/usr/bin/env python3
"""Pipeline module: emit repo cleanup warnings as a heading row.

Produces a standalone warning row (e.g. "⚠ 2 merged, 1 remote-only") that
sits immediately after base_info's git rows. Emits nothing when the repo
is clean or not a git checkout.
"""
import re
import subprocess

from statusline.formatting import RED, RST, Row

WARN = RED


def git_cmd(*args: str) -> str:
    """Run a git command, return stdout or empty string on failure."""
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (subprocess.TimeoutExpired, OSError):
        return ""


def compute_warning_text():
    """Return the raw warning string (ANSI-colored), or "" when clean.

    Shared by base_info (which appends it as trailing text on the git
    detail row so it sits at the end of that line) and the legacy `run`
    entry point below.
    """
    if not git_cmd("rev-parse", "--git-dir"):
        return ""

    # Detect default branch
    default_branch = ""
    head_ref = git_cmd("symbolic-ref", "refs/remotes/origin/HEAD")
    if head_ref:
        default_branch = head_ref.replace("refs/remotes/origin/", "")
    if not default_branch:
        for candidate in ("main", "master"):
            if git_cmd("rev-parse", "--verify", f"refs/heads/{candidate}"):
                default_branch = candidate
                break
    if not default_branch:
        return ""

    items = []

    # Stale branches — remote tracking branch deleted
    branch_vv = git_cmd("branch", "-vv")
    if branch_vv:
        stale = sum(1 for line in branch_vv.splitlines() if ": gone]" in line)
        if stale > 0:
            items.append(f"{stale} stale")

    # Merged branches — fully merged into default, safe to delete
    merged_output = git_cmd("branch", "--merged", default_branch)
    if merged_output:
        merged = 0
        for line in merged_output.splitlines():
            name = line.lstrip("* ").strip()
            if name and name not in (default_branch, "main", "master"):
                merged += 1
        if merged > 0:
            items.append(f"{merged} merged")

    # Prunable worktrees
    prune_output = git_cmd("worktree", "prune", "--dry-run")
    if prune_output:
        prunable = len(prune_output.splitlines())
        if prunable > 0:
            items.append(f"{prunable} prunable wt")

    # Remote-only branches
    remote_branches = git_cmd("branch", "-r")
    local_branches = git_cmd("branch")
    if remote_branches and local_branches:
        remotes = set()
        for line in remote_branches.splitlines():
            name = line.strip()
            if "/HEAD" not in name:
                remotes.add(re.sub(r"^origin/", "", name))
        locals_ = set()
        for line in local_branches.splitlines():
            # git prefixes checked-out branches with '*' and branches checked
            # out in a linked worktree with '+'. Strip both so the local name
            # matches the remote counterpart.
            locals_.add(line.lstrip("*+ ").strip())
        remote_only = len(remotes - locals_)
        if remote_only > 0:
            items.append(f"{remote_only} remote-only")

    # Finished worktrees — branch merged but worktree still exists
    wt_list = git_cmd("worktree", "list")
    main_path = git_cmd("rev-parse", "--show-toplevel")
    if wt_list and main_path:
        finished = 0
        for line in wt_list.splitlines():
            if not line.strip():
                continue
            parts = line.split()
            wt_path = parts[0] if parts else ""
            branch_match = re.search(r"\[(.+)\]", line)
            wt_branch = branch_match.group(1) if branch_match else ""
            if wt_path == main_path or not wt_branch:
                continue
            check = subprocess.run(
                ["git", "merge-base", "--is-ancestor", wt_branch, default_branch],
                capture_output=True, timeout=5,
            )
            if check.returncode == 0:
                finished += 1
        if finished > 0:
            items.append(f"{finished} done wt")

    if not items:
        return ""

    status = ", ".join(items)
    return f"{WARN}\u26a0 {status}{RST}"


def run(claude_data: dict, lines: list, rows: list = None) -> list:
    """Pipeline entry point — legacy no-op.

    base_info now attaches the warning as trailing text on the git
    detail row, so this stage is effectively a no-op. Kept so pipeline
    configs that still list "repo-cleanup" don't fail to import.
    """
    return lines
