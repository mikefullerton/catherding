#!/usr/bin/env python3
"""Materialize dependencies from dependencies.json into dependencies/<name>/.

Usage:
  cc-deps-sync [--update | --lock | --ci] [--bump] [--name NAME]

Reads `dependencies.json` at the repo root. For each entry, ensures
`dependencies/<name>/` exists (cloning if missing), then places it at
the right state:

  --update (default)  Checkout `branch`; `git pull --ff-only origin <branch>`.
  --lock              Detached HEAD at the pin: `tag` if set, else `last-sha`.
  --ci                Use `ci-guidance`: mode=sha|branch|tag. Falls back
                      to --lock behavior when ci-guidance is absent.

Pass --bump after --update to write the resolved HEAD SHA back to
`last-sha` in `dependencies.json` (same effect as `cc-deps-bump <name>`).

Pass --name to operate on a single entry by clone-directory name.

`dependencies/` is created if missing. It MUST be in .gitignore — this
script does not modify it.

Exit non-zero if any clone/fetch/checkout fails.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def run(cmd: list[str], cwd: str | Path | None = None, quiet: bool = False) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if proc.returncode != 0 and not quiet:
        print(f"cc-deps-sync: command failed: {' '.join(cmd)}", file=sys.stderr)
        if proc.stderr.strip():
            print(proc.stderr.strip(), file=sys.stderr)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def clone_name(repo_url: str) -> str:
    basename = repo_url.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1]
    return basename.removesuffix(".git")


def load_manifest(repo_root: Path) -> list[dict[str, Any]]:
    manifest = repo_root / "dependencies.json"
    if not manifest.is_file():
        print(f"cc-deps-sync: no dependencies.json at {repo_root}", file=sys.stderr)
        return []
    try:
        data = json.loads(manifest.read_text())
    except json.JSONDecodeError as e:
        print(f"cc-deps-sync: dependencies.json parse error: {e}", file=sys.stderr)
        raise SystemExit(2)
    if not isinstance(data, list):
        print("cc-deps-sync: dependencies.json must be a JSON array", file=sys.stderr)
        raise SystemExit(2)
    return data


def write_manifest(repo_root: Path, entries: list[dict[str, Any]]) -> None:
    (repo_root / "dependencies.json").write_text(json.dumps(entries, indent=2) + "\n")


def ensure_clone(entry: dict[str, Any], deps_dir: Path) -> Path:
    repo = entry["repo"]
    name = clone_name(repo)
    clone = deps_dir / name
    if clone.is_dir() and (clone / ".git").exists():
        return clone
    deps_dir.mkdir(parents=True, exist_ok=True)
    rc, _, _ = run(["git", "clone", "--quiet", repo, str(clone)])
    if rc != 0:
        raise SystemExit(1)
    return clone


def fetch(clone: Path) -> None:
    run(["git", "fetch", "--quiet", "--tags", "origin"], cwd=clone)


def checkout_branch(clone: Path, branch: str) -> None:
    rc, _, _ = run(["git", "checkout", branch], cwd=clone, quiet=True)
    if rc != 0:
        rc, _, _ = run(["git", "checkout", "-B", branch, f"origin/{branch}"], cwd=clone)
        if rc != 0:
            raise SystemExit(1)
    rc, _, _ = run(["git", "pull", "--ff-only", "--quiet", "origin", branch], cwd=clone)
    if rc != 0:
        raise SystemExit(1)


def detach_at(clone: Path, ref: str) -> None:
    rc, _, _ = run(["git", "checkout", "--quiet", "--detach", ref], cwd=clone)
    if rc != 0:
        raise SystemExit(1)


def apply_mode(entry: dict[str, Any], clone: Path, mode: str) -> str:
    branch = entry["branch"]
    last_sha = entry.get("last-sha", "")
    tag = entry.get("tag")
    ci = entry.get("ci-guidance") or {}

    if mode == "update":
        checkout_branch(clone, branch)
        label = f"on {branch}"
    elif mode == "lock":
        ref = tag if tag else last_sha
        detach_at(clone, ref)
        label = f"detached at {('tag ' + tag) if tag else last_sha[:12]}"
    elif mode == "ci":
        ci_mode = ci.get("mode")
        if ci_mode == "sha":
            detach_at(clone, ci["sha"])
            label = f"detached at {ci['sha'][:12]} (ci-guidance sha)"
        elif ci_mode == "branch":
            checkout_branch(clone, ci["branch"])
            label = f"on {ci['branch']} (ci-guidance branch)"
        elif ci_mode == "tag":
            detach_at(clone, ci["tag"])
            label = f"detached at tag {ci['tag']} (ci-guidance tag)"
        else:
            ref = tag if tag else last_sha
            detach_at(clone, ref)
            label = f"detached at {('tag ' + tag) if tag else last_sha[:12]} (ci fallback to lock)"
    else:
        raise ValueError(f"unknown mode: {mode}")
    return label


def head_sha(clone: Path) -> str:
    rc, out, _ = run(["git", "rev-parse", "HEAD"], cwd=clone)
    if rc != 0:
        raise SystemExit(1)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="cc-deps-sync",
        description="Materialize dependencies from dependencies.json into dependencies/<name>/.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--update", action="store_const", dest="mode", const="update", help="checkout branch + ff-only pull (default)")
    group.add_argument("--lock", action="store_const", dest="mode", const="lock", help="detached HEAD at pin (tag or last-sha)")
    group.add_argument("--ci", action="store_const", dest="mode", const="ci", help="use ci-guidance, fall back to --lock")
    parser.add_argument("--bump", action="store_true", help="after --update, write the new HEAD SHA to last-sha")
    parser.add_argument("--name", help="operate on a single entry by clone-directory name")
    args = parser.parse_args()

    mode = args.mode or "update"
    if args.bump and mode != "update":
        print("cc-deps-sync: --bump is only valid with --update", file=sys.stderr)
        return 2

    repo_root = Path.cwd()
    entries = load_manifest(repo_root)
    if not entries:
        return 0

    filtered = entries
    if args.name:
        filtered = [e for e in entries if clone_name(e.get("repo", "")) == args.name]
        if not filtered:
            print(f"cc-deps-sync: no entry matches name {args.name!r}", file=sys.stderr)
            return 2

    deps_dir = repo_root / "dependencies"
    changed_sha = 0
    for entry in filtered:
        name = clone_name(entry["repo"])
        clone = ensure_clone(entry, deps_dir)
        fetch(clone)
        label = apply_mode(entry, clone, mode)
        sha = head_sha(clone)
        print(f"{name}  {sha[:12]}  {label}")
        if args.bump and mode == "update":
            old = entry.get("last-sha", "")
            if sha != old:
                entry["last-sha"] = sha
                changed_sha += 1

    if changed_sha:
        write_manifest(repo_root, entries)
        print(f"bumped {changed_sha} last-sha field(s) in dependencies.json")

    print(f"did: {len(filtered)} entr(y|ies) | mode {mode}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
