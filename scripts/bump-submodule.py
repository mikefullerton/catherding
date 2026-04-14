#!/usr/bin/env python3
"""Bump a git submodule to the tip of its origin/<default> branch.

Usage:
  cc-bump-submodule <submodule-path>

Steps:
  1. `git -C <submodule> fetch origin`
  2. `git -C <submodule> checkout origin/<default>`
  3. `git add <submodule>` at the super-repo (stages the new SHA).

Caller is expected to commit the submodule bump themselves (e.g. with
`cc-commit-push "Bump X submodule to main"`), so that they control the
commit message.

Prints a `did:` summary with old→new SHAs.
"""
import argparse
import subprocess
import sys
from pathlib import Path


def run(cmd, cwd=None, check=True, capture=True):
    result = subprocess.run(cmd, cwd=cwd, capture_output=capture, text=True, timeout=120)
    if check and result.returncode != 0:
        print(f"FAIL: {' '.join(cmd)}", file=sys.stderr)
        print(result.stderr or result.stdout, file=sys.stderr)
        sys.exit(result.returncode)
    return result.stdout.strip(), result.returncode


def default_branch(path: Path) -> str:
    out, rc = run(
        ["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
        cwd=str(path), check=False,
    )
    if rc == 0 and out.startswith("origin/"):
        return out[len("origin/"):]
    return "main"


def main() -> int:
    ap = argparse.ArgumentParser(description="Bump a git submodule to origin/<default>.")
    ap.add_argument("submodule", help="Path to the submodule (relative to repo root)")
    args = ap.parse_args()

    sub = Path(args.submodule)
    if not sub.is_dir():
        print(f"FAIL: {sub} does not exist", file=sys.stderr)
        return 2
    if not (sub / ".git").exists():
        print(f"FAIL: {sub} is not a git submodule checkout", file=sys.stderr)
        return 2

    before, _ = run(["git", "rev-parse", "HEAD"], cwd=str(sub))
    default = default_branch(sub)

    run(["git", "fetch", "origin"], cwd=str(sub))
    run(["git", "checkout", f"origin/{default}"], cwd=str(sub))

    after, _ = run(["git", "rev-parse", "HEAD"], cwd=str(sub))

    if before == after:
        print(f"did: {sub} already at {after[:12]}")
        return 0

    run(["git", "add", str(sub)])
    print(f"did: {sub} {before[:12]} -> {after[:12]} (staged)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
