#!/usr/bin/env python3
"""Print resolved Xcode build-setting values for a scheme.

Usage:
  cc-xcsetting <scheme> <key> [<key> ...]
               [--workspace PATH | --project PATH]
               [--configuration NAME]
               [--target NAME]

Wraps `xcodebuild -showBuildSettings` and filters for the requested keys,
so you don't grep the pbxproj by hand. Auto-detects a single *.xcworkspace
or *.xcodeproj in the current directory (first workspace wins).

Output: one `KEY = VALUE` line per key requested. Unknown keys print
`KEY = <not set>` and cause a non-zero exit.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def detect_container(explicit_workspace: str | None, explicit_project: str | None) -> list[str]:
    if explicit_workspace:
        return ["-workspace", explicit_workspace]
    if explicit_project:
        return ["-project", explicit_project]
    workspaces = sorted(Path(".").glob("*.xcworkspace"))
    if workspaces:
        return ["-workspace", str(workspaces[0])]
    projects = sorted(Path(".").glob("*.xcodeproj"))
    if projects:
        return ["-project", str(projects[0])]
    print("cc-xcsetting: no *.xcworkspace or *.xcodeproj in cwd", file=sys.stderr)
    sys.exit(1)


def fetch_settings(container: list[str], scheme: str, configuration: str | None, target: str | None) -> dict[str, str]:
    cmd = ["xcodebuild", "-showBuildSettings", "-scheme", scheme, *container]
    if configuration:
        cmd += ["-configuration", configuration]
    if target:
        cmd += ["-target", target]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        print(f"cc-xcsetting: xcodebuild failed (exit {proc.returncode})", file=sys.stderr)
        sys.exit(proc.returncode)

    settings: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        stripped = line.strip()
        if " = " not in stripped:
            continue
        key, _, value = stripped.partition(" = ")
        if key and key.replace("_", "").isalnum():
            settings[key] = value
    return settings


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="cc-xcsetting",
        description="Print resolved Xcode build-setting values for a scheme.",
    )
    parser.add_argument("scheme", help="Scheme name")
    parser.add_argument("keys", nargs="+", help="Build setting keys (e.g. PRODUCT_BUNDLE_IDENTIFIER)")
    parser.add_argument("--workspace", help="Path to .xcworkspace")
    parser.add_argument("--project", help="Path to .xcodeproj")
    parser.add_argument("--configuration", help="Build configuration (Debug/Release/...)")
    parser.add_argument("--target", help="Target filter")
    args = parser.parse_args()

    container = detect_container(args.workspace, args.project)
    settings = fetch_settings(container, args.scheme, args.configuration, args.target)

    missing = 0
    for key in args.keys:
        if key in settings:
            print(f"{key} = {settings[key]}")
        else:
            print(f"{key} = <not set>")
            missing += 1
    if missing:
        print(f"did: resolved {len(args.keys) - missing}/{len(args.keys)} keys | {missing} missing", file=sys.stderr)
        return 1
    print(f"did: resolved {len(args.keys)} key(s) for scheme {args.scheme}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
