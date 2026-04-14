#!/usr/bin/env python3
"""List available cc-* workflow scripts with one-line summaries.

Usage:
  cc-help
  cc-help <name>   # show full --help output for a specific script

Walks ~/.local/bin/cc-* and prints each script's name + its
argparse description (or first docstring line) so Claude can
discover what's available mid-task without consulting CLAUDE.md.

Output format:
  cc-NAME  — SUMMARY
  ...

Exit non-zero if no cc-* scripts are installed.
"""
from __future__ import annotations

import argparse
import ast
import os
import re
import subprocess
import sys
from pathlib import Path


BIN_DIR = Path.home() / ".local" / "bin"


def find_scripts() -> list[Path]:
    if not BIN_DIR.is_dir():
        return []
    return sorted(
        p for p in BIN_DIR.iterdir()
        if p.name.startswith("cc-") and p.is_file() and os.access(p, os.X_OK)
    )


def script_source(path: Path) -> Path | None:
    """Resolve symlinks to the underlying script file."""
    try:
        resolved = path.resolve(strict=True)
    except OSError:
        return None
    return resolved


def extract_summary(path: Path) -> str:
    """First non-empty line of the module docstring, or empty string."""
    src = script_source(path)
    if src is None or not src.is_file():
        return ""
    try:
        text = src.read_text()
    except OSError:
        return ""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return ""
    doc = ast.get_docstring(tree) or ""
    for line in doc.splitlines():
        line = line.strip()
        if line:
            return line
    return ""


def show_script_help(name: str) -> int:
    target = BIN_DIR / name
    if not target.exists():
        # Allow bare "foo" to mean "cc-foo".
        target = BIN_DIR / f"cc-{name}"
    if not target.exists():
        # Suggest closest matches if the user likely typoed.
        import difflib
        all_names = [p.name for p in find_scripts()]
        matches = difflib.get_close_matches(
            name if name.startswith("cc-") else f"cc-{name}",
            all_names,
            n=3,
            cutoff=0.55,
        )
        print(f"cc-help: no such script: {name}", file=sys.stderr)
        if matches:
            print("did you mean:", file=sys.stderr)
            for m in matches:
                print(f"  {m}", file=sys.stderr)
        return 1
    result = subprocess.run([str(target), "--help"], check=False)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="cc-help",
        description="List cc-* workflow scripts, or show --help for a specific one.",
    )
    parser.add_argument(
        "name",
        nargs="?",
        help="Optional script name (e.g. 'commit-push' or 'cc-commit-push') to show its full --help.",
    )
    args = parser.parse_args()

    if args.name:
        return show_script_help(args.name)

    scripts = find_scripts()
    if not scripts:
        print(f"cc-help: no cc-* scripts found in {BIN_DIR}", file=sys.stderr)
        return 1

    name_width = max(len(p.name) for p in scripts)
    for p in scripts:
        if p.name == "cc-help":
            summary = "list all cc-* scripts (this one)"
        else:
            summary = extract_summary(p)
        if summary:
            # Collapse summary to a single line for alignment.
            summary = re.sub(r"\s+", " ", summary).strip()
            print(f"{p.name:<{name_width}}  — {summary}")
        else:
            print(p.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
