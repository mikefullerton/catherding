#!/usr/bin/env python3
"""Comprehensive PR review state: reviewers, approvals, inline comments, CI.

Usage:
  cc-pr-review <num> [--inline N]

Prints:
  - title / state / draft / mergeable
  - requested reviewers (still pending)
  - latest review per reviewer (APPROVED / CHANGES_REQUESTED / COMMENTED)
  - review comment count (unresolved inline) + latest N excerpts
  - CI rollup (per-check status)

Differs from cc-pr-status (which is the quick "is it green?" view) by
surfacing per-reviewer state and inline comment content. Use this when
preparing to address review feedback.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys


def gh_json(args: list[str]) -> object:
    proc = subprocess.run(["gh", *args], capture_output=True, text=True)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        print(f"cc-pr-review: gh {' '.join(args)} failed", file=sys.stderr)
        sys.exit(proc.returncode)
    return json.loads(proc.stdout) if proc.stdout.strip() else None


def short(text: str, limit: int = 120) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="cc-pr-review",
        description="Comprehensive PR review state (reviews, inline comments, CI).",
    )
    parser.add_argument("num", type=int, help="PR number")
    parser.add_argument("--inline", type=int, default=5, help="How many latest inline comments to print (default 5)")
    args = parser.parse_args()

    pr = gh_json([
        "pr", "view", str(args.num),
        "--json", "title,state,isDraft,mergeable,author,reviewRequests,latestReviews,reviews,statusCheckRollup,url",
    ])
    assert isinstance(pr, dict)

    print(f"#{args.num}  {pr['title']}")
    print(f"  {pr['url']}")
    print(
        f"  state={pr['state']}  draft={pr['isDraft']}  mergeable={pr['mergeable']}  "
        f"author={pr['author'].get('login', '?')}"
    )

    requested = pr.get("reviewRequests") or []
    if requested:
        names = ", ".join(r.get("login") or r.get("name") or "?" for r in requested)
        print(f"  requested: {names}")

    latest_by_user: dict[str, str] = {}
    for r in pr.get("latestReviews") or []:
        login = (r.get("author") or {}).get("login") or "?"
        latest_by_user[login] = r.get("state", "?")
    if latest_by_user:
        print("  latest reviews:")
        for user, state in latest_by_user.items():
            print(f"    {user}: {state}")

    checks = pr.get("statusCheckRollup") or []
    if checks:
        by_state: dict[str, int] = {}
        failing: list[str] = []
        for c in checks:
            state = c.get("conclusion") or c.get("status") or "?"
            by_state[state] = by_state.get(state, 0) + 1
            if state in ("FAILURE", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED"):
                failing.append(c.get("name") or c.get("context") or "?")
        rollup = ", ".join(f"{k}={v}" for k, v in sorted(by_state.items()))
        print(f"  checks: {rollup}")
        for name in failing:
            print(f"    FAIL: {name}")

    repo = gh_json(["repo", "view", "--json", "nameWithOwner"])
    assert isinstance(repo, dict)
    inline = gh_json(["api", f"repos/{repo['nameWithOwner']}/pulls/{args.num}/comments"])
    assert isinstance(inline, list)
    print(f"  inline comments: {len(inline)}")
    if inline and args.inline > 0:
        for c in sorted(inline, key=lambda x: x.get("updated_at", ""), reverse=True)[: args.inline]:
            user = (c.get("user") or {}).get("login") or "?"
            path = c.get("path") or "?"
            line = c.get("line") or c.get("original_line") or "?"
            body = short(c.get("body") or "")
            print(f"    {user} @ {path}:{line}  {body}")

    print(f"did: reviewed PR #{args.num}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
