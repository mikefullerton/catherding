#!/usr/bin/env python3
"""Repo-wide ripgrep with sensible excludes.

Usage:
  cc-grep <pattern>              # ripgrep with standard excludes
  cc-grep <pattern> --type swift # restrict to Swift files
  cc-grep <pattern> path1 path2  # limit search to given paths

Excludes: .build, DerivedData, xcuserdata, .swiftpm, graphify-out,
.claude/worktrees/*/agentic-toolkit (submodule), .xcodeproj contents.

Passes through to `rg`; assumes ripgrep is installed.
"""
import argparse
import subprocess
import sys


EXCLUDES = [
    "!.build/",
    "!DerivedData/",
    "!xcuserdata/",
    "!.swiftpm/",
    "!graphify-out/",
    "!*.xcodeproj/",
    "!.claude/worktrees/*/agentic-toolkit/",
    "!node_modules/",
]


def main() -> int:
    ap = argparse.ArgumentParser(description="Repo-wide ripgrep with sensible excludes.")
    ap.add_argument("pattern", help="Search pattern")
    ap.add_argument("paths", nargs="*", help="Paths to search (default: current dir)")
    ap.add_argument("--type", help="Restrict by filetype (passed to rg --type)")
    ap.add_argument("--files-with-matches", "-l", action="store_true", help="Only print matching file names")
    ap.add_argument("--count", "-c", action="store_true", help="Only print match counts per file")
    ap.add_argument("--ignore-case", "-i", action="store_true")
    args, passthrough = ap.parse_known_args()

    cmd = ["rg"]
    for ex in EXCLUDES:
        cmd += ["--glob", ex]
    if args.type:
        cmd += ["--type", args.type]
    if args.files_with_matches:
        cmd.append("-l")
    if args.count:
        cmd.append("-c")
    if args.ignore_case:
        cmd.append("-i")
    cmd += passthrough
    cmd.append(args.pattern)
    cmd += args.paths

    proc = subprocess.run(cmd)
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
