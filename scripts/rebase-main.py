#!/usr/bin/env python3
"""Rebase the current branch onto origin/<default> and force-push with lease.

Usage:
  cc-rebase-main [--no-push]

Steps:
  1. Verify we're not on the default branch.
  2. `git fetch origin`
  3. `git rebase origin/<default>`
     - If conflicts: prints conflicted paths and exits non-zero. Caller resolves
       and runs `git rebase --continue` manually.
  4. `git push --force-with-lease` (skipped with --no-push).

Prints a `did:` summary line so Claude can verify without follow-up git calls.
"""
import argparse
import subprocess
import sys


def run(cmd, check=True, capture=True):
    result = subprocess.run(cmd, capture_output=capture, text=True, timeout=120)
    if check and result.returncode != 0:
        print(f"FAIL: {' '.join(cmd)}", file=sys.stderr)
        print(result.stderr or result.stdout, file=sys.stderr)
        sys.exit(result.returncode)
    return result.stdout.strip(), result.returncode


def default_branch() -> str:
    """Resolve origin/HEAD → main/master."""
    out, rc = run(["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"], check=False)
    if rc == 0 and out.startswith("origin/"):
        return out[len("origin/"):]
    # Fallback: assume main.
    return "main"


def main() -> int:
    ap = argparse.ArgumentParser(description="Rebase current branch onto origin/<default> and force-push.")
    ap.add_argument("--no-push", action="store_true", help="Rebase only, skip the force-push.")
    args = ap.parse_args()

    branch, _ = run(["git", "branch", "--show-current"])
    if not branch:
        print("FAIL: detached HEAD", file=sys.stderr)
        return 2
    default = default_branch()
    if branch == default:
        print(f"FAIL: already on {default}; nothing to rebase", file=sys.stderr)
        return 2

    run(["git", "fetch", "origin"])
    result = subprocess.run(["git", "rebase", f"origin/{default}"], capture_output=True, text=True)
    if result.returncode != 0:
        # Conflict path — surface files and stop.
        conflicted, _ = run(["git", "diff", "--name-only", "--diff-filter=U"], check=False)
        print("CONFLICT during rebase. Resolve then `git rebase --continue`.", file=sys.stderr)
        if conflicted:
            for f in conflicted.splitlines():
                print(f"  {f}", file=sys.stderr)
        print(result.stderr or result.stdout, file=sys.stderr)
        return result.returncode

    # Sync submodules — a rebase that pulls in submodule pointer bumps leaves
    # the working tree drifted otherwise, which then trips the next merge gate.
    has_subs, _ = run(["git", "config", "--file", ".gitmodules", "--get-regexp", r"^submodule\..*\.path$"], check=False)
    if has_subs:
        run(["git", "submodule", "update", "--init", "--recursive"])

    if not args.no_push:
        run(["git", "push", "--force-with-lease", "origin", branch])

    head, _ = run(["git", "log", "--oneline", "-1"])
    action = "rebased" if args.no_push else "rebased + pushed"
    print(f"did: {action} {branch} onto origin/{default} | {head}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
