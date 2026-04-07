#!/usr/bin/env python3
"""Discover git repositories under a root directory.

Does a quick local-only pre-check on each repo and only returns repos
that need processing (uncommitted changes, extra branches, or out of
sync with remote).

Usage:
    python3 discover.py [--depth N] [ROOT]

Output (stdout): JSON object with:
    all     — array of {repo, path} for every discovered repo
    process — array of {repo, path, reasons: [...]} for repos needing work
Progress goes to stderr.
"""

import argparse
import json
import os
import subprocess
import sys


def log(msg):
    print(msg, file=sys.stderr)


def git(repo, *args):
    r = subprocess.run(
        ["git", "-C", repo, *args],
        capture_output=True, text=True,
    )
    return r.stdout.strip(), r.returncode


def quick_check(repo):
    """Fast local-only check. Returns list of reasons to process, or empty if clean."""
    reasons = []

    # uncommitted changes
    status, _ = git(repo, "status", "--porcelain")
    if status:
        lines = [l for l in status.splitlines()
                 if not any(s in l for s in ("node_modules/", ".build/", "dist/", "__pycache__/", ".venv/", ".egg-info/"))]
        if lines:
            reasons.append(f"{len(lines)} uncommitted")

    # branches beyond default
    default = None
    ref, rc = git(repo, "symbolic-ref", "refs/remotes/origin/HEAD")
    if rc == 0 and ref:
        default = ref.split("/")[-1]
    else:
        for candidate in ("main", "master"):
            _, rc = git(repo, "rev-parse", "--verify", f"refs/heads/{candidate}")
            if rc == 0:
                default = candidate
                break
    if not default:
        default = "main"

    branches_out, _ = git(repo, "branch", "--format=%(refname:short)")
    branches = [b for b in branches_out.splitlines() if b and b != default]
    if branches:
        reasons.append(f"{len(branches)} branch(es)")

    # local vs remote out of sync (no fetch — uses last known state)
    cur, _ = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    if cur:
        upstream, rc = git(repo, "rev-parse", "--abbrev-ref", f"{cur}@{{upstream}}")
        if rc == 0 and upstream:
            ahead, _ = git(repo, "rev-list", "--count", f"{upstream}..{cur}")
            behind, _ = git(repo, "rev-list", "--count", f"{cur}..{upstream}")
            if ahead.isdigit() and int(ahead) > 0:
                reasons.append(f"{ahead} ahead")
            if behind.isdigit() and int(behind) > 0:
                reasons.append(f"{behind} behind")

    # worktrees
    wt_out, _ = git(repo, "worktree", "list", "--porcelain")
    wt_count = sum(1 for line in wt_out.splitlines() if line.startswith("worktree ")) - 1
    if wt_count > 0:
        reasons.append(f"{wt_count} worktree(s)")

    return reasons


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
        json.dump({"all": [], "process": []}, sys.stdout, indent=2)
        return

    all_repos = []
    to_process = []
    clean_count = 0

    for repo in repos:
        name = os.path.basename(repo)
        entry = {"repo": name, "path": repo}
        all_repos.append(entry)

        reasons = quick_check(repo)
        if reasons:
            to_process.append({"repo": name, "path": repo, "reasons": reasons})
            log(f"  {name}: {', '.join(reasons)}")
        else:
            clean_count += 1

    log(f"\n{len(all_repos)} repos found, {len(to_process)} need processing, {clean_count} clean")

    json.dump({"all": all_repos, "process": to_process}, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
