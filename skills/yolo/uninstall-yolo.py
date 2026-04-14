#!/usr/bin/env python3
"""Remove YOLO hooks, statusline indicator, and (optionally) session markers.

Usage: uninstall-yolo.py [--all]
  --all: also delete ~/.claude-yolo-sessions/ (deny config + session markers)

Idempotent. Writes a one-line JSON status summary on stdout (matches the
shape of the previous yolo-uninstall.sh).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


HOME = Path.home()
HOOKS_DIR = HOME / ".claude" / "hooks"
SETTINGS = HOME / ".claude" / "settings.json"
PIPELINE = HOME / ".claude-status-line" / "pipeline.json"
MARKER_DIR = HOME / ".claude-yolo-sessions"
STATUSLINE_INDICATOR = HOME / ".claude-status-line" / "scripts" / "yolo-indicator.sh"

HOOK_SCRIPTS = [
    "yolo-approve-all.sh",
    "yolo-session-cleanup.sh",
    "yolo-session-start.sh",
]

SETTINGS_HOOKS_TO_REMOVE = [
    ("PermissionRequest", "yolo-approve-all"),
    ("SessionEnd",        "yolo-session-cleanup"),
    ("SessionStart",      "yolo-session-start"),
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n")


def strip_hook(settings: dict, event: str, match: str) -> bool:
    """Remove any hook command containing `match` from the named event. Return True if anything was removed."""
    groups = settings.get("hooks", {}).get(event, [])
    if not groups:
        return False
    changed = False
    new_groups: list[dict] = []
    for grp in groups:
        kept = [h for h in grp.get("hooks", []) if match not in h.get("command", "")]
        if len(kept) != len(grp.get("hooks", [])):
            changed = True
        if kept:
            new_groups.append({**grp, "hooks": kept})
    settings["hooks"][event] = new_groups
    return changed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--all", action="store_true", help="Also remove ~/.claude-yolo-sessions/")
    args = ap.parse_args()

    removed_hooks = False
    removed_scripts = False
    removed_indicator = False
    removed_sessions = False

    # 1. Strip YOLO hooks from settings.json
    if SETTINGS.exists():
        settings = load_json(SETTINGS)
        changed = False
        for event, match in SETTINGS_HOOKS_TO_REMOVE:
            if strip_hook(settings, event, match):
                changed = True
        # Prune empty event lists + empty hooks object
        if changed:
            settings.setdefault("hooks", {})
            for event in list(settings["hooks"].keys()):
                if not settings["hooks"][event]:
                    del settings["hooks"][event]
            if not settings["hooks"]:
                del settings["hooks"]
            save_json(SETTINGS, settings)
            removed_hooks = True

    # 2. Delete hook script files
    for name in HOOK_SCRIPTS:
        p = HOOKS_DIR / name
        if p.exists():
            p.unlink()
            removed_scripts = True

    # 3. Remove statusline indicator
    if PIPELINE.exists():
        pipeline = load_json(PIPELINE)
        steps = pipeline.get("pipeline", [])
        kept = [s for s in steps if s.get("name") != "yolo-indicator"]
        if len(kept) != len(steps):
            pipeline["pipeline"] = kept
            save_json(PIPELINE, pipeline)
            removed_indicator = True
    if STATUSLINE_INDICATOR.exists():
        STATUSLINE_INDICATOR.unlink()

    # 4. Optionally nuke session markers / deny config
    if args.all and MARKER_DIR.exists():
        shutil.rmtree(MARKER_DIR)
        removed_sessions = True

    if not (removed_hooks or removed_scripts):
        print(json.dumps({"status": "not_installed"}))
        return 0

    print(json.dumps({
        "status": "uninstalled",
        "removed_hooks": removed_hooks,
        "removed_scripts": removed_scripts,
        "removed_indicator": removed_indicator,
        "removed_sessions": removed_sessions,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
