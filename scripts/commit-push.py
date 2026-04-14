#!/usr/bin/env python3
"""Stage, commit, push, optionally open a draft PR.

Usage:
  commit-push.py "commit message"
  commit-push.py --message-file msg.txt
  commit-push.py --message-file -          # read commit message from stdin
  commit-push.py "msg" --files path1 path2
  commit-push.py "msg" --pr "PR title" [--body "PR body" | --body-file body.md]
  commit-push.py "msg" --tracked-only

By default stages everything that isn't ignored (equivalent to `git add -A`),
matching the user's "commit all when told to" preference. This avoids the
common footgun where a new file is silently left behind by `git add -u` and
Claude has to diagnose a later "nothing to commit" error.

Flags:
  --files PATHS      stage only the given paths
  --tracked-only     stage only modifications to tracked files (old -u behavior)
  --message-file F   read commit message from file (use '-' for stdin). Mutually
                     exclusive with the positional message.
  --pr TITLE         also open a PR (implies push; draft by default)
  --body TEXT        PR body (mutually exclusive with --body-file)
  --body-file F      read PR body from file (use '-' for stdin)
  --no-draft         open the PR as ready-for-review instead of draft
  --ship             create PR, mark ready, squash-merge, then run
                     cc-merge-worktree to clean up the branch + worktree.
                     Use for solo work where the PR is record-keeping only.

Always appends Claude's Co-Authored-By trailer to the commit. Prints a one-line
`did:` summary of what was staged, committed, pushed, and (if applicable)
the PR URL — so Claude can verify without follow-up git/gh calls.
"""
import argparse
import subprocess
import sys


CO_AUTHOR = "Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
PR_TRAILER = "\n\nGenerated with [Claude Code](https://claude.com/claude-code)\n"


def run(cmd, check=True, capture=True):
    result = subprocess.run(cmd, capture_output=capture, text=True, timeout=120)
    if check and result.returncode != 0:
        print(f"FAIL: {' '.join(cmd)}", file=sys.stderr)
        print(result.stderr or result.stdout, file=sys.stderr)
        sys.exit(result.returncode)
    return result.stdout.strip(), result.returncode


def read_text(source: str) -> str:
    if source == "-":
        return sys.stdin.read()
    with open(source) as f:
        return f.read()


def resolve_message(args: argparse.Namespace) -> str:
    if args.message and args.message_file:
        print("FAIL: pass either a positional message or --message-file, not both", file=sys.stderr)
        sys.exit(2)
    if args.message_file:
        return read_text(args.message_file).rstrip()
    if args.message:
        return args.message.rstrip()
    print("FAIL: no commit message supplied (positional or --message-file)", file=sys.stderr)
    sys.exit(2)


def resolve_body(args: argparse.Namespace) -> str:
    if args.body and args.body_file:
        print("FAIL: pass either --body or --body-file, not both", file=sys.stderr)
        sys.exit(2)
    if args.body_file:
        return read_text(args.body_file).rstrip()
    return (args.body or "").rstrip()


def main():
    ap = argparse.ArgumentParser(description="Stage, commit, push, optionally open a draft PR.")
    ap.add_argument("message", nargs="?", help="Commit message (first line is subject). Omit to use --message-file.")
    ap.add_argument("--message-file", help="Read commit message from file ('-' for stdin).")
    ap.add_argument("--files", nargs="+", help="Specific files to stage (default: all changes)")
    ap.add_argument("--tracked-only", action="store_true",
                    help="Stage only tracked-file modifications (git add -u)")
    ap.add_argument("--pr", help="Open a PR with this title")
    ap.add_argument("--body", default="", help="PR body (mutually exclusive with --body-file)")
    ap.add_argument("--body-file", help="Read PR body from file ('-' for stdin)")
    ap.add_argument("--no-draft", action="store_true", help="Open PR as ready-for-review (default: draft)")
    ap.add_argument("--ship", action="store_true",
                    help="After PR creation: mark ready, squash-merge, run cc-merge-worktree cleanup.")
    args = ap.parse_args()

    message = resolve_message(args)

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

    # 3. Build full message
    msg = message + "\n\n" + CO_AUTHOR + "\n"
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
    _, up_rc = run(
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
        body = resolve_body(args)
        body_full = body + PR_TRAILER
        cmd = ["gh", "pr", "create", "--title", args.pr, "--body", body_full]
        if not args.no_draft:
            cmd.append("--draft")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print("FAIL: gh pr create", file=sys.stderr)
            print(result.stderr or result.stdout, file=sys.stderr)
            sys.exit(result.returncode)
        pr_url = result.stdout.strip()

    # Optional ship: ready + squash-merge + cleanup.
    shipped = False
    if args.ship:
        if not pr_url:
            print("FAIL: --ship requires --pr to create a PR first", file=sys.stderr)
            sys.exit(2)
        pr_number = pr_url.rstrip("/").rsplit("/", 1)[-1]
        run(["gh", "pr", "ready", pr_number], check=False)
        result = subprocess.run(
            ["gh", "pr", "merge", pr_number, "--squash"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print("FAIL: gh pr merge", file=sys.stderr)
            print(result.stderr or result.stdout, file=sys.stderr)
            sys.exit(result.returncode)
        # Hand off to cc-merge-worktree for the rest of the cleanup ritual.
        # Run via PATH so the latest installed version is used.
        result = subprocess.run(
            ["cc-merge-worktree", pr_number, "--branch", branch],
            text=True,
        )
        if result.returncode != 0:
            print("FAIL: cc-merge-worktree", file=sys.stderr)
            sys.exit(result.returncode)
        shipped = True

    # Summary — single `did:` line so Claude can pattern-match the result.
    head, _ = run(["git", "log", "--oneline", "-1"])
    summary = f"staged {len(staged_lines)} | {head} | pushed {branch}"
    if pr_url:
        summary += f" | pr {pr_url}"
    if shipped:
        summary += " | shipped (merged + cleaned up)"
    print(f"did: {summary}")


if __name__ == "__main__":
    main()
