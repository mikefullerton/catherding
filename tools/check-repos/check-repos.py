#!/usr/bin/env python3
"""Walk the current directory and print a status block for every git repo found.

Zero arguments. Starts at cwd. For each git repo:
  - current branch (or detached HEAD)
  - last commit sha + subject
  - dirty/clean (modified + untracked counts)
  - ahead/behind the upstream (if set)
  - stale branches whose upstream is gone
  - merged remote-only branches
  - prunable worktrees

Uses whatever remote-tracking refs are already local — does NOT `git fetch`.
So ahead/behind and remote-only results are only as fresh as the last manual
fetch in each repo.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PRUNE_DIRS = {
    "node_modules", ".venv", "venv", "__pycache__",
    "build", "dist", ".next", "target",
    ".tox", ".mypy_cache", ".pytest_cache", ".gradle",
}


def run_git(args: list[str], cwd: Path) -> tuple[str, int]:
    """Run a git command in `cwd`. Returns (stdout, returncode). Never raises.

    Strips trailing newlines only — leading whitespace is significant in some
    outputs (e.g. `git status --porcelain` where the first char of each line
    is the index state and can be a space).
    """
    try:
        p = subprocess.run(
            ["git", *args],
            cwd=cwd, capture_output=True, text=True, timeout=10,
        )
        return p.stdout.rstrip("\n"), p.returncode
    except (subprocess.TimeoutExpired, OSError) as e:
        return f"<error: {e}>", 1


def find_repos(root: Path) -> list[Path]:
    """Walk `root`, returning each directory that contains `.git/`.

    Prunes noise dirs and stops descending into a repo once found.
    """
    repos: list[Path] = []
    for dirpath, dirnames, _ in os.walk(root, followlinks=False):
        d = Path(dirpath)
        if (d / ".git").is_dir():
            repos.append(d)
            dirnames[:] = []  # don't descend into this repo
            continue
        dirnames[:] = [n for n in dirnames if n not in PRUNE_DIRS and not n.startswith(".git")]
    repos.sort()
    return repos


def branch_info(repo: Path) -> str:
    out, rc = run_git(["symbolic-ref", "--short", "-q", "HEAD"], repo)
    if rc == 0 and out:
        return out
    sha, _ = run_git(["rev-parse", "--short", "HEAD"], repo)
    return f"(detached) {sha}"


def last_commit(repo: Path) -> str:
    out, rc = run_git(["log", "-1", "--format=%h %s"], repo)
    return out if rc == 0 else "<no commits>"


def _classify(code: str) -> str:
    """Map a 2-char porcelain status code to new/modified/deleted."""
    if code == "??":
        return "new"
    chars = set(code) - {" "}
    if "A" in chars:
        return "new"
    if "D" in chars:
        return "deleted"
    return "modified"


def status_line(repo: Path) -> tuple[str, list[str]]:
    """Return (summary, labelled_files). Each file line is
    "[<kind>]  <path>" where <kind> is new | modified | deleted."""
    out, rc = run_git(["status", "--porcelain"], repo)
    if rc != 0:
        return f"error ({out})", []
    if not out:
        return "clean", []

    modified = untracked = 0
    labelled: list[str] = []
    for line in out.splitlines():
        if len(line) < 3:
            continue
        code, path = line[:2], line[3:]
        kind = _classify(code)
        if code == "??":
            untracked += 1
        else:
            modified += 1
        labelled.append(f"[{kind}]".ljust(11) + path)
    return f"dirty ({modified} modified, {untracked} untracked)", labelled


def remote_line(repo: Path) -> str:
    upstream, rc = run_git(["rev-parse", "--abbrev-ref", "@{u}"], repo)
    if rc != 0 or not upstream:
        return "(no upstream)"
    counts, rc = run_git(["rev-list", "--left-right", "--count", "HEAD...@{u}"], repo)
    if rc != 0 or not counts:
        return f"upstream {upstream} (sync unknown)"
    parts = counts.split()
    if len(parts) != 2:
        return f"upstream {upstream}"
    ahead, behind = parts
    if ahead == "0" and behind == "0":
        return f"in sync with {upstream}"
    return f"ahead {ahead}, behind {behind} ({upstream})"


def default_branch(repo: Path) -> str | None:
    out, rc = run_git(["symbolic-ref", "--short", "-q", "refs/remotes/origin/HEAD"], repo)
    if rc == 0 and out:
        return out  # e.g. "origin/main"
    for guess in ("origin/main", "origin/master"):
        _, rc = run_git(["rev-parse", "--verify", "--quiet", guess], repo)
        if rc == 0:
            return guess
    return None


def stale_branches(repo: Path) -> list[str]:
    out, rc = run_git(["branch", "-vv"], repo)
    if rc != 0:
        return []
    stale = []
    for line in out.splitlines():
        if ": gone]" in line:
            # `git branch -vv` prefixes the current branch with `*` and any
            # branch held by another worktree with `+`.
            name = line.strip().lstrip("*+ ").split()[0]
            stale.append(name)
    return stale


def merged_remote_only(repo: Path) -> list[str]:
    default = default_branch(repo)
    if default is None:
        return []
    local_out, rc = run_git(["branch", "--format=%(refname:short)"], repo)
    locals_ = set(local_out.splitlines()) if rc == 0 else set()
    merged_out, rc = run_git(["branch", "-r", "--merged", default, "--format=%(refname:short)"], repo)
    if rc != 0:
        return []
    result = []
    for ref in merged_out.splitlines():
        if ref == default:
            continue
        if ref.endswith("/HEAD"):
            continue
        # strip leading remote name (e.g. "origin/")
        if "/" not in ref:
            continue
        short = ref.split("/", 1)[1]
        if short in locals_:
            continue
        result.append(ref)
    return result


def prunable_worktrees(repo: Path) -> int:
    out, rc = run_git(["worktree", "prune", "--dry-run"], repo)
    if rc != 0 or not out:
        return 0
    return len([l for l in out.splitlines() if l.strip()])


def repo_label(repo: Path, root: Path) -> str:
    rel = repo.relative_to(root) if repo != root else Path(".")
    return f"./{rel}" if str(rel) != "." else "."


def print_repo(repo: Path, root: Path) -> bool:
    """Print the block for `repo`. Returns True if the repo is clean (nothing
    interesting printed) so the caller can roll it into a summary line."""
    label = repo_label(repo, root)

    # Validate it's actually a working repo. A `.git/` can exist without being
    # a real repo (leftover build artifacts, Xcode SourcePackages, etc.).
    _, rc = run_git(["rev-parse", "--is-inside-work-tree"], repo)
    if rc != 0:
        print(label)
        print("  error: not a valid git repository")
        print()
        return False

    branch = branch_info(repo)
    status, dirty_files = status_line(repo)
    remote = remote_line(repo)
    in_sync = remote.startswith("in sync with ")
    dirty = status != "clean"
    stale = stale_branches(repo)
    merged_ro = merged_remote_only(repo)
    prunable = prunable_worktrees(repo)

    is_clean = (
        branch == "main" and not dirty and in_sync
        and not stale and not merged_ro and not prunable
    )
    if is_clean:
        return True

    print(label)
    if branch != "main":
        print(f"  branch: {branch}")
    if dirty:
        print(f"  status: {status}")
        for line in dirty_files:
            print(f"    {line}")
    if not in_sync or dirty:
        print(f"  last:   {last_commit(repo)}")
    if not in_sync:
        print(f"  remote: {remote}")
    if stale:
        print(f"  stale branches (upstream gone): {', '.join(stale)}")
    if merged_ro:
        print(f"  merged remote-only branches: {', '.join(merged_ro)}")
    if prunable:
        print(f"  prunable worktrees: {prunable}")
    print()
    return False


def main() -> int:
    root = Path.cwd()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2

    repos = find_repos(root)
    if not repos:
        print(f"no git repos under {root}")
        return 0

    clean_count = sum(1 for repo in repos if print_repo(repo, root))
    print(f"summary: {len(repos)} repos scanned, {clean_count} clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
