#!/usr/bin/env python3
"""Verify every cc-* entry resolves to an executable script.

Usage: cc-doctor

Walks both `~/.local/bin/cc-*` (regular scripts) and `~/.claude/hooks/cc-*-hook.py`
(Claude Code hook scripts). Reports broken symlinks (target deleted/moved),
non-symlinks shadowing the namespace, and stale entries pointing outside the
canonical scripts dir. Exits non-zero on any problem.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


REPO_ROOT = Path.home() / "projects" / "active" / "cat-herding"
CANONICAL_SOURCES = [REPO_ROOT / "scripts", REPO_ROOT / "skill-scripts"]
BIN_DIR = Path.home() / ".local" / "bin"
HOOKS_DIR = Path.home() / ".claude" / "hooks"


def _entries() -> list[Path]:
    """All cc-* entries we manage across both install destinations."""
    out: list[Path] = []
    if BIN_DIR.is_dir():
        out.extend(p for p in sorted(BIN_DIR.iterdir()) if p.name.startswith("cc-"))
    if HOOKS_DIR.is_dir():
        out.extend(
            p for p in sorted(HOOKS_DIR.iterdir())
            if p.name.startswith("cc-") and p.name.endswith("-hook.py")
        )
    return out


def main() -> int:
    if not BIN_DIR.is_dir() and not HOOKS_DIR.is_dir():
        print(f"FAIL: neither {BIN_DIR} nor {HOOKS_DIR} exists", file=sys.stderr)
        return 1

    ok = broken = non_symlink = stale = 0
    issues: list[str] = []

    for entry in _entries():
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
        # Stale = points outside the canonical script dirs AND outside any
        # cat-herding worktree. Worktrees use `.claude/worktrees/<name>/{scripts,skill-scripts}/`,
        # which is fine while testing.
        real_s = str(real)
        is_canonical = any(real_s.startswith(str(src) + "/") for src in CANONICAL_SOURCES)
        is_worktree = (
            "/cat-herding/.claude/worktrees/" in real_s
            and ("/scripts/" in real_s or "/skill-scripts/" in real_s)
        )
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
