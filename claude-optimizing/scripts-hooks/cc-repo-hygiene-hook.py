#!/usr/bin/env python3
"""Repo hygiene Stop hook — block if Claude left its own work uncommitted.

Single purpose: detect staged, unstaged, or untracked changes that this
session produced (via Edit / Write / NotebookEdit / Bash tool_use inputs)
and refuse to end the turn until they're committed and pushed. Prior-
session dirt is ignored entirely — surfacing it is the user's call, not
the hook's.

Only enforces under ~/projects/ (but not ~/projects/external/).
"""

import json
import os
import subprocess
import sys


def run(cmd, cwd=None, timeout=10):
    """Run a git command, return (stdout, returncode)."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout
        )
        return result.stdout.strip(), result.returncode
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return "", 1


def _read_transcript_tool_uses(transcript_path):
    """Return (edit_paths, bash_commands) from the Claude Code transcript.

    Returns (None, None) on any failure (missing file, IO error, malformed
    JSON line, or unexpected structure). Callers treat None as "fail
    closed" — classify every dirty path as this-session.
    """
    if not transcript_path:
        return None, None
    try:
        edit_paths = set()
        bash_commands = []
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    return None, None
                msg = obj.get("message") or {}
                content = msg.get("content")
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") != "tool_use":
                        continue
                    name = block.get("name")
                    inp = block.get("input") or {}
                    if not isinstance(inp, dict):
                        continue
                    if name in ("Edit", "Write", "NotebookEdit"):
                        fp = inp.get("file_path")
                        if isinstance(fp, str) and fp:
                            edit_paths.add(os.path.realpath(fp))
                    elif name == "Bash":
                        cmd = inp.get("command")
                        if isinstance(cmd, str) and cmd:
                            bash_commands.append(cmd)
        return edit_paths, bash_commands
    except (OSError, IOError):
        return None, None


def _session_touched(rel_paths, cwd, edit_paths, bash_commands):
    """Return the subset of rel_paths that this session touched.

    A path counts as touched if its absolute form appears in edit_paths,
    or its relative/absolute form appears as a substring in any Bash
    command. The substring check is intentionally loose: a false positive
    (prior-session path promoted to session-touched) only means an extra
    block, while a false negative would let real session dirt slip past
    Stop — the dangerous direction.
    """
    touched = []
    for rel in rel_paths:
        abs_path = os.path.realpath(os.path.join(cwd, rel))
        if abs_path in edit_paths:
            touched.append(rel)
            continue
        for cmd in bash_commands:
            if rel in cmd or abs_path in cmd:
                touched.append(rel)
                break
    return touched


def main():
    input_json = json.loads(sys.stdin.read())

    if input_json.get("stop_hook_active"):
        sys.exit(0)

    cwd = input_json.get("cwd", "")
    if not cwd:
        sys.exit(0)

    home = os.path.expanduser("~")
    projects_root = os.path.join(home, "projects")
    external_root = os.path.join(home, "projects", "external")
    abs_cwd = os.path.realpath(cwd)
    in_projects = abs_cwd.startswith(projects_root + os.sep) or abs_cwd == projects_root
    in_external = abs_cwd.startswith(external_root + os.sep) or abs_cwd == external_root
    if not in_projects or in_external:
        sys.exit(0)

    _, rc = run(["git", "-C", cwd, "rev-parse", "--is-inside-work-tree"])
    if rc != 0:
        sys.exit(0)

    transcript_path = input_json.get("transcript_path") or ""
    edit_paths, bash_commands = _read_transcript_tool_uses(transcript_path)
    classify_enabled = edit_paths is not None

    def _session_only(rel_paths):
        if not classify_enabled:
            return rel_paths
        return _session_touched(rel_paths, cwd, edit_paths, bash_commands)

    violations = []

    out, _ = run(["git", "-C", cwd, "diff", "--cached", "--name-only"])
    staged = _session_only([p for p in out.splitlines() if p])
    if staged:
        violations.append("Staged changes not committed: " + ", ".join(staged))

    out, _ = run(["git", "-C", cwd, "diff", "--name-only"])
    unstaged = _session_only([p for p in out.splitlines() if p])
    if unstaged:
        violations.append("Unstaged changes to tracked files: " + ", ".join(unstaged))

    out, _ = run(["git", "-C", cwd, "ls-files", "--others", "--exclude-standard"])
    untracked = _session_only([p for p in out.splitlines() if p])
    if untracked:
        violations.append(
            f"{len(untracked)} untracked file(s) not in .gitignore: "
            + ", ".join(untracked)
        )

    if not violations:
        sys.exit(0)

    reason = "Repo hygiene violations: " + "; ".join(violations)
    json.dump({"decision": "block", "reason": reason}, sys.stdout)
    sys.exit(0)


if __name__ == "__main__":
    main()
