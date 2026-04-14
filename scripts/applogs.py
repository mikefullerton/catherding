#!/usr/bin/env python3
"""Show macOS unified log entries for a given process.

Usage:
  cc-applogs <process>                       # last 30s of process logs
  cc-applogs <process> --last 60s
  cc-applogs <process> --grep PluginManager  # case-insensitive substring filter
  cc-applogs <process> --subsystem com.agentictoolkit
  cc-applogs <process> --tail 50             # only last N matching lines

Wraps `log show --predicate 'process == "X"' --info` so callers don't
have to remember the predicate syntax.
"""
from __future__ import annotations

import argparse
import subprocess
import sys


def main() -> int:
    ap = argparse.ArgumentParser(description="Show macOS unified-log entries for a process.")
    ap.add_argument("process", help="Process name (e.g. AgenticPluginTester)")
    ap.add_argument("--last", default="30s", help="Time window passed to `log show --last` (default: 30s)")
    ap.add_argument("--grep", help="Case-insensitive substring filter applied client-side")
    ap.add_argument("--subsystem", help="Restrict to a subsystem (e.g. com.agentictoolkit)")
    ap.add_argument("--category", help="Restrict to a subsystem+category (use with --subsystem)")
    ap.add_argument("--tail", type=int, default=100, help="Show only the last N matching lines (default: 100)")
    args = ap.parse_args()

    predicate = f'process == "{args.process}"'
    if args.subsystem:
        predicate += f' AND subsystem BEGINSWITH "{args.subsystem}"'
    if args.category:
        predicate += f' AND category == "{args.category}"'

    cmd = ["/usr/bin/log", "show", "--predicate", predicate, "--info", "--last", args.last]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout, file=sys.stderr)
        return proc.returncode

    lines = [ln for ln in proc.stdout.splitlines() if ln.strip() and not ln.startswith("Timestamp ")]
    if args.grep:
        needle = args.grep.lower()
        lines = [ln for ln in lines if needle in ln.lower()]

    for ln in lines[-args.tail:]:
        print(ln)
    print(f"did: {len(lines)} line(s) for process={args.process} last={args.last}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
