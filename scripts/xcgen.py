#!/usr/bin/env python3
"""Run `xcodegen generate` in every directory under the repo that has a project.yml.

Usage:
  cc-xcgen             # find and regenerate every project.yml-backed xcodeproj
  cc-xcgen --list      # just list what would be regenerated
  cc-xcgen <path>...   # regenerate the given project.yml dirs only

Prints `did:` with the count of projects regenerated.
"""
import argparse
import subprocess
import sys
from pathlib import Path


SKIP_SEGMENTS = {".build", ".swiftpm", "DerivedData", "build"}


def find_project_yml(root: Path) -> list[Path]:
    hits: list[Path] = []
    for p in root.rglob("project.yml"):
        if any(seg in SKIP_SEGMENTS for seg in p.parts):
            continue
        hits.append(p)
    hits.sort()
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description="Regenerate every project.yml-backed xcodeproj in the repo.")
    ap.add_argument("--list", action="store_true", help="List the project.yml files, don't regenerate.")
    ap.add_argument("paths", nargs="*", help="Specific project.yml dirs to regenerate (default: all).")
    args = ap.parse_args()

    if args.paths:
        ymls = []
        for p in args.paths:
            path = Path(p)
            if path.is_dir():
                candidate = path / "project.yml"
                if candidate.is_file():
                    ymls.append(candidate)
                else:
                    print(f"WARN: no project.yml in {path}", file=sys.stderr)
            elif path.is_file() and path.name == "project.yml":
                ymls.append(path)
            else:
                print(f"WARN: not a project.yml or dir: {p}", file=sys.stderr)
    else:
        ymls = find_project_yml(Path("."))

    if not ymls:
        print("no project.yml files found", file=sys.stderr)
        return 1

    if args.list:
        for y in ymls:
            print(y)
        return 0

    for yml in ymls:
        proc = subprocess.run(["xcodegen", "generate"], cwd=str(yml.parent), capture_output=True, text=True)
        if proc.returncode != 0:
            print(f"FAIL: xcodegen in {yml.parent}", file=sys.stderr)
            print(proc.stderr or proc.stdout, file=sys.stderr)
            return proc.returncode

    print(f"did: regenerated {len(ymls)} xcodeproj(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
