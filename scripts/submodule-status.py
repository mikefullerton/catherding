#!/usr/bin/env python3
"""Per-submodule diagnostic: recorded SHA vs checked-out SHA vs origin HEAD.

Usage:
  cc-submodule-status [--fetch]

For every submodule in the current repo, prints:
  path | recorded (parent index) | checked-out (HEAD in submodule) | drift | behind-origin

- drift = recorded != checked-out
- behind-origin = commits on the submodule's default-branch remote not in HEAD

Pass --fetch to run `git fetch` inside each submodule first (otherwise
behind-origin is only as fresh as the last fetch).

Exit non-zero if any submodule has drift or is behind origin.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], cwd: str | None = None) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return proc.returncode, proc.stdout.strip()


def submodule_paths() -> list[str]:
    rc, out = run(["git", "config", "--file", ".gitmodules", "--get-regexp", r"submodule\..*\.path"])
    if rc != 0 or not out:
        return []
    return [line.split(None, 1)[1] for line in out.splitlines() if line]


def recorded_sha(path: str) -> str:
    rc, out = run(["git", "ls-tree", "HEAD", path])
    if rc != 0 or not out:
        return "?"
    parts = out.split()
    return parts[2] if len(parts) >= 3 else "?"


def checked_out_sha(path: str) -> str:
    rc, out = run(["git", "rev-parse", "HEAD"], cwd=path)
    return out if rc == 0 else "?"


def default_branch(path: str) -> str:
    rc, out = run(["git", "symbolic-ref", "refs/remotes/origin/HEAD"], cwd=path)
    if rc == 0 and out.startswith("refs/remotes/origin/"):
        return out.removeprefix("refs/remotes/origin/")
    return "main"


def commits_behind(path: str, branch: str) -> str:
    rc, out = run(["git", "rev-list", "--count", f"HEAD..origin/{branch}"], cwd=path)
    return out if rc == 0 else "?"


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="cc-submodule-status",
        description="Per-submodule recorded/checked-out/origin SHA diagnostic.",
    )
    parser.add_argument("--fetch", action="store_true", help="git fetch inside each submodule first")
    args = parser.parse_args()

    if not Path(".gitmodules").is_file():
        print("cc-submodule-status: no .gitmodules in cwd")
        return 0

    paths = submodule_paths()
    if not paths:
        print("cc-submodule-status: no submodules registered")
        return 0

    drift_count = 0
    behind_count = 0
    rows: list[tuple[str, str, str, str, str]] = []
    for path in paths:
        if args.fetch:
            run(["git", "fetch", "--quiet"], cwd=path)
        recorded = recorded_sha(path)
        current = checked_out_sha(path)
        branch = default_branch(path)
        behind = commits_behind(path, branch)
        drift = "DRIFT" if recorded != current and recorded != "?" and current != "?" else ""
        if drift:
            drift_count += 1
        if behind.isdigit() and int(behind) > 0:
            behind_count += 1
        rows.append((path, recorded[:12], current[:12], drift, behind))

    path_w = max(len(r[0]) for r in rows)
    print(f"{'path':<{path_w}}  {'recorded':<12}  {'checked-out':<12}  drift  behind-origin")
    for path, rec, cur, drift, behind in rows:
        print(f"{path:<{path_w}}  {rec:<12}  {cur:<12}  {drift:<5}  {behind}")

    print(f"did: {len(rows)} submodule(s) | drift {drift_count} | behind-origin {behind_count}")
    return 1 if (drift_count or behind_count) else 0


if __name__ == "__main__":
    sys.exit(main())
