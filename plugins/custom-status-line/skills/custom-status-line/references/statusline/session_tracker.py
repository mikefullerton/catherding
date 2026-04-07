#!/usr/bin/env python3
"""Pipeline module: concurrent session tracking."""
import json
import os
import time

from statusline.formatting import ORANGE, DIM, RST

SESSIONS_DIR = os.path.expanduser("~/.claude-status-line/sessions")
STALE_THRESHOLD = 3600  # 1 hour — remove sessions with no activity


def run(claude_data: dict, lines: list) -> list:
    """Insert session counts line between model and usage lines."""
    if not os.path.isdir(SESSIONS_DIR):
        return lines

    now = time.time()
    thinking = 0
    waiting = 0

    for fname in os.listdir(SESSIONS_DIR):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(SESSIONS_DIR, fname)
        try:
            mtime = os.path.getmtime(path)
            if now - mtime > STALE_THRESHOLD:
                os.remove(path)
                continue
            with open(path) as f:
                data = json.load(f)
            if data.get("state") == "thinking":
                thinking += 1
            else:
                waiting += 1
        except (OSError, json.JSONDecodeError):
            continue

    active = thinking + waiting
    sep = f" {ORANGE}|{RST} "
    lbor = f"{ORANGE}|{RST} "
    line = (
        f"{lbor}{DIM}all sessions{RST}"
        f"{sep}{active} active"
        f"{sep}{thinking} thinking"
        f"{sep}{waiting} waiting"
    )

    # Insert between line 2 (model) and line 3 (usage)
    if len(lines) >= 3:
        lines.insert(2, line)
    else:
        lines.append(line)

    return lines
