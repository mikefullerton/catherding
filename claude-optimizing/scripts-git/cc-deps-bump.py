#!/usr/bin/env python3
"""Bump last-sha in dependencies.json to the current HEAD of a dependency clone.

Usage:
  cc-deps-bump <name> [--verify]
  cc-deps-bump --all [--verify]

Reads `dependencies.json` at the repo root, reads the current HEAD SHA
of `dependencies/<name>/`, writes it back to that entry's `last-sha`.

- `<name>` is the clone directory name (repo URL basename minus `.git`).
- `--all` bumps every entry.
- `--verify` runs `cc-deps-verify --fetch` after writing; exits non-zero
  if verification fails.

Exit codes: 0 success; 1 verify failure; 2 usage / manifest error.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def run(cmd: list[str], cwd: str | Path | None = None) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return proc.returncode, proc.stdout.strip()


def clone_name(repo_url: str) -> str:
    basename = repo_url.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1]
    return basename.removesuffix(".git")


def load_manifest(repo_root: Path) -> list[dict[str, Any]]:
    manifest = repo_root / "dependencies.json"
    if not manifest.is_file():
        print(f"cc-deps-bump: no dependencies.json at {repo_root}", file=sys.stderr)
        raise SystemExit(2)
    try:
        data = json.loads(manifest.read_text())
    except json.JSONDecodeError as e:
        print(f"cc-deps-bump: dependencies.json parse error: {e}", file=sys.stderr)
        raise SystemExit(2)
    if not isinstance(data, list):
        print("cc-deps-bump: dependencies.json must be a JSON array", file=sys.stderr)
        raise SystemExit(2)
    return data


def write_manifest(repo_root: Path, entries: list[dict[str, Any]]) -> None:
    path = repo_root / "dependencies.json"
    path.write_text(json.dumps(entries, indent=2) + "\n")


def head_sha(clone: Path) -> str:
    rc, out = run(["git", "rev-parse", "HEAD"], cwd=clone)
    if rc != 0 or not out:
        raise RuntimeError(f"could not read HEAD in {clone}")
    return out


def bump_entry(entry: dict[str, Any], repo_root: Path) -> tuple[str, str, str]:
    repo = entry.get("repo", "")
    name = clone_name(repo)
    clone = repo_root / "dependencies" / name
    if not clone.is_dir() or not (clone / ".git").exists():
        raise RuntimeError(f"clone missing at dependencies/{name}/")
    old = entry.get("last-sha", "?")
    new = head_sha(clone)
    entry["last-sha"] = new
    return name, old, new


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="cc-deps-bump",
        description="Update last-sha in dependencies.json to the clone's current HEAD.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("name", nargs="?", help="clone-directory name (repo URL basename minus .git)")
    group.add_argument("--all", action="store_true", help="bump every entry")
    parser.add_argument("--verify", action="store_true", help="run cc-deps-verify --fetch after writing")
    args = parser.parse_args()

    repo_root = Path.cwd()
    entries = load_manifest(repo_root)

    targets: list[dict[str, Any]]
    if args.all:
        targets = entries
    else:
        targets = [e for e in entries if clone_name(e.get("repo", "")) == args.name]
        if not targets:
            print(f"cc-deps-bump: no entry matches name {args.name!r}", file=sys.stderr)
            return 2

    changed = 0
    for entry in targets:
        try:
            name, old, new = bump_entry(entry, repo_root)
        except RuntimeError as e:
            print(f"cc-deps-bump: {e}", file=sys.stderr)
            return 2
        if old == new:
            print(f"{name}  unchanged  {old[:12]}")
        else:
            changed += 1
            print(f"{name}  bumped     {old[:12]} -> {new[:12]}")

    if changed:
        write_manifest(repo_root, entries)
    print(f"did: {len(targets)} entr(y|ies) | changed {changed}")

    if args.verify:
        verify_cmd = ["cc-deps-verify", "--fetch"]
        if not args.all and args.name:
            verify_cmd += ["--name", args.name]
        rc = subprocess.run(verify_cmd).returncode
        if rc != 0:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
