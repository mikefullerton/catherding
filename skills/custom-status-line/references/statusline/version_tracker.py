#!/usr/bin/env python3
"""Pipeline module: track Claude Code version changes and new fields."""
import json
import os

from statusline.formatting import BLUE, YELLOW, GREEN, ORANGE, DIM, RST


VERSION_FILE = os.path.expanduser("~/.claude-status-line/claude_version.json")


def extract_paths(obj, prefix=""):
    """Recursively extract all dotted field paths from a JSON object."""
    paths = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else k
            paths.append(p)
            paths.extend(extract_paths(v, p))
    elif isinstance(obj, list) and obj:
        paths.extend(extract_paths(obj[0], prefix + "[]"))
    return paths


def load_version_info():
    """Load the baseline version file."""
    try:
        with open(VERSION_FILE) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def run(claude_data: dict, lines: list) -> list:
    """Append a version-change line if Claude was updated since our baseline."""
    info = load_version_info()
    if info is None:
        return lines

    current_version = claude_data.get("version", "")
    built_against = info.get("built_against", "")
    known_fields = set(info.get("fields", []))

    if not current_version or current_version == built_against:
        return lines

    # Version changed — find new fields
    current_fields = set(extract_paths(claude_data))
    new_fields = sorted(current_fields - known_fields)

    lbor = f"{ORANGE}|{RST} "
    sep = f" {ORANGE}|{RST} "

    version_part = f"{YELLOW}claude updated to {current_version}{RST} (built against {built_against})"
    if new_fields:
        count = len(new_fields)
        fields_part = f"{GREEN}{count} new field{'s' if count != 1 else ''}{RST}"
    else:
        fields_part = f"{DIM}no new fields{RST}"

    lines.append(f"{lbor}{version_part}{sep}{fields_part}")
    return lines
