#!/usr/bin/env python3
"""Bump one or more git submodules to the tip of origin/<default>.

Usage:
  cc-bump-submodule <submodule-path>...

Steps for each submodule:
  1. `git -C <submodule> fetch origin`
  2. `git -C <submodule> checkout origin/<default>`
  3. `git add <submodule>` at the super-repo (stages the new SHA).

Caller is expected to commit the bumps themselves (e.g. with
`cc-commit-push "Bump submodules to main"`), so that they control the
commit message.

Prints a `did:` summary with old→new SHAs for each.
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


def bump_one(sub: Path) -> tuple[str, str, bool]:
    """Returns (before, after, staged)."""
    before, _ = run(["git", "rev-parse", "HEAD"], cwd=str(sub))
    default = default_branch(sub)
    run(["git", "fetch", "origin"], cwd=str(sub))
    run(["git", "checkout", f"origin/{default}"], cwd=str(sub))
    after, _ = run(["git", "rev-parse", "HEAD"], cwd=str(sub))
    if before == after:
        return before, after, False
    run(["git", "add", str(sub)])
    return before, after, True


def main() -> int:
    ap = argparse.ArgumentParser(description="Bump one or more git submodules to origin/<default>.")
    ap.add_argument("submodules", nargs="+", help="Submodule paths (relative to repo root)")
    args = ap.parse_args()

    bumped = unchanged = 0
    parts: list[str] = []
    for sub_str in args.submodules:
        sub = Path(sub_str)
        if not sub.is_dir():
            print(f"FAIL: {sub} does not exist", file=sys.stderr)
            return 2
        if not (sub / ".git").exists():
            print(f"FAIL: {sub} is not a git submodule checkout", file=sys.stderr)
            return 2
        before, after, staged = bump_one(sub)
        if staged:
            parts.append(f"{sub} {before[:12]}->{after[:12]}")
            bumped += 1
        else:
            parts.append(f"{sub} unchanged at {after[:12]}")
            unchanged += 1

    summary = " | ".join(parts)
    print(f"did: bumped {bumped} | unchanged {unchanged} | {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
