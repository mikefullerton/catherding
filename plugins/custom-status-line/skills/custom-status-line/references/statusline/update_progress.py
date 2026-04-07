#!/usr/bin/env python3
"""Standalone CLI: update per-session progress bar file.

Usage:
    python3 -m statusline.update_progress <title> <subtitle> <count> <max>
    python3 -m statusline.update_progress --clear
"""
import json
import os
import shutil
import subprocess
import sys


def find_session_id() -> str:
    """Walk up the process tree to find the Claude session ID."""
    pid = os.getpid()
    home = os.path.expanduser("~")
    while pid > 1:
        session_file = os.path.join(home, ".claude", "sessions", f"{pid}.json")
        if os.path.isfile(session_file):
            try:
                with open(session_file) as f:
                    data = json.load(f)
                    sid = data.get("sessionId", "")
                    if sid:
                        return sid
            except (OSError, json.JSONDecodeError):
                pass
        try:
            result = subprocess.run(
                ["ps", "-o", "ppid=", "-p", str(pid)],
                capture_output=True, text=True, timeout=2,
            )
            pid = int(result.stdout.strip())
        except (subprocess.TimeoutExpired, ValueError, OSError):
            break
    return ""


def write_progress(session_id: str, title: str, subtitle: str,
                   count: int, max_val: int, cols: int) -> None:
    """Write a progress file for the given session."""
    progress_dir = os.path.expanduser("~/.claude-status-line/progress")
    os.makedirs(progress_dir, exist_ok=True)
    progress_file = os.path.join(progress_dir, f"{session_id}.json")
    data = {
        "title": title,
        "subtitle": subtitle,
        "count": count,
        "max": max_val,
        "cols": cols,
        "session_id": session_id,
    }
    with open(progress_file, "w") as f:
        json.dump(data, f)


def clear_progress(session_id: str) -> None:
    """Remove the progress file for the given session."""
    progress_dir = os.path.expanduser("~/.claude-status-line/progress")
    progress_file = os.path.join(progress_dir, f"{session_id}.json")
    try:
        os.remove(progress_file)
    except FileNotFoundError:
        pass


def show_progress_example() -> None:
    """Write one step of the demo, or clear it. Called repeatedly by the skill."""
    # Usage: --show-progress-example <step> <total>
    #        --show-progress-example --clear
    if len(sys.argv) >= 3 and sys.argv[2] == "--clear":
        session_id = find_session_id()
        if session_id:
            clear_progress(session_id)
        print("Demo complete.")
        return

    step = int(sys.argv[2]) if len(sys.argv) >= 3 else 1
    total = int(sys.argv[3]) if len(sys.argv) >= 4 else 10

    session_id = find_session_id()
    if not session_id:
        print("Error: could not determine session ID.")
        sys.exit(1)

    cols = shutil.get_terminal_size((80, 24)).columns
    write_progress(session_id, "Demo progress", f"Step {step}", step, total, cols)
    print(f"Demo: step {step}/{total}")


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--show-progress-example":
        show_progress_example()
        return

    if len(sys.argv) >= 2 and sys.argv[1] == "--clear":
        session_id = find_session_id()
        if not session_id:
            print("Error: could not determine session ID", file=sys.stderr)
            sys.exit(1)
        clear_progress(session_id)
        print("Progress cleared.")
        return

    if len(sys.argv) < 5:
        print("Usage: python3 -m statusline.update_progress <title> <subtitle> <count> <max>")
        print("       python3 -m statusline.update_progress --clear")
        sys.exit(1)

    title = sys.argv[1]
    subtitle = sys.argv[2]
    count = int(sys.argv[3])
    max_val = int(sys.argv[4])

    session_id = find_session_id()
    if not session_id:
        print("Error: could not determine session ID", file=sys.stderr)
        sys.exit(1)

    cols = shutil.get_terminal_size((80, 24)).columns
    write_progress(session_id, title, subtitle, count, max_val, cols)

    pct = count * 100 // max_val if max_val > 0 else 0
    print(f"{title}: {subtitle} {count}/{max_val} ({pct}%)")


if __name__ == "__main__":
    main()
