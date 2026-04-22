#!/usr/bin/env python3
"""Per-dependency diagnostic: last-sha reachable, tag consistent, ci-guidance valid.

Usage:
  cc-deps-verify [--fetch] [--name NAME]

Reads `dependencies.json` at the repo root and checks each entry:

  1. `dependencies/<name>/` clone exists
  2. `last-sha` resolves in the clone
  3. `last-sha` is an ancestor of `origin/<branch>`
  4. If `tag` is set, tag resolves and matches `last-sha`
  5. If `ci-guidance` is set, mode matches the required sibling field

Pass --fetch to run `git fetch` inside each clone first (authoritative
check; otherwise reachability is only as fresh as the last fetch).

Pass --name NAME to verify a single entry (matched against the clone
directory name, which is the repo URL basename minus `.git`).

Exit non-zero if any check fails.
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


def load_manifest(repo_root: Path) -> list[dict[str, Any]]:
    manifest = repo_root / "dependencies.json"
    if not manifest.is_file():
        print(f"cc-deps-verify: no dependencies.json at {repo_root}", file=sys.stderr)
        return []
    try:
        data = json.loads(manifest.read_text())
    except json.JSONDecodeError as e:
        print(f"cc-deps-verify: dependencies.json parse error: {e}", file=sys.stderr)
        raise SystemExit(2)
    if not isinstance(data, list):
        print("cc-deps-verify: dependencies.json must be a JSON array", file=sys.stderr)
        raise SystemExit(2)
    return data


def clone_name(repo_url: str) -> str:
    basename = repo_url.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1]
    return basename.removesuffix(".git")


def check_entry(entry: dict[str, Any], repo_root: Path, do_fetch: bool) -> list[str]:
    failures: list[str] = []
    repo = entry.get("repo")
    branch = entry.get("branch")
    last_sha = entry.get("last-sha")
    tag = entry.get("tag")
    ci = entry.get("ci-guidance")

    if not repo or not branch or not last_sha:
        failures.append("missing required field (repo, branch, last-sha)")
        return failures

    name = clone_name(repo)
    clone = repo_root / "dependencies" / name
    if not clone.is_dir() or not (clone / ".git").exists():
        failures.append(f"clone missing at dependencies/{name}/")
        return failures

    if do_fetch:
        run(["git", "fetch", "--quiet", "--tags"], cwd=clone)

    rc, _ = run(["git", "cat-file", "-e", f"{last_sha}^{{commit}}"], cwd=clone)
    if rc != 0:
        failures.append(f"last-sha {last_sha[:12]} does not resolve in clone")
        return failures

    rc, _ = run(["git", "rev-parse", "--verify", f"refs/remotes/origin/{branch}"], cwd=clone)
    if rc != 0:
        failures.append(f"origin/{branch} does not exist (did you --fetch?)")
        return failures

    rc, _ = run(["git", "merge-base", "--is-ancestor", last_sha, f"origin/{branch}"], cwd=clone)
    if rc != 0:
        failures.append(f"last-sha {last_sha[:12]} is NOT an ancestor of origin/{branch}")

    if tag is not None:
        rc, tag_sha = run(["git", "rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}"], cwd=clone)
        if rc != 0:
            failures.append(f"tag {tag!r} does not resolve in clone")
        elif tag_sha != last_sha:
            failures.append(f"tag {tag!r} resolves to {tag_sha[:12]}, not last-sha {last_sha[:12]}")

    if ci is not None:
        if not isinstance(ci, dict):
            failures.append("ci-guidance must be an object")
        else:
            mode = ci.get("mode")
            if mode not in ("sha", "branch", "tag"):
                failures.append(f"ci-guidance.mode must be 'sha', 'branch', or 'tag' (got {mode!r})")
            elif mode not in ci:
                failures.append(f"ci-guidance.mode={mode!r} requires sibling field {mode!r}")
            elif mode == "sha":
                rc, _ = run(["git", "cat-file", "-e", f"{ci['sha']}^{{commit}}"], cwd=clone)
                if rc != 0:
                    failures.append(f"ci-guidance.sha {ci['sha'][:12]} does not resolve in clone")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="cc-deps-verify",
        description="Verify dependencies.json pins are reachable and internally consistent.",
    )
    parser.add_argument("--fetch", action="store_true", help="git fetch inside each clone first")
    parser.add_argument("--name", help="verify a single entry by clone-directory name")
    args = parser.parse_args()

    repo_root = Path.cwd()
    entries = load_manifest(repo_root)
    if not entries:
        return 0

    filtered = entries
    if args.name:
        filtered = [e for e in entries if clone_name(e.get("repo", "")) == args.name]
        if not filtered:
            print(f"cc-deps-verify: no entry matches name {args.name!r}", file=sys.stderr)
            return 2

    name_w = max(len(clone_name(e.get("repo", "?"))) for e in filtered)
    failed = 0
    for entry in filtered:
        name = clone_name(entry.get("repo", "?"))
        failures = check_entry(entry, repo_root, args.fetch)
        if failures:
            failed += 1
            for f in failures:
                print(f"{name:<{name_w}}  FAIL  {f}")
        else:
            print(f"{name:<{name_w}}  OK")

    print(f"did: {len(filtered)} entr(y|ies) | failed {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
