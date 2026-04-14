#!/usr/bin/env python3
"""Report branch/worktree hygiene issues.

Usage: branch-hygiene.py [--cleanup]

Detects:
  - stale branches (remote tracking branch gone)
  - local branches already merged into default
  - remote-only branches (on origin but not local)
  - prunable worktrees

With --cleanup, performs safe deletions (merged branches, prunable worktrees).
Stale / remote-only are reported only.
"""
import argparse
import re
import subprocess
import sys


def run(cmd, check=False):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return r.stdout.strip(), r.returncode


def detect_default():
    ref, _ = run(["git", "symbolic-ref", "refs/remotes/origin/HEAD"])
    if ref:
        return ref.replace("refs/remotes/origin/", "")
    for c in ("main", "master"):
        _, rc = run(["git", "rev-parse", "--verify", f"refs/heads/{c}"])
        if rc == 0:
            return c
    return ""


def find_stale():
    out, _ = run(["git", "branch", "-vv"])
    return [l.split()[0].lstrip("+*").strip()
            for l in out.splitlines() if ": gone]" in l]


def find_merged(default):
    out, _ = run(["git", "branch", "--merged", default])
    # Get branches currently checked out in any worktree (have '+' or '*' prefix)
    checked_out = set()
    for l in out.splitlines():
        stripped = l.strip()
        if stripped.startswith(("* ", "+ ")):
            checked_out.add(stripped[2:].strip())
    names = []
    for l in out.splitlines():
        n = l.lstrip("+* ").strip()
        if n and n not in (default, "main", "master") and n not in checked_out:
            names.append(n)
    return names


def find_remote_only():
    remote, _ = run(["git", "branch", "-r"])
    local, _ = run(["git", "branch"])
    remotes = set()
    for l in remote.splitlines():
        n = l.strip()
        if "/HEAD" not in n:
            remotes.add(re.sub(r"^origin/", "", n))
    locals_ = set(l.lstrip("+* ").strip() for l in local.splitlines() if l.strip())
    return sorted(remotes - locals_)


def find_prunable():
    out, _ = run(["git", "worktree", "prune", "--dry-run"])
    return [l for l in out.splitlines() if l.strip()]


def main():
    ap = argparse.ArgumentParser(description="Branch/worktree hygiene.")
    ap.add_argument("--cleanup", action="store_true",
                    help="Delete merged branches and prune worktrees")
    args = ap.parse_args()

    _, rc = run(["git", "rev-parse", "--git-dir"])
    if rc != 0:
        print("not a git repo", file=sys.stderr)
        sys.exit(1)

    default = detect_default()
    if not default:
        print("could not detect default branch", file=sys.stderr)
        sys.exit(2)

    stale = find_stale()
    merged = find_merged(default)
    remote_only = find_remote_only()
    prunable = find_prunable()

    def _list(label, items):
        if items:
            print(f"{label} ({len(items)}):")
            for i in items:
                print(f"  {i}")

    _list("stale", stale)
    _list("merged (local)", merged)
    _list("remote-only", remote_only)
    _list("prunable worktrees", prunable)

    if not any([stale, merged, remote_only, prunable]):
        print("clean")
        return

    if args.cleanup:
        if merged:
            for b in merged:
                run(["git", "branch", "-d", b])
            print(f"deleted {len(merged)} merged branches")
        if prunable:
            run(["git", "worktree", "prune"])
            print("pruned worktrees")


if __name__ == "__main__":
    main()
