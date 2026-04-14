#!/usr/bin/env python3
"""Print the most recent .app or .framework path for a scheme in DerivedData.

Usage:
  cc-app-path <scheme>                # latest <scheme>.app
  cc-app-path <scheme> --kind framework
  cc-app-path <scheme> --configuration Release

Walks ~/Library/Developer/Xcode/DerivedData and returns the most recently
modified product matching the scheme. Empty stdout + non-zero exit if not found.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description="Find a built product in DerivedData.")
    ap.add_argument("scheme", help="Scheme / product name (without extension)")
    ap.add_argument("--kind", choices=["app", "framework", "bundle", "xctest"], default="app")
    ap.add_argument("--configuration", default="Debug")
    args = ap.parse_args()

    dd = Path.home() / "Library" / "Developer" / "Xcode" / "DerivedData"
    if not dd.is_dir():
        print(f"FAIL: no DerivedData at {dd}", file=sys.stderr)
        return 1

    pattern = f"*/Build/Products/{args.configuration}/{args.scheme}.{args.kind}"
    candidates = sorted(dd.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        print(f"FAIL: no {args.scheme}.{args.kind} in {args.configuration} build products", file=sys.stderr)
        return 1
    print(candidates[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
