#!/usr/bin/env python3
"""Pipeline module: track Claude Code version changes and new fields."""
import json
import os

from statusline.formatting import (
    YELLOW, GREEN, DIM, RST,
    visible_len, pad_right, pad_left,
)


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


def _extract_col_widths(lines):
    """Extract column visible widths from existing status lines."""
    sep = " | "
    for idx in range(len(lines) - 1, 0, -1):
        parts = lines[idx].split(sep)
        if len(parts) >= 4:
            widths = [visible_len(parts[0]) - 2]
            widths.extend(visible_len(p) for p in parts[1:])
            return widths
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

    lbor = "| "
    sep = " | "

    v1 = "claude upgrade"
    v2 = f"{YELLOW}{current_version}{RST} (from {built_against})"
    if new_fields:
        count = len(new_fields)
        v3 = f"{GREEN}{count} new field{'s' if count != 1 else ''}{RST}"
    else:
        v3 = f"{DIM}no new fields{RST}"

    # Match column widths from existing lines, widen if version content is wider
    col_widths = _extract_col_widths(lines)
    if col_widths and len(col_widths) >= 3:
        vc_widths = [visible_len(v1), visible_len(v2), visible_len(v3)]
        new_widths = [max(col_widths[i], vc_widths[i]) for i in range(3)]

        # Reformat existing aligned lines if any column got wider
        if new_widths != col_widths[:3]:
            for i, line in enumerate(lines):
                if not line.startswith(lbor):
                    continue
                parts = line.split(sep)
                if len(parts) < 3:
                    continue
                # Skip lines with different column structure (model line with session name)
                first_col_w = visible_len(parts[0]) - len(lbor)
                if abs(first_col_w - col_widths[0]) > 1:
                    continue
                rebuilt = lbor + pad_left(parts[0][len(lbor):], new_widths[0])
                for j in range(1, len(parts)):
                    col = pad_right(parts[j], new_widths[j]) if j < len(new_widths) else parts[j]
                    rebuilt += sep + col
                lines[i] = rebuilt

        v1 = pad_left(v1, new_widths[0])
        v2 = pad_right(v2, new_widths[1])
        v3 = pad_right(v3, new_widths[2])

    lines.append(f"{lbor}{v1}{sep}{v2}{sep}{v3}")
    return lines
