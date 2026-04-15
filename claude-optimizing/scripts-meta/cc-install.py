#!/usr/bin/env python3
"""Re-symlink every cc-* script from the repo into ~/.local/bin/.

Usage:
  cc-install                           # install from canonical repo (claude-optimizing/scripts-*/)
  cc-install --from <dir>              # install from an explicit directory (single dir)
  cc-install --dry-run                 # just print what would change

Each `cc-<name>.py` becomes `~/.local/bin/cc-<name>` (extension stripped), except
`cc-*-hook.py` files which go to `~/.claude/hooks/cc-*-hook.py` (Claude Code
expects hook scripts there, not on PATH).

By default, installs from every `claude-optimizing/scripts-*/` category dir
(scripts-git, scripts-bash, scripts-xcode, scripts-claude, scripts-meta,
scripts-hooks). Skill-internal scripts live under each skill's own
`scripts/` subdir and are NOT on $PATH (the relevant skill invokes them
directly). Pass `--from <dir>` to override with a single explicit source
(useful for testing a worktree in isolation).

Useful when:
  - a new script was added (so install.sh needs to re-run)
  - testing modified scripts from a worktree before merging them
  - cc-doctor reports broken symlinks
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


REPO_ROOT = Path.home() / "projects" / "active" / "cat-herding"
# Scripts are organized into category directories under `claude-optimizing/`
# (scripts-git/, scripts-bash/, scripts-xcode/, scripts-claude/, scripts-meta/,
# scripts-hooks/). Skill-internal scripts live under each skill's own `scripts/`
# subdir and are NOT installed to $PATH — the owning skill invokes them directly.
DEFAULT_SOURCES = sorted((REPO_ROOT / "claude-optimizing").glob("scripts-*"))
BIN_DIR = Path.home() / ".local" / "bin"
HOOKS_DIR = Path.home() / ".claude" / "hooks"


def _install_target(script: Path) -> Path:
    """Where this script should be installed.

    `cc-*-hook.py` scripts are Claude Code hook handlers (read JSON on stdin,
    integrate with the hook protocol). They live under ~/.claude/hooks/ and
    KEEP the .py extension because Claude Code invokes them as Python files.
    Everything else goes on $PATH at ~/.local/bin/cc-* (extension stripped).
    """
    if script.stem.endswith("-hook"):
        return HOOKS_DIR / script.name
    return BIN_DIR / script.stem


def main() -> int:
    ap = argparse.ArgumentParser(description="Repoint cc-* symlinks in ~/.local/bin/.")
    ap.add_argument(
        "--from", dest="source", default=None,
        help="Explicit source dir containing cc-*.py scripts "
             "(default: claude-optimizing/scripts-*/ under the cat-herding repo)",
    )
    ap.add_argument("--dry-run", action="store_true", help="Print actions without applying them")
    args = ap.parse_args()

    if args.source:
        sources = [Path(args.source).expanduser().resolve()]
    else:
        sources = [s for s in DEFAULT_SOURCES if s.is_dir()]

    missing = [s for s in sources if not s.is_dir()]
    if missing:
        for m in missing:
            print(f"FAIL: source dir not found: {m}", file=sys.stderr)
        return 2

    if not sources:
        print("FAIL: no source directories available", file=sys.stderr)
        return 2

    BIN_DIR.mkdir(parents=True, exist_ok=True)
    HOOKS_DIR.mkdir(parents=True, exist_ok=True)

    scripts: list[Path] = []
    for src in sources:
        scripts.extend(sorted(p for p in src.glob("cc-*.py") if p.is_file()))
    if not scripts:
        print(f"FAIL: no cc-*.py scripts in {', '.join(str(s) for s in sources)}", file=sys.stderr)
        return 1

    # Detect collisions (same command name in two source dirs) — first one wins
    # but warn loudly so the conflict isn't silent.
    seen: dict[str, Path] = {}
    resolved: list[Path] = []
    for script in scripts:
        if script.stem in seen:
            print(f"WARN: duplicate '{script.stem}' in {script.parent} "
                  f"(already installed from {seen[script.stem].parent}); skipping",
                  file=sys.stderr)
            continue
        seen[script.stem] = script
        resolved.append(script)

    changed = unchanged = 0
    for script in resolved:
        target = _install_target(script)
        if target.is_symlink() and os.readlink(target) == str(script):
            unchanged += 1
            continue
        if args.dry_run:
            print(f"would link {target} -> {script}")
        else:
            if target.exists() or target.is_symlink():
                target.unlink()
            target.symlink_to(script)
            os.chmod(script, 0o755)
        changed += 1

    sources_str = ", ".join(str(s) for s in sources)
    print(
        f"did: {changed} symlink(s) {'planned' if args.dry_run else 'updated'} "
        f"| {unchanged} already current | from {sources_str}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
