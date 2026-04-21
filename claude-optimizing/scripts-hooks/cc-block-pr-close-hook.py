#!/usr/bin/env python3
"""PreToolUse:Bash hook — block `gh pr close` (the non-merging closure).

Rationale: `gh pr close` abandons a PR without merging. Usually the intent
was actually `gh pr merge`, which merges AND closes. Blocking `gh pr close`
forces an intentional override when an unmerged close is actually desired.

Escape hatch: prefix the command with `CC_ALLOW_PR_CLOSE=1 ` (the marker
must appear in the command string itself — hook input doesn't reliably
carry the parent process environment).

Exits:
  0 — allow (command doesn't match, or escape hatch present)
  2 — block; stderr message is fed back to Claude
"""
from __future__ import annotations

import json
import re
import sys


_CLOSE_RE = re.compile(r"\bgh\s+pr\s+close\b")
_OVERRIDE_RE = re.compile(r"\bCC_ALLOW_PR_CLOSE=1\b")


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return 0

    if data.get("tool_name") != "Bash":
        return 0

    cmd = (data.get("tool_input") or {}).get("command", "")
    if not isinstance(cmd, str) or not _CLOSE_RE.search(cmd):
        return 0

    if _OVERRIDE_RE.search(cmd):
        return 0

    print(
        "Blocked: `gh pr close` closes a PR without merging it.\n"
        "\n"
        "  If you meant to merge, use `gh pr merge` (merges AND closes).\n"
        "  If you intentionally want to abandon this PR, prefix the command\n"
        "  with CC_ALLOW_PR_CLOSE=1 — e.g. `CC_ALLOW_PR_CLOSE=1 gh pr close 42`.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
