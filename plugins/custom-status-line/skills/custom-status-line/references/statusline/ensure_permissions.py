#!/usr/bin/env python3
"""Standalone CLI: merge Bash() tool patterns from SKILL.md into settings.json.

Usage:
    python3 -m statusline.ensure_permissions /path/to/SKILL.md
"""
import json
import os
import re
import sys


def merge_permissions(skill_path: str, settings_path: str) -> None:
    """Extract Bash() patterns from SKILL.md frontmatter and merge into settings."""
    if not os.path.isfile(skill_path) or not os.path.isfile(settings_path):
        return

    try:
        with open(skill_path) as f:
            content = f.read()
    except OSError:
        return

    parts = content.split("---", 2)
    if len(parts) < 3:
        return
    frontmatter = parts[1]

    patterns = re.findall(r"Bash\([^)]+\)", frontmatter)
    if not patterns:
        return

    try:
        with open(settings_path) as f:
            settings = json.load(f)
    except (OSError, json.JSONDecodeError):
        return

    allow = settings.get("permissions", {}).get("allow", [])
    merged = list(dict.fromkeys(allow + patterns))
    settings.setdefault("permissions", {})["allow"] = merged

    tmp_path = settings_path + ".tmp"
    try:
        with open(tmp_path, "w") as f:
            json.dump(settings, f, indent=2)
        os.replace(tmp_path, settings_path)
    except OSError:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 -m statusline.ensure_permissions /path/to/SKILL.md")
        sys.exit(1)

    skill_path = sys.argv[1]
    settings_path = os.path.expanduser("~/.claude/settings.json")
    merge_permissions(skill_path, settings_path)


if __name__ == "__main__":
    main()
