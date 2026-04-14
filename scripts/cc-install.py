#!/usr/bin/env python3
"""Re-symlink every cc-* script from the repo into ~/.local/bin/.

Usage:
  cc-install                           # install from canonical repo (scripts/ + skill-scripts/)
  cc-install --from <dir>              # install from an explicit directory (single dir)
  cc-install --dry-run                 # just print what would change

Each `cc-<name>.py` becomes `~/.local/bin/cc-<name>` (extension stripped).

By default, installs from BOTH `scripts/` (workflow scripts) and `skill-scripts/`
(skill-specific scripts — see each directory's README) under the cat-herding
repo. Pass `--from <dir>` to override with a single explicit source (useful for
testing a worktree in isolation).

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
DEFAULT_SOURCES = [REPO_ROOT / "scripts", REPO_ROOT / "skill-scripts"]
BIN_DIR = Path.home() / ".local" / "bin"


def main() -> int:
    ap = argparse.ArgumentParser(description="Repoint cc-* symlinks in ~/.local/bin/.")
    ap.add_argument(
        "--from", dest="source", default=None,
        help="Explicit source dir containing cc-*.py scripts "
             "(default: scripts/ + skill-scripts/ under the cat-herding repo)",
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
        name = script.stem  # already prefixed cc-
        target = BIN_DIR / name
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
