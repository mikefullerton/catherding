#!/usr/bin/env python3
"""Controlled find-and-replace across the repo using git ls-files + Python.

Usage:
  cc-rename <pattern> <replacement> [--apply]
            [--literal] [--ext EXT]... [--glob G]... [--path P]

Defaults to dry-run: prints per-file match counts and total, no writes.
Pass --apply to actually rewrite files. Uses regex by default; --literal
treats <pattern> as a fixed string.

File enumeration uses `git ls-files -co --exclude-standard` so .gitignore
is honored and only tracked / untracked-but-not-ignored files are scanned.
Optional filters: --ext (e.g. swift), --glob (fnmatch), --path (path prefix).

Designed to replace `sed -i ''` chains with something Claude can invoke
once, preview, and then re-invoke with --apply.
"""
from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
from pathlib import Path


def list_repo_files() -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        print("cc-rename: not a git repo (git ls-files failed)", file=sys.stderr)
        sys.exit(proc.returncode)
    return [line for line in proc.stdout.splitlines() if line]


def filter_files(files: list[str], exts: list[str], globs: list[str], paths: list[str]) -> list[str]:
    def keep(path: str) -> bool:
        if exts and not any(path.endswith(f".{e.lstrip('.')}" ) for e in exts):
            return False
        if globs and not any(fnmatch.fnmatch(path, g) for g in globs):
            return False
        if paths and not any(path == p or path.startswith(p.rstrip("/") + "/") for p in paths):
            return False
        return True
    return [p for p in files if keep(p)]


def count_matches(text: str, pattern: str, literal: bool) -> int:
    if literal:
        return text.count(pattern)
    return len(re.findall(pattern, text))


def replace_text(text: str, pattern: str, replacement: str, literal: bool) -> str:
    if literal:
        return text.replace(pattern, replacement)
    return re.sub(pattern, replacement, text)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="cc-rename",
        description="Dry-run-by-default find-and-replace across repo files.",
    )
    parser.add_argument("pattern", help="Search pattern (regex by default, literal with --literal)")
    parser.add_argument("replacement", help="Replacement string (supports \\1 etc. unless --literal)")
    parser.add_argument("--apply", action="store_true", help="Actually write changes (default is dry-run)")
    parser.add_argument("--literal", action="store_true", help="Treat pattern/replacement as fixed strings")
    parser.add_argument("--ext", action="append", default=[], dest="exts", help="Filter by extension (repeatable, e.g. --ext swift)")
    parser.add_argument("--glob", action="append", default=[], dest="globs", help="fnmatch glob against path (repeatable)")
    parser.add_argument("--path", action="append", default=[], dest="paths", help="Limit to path prefix (repeatable)")
    args = parser.parse_args()

    if not args.literal:
        try:
            re.compile(args.pattern)
        except re.error as exc:
            print(f"cc-rename: invalid regex: {exc}", file=sys.stderr)
            return 1

    files = filter_files(list_repo_files(), args.exts, args.globs, args.paths)
    if not files:
        print("cc-rename: no files matched filters")
        return 0

    per_file: list[tuple[str, int]] = []
    total_matches = 0
    for path in files:
        try:
            text = Path(path).read_text()
        except (OSError, UnicodeDecodeError):
            continue
        n = count_matches(text, args.pattern, args.literal)
        if n:
            per_file.append((path, n))
            total_matches += n

    if not per_file:
        print("cc-rename: no matches")
        return 0

    width = max(len(p) for p, _ in per_file)
    mode = "APPLY" if args.apply else "dry-run"
    print(f"[{mode}] {args.pattern!r} -> {args.replacement!r} ({'literal' if args.literal else 'regex'})")
    for path, n in per_file:
        print(f"  {path:<{width}}  {n}")

    if not args.apply:
        print(f"did: {len(per_file)} file(s), {total_matches} match(es) — dry run (use --apply to write)")
        return 0

    written = 0
    for path, _ in per_file:
        original = Path(path).read_text()
        updated = replace_text(original, args.pattern, args.replacement, args.literal)
        if updated != original:
            Path(path).write_text(updated)
            written += 1
    print(f"did: wrote {written} file(s), {total_matches} replacement(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
