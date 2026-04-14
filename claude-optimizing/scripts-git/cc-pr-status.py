#!/usr/bin/env python3
"""Summarize a PR: state, checks, diff size, recent comments.

Usage: pr-status.py <pr-number> [--comments N]

Replaces 3-4 gh/git calls with one structured report.
"""
import argparse
import json
import subprocess
import sys


def gh_json(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        print(f"FAIL: {' '.join(cmd)}", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)
    return json.loads(result.stdout) if result.stdout.strip() else {}


def main():
    ap = argparse.ArgumentParser(description="PR status summary.")
    ap.add_argument("pr", type=int, help="PR number")
    ap.add_argument("--comments", type=int, default=3, help="Number of recent comments (default 3)")
    args = ap.parse_args()

    fields = [
        "title", "state", "isDraft", "mergeable", "mergeStateStatus",
        "headRefName", "baseRefName", "author", "url",
        "additions", "deletions", "changedFiles",
        "statusCheckRollup", "reviewDecision",
    ]
    data = gh_json(["gh", "pr", "view", str(args.pr), "--json", ",".join(fields)])

    print(f"#{args.pr}: {data['title']}")
    print(f"  {data['url']}")
    state = data["state"]
    if data.get("isDraft"):
        state += " (draft)"
    print(f"  state:    {state}   merge: {data.get('mergeStateStatus','?')}")
    print(f"  branch:   {data['headRefName']} -> {data['baseRefName']}")
    print(f"  author:   {data.get('author',{}).get('login','?')}")
    print(f"  diff:     +{data['additions']} -{data['deletions']}  ({data['changedFiles']} files)")

    if data.get("reviewDecision"):
        print(f"  review:   {data['reviewDecision']}")

    # Checks rollup
    checks = data.get("statusCheckRollup") or []
    if checks:
        counts = {}
        for c in checks:
            conclusion = c.get("conclusion") or c.get("state") or "PENDING"
            counts[conclusion] = counts.get(conclusion, 0) + 1
        check_bits = [f"{v} {k.lower()}" for k, v in sorted(counts.items())]
        print(f"  checks:   {', '.join(check_bits)}")

    # Recent comments
    if args.comments > 0:
        comments = gh_json([
            "gh", "pr", "view", str(args.pr),
            "--json", "comments",
            "-q", ".comments",
        ])
        if comments:
            print(f"  comments: {len(comments)} total")
            for c in comments[-args.comments:]:
                author = c.get("author", {}).get("login", "?")
                body = (c.get("body") or "").strip().replace("\n", " ")[:80]
                print(f"    {author}: {body}")


if __name__ == "__main__":
    main()
