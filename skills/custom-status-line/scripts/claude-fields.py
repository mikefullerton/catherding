#!/usr/bin/env python3
"""Inspect stored Claude version data in ~/claude-usage.db.

Usage:
  claude-fields.py --list                   list all versions in DB
  claude-fields.py <version>                show field paths for that version
  claude-fields.py --blob <version>         dump the full JSON blob
  claude-fields.py --diff <v1> <v2>         diff fields between two versions
  claude-fields.py --new-since <version>    fields added since a version (vs all newer)
"""
import argparse
import json
import os
import sqlite3
import sys

DB = os.path.expanduser("~/claude-usage.db")


def extract_paths(obj, prefix=""):
    paths = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else k
            paths.append(p)
            paths.extend(extract_paths(v, p))
    elif isinstance(obj, list) and obj:
        paths.extend(extract_paths(obj[0], prefix + "[]"))
    return paths


def load_blob(db, version):
    row = db.execute(
        "SELECT fields FROM claude_versions WHERE claude_version=?",
        (version,),
    ).fetchone()
    if not row:
        return None
    return json.loads(row[0])


def load_fields(db, version):
    """Return the union of field paths observed for a version.

    Prefers the stored `field_paths` column (union across all captures) so
    that conditional fields — only present in some contexts — don't appear
    as spurious additions/removals in diffs. Falls back to deriving paths
    from the first-seen blob when the column is missing (pre-migration DBs).
    """
    try:
        row = db.execute(
            "SELECT field_paths, fields FROM claude_versions "
            "WHERE claude_version=?",
            (version,),
        ).fetchone()
    except sqlite3.OperationalError:
        blob = load_blob(db, version)
        return None if blob is None else sorted(set(extract_paths(blob)))
    if not row:
        return None
    if row[0]:
        return sorted(json.loads(row[0]))
    return sorted(set(extract_paths(json.loads(row[1]))))


def main():
    ap = argparse.ArgumentParser(description="Inspect Claude version data.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--list", action="store_true")
    g.add_argument("--blob", metavar="VERSION")
    g.add_argument("--diff", nargs=2, metavar=("V1", "V2"))
    g.add_argument("--new-since", metavar="VERSION")
    g.add_argument("version", nargs="?", help="Show fields for this version")
    args = ap.parse_args()

    if not os.path.exists(DB):
        print(f"{DB} not found", file=sys.stderr)
        sys.exit(1)
    db = sqlite3.connect(DB, timeout=5)

    if args.list:
        rows = db.execute("""
            SELECT claude_version, fields_count, first_seen
            FROM claude_versions ORDER BY claude_version
        """).fetchall()
        for v, n, ts in rows:
            print(f"{v:<12} {n:>4} fields   first_seen: {ts}")

    elif args.blob:
        blob = load_blob(db, args.blob)
        if not blob:
            print(f"version not found: {args.blob}", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(blob, indent=2))

    elif args.diff:
        v1, v2 = args.diff
        p1 = load_fields(db, v1)
        p2 = load_fields(db, v2)
        if p1 is None or p2 is None:
            missing = [v for v, p in [(v1, p1), (v2, p2)] if p is None]
            print(f"not found: {missing}", file=sys.stderr)
            sys.exit(1)
        f1, f2 = set(p1), set(p2)
        added = sorted(f2 - f1)
        removed = sorted(f1 - f2)
        print(f"{v1} -> {v2}")
        if added:
            print(f"  added ({len(added)}):")
            for f in added:
                print(f"    + {f}")
        if removed:
            print(f"  removed ({len(removed)}):")
            for f in removed:
                print(f"    - {f}")
        if not added and not removed:
            print("  identical")

    elif args.new_since:
        prev_paths = load_fields(db, args.new_since)
        if prev_paths is None:
            print(f"version not found: {args.new_since}", file=sys.stderr)
            sys.exit(1)
        versions = [r[0] for r in db.execute(
            "SELECT claude_version FROM claude_versions "
            "WHERE claude_version > ? ORDER BY claude_version ASC",
            (args.new_since,),
        ).fetchall()]
        if not versions:
            print(f"no versions newer than {args.new_since}")
            return
        cur_fields = set(prev_paths)
        for v in versions:
            fields = set(load_fields(db, v))
            added = sorted(fields - cur_fields)
            removed = sorted(cur_fields - fields)
            print(f"{v}")
            if added:
                print(f"  + {len(added)}: {', '.join(added)}")
            if removed:
                print(f"  - {len(removed)}: {', '.join(removed)}")
            cur_fields = fields

    elif args.version:
        paths = load_fields(db, args.version)
        if paths is None:
            print(f"version not found: {args.version}", file=sys.stderr)
            sys.exit(1)
        print(f"{args.version}: {len(paths)} fields")
        for p in paths:
            print(f"  {p}")

    db.close()


if __name__ == "__main__":
    main()
