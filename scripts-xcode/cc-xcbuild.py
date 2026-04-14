#!/usr/bin/env python3
"""Run `xcodebuild build` or `test` with compact output.

Usage:
  cc-xcbuild <scheme>                        # build, auto-detect workspace/project
  cc-xcbuild <scheme> --test                 # test instead of build
  cc-xcbuild <scheme> --workspace path.xcworkspace
  cc-xcbuild <scheme> --project path.xcodeproj
  cc-xcbuild <scheme> --configuration Release

Default auto-detection:
  - If exactly one .xcworkspace exists in CWD or Apple/, use it.
  - Else if exactly one .xcodeproj exists in CWD or Apple/, use it.
  - Else --workspace/--project is required.

On success, prints: `did: build|test <scheme> ok`.
On failure, prints up to the first 5 `error:` lines from xcodebuild and exits
non-zero — no more scrolling through thousands of lines of build log.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def find_build_target() -> tuple[str, str] | None:
    """Return ('workspace'|'project', path) for a single auto-detected artifact."""
    roots = [Path("."), Path("Apple")]
    for root in roots:
        if not root.is_dir():
            continue
        ws = sorted(root.glob("*.xcworkspace"))
        if len(ws) == 1:
            return ("workspace", str(ws[0]))
    for root in roots:
        if not root.is_dir():
            continue
        pj = sorted(root.glob("*.xcodeproj"))
        if len(pj) == 1:
            return ("project", str(pj[0]))
    # Deeper workspace search — typical for this stack.
    for root in [Path("Apple")]:
        if root.is_dir():
            ws = sorted(root.glob("*.xcworkspace"))
            if len(ws) == 1:
                return ("workspace", str(ws[0]))
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Run xcodebuild with compact output.")
    ap.add_argument("scheme", help="Scheme name")
    ap.add_argument("--test", action="store_true", help="Run `test` instead of `build`")
    ap.add_argument("--configuration", default="Debug")
    ap.add_argument("--workspace", help="Explicit .xcworkspace path")
    ap.add_argument("--project", help="Explicit .xcodeproj path")
    ap.add_argument("--derived-data", help="Derived data path (default: Xcode default)")
    ap.add_argument("--clean", action="store_true", help="Run `clean` before build to flush stale caches")
    args = ap.parse_args()

    cmd = ["xcodebuild"]
    if args.workspace:
        cmd += ["-workspace", args.workspace]
    elif args.project:
        cmd += ["-project", args.project]
    else:
        detected = find_build_target()
        if detected is None:
            print("FAIL: pass --workspace or --project (couldn't auto-detect)", file=sys.stderr)
            return 2
        kind, path = detected
        cmd += [f"-{kind}", path]
    cmd += ["-scheme", args.scheme, "-configuration", args.configuration]
    if args.derived_data:
        cmd += ["-derivedDataPath", args.derived_data]
    if args.clean:
        cmd.append("clean")
    cmd.append("test" if args.test else "build")

    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    out = proc.stdout + proc.stderr
    if proc.returncode == 0:
        action = "test" if args.test else "build"
        print(f"did: {action} {args.scheme} ({args.configuration}) ok")
        return 0

    # Failure path — surface the first few error lines with surrounding
    # "in target 'X' from project 'Y'" context so the caller knows which
    # subproject failed (referenced projects are common in this stack).
    lines = out.splitlines()
    errors_with_context: list[str] = []
    for i, ln in enumerate(lines):
        if "error:" not in ln:
            continue
        # Look ahead up to 3 lines for the matching "in target ... from project ..." annotation.
        context = ""
        for j in range(i + 1, min(i + 4, len(lines))):
            stripped = lines[j].strip()
            if stripped.startswith("(in target '"):
                context = " " + stripped
                break
        errors_with_context.append(ln + context)
    print("FAIL: xcodebuild", file=sys.stderr)
    for ln in errors_with_context[:5]:
        print(f"  {ln}", file=sys.stderr)
    if not errors_with_context:
        tail = lines[-20:]
        for ln in tail:
            print(f"  {ln}", file=sys.stderr)
    if len(errors_with_context) > 5:
        print(f"  … and {len(errors_with_context) - 5} more errors (run xcodebuild directly for full log)", file=sys.stderr)
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
