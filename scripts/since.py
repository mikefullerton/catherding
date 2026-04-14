#!/usr/bin/env python3
"""List merged PRs and commits since a given ref (tag / branch / SHA).

Usage:
  cc-since <ref> [--head REF] [--prs-only] [--commits-only]

Compares `<ref>..HEAD` (or `<ref>..<head>` with --head) and extracts
PR numbers from commit subject lines — handles both squash-merge
("Title (#NNN)") and merge commits ("Merge pull request #NNN").

Output:
  - merged PRs: number, title, author, merged-at
  - other commits: short SHA + subject (excluded when --prs-only)

Good for "what shipped since v1.2?" or "what went into main since this
branch forked off?". Exit non-zero if the ref is unknown.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys


PR_PATTERN = re.compile(r"(?:#|pull request #)(\d+)")


def run(cmd: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def git_log(base: str, head: str) -> list[tuple[str, str]]:
    rc, out, err = run(["git", "log", f"{base}..{head}", "--pretty=%h%x09%s"])
    if rc != 0:
        sys.stderr.write(err)
        print(f"cc-since: git log {base}..{head} failed", file=sys.stderr)
        sys.exit(rc)
    rows: list[tuple[str, str]] = []
    for line in out.splitlines():
        if "\t" in line:
            sha, subject = line.split("\t", 1)
            rows.append((sha, subject))
    return rows


def pr_numbers(commits: list[tuple[str, str]]) -> list[int]:
    seen: dict[int, None] = {}
    for _, subject in commits:
        for m in PR_PATTERN.finditer(subject):
            seen[int(m.group(1))] = None
    return list(seen.keys())


def pr_info(num: int) -> dict | None:
    rc, out, _ = run(["gh", "pr", "view", str(num), "--json", "number,title,author,mergedAt,state"])
    if rc != 0:
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="cc-since",
        description="List PRs and commits merged since a given ref.",
    )
    parser.add_argument("ref", help="Base ref (tag, branch, SHA, etc.)")
    parser.add_argument("--head", default="HEAD", help="Head ref (default: HEAD)")
    parser.add_argument("--prs-only", action="store_true", help="Only print PRs")
    parser.add_argument("--commits-only", action="store_true", help="Only print raw commits")
    args = parser.parse_args()

    rc, _, err = run(["git", "rev-parse", "--verify", args.ref])
    if rc != 0:
        sys.stderr.write(err)
        print(f"cc-since: unknown ref {args.ref!r}", file=sys.stderr)
        return 1

    commits = git_log(args.ref, args.head)
    if not commits:
        print(f"cc-since: no commits in {args.ref}..{args.head}")
        return 0

    numbers = pr_numbers(commits)

    if not args.commits_only:
        print(f"PRs merged in {args.ref}..{args.head}: {len(numbers)}")
        for n in numbers:
            info = pr_info(n)
            if info:
                author = (info.get("author") or {}).get("login") or "?"
                merged = info.get("mergedAt") or "?"
                print(f"  #{n:<5}  {info.get('state', '?'):<7}  {author:<20}  {merged[:10]}  {info.get('title', '')}")
            else:
                print(f"  #{n:<5}  (fetch failed)")

    if not args.prs_only:
        print(f"Commits in {args.ref}..{args.head}: {len(commits)}")
        for sha, subject in commits:
            print(f"  {sha}  {subject}")

    print(f"did: {len(numbers)} PR(s), {len(commits)} commit(s) since {args.ref}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
