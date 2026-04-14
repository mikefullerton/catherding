#!/usr/bin/env python3
"""Track Claude session state for status line display.

Called by hooks: SessionStart, UserPromptSubmit, Stop, SessionEnd.
Writes per-session JSON files to ~/.claude-status-line/sessions/.
"""
import json
import os
import sys
import time

SESSIONS_DIR = os.path.expanduser("~/.claude-status-line/sessions")


def main():
    event = sys.argv[1] if len(sys.argv) > 1 else ""
    data = json.loads(sys.stdin.read())
    session_id = data.get("session_id", "")
    if not session_id:
        return

    os.makedirs(SESSIONS_DIR, exist_ok=True)
    path = os.path.join(SESSIONS_DIR, f"{session_id}.json")

    if event == "SessionEnd":
        try:
            os.remove(path)
        except OSError:
            pass
        return

    if event == "UserPromptSubmit":
        state = "thinking"
    else:
        state = "waiting"

    with open(path, "w") as f:
        json.dump({"state": state, "ts": time.time()}, f)


if __name__ == "__main__":
    main()
