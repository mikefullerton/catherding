#!/usr/bin/env python3
"""List or delete Xcode DerivedData directories by name pattern.

Usage:
  cc-clean-dd                       # list every top-level DerivedData entry + size
  cc-clean-dd <pattern>             # list entries matching *pattern* (dry run)
  cc-clean-dd <pattern> --yes       # actually delete matching entries
  cc-clean-dd --older-than 30       # filter to entries whose mtime is older than N days

Default is always dry-run — prints entry name, size (GiB), and mtime age.
Pass --yes to perform the deletion. Combine with --older-than to limit
by last-modified age.

DerivedData root: ~/Library/Developer/Xcode/DerivedData/
"""
from __future__ import annotations

import argparse
import fnmatch
import shutil
import sys
import time
from pathlib import Path

DD_ROOT = Path.home() / "Library" / "Developer" / "Xcode" / "DerivedData"


def dir_size_bytes(path: Path) -> int:
    total = 0
    for p in path.rglob("*"):
        try:
            if p.is_file() and not p.is_symlink():
                total += p.stat().st_size
        except OSError:
            continue
    return total


def fmt_gib(n: int) -> str:
    return f"{n / (1024 ** 3):.2f} GiB"


def fmt_age(mtime: float) -> str:
    days = (time.time() - mtime) / 86400
    return f"{days:.0f}d"


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="cc-clean-dd",
        description="List or delete Xcode DerivedData directories.",
    )
    parser.add_argument("pattern", nargs="?", help="fnmatch pattern (default: * = all)")
    parser.add_argument("--yes", action="store_true", help="Actually delete (default is dry-run)")
    parser.add_argument("--older-than", type=int, metavar="DAYS", help="Only match entries older than N days")
    args = parser.parse_args()

    if not DD_ROOT.is_dir():
        print(f"cc-clean-dd: no DerivedData root at {DD_ROOT}", file=sys.stderr)
        return 1

    pattern = args.pattern or "*"
    if "*" not in pattern and "?" not in pattern:
        pattern = f"*{pattern}*"

    cutoff = None
    if args.older_than is not None:
        cutoff = time.time() - args.older_than * 86400

    entries: list[tuple[Path, int, float]] = []
    for entry in sorted(DD_ROOT.iterdir()):
        if not entry.is_dir():
            continue
        if not fnmatch.fnmatch(entry.name, pattern):
            continue
        try:
            mtime = entry.stat().st_mtime
        except OSError:
            continue
        if cutoff is not None and mtime >= cutoff:
            continue
        entries.append((entry, dir_size_bytes(entry), mtime))

    if not entries:
        print(f"cc-clean-dd: no entries match {pattern!r}")
        return 0

    name_width = max(len(e.name) for e, _, _ in entries)
    mode = "DELETE" if args.yes else "dry-run"
    total_bytes = 0
    print(f"[{mode}] DerivedData entries matching {pattern!r}:")
    for entry, size, mtime in entries:
        total_bytes += size
        print(f"  {entry.name:<{name_width}}  {fmt_gib(size):>10}  {fmt_age(mtime):>6}")

    if not args.yes:
        print(f"did: {len(entries)} entry/ies, {fmt_gib(total_bytes)} — dry run (use --yes to delete)")
        return 0

    deleted = 0
    freed = 0
    for entry, size, _ in entries:
        try:
            shutil.rmtree(entry)
            deleted += 1
            freed += size
        except OSError as exc:
            print(f"  failed: {entry.name}: {exc}", file=sys.stderr)
    print(f"did: deleted {deleted}/{len(entries)} entry/ies, freed {fmt_gib(freed)}")
    return 0 if deleted == len(entries) else 1


if __name__ == "__main__":
    sys.exit(main())
