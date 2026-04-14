#!/usr/bin/env python3
"""Install YOLO hooks, statusline indicator, and deny defaults.

Usage: install-yolo.py [--skill-dir DIR]

Idempotent. When invoked via `python3 skills/yolo/install-yolo.py`, defaults
`--skill-dir` to the directory containing this script. When invoked from the
skill's SKILL.md with CLAUDE_SKILL_DIR set, the caller can pass it explicitly.

Writes a one-line JSON status summary to stdout on success (matches the
shape of the previous yolo-install.sh for any callers that parse it).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


HOME = Path.home()
HOOKS_DIR = HOME / ".claude" / "hooks"
MARKER_DIR = HOME / ".claude-yolo-sessions"
DENY_FILE = MARKER_DIR / "yolo-deny.json"
SETTINGS = HOME / ".claude" / "settings.json"
PIPELINE = HOME / ".claude-status-line" / "pipeline.json"
STATUSLINE_SCRIPTS = HOME / ".claude-status-line" / "scripts"

HOOK_SCRIPTS = [
    "yolo-approve-all.sh",
    "yolo-session-cleanup.sh",
    "yolo-session-start.sh",
]

SETTINGS_HOOKS = [
    # (event, matcher, command-key-for-dedup, command-template)
    ("PermissionRequest", "", "yolo-approve-all",      "$HOME/.claude/hooks/yolo-approve-all.sh"),
    ("SessionEnd",        "", "yolo-session-cleanup", "$HOME/.claude/hooks/yolo-session-cleanup.sh"),
    ("SessionStart",      "", "yolo-session-start",   "$HOME/.claude/hooks/yolo-session-start.sh"),
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def hooks_for_event(settings: dict, event: str) -> list:
    return settings.setdefault("hooks", {}).setdefault(event, [])


def hook_already_registered(settings: dict, event: str, match: str) -> bool:
    return any(
        match in h.get("command", "")
        for grp in settings.get("hooks", {}).get(event, [])
        for h in grp.get("hooks", [])
    )


def copy_hook_scripts(skill_dir: Path) -> None:
    HOOKS_DIR.mkdir(parents=True, exist_ok=True)
    MARKER_DIR.mkdir(parents=True, exist_ok=True)
    for name in HOOK_SCRIPTS:
        src = skill_dir / "references" / name
        if not src.is_file():
            continue
        dst = HOOKS_DIR / name
        shutil.copy2(src, dst)
        dst.chmod(0o755)


def register_settings_hooks(settings: dict) -> None:
    for event, matcher, dedup_key, cmd in SETTINGS_HOOKS:
        if hook_already_registered(settings, event, dedup_key):
            continue
        groups = hooks_for_event(settings, event)
        entry = {"type": "command", "command": cmd}
        # Append to the first matching-matcher group if one exists, otherwise
        # add a new group.
        for grp in groups:
            if grp.get("matcher", "") == matcher:
                grp.setdefault("hooks", []).append(entry)
                break
        else:
            groups.append({"matcher": matcher, "hooks": [entry]})


def install_statusline_indicator(skill_dir: Path) -> None:
    """Plug the yolo-indicator into the status-line pipeline, if installed."""
    indicator_src = skill_dir / "references" / "yolo-indicator.sh"
    if not (PIPELINE.is_file() and indicator_src.is_file()):
        return
    STATUSLINE_SCRIPTS.mkdir(parents=True, exist_ok=True)
    indicator_dst = STATUSLINE_SCRIPTS / "yolo-indicator.sh"
    # Unlink first in case the dst is a broken symlink from a previous
    # install layout — shutil.copy2 opens the target for writing, which fails
    # on a dangling symlink with ENOENT.
    if indicator_dst.is_symlink() or indicator_dst.exists():
        indicator_dst.unlink()
    shutil.copy2(indicator_src, indicator_dst)
    indicator_dst.chmod(0o755)

    pipeline = load_json(PIPELINE)
    pipeline_list = pipeline.setdefault("pipeline", [])
    if not any(step.get("name") == "yolo-indicator" for step in pipeline_list):
        pipeline_list.append({
            "name": "yolo-indicator",
            "script": "~/.claude-status-line/scripts/yolo-indicator.sh",
        })
        save_json(PIPELINE, pipeline)


def install_deny_config(skill_dir: Path) -> int:
    """Seed the deny config if not already present. Return the deny count."""
    defaults = skill_dir / "references" / "yolo-deny-defaults.json"
    if not DENY_FILE.exists() and defaults.is_file():
        MARKER_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(defaults, DENY_FILE)
    if not DENY_FILE.exists():
        return 0
    try:
        deny = json.loads(DENY_FILE.read_text()).get("deny", [])
        return len(deny)
    except json.JSONDecodeError:
        return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--skill-dir",
        default=str(Path(__file__).resolve().parent),
        help="YOLO skill source directory (default: this script's dir)",
    )
    args = ap.parse_args()
    skill_dir = Path(args.skill_dir).resolve()

    if not (skill_dir / "references").is_dir():
        print(f"FAIL: {skill_dir}/references not found", file=sys.stderr)
        return 2

    copy_hook_scripts(skill_dir)

    settings = load_json(SETTINGS)
    was_already_installed = hook_already_registered(
        settings, "PermissionRequest", "yolo-approve-all",
    )
    register_settings_hooks(settings)
    save_json(SETTINGS, settings)

    install_statusline_indicator(skill_dir)
    deny_count = install_deny_config(skill_dir)

    status = "already_installed" if was_already_installed else "installed"
    print(json.dumps({"status": status, "deny_count": deny_count}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
