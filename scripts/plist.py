#!/usr/bin/env python3
"""Pretty-print a plist file (XML or binary).

Usage:
  cc-plist path/to/Info.plist
  cc-plist path/to/Info.plist --key NSPrincipalClass    # print one key
  cc-plist path/to/Info.plist --json                    # JSON output

Wraps PlistBuddy / plutil so callers don't have to remember the syntax.
"""
from __future__ import annotations

import argparse
import json
import plistlib
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description="Pretty-print a plist file.")
    ap.add_argument("path", help="Path to the plist (XML or binary)")
    ap.add_argument("--key", help="Print just the value at this key (dot-separated path supported)")
    ap.add_argument("--json", action="store_true", help="Output JSON instead of plist text")
    args = ap.parse_args()

    p = Path(args.path)
    if not p.is_file():
        print(f"FAIL: not a file: {p}", file=sys.stderr)
        return 2

    try:
        with p.open("rb") as f:
            data = plistlib.load(f)
    except Exception as e:
        print(f"FAIL: couldn't parse plist: {e}", file=sys.stderr)
        return 1

    if args.key:
        value = data
        for part in args.key.split("."):
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                print(f"FAIL: key not found: {args.key}", file=sys.stderr)
                return 1
        if isinstance(value, (dict, list)):
            print(json.dumps(value, indent=2, default=str))
        else:
            print(value)
        return 0

    if args.json:
        print(json.dumps(data, indent=2, default=str))
    else:
        # Sort keys for stable output, similar to PlistBuddy.
        for k in sorted(data) if isinstance(data, dict) else []:
            v = data[k]
            if isinstance(v, (dict, list)):
                print(f"{k} = {json.dumps(v, default=str)}")
            else:
                print(f"{k} = {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
