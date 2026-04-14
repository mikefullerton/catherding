#!/usr/bin/env python3
"""List the schemes in an Xcode workspace or project.

Usage:
  cc-xcschemes                         # auto-detect workspace or project in cwd / Apple/
  cc-xcschemes --workspace path.xcworkspace
  cc-xcschemes --project path.xcodeproj

Wraps `xcodebuild -list -json` and prints just the scheme names.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def find_target() -> tuple[str, str] | None:
    for root in [Path("."), Path("Apple")]:
        if not root.is_dir():
            continue
        ws = sorted(root.glob("*.xcworkspace"))
        if len(ws) == 1:
            return ("workspace", str(ws[0]))
    for root in [Path("."), Path("Apple")]:
        if not root.is_dir():
            continue
        pj = sorted(root.glob("*.xcodeproj"))
        if len(pj) == 1:
            return ("project", str(pj[0]))
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="List schemes in an Xcode workspace/project.")
    ap.add_argument("--workspace", help="Explicit .xcworkspace path")
    ap.add_argument("--project", help="Explicit .xcodeproj path")
    args = ap.parse_args()

    cmd = ["xcodebuild", "-list", "-json"]
    if args.workspace:
        cmd += ["-workspace", args.workspace]
    elif args.project:
        cmd += ["-project", args.project]
    else:
        detected = find_target()
        if detected is None:
            print("FAIL: pass --workspace or --project (couldn't auto-detect)", file=sys.stderr)
            return 2
        kind, path = detected
        cmd += [f"-{kind}", path]

    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout, file=sys.stderr)
        return proc.returncode

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        print(proc.stdout)
        return 0

    schemes: list[str] = []
    if "workspace" in data:
        schemes = data["workspace"].get("schemes", [])
    elif "project" in data:
        schemes = data["project"].get("schemes", [])
    for s in schemes:
        print(s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
