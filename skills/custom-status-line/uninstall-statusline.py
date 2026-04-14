#!/usr/bin/env python3
"""Uninstall the custom-status-line runtime.

Removes:
  ~/.claude-status-line/statusline/*.py
  ~/.claude-status-line/scripts/*.py  (only files we manage)
  ~/.claude/hooks/session-tracker.py

Leaves the ~/.claude-status-line/pipeline.json and user data (progress/, sessions/)
alone by default — pass --all to remove the whole ~/.claude-status-line/ tree.

Idempotent. Writes a one-line JSON status summary on stdout.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

HOME = Path.home()
INSTALLED = HOME / ".claude-status-line"
INSTALLED_STATUSLINE = INSTALLED / "statusline"
INSTALLED_SCRIPTS = INSTALLED / "scripts"
SESSION_TRACKER = HOME / ".claude" / "hooks" / "session-tracker.py"


def wipe_dir(path: Path) -> int:
    """Delete every file in `path` (non-recursive). Return count removed."""
    if not path.is_dir():
        return 0
    removed = 0
    for f in path.iterdir():
        if f.is_file():
            f.unlink()
            removed += 1
    return removed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--all", action="store_true",
        help="Also remove ~/.claude-status-line/ entirely (pipeline, progress, sessions).",
    )
    args = ap.parse_args()

    out = {"status": "not_installed"}
    removed_any = False

    if args.all and INSTALLED.exists():
        shutil.rmtree(INSTALLED)
        out["removed_tree"] = True
        removed_any = True
    else:
        n_sl = wipe_dir(INSTALLED_STATUSLINE)
        n_sc = wipe_dir(INSTALLED_SCRIPTS)
        out["removed_statusline"] = n_sl
        out["removed_scripts"] = n_sc
        removed_any = removed_any or bool(n_sl or n_sc)

    if SESSION_TRACKER.exists():
        SESSION_TRACKER.unlink()
        out["removed_session_tracker"] = True
        removed_any = True

    if removed_any:
        out["status"] = "uninstalled"
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
