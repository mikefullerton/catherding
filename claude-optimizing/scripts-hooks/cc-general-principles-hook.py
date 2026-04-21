#!/usr/bin/env python3
"""PreToolUse:Edit|Write|MultiEdit|NotebookEdit hook — nudge toward general-principles.

Emits a one-line stderr reminder, once per session, pointing at the
general-principles skill before the first code-writing tool call. The goal
is to put the 21 cookbook principles on the attention path for every
non-trivial change. Does not block.

Non-blocking: always exits 0.

Once-per-session: uses session_id from the hook payload to write a marker
under $HOME/.claude/runtime/general-principles-seen/. Subsequent Edit/Write
calls in the same session stay silent.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
_REMINDER = (
    "general-principles: before this change, invoke the `general-principles` "
    "skill and name the principles in play (simplicity, yagni, fail-fast, "
    "explicit-over-implicit, etc.). Silent for the rest of this session."
)


def _marker_dir() -> Path:
    return Path(os.environ.get("HOME", "")) / ".claude" / "runtime" / "general-principles-seen"


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return 0

    if data.get("tool_name") not in _TOOLS:
        return 0

    session_id = data.get("session_id") or ""
    if not session_id:
        return 0

    marker_dir = _marker_dir()
    marker = marker_dir / session_id
    if marker.exists():
        return 0

    marker_dir.mkdir(parents=True, exist_ok=True)
    marker.touch()

    print(_REMINDER, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
