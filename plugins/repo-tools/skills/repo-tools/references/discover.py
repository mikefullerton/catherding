#!/usr/bin/env python3
"""Discover git repositories under a root directory.

Usage:
    python3 discover.py [--depth N] [ROOT]

Output (stdout): JSON array of {repo, path} objects.
Progress goes to stderr.
"""

import argparse
import json
import os
import subprocess
import sys


def log(msg):
    print(msg, file=sys.stderr)


def discover_repos(root, depth):
    r = subprocess.run(
        ["find", root, "-maxdepth", str(depth), "-name", ".git", "-type", "d"],
        capture_output=True, text=True,
    )
    raw = sorted(r.stdout.strip().splitlines()) if r.stdout.strip() else []
    repos = []
    for dot_git in raw:
        if "/worktrees/" in dot_git:
            continue
        repo = os.path.dirname(os.path.abspath(dot_git))
        name = os.path.basename(repo)
        if name.endswith("-test") or name.endswith("-tests"):
            continue
        if any(repo.startswith(os.path.join(existing, ".git")) for existing in repos):
            continue
        repos.append(repo)
    return repos


def main():
    parser = argparse.ArgumentParser(description="Discover git repos")
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--depth", type=int, default=3)
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    repos = discover_repos(root, args.depth)

    if not repos:
        log(f"No git repositories found within depth {args.depth} of {root}")

    result = [{"repo": os.path.basename(r), "path": r} for r in repos]
    json.dump(result, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
