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
    ap.add_argument("--type", action="append", default=[],
                    help="Restrict by filetype (passed to rg --type, repeatable)")
    ap.add_argument("--list", "--files-with-matches", "-l", action="store_true",
                    dest="files_with_matches",
                    help="Only print matching file names")
    ap.add_argument("--count", "-c", action="store_true", help="Only print match counts per file")
    ap.add_argument("--ignore-case", "-i", action="store_true")
    ap.add_argument("--code-only", action="store_true",
                    help="Restrict to common project file types (swift, yml, plist, md)")
    args, passthrough = ap.parse_known_args()

    cmd = ["rg"]
    for ex in EXCLUDES:
        cmd += ["--glob", ex]
    types = list(args.type)
    if args.code_only and not types:
        types = ["swift", "yml", "plist", "md"]
    for t in types:
        cmd += ["--type", t]
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
