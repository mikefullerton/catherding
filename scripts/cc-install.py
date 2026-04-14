#!/usr/bin/env python3
"""Re-symlink every cc-* script from a chosen scripts directory.

Usage:
  cc-install                           # repoint at canonical ~/projects/active/cat-herding/scripts/
  cc-install --from <dir>              # repoint at any directory containing cc-*.py scripts
  cc-install --dry-run                 # just print what would change

Each `cc-<name>.py` becomes `~/.local/bin/cc-<name>` (extension stripped). Useful when:
  - a new script was added (so install.sh needs to re-run)
  - testing modified scripts from a worktree before merging them
  - cc-doctor reports broken symlinks
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


DEFAULT_SOURCE = Path.home() / "projects" / "active" / "cat-herding" / "scripts"
BIN_DIR = Path.home() / ".local" / "bin"


def main() -> int:
    ap = argparse.ArgumentParser(description="Repoint cc-* symlinks in ~/.local/bin/.")
    ap.add_argument("--from", dest="source", default=str(DEFAULT_SOURCE),
                    help=f"Source dir containing cc-*.py scripts (default: {DEFAULT_SOURCE})")
    ap.add_argument("--dry-run", action="store_true", help="Print actions without applying them")
    args = ap.parse_args()

    src = Path(args.source).expanduser().resolve()
    if not src.is_dir():
        print(f"FAIL: source dir not found: {src}", file=sys.stderr)
        return 2

    BIN_DIR.mkdir(parents=True, exist_ok=True)

    scripts = sorted(p for p in src.glob("cc-*.py") if p.is_file())
    if not scripts:
        print(f"FAIL: no cc-*.py scripts in {src}", file=sys.stderr)
        return 1

    changed = unchanged = 0
    for script in scripts:
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

    print(f"did: {changed} symlink(s) {'planned' if args.dry_run else 'updated'} | {unchanged} already current | from {src}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
