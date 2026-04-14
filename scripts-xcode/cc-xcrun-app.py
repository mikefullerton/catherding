#!/usr/bin/env python3
"""Build, launch, and tail logs for a macOS app target.

Usage:
  cc-xcrun-app <scheme>                 # build + launch + tail logs for 10s
  cc-xcrun-app <scheme> --tail 30       # tail logs for 30s after launch
  cc-xcrun-app <scheme> --no-build      # skip build; just launch latest binary
  cc-xcrun-app <scheme> --grep pattern  # filter tailed logs by pattern

Steps:
  1. pkill the running instance (no-op if none).
  2. xcodebuild build (unless --no-build).
  3. open the .app from DerivedData.
  4. `log show` for the process, grepped to interesting categories.

Prints the filtered log lines and a `did:` summary.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path


def run(cmd, check=True, capture=True, timeout=600):
    result = subprocess.run(cmd, capture_output=capture, text=True, timeout=timeout)
    if check and result.returncode != 0:
        print(f"FAIL: {' '.join(cmd)}", file=sys.stderr)
        print(result.stderr or result.stdout, file=sys.stderr)
        sys.exit(result.returncode)
    return result.stdout.strip(), result.returncode


def find_app(scheme: str) -> Path | None:
    """Find the most recently built .app for the scheme in DerivedData."""
    dd = Path.home() / "Library" / "Developer" / "Xcode" / "DerivedData"
    if not dd.is_dir():
        return None
    candidates = sorted(
        dd.glob(f"*/Build/Products/Debug/{scheme}.app"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def main() -> int:
    ap = argparse.ArgumentParser(description="Build, launch, and tail logs for a macOS app target.")
    ap.add_argument("scheme", help="Scheme/app name (also used to resolve the .app in DerivedData)")
    ap.add_argument("--tail", type=int, default=10, help="Seconds to tail logs after launch (default: 10)")
    ap.add_argument("--no-build", action="store_true", help="Skip build; launch latest binary")
    ap.add_argument("--grep", help="Case-insensitive substring to filter tailed logs")
    ap.add_argument("--workspace", help="Explicit .xcworkspace (forwarded to cc-xcbuild)")
    ap.add_argument("--project", help="Explicit .xcodeproj (forwarded to cc-xcbuild)")
    args = ap.parse_args()

    # 1. pkill
    subprocess.run(["pkill", "-x", args.scheme], capture_output=True)
    time.sleep(1)

    # 2. build
    if not args.no_build:
        cc_xcbuild = shutil.which("cc-xcbuild")
        if cc_xcbuild:
            cmd = [cc_xcbuild, args.scheme]
            if args.workspace:
                cmd += ["--workspace", args.workspace]
            elif args.project:
                cmd += ["--project", args.project]
            proc = subprocess.run(cmd)
            if proc.returncode != 0:
                return proc.returncode
        else:
            print("WARN: cc-xcbuild not in PATH; skipping build step", file=sys.stderr)

    # 3. open the .app
    app = find_app(args.scheme)
    if app is None:
        print(f"FAIL: couldn't find {args.scheme}.app in DerivedData", file=sys.stderr)
        return 2
    run(["open", str(app)])

    # 4. tail logs
    time.sleep(args.tail)
    log_cmd = [
        "/usr/bin/log", "show",
        "--predicate", f'process == "{args.scheme}"',
        "--info",
        "--last", f"{args.tail + 2}s",
    ]
    proc = subprocess.run(log_cmd, capture_output=True, text=True, timeout=30)
    lines = proc.stdout.splitlines()
    if args.grep:
        pattern = args.grep.lower()
        lines = [ln for ln in lines if pattern in ln.lower()]
    # Drop the standard header row.
    lines = [ln for ln in lines if ln.strip() and not ln.startswith("Timestamp ")]
    for ln in lines[-50:]:
        print(ln)

    print(f"did: built + launched {args.scheme} | {len(lines)} log line(s) after filter")
    return 0


if __name__ == "__main__":
    sys.exit(main())
