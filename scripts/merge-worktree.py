#!/usr/bin/env python3
"""Merge a worktree PR and clean up.

Usage: merge-worktree.py <pr-number> [--branch <branch-name>]

Runs the full worktree-exit ritual in one call:
  1. Verify cwd is main project, on default branch
  2. Merge the PR via gh (squash)
  3. Pull main
  4. Gate: verify MERGED state + commit landed + main==origin/main + clean tracked
  5. Remove worktree directory
  6. Delete local branch
  7. Delete remote branch
  8. Final verification

Exits non-zero on any gate failure. Safe to re-run if a step failed midway.
"""
import argparse
import subprocess
import sys


def run(cmd, check=True, capture=True):
    """Run a command, return (stdout, returncode). Exit on non-zero if check=True."""
    result = subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        timeout=60,
    )
    if check and result.returncode != 0:
        print(f"FAIL: {' '.join(cmd)}", file=sys.stderr)
        print(result.stderr or result.stdout, file=sys.stderr)
        sys.exit(result.returncode)
    return result.stdout.strip(), result.returncode


def main():
    ap = argparse.ArgumentParser(description="Merge worktree PR and clean up.")
    ap.add_argument("pr", type=int, help="PR number")
    ap.add_argument("--branch", help="Worktree branch name (auto-detected if omitted)")
    args = ap.parse_args()

    # 1. Verify on default branch in main worktree
    branch, _ = run(["git", "branch", "--show-current"])
    if branch not in ("main", "master"):
        print(f"FAIL: current branch is '{branch}', must be main/master", file=sys.stderr)
        print("Run ExitWorktree with action: keep before calling this script.", file=sys.stderr)
        sys.exit(2)
    default_branch = branch

    # 2. Detect worktree branch if not provided
    wt_branch = args.branch
    if not wt_branch:
        wt_list, _ = run(["git", "worktree", "list", "--porcelain"])
        for line in wt_list.splitlines():
            if line.startswith("branch refs/heads/worktree-"):
                wt_branch = line.replace("branch refs/heads/", "")
                break
        if not wt_branch:
            print("FAIL: could not auto-detect worktree branch; pass --branch", file=sys.stderr)
            sys.exit(2)

    print(f"merging PR #{args.pr} (worktree branch: {wt_branch})")

    # 3. Merge PR (skip if already merged)
    pr_state, _ = run(["gh", "pr", "view", str(args.pr), "--json", "state", "-q", ".state"])
    if pr_state == "OPEN":
        run(["gh", "pr", "merge", str(args.pr), "--squash"])
        pr_state, _ = run(["gh", "pr", "view", str(args.pr), "--json", "state", "-q", ".state"])

    # 4. Pull default branch
    run(["git", "pull", "origin", default_branch])

    # 5. Gate checks
    if pr_state != "MERGED":
        print(f"FAIL: PR state is {pr_state}, expected MERGED", file=sys.stderr)
        sys.exit(3)

    local_head, _ = run(["git", "rev-parse", default_branch])
    remote_head, _ = run(["git", "rev-parse", f"origin/{default_branch}"])
    if local_head != remote_head:
        print(f"FAIL: {default_branch} != origin/{default_branch}", file=sys.stderr)
        sys.exit(3)

    _, unstaged = run(["git", "diff", "--quiet"], check=False)
    _, staged = run(["git", "diff", "--cached", "--quiet"], check=False)
    if unstaged != 0 or staged != 0:
        print("FAIL: working tree has uncommitted tracked changes", file=sys.stderr)
        sys.exit(3)

    print("gate passed")

    # 6. Remove worktree directory
    wt_list, _ = run(["git", "worktree", "list", "--porcelain"])
    wt_path = None
    cur_path = None
    for line in wt_list.splitlines():
        if line.startswith("worktree "):
            cur_path = line[9:]
        elif line == f"branch refs/heads/{wt_branch}":
            wt_path = cur_path
            break
    if wt_path:
        run(["git", "worktree", "remove", wt_path, "--force"])

    # 7. Delete local branch
    local_branches, _ = run(["git", "branch", "--list", wt_branch])
    if local_branches:
        run(["git", "branch", "-D", wt_branch])

    # 8. Delete remote branch (harmless if already gone)
    run(["git", "push", "origin", "--delete", wt_branch], check=False)

    # 9. Final verification
    still_there, _ = run(["git", "ls-remote", "--heads", "origin", wt_branch], check=False)
    if still_there:
        print(f"WARN: remote branch still exists: {still_there}", file=sys.stderr)

    head_msg, _ = run(["git", "log", "--oneline", "-1"])
    print(f"done: {head_msg}")


if __name__ == "__main__":
    main()
