#!/usr/bin/env python3
"""Verify every cc-* symlink in ~/.local/bin/ resolves to an executable script.

Usage: cc-doctor

Reports broken symlinks (target deleted/moved), non-symlinks shadowing the
namespace, and stale entries pointing outside the canonical scripts dir.
Exits non-zero on any problem.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


CANONICAL_SOURCE = Path.home() / "projects" / "active" / "cat-herding" / "scripts"
BIN_DIR = Path.home() / ".local" / "bin"


def main() -> int:
    if not BIN_DIR.is_dir():
        print(f"FAIL: {BIN_DIR} does not exist", file=sys.stderr)
        return 1

    ok = broken = non_symlink = stale = 0
    issues: list[str] = []

    for entry in sorted(BIN_DIR.iterdir()):
        if not entry.name.startswith("cc-"):
            continue
        if not entry.is_symlink():
            non_symlink += 1
            issues.append(f"  not a symlink: {entry}")
            continue
        try:
            real = entry.resolve(strict=True)
        except FileNotFoundError:
            broken += 1
            issues.append(f"  BROKEN symlink: {entry} -> {os.readlink(entry)}")
            continue
        if not os.access(real, os.X_OK):
            issues.append(f"  not executable: {real}")
            broken += 1
            continue
        # Stale = points outside the canonical scripts dir AND outside any
        # cat-herding worktree. Worktrees use `.claude/worktrees/<name>/scripts/`,
        # which is fine while testing.
        is_canonical = str(real).startswith(str(CANONICAL_SOURCE) + "/")
        is_worktree = "/cat-herding/.claude/worktrees/" in str(real) and "/scripts/" in str(real)
        if not (is_canonical or is_worktree):
            stale += 1
            issues.append(f"  stale (points outside cat-herding): {entry} -> {real}")
        ok += 1

    for line in issues:
        print(line)

    summary = f"did: ok {ok} | broken {broken} | non-symlink {non_symlink} | stale {stale}"
    if broken or non_symlink or stale:
        print(summary, file=sys.stderr)
        return 1
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
