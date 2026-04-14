#!/usr/bin/env python3
"""Session-start repo audit: branch, status, worktrees, sync state.

Usage: repo-state.py

Outputs a tight summary of the repo's current state. Useful at session start to
answer "what's going on here" in one call instead of 5-6 git invocations.
"""
import subprocess
import sys


def run(cmd, check=False):
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.stdout.strip(), result.returncode


def main():
    # Verify we're in a git repo
    _, rc = run(["git", "rev-parse", "--git-dir"])
    if rc != 0:
        print("not a git repo", file=sys.stderr)
        sys.exit(1)

    branch, _ = run(["git", "branch", "--show-current"])
    head_msg, _ = run(["git", "log", "--oneline", "-1"])

    # Default branch detection
    default = ""
    head_ref, _ = run(["git", "symbolic-ref", "refs/remotes/origin/HEAD"])
    if head_ref:
        default = head_ref.replace("refs/remotes/origin/", "")
    if not default:
        for c in ("main", "master"):
            _, rc = run(["git", "rev-parse", "--verify", f"refs/heads/{c}"])
            if rc == 0:
                default = c
                break

    # Status: changed/untracked counts
    porcelain, _ = run(["git", "status", "--porcelain"])
    changed = added = untracked = 0
    for line in porcelain.splitlines():
        code = line[:2]
        if code == "??":
            untracked += 1
        elif "D" in code:
            added += 1  # counted as changed
            changed += 1
        else:
            changed += 1

    # Ahead/behind
    ahead = behind = 0
    if branch:
        upstream, rc = run(["git", "rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}"])
        if rc == 0:
            a, _ = run(["git", "rev-list", "--count", f"{upstream}..HEAD"])
            b, _ = run(["git", "rev-list", "--count", f"HEAD..{upstream}"])
            ahead = int(a or 0)
            behind = int(b or 0)

    # Worktrees
    wt_out, _ = run(["git", "worktree", "list", "--porcelain"])
    worktrees = []
    cur = {}
    for line in wt_out.splitlines() + [""]:
        if line.startswith("worktree "):
            if cur: worktrees.append(cur)
            cur = {"path": line[9:]}
        elif line.startswith("branch "):
            cur["branch"] = line[7:].replace("refs/heads/", "")
        elif line == "bare":
            cur["bare"] = True
        elif not line and cur:
            worktrees.append(cur)
            cur = {}
    main_wt = worktrees[0]["path"] if worktrees else ""
    extra_wts = [w for w in worktrees[1:] if not w.get("bare")]

    # Stale branches (gone upstream)
    vv, _ = run(["git", "branch", "-vv"])
    stale = sum(1 for ln in vv.splitlines() if ": gone]" in ln)

    # Drifted submodules (parent's recorded SHA != checked-out SHA)
    sub_status, _ = run(["git", "submodule", "status"])
    drifted_subs: list[str] = []
    for line in sub_status.splitlines():
        if line.startswith("+"):
            parts = line[1:].split()
            if len(parts) >= 2:
                drifted_subs.append(parts[1])

    # Default branch sync (only meaningful when on or near default)
    default_behind = 0
    if default:
        b, rc = run(["git", "rev-list", "--count", f"{default}..origin/{default}"])
        if rc == 0:
            try:
                default_behind = int(b or 0)
            except ValueError:
                default_behind = 0

    # Print
    print(f"repo:    {main_wt}")
    print(f"branch:  {branch} ({head_msg})")
    print(f"default: {default}")
    status_bits = []
    if changed: status_bits.append(f"{changed} changed")
    if untracked: status_bits.append(f"{untracked} untracked")
    if ahead: status_bits.append(f"{ahead} ahead")
    if behind: status_bits.append(f"{behind} behind")
    print(f"status:  {', '.join(status_bits) or 'clean'}")
    if extra_wts:
        print(f"worktrees: {len(extra_wts)}")
        for w in extra_wts:
            print(f"  {w.get('branch','?'):<40} {w['path']}")
    if stale:
        print(f"stale branches: {stale}")
    if drifted_subs:
        print(f"drifted submodules: {len(drifted_subs)}")
        for s in drifted_subs:
            print(f"  {s}")

    # Hints — name a cc-* command for each fixable issue.
    hints: list[str] = []
    for s in drifted_subs:
        hints.append(f"cc-bump-submodule {s}   # or `git submodule update --init {s}` to match recorded SHA")
    if default_behind > 0:
        hints.append(f"git pull origin {default}   # default branch is {default_behind} commit(s) behind")
    if stale > 0:
        hints.append("cc-branch-hygiene --cleanup   # delete branches whose upstream is gone")
    if behind > 0 and branch and branch != default:
        hints.append(f"cc-rebase-main   # current branch is {behind} commit(s) behind origin/{branch}")
    for h in hints:
        print(f"hint: {h}")


if __name__ == "__main__":
    main()
