#!/usr/bin/env python3
"""Stage, commit, push, optionally open a draft PR.

Usage:
  commit-push.py "commit message"
  commit-push.py "commit message" --files path1 path2
  commit-push.py "commit message" --pr "PR title" [--body "PR body"]
  commit-push.py "commit message" --tracked-only

By default stages everything that isn't ignored (equivalent to `git add -A`),
matching the user's "commit all when told to" preference. This avoids the
common footgun where a new file is silently left behind by `git add -u` and
Claude has to diagnose a later "nothing to commit" error.

Flags:
  --files PATHS     stage only the given paths
  --tracked-only    stage only modifications to tracked files (old -u behavior)
  --pr TITLE        also open a draft PR (implies push)
  --body TEXT       PR body (only used with --pr)

Always appends Claude's Co-Authored-By trailer to the commit. Prints a one-line
summary of what was staged so Claude can verify without a follow-up git status.
"""
import argparse
import subprocess
import sys


CO_AUTHOR = "Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"


def run(cmd, check=True, capture=True):
    result = subprocess.run(cmd, capture_output=capture, text=True, timeout=120)
    if check and result.returncode != 0:
        print(f"FAIL: {' '.join(cmd)}", file=sys.stderr)
        print(result.stderr or result.stdout, file=sys.stderr)
        sys.exit(result.returncode)
    return result.stdout.strip(), result.returncode


def main():
    ap = argparse.ArgumentParser(description="Commit, push, optionally open a PR.")
    ap.add_argument("message", help="Commit message (first line is subject)")
    ap.add_argument("--files", nargs="+", help="Specific files to stage (default: all changes)")
    ap.add_argument("--tracked-only", action="store_true",
                    help="Stage only tracked-file modifications (git add -u)")
    ap.add_argument("--pr", help="Open a draft PR with this title")
    ap.add_argument("--body", default="", help="PR body (only used with --pr)")
    args = ap.parse_args()

    # 1. Stage
    if args.files:
        run(["git", "add", "--"] + args.files)
    elif args.tracked_only:
        run(["git", "add", "-u"])
    else:
        run(["git", "add", "-A"])

    # 2. Check there's something to commit; print a summary either way so Claude
    #    doesn't need a follow-up `git status` to understand what happened.
    status, _ = run(["git", "status", "--porcelain=v1"])
    staged_lines = [ln for ln in status.splitlines() if ln and ln[0] not in " ?"]
    unstaged_lines = [ln for ln in status.splitlines() if ln and ln[0] == " " and ln[1] != " "]
    untracked_lines = [ln for ln in status.splitlines() if ln.startswith("??")]
    if not staged_lines:
        print("no staged changes; nothing to commit", file=sys.stderr)
        if unstaged_lines or untracked_lines:
            print(f"  unstaged: {len(unstaged_lines)}, untracked: {len(untracked_lines)} "
                  "(use --files or drop --tracked-only)", file=sys.stderr)
        sys.exit(1)

    print(f"staged: {len(staged_lines)} file(s)")

    # 3. Build full message
    msg = args.message.rstrip() + "\n\n" + CO_AUTHOR + "\n"
    result = subprocess.run(
        ["git", "commit", "-m", msg],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print("FAIL: git commit", file=sys.stderr)
        print(result.stderr or result.stdout, file=sys.stderr)
        sys.exit(result.returncode)

    # 4. Determine current branch for push
    branch, _ = run(["git", "branch", "--show-current"])
    if not branch:
        print("FAIL: detached HEAD", file=sys.stderr)
        sys.exit(2)

    # 5. Push (set upstream if needed)
    upstream, up_rc = run(
        ["git", "rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}"],
        check=False,
    )
    if up_rc != 0:
        run(["git", "push", "-u", "origin", branch])
    else:
        run(["git", "push", "origin", branch])

    # 6. Optional PR
    pr_url = None
    if args.pr:
        body = args.body or ""
        body_full = body.rstrip() + "\n\nGenerated with [Claude Code](https://claude.com/claude-code)\n"
        cmd = ["gh", "pr", "create", "--title", args.pr, "--body", body_full, "--draft"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print("FAIL: gh pr create", file=sys.stderr)
            print(result.stderr or result.stdout, file=sys.stderr)
            sys.exit(result.returncode)
        pr_url = result.stdout.strip()

    # Summary
    head, _ = run(["git", "log", "--oneline", "-1"])
    print(f"committed: {head}")
    print(f"pushed: {branch}")
    if pr_url:
        print(f"pr: {pr_url}")


if __name__ == "__main__":
    main()
