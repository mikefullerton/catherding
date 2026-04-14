#!/usr/bin/env python3
"""Find projects under ~/projects by criteria.

Usage: project-index.py [--filter <type>] [--root <path>]

Filters:
  graphify   — projects with graphify-out/ directory
  git        — projects that are git repos
  worktrees  — projects with active worktrees
  stale      — projects with uncommitted changes or stale branches
  all        — all project-like directories (default)

Output: one line per project, columns: name, type flags, extra info.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

HOME = Path.home()


def is_git(path: Path) -> bool:
    return (path / ".git").is_dir() or (path / ".git").is_file()


def has_graphify(path: Path) -> bool:
    return (path / "graphify-out").is_dir()


def git_cmd(path: Path, *args) -> str:
    r = subprocess.run(
        ["git", "-C", str(path), *args],
        capture_output=True, text=True, timeout=10,
    )
    return r.stdout.strip() if r.returncode == 0 else ""


def project_info(path: Path) -> dict:
    info = {
        "name": str(path.relative_to(HOME / "projects")),
        "path": path,
        "git": is_git(path),
        "graphify": has_graphify(path),
        "uncommitted": False,
        "worktrees": 0,
        "stale_branches": 0,
    }
    if info["git"]:
        porcelain = git_cmd(path, "status", "--porcelain")
        info["uncommitted"] = bool(porcelain.strip())

        wt = git_cmd(path, "worktree", "list", "--porcelain")
        info["worktrees"] = sum(1 for l in wt.splitlines() if l.startswith("worktree "))
        # Subtract the main worktree
        info["worktrees"] = max(0, info["worktrees"] - 1)

        vv = git_cmd(path, "branch", "-vv")
        info["stale_branches"] = sum(1 for l in vv.splitlines() if ": gone]" in l)
    return info


def scan(root: Path, max_depth: int = 3):
    """Yield project directories."""
    for top in sorted(root.iterdir()):
        if not top.is_dir() or top.name.startswith("."):
            continue
        # Depth 1 dirs (e.g., active/, external/)
        for sub in sorted(top.iterdir()):
            if not sub.is_dir() or sub.name.startswith("."):
                continue
            yield sub


def main():
    ap = argparse.ArgumentParser(description="Project index.")
    ap.add_argument("--filter", choices=["graphify", "git", "worktrees", "stale", "all"], default="all")
    ap.add_argument("--root", default=str(HOME / "projects"), help="Projects root (default: ~/projects)")
    args = ap.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        print(f"no such dir: {root}", file=sys.stderr)
        sys.exit(1)

    rows = []
    for path in scan(root):
        info = project_info(path)
        if args.filter == "graphify" and not info["graphify"]:
            continue
        if args.filter == "git" and not info["git"]:
            continue
        if args.filter == "worktrees" and info["worktrees"] == 0:
            continue
        if args.filter == "stale" and not (info["uncommitted"] or info["stale_branches"]):
            continue
        rows.append(info)

    if not rows:
        print("(none)")
        return

    name_w = max(len(r["name"]) for r in rows)
    for r in rows:
        flags = []
        if r["git"]: flags.append("git")
        if r["graphify"]: flags.append("graphify")
        if r["uncommitted"]: flags.append("dirty")
        if r["worktrees"]: flags.append(f"{r['worktrees']}wt")
        if r["stale_branches"]: flags.append(f"{r['stale_branches']}stale")
        print(f"{r['name']:<{name_w}}  {' '.join(flags)}")


if __name__ == "__main__":
    main()
