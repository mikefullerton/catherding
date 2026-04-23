#!/usr/bin/env python3
"""Remove a git worktree and the branch it holds.

Two modes:
  remove-worktree            # sweep: find worktrees whose upstream is gone,
                             # prompt y/n for each, remove confirmed ones.
                             # If cwd is not a git repo, walks subdirectories
                             # and sweeps every repo found.
  remove-worktree <path>     # targeted: remove the worktree at <path> and
                             # delete its branch. The owning repo is derived
                             # from <path>, so cwd does not need to be inside
                             # a git repo.

Does `git worktree remove <path>` followed by `git branch -D <branch>`
(force — matches the fact that we're cleaning up stale/abandoned work). If
git refuses to remove a dirty worktree, the error is surfaced and the branch
is NOT deleted.

Non-interactive stdin (pipe / CI) defaults every prompt to YES so scripted
use works — consistent with the repo's other installers.
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


def run_git(args: list[str], cwd: Path | None = None) -> tuple[str, str, int]:
    """Run `git <args>`. Returns (stdout, stderr, rc). Never raises."""
    try:
        p = subprocess.run(
            ["git", *args],
            cwd=cwd, capture_output=True, text=True, timeout=30,
        )
        return p.stdout.rstrip("\n"), p.stderr.rstrip("\n"), p.returncode
    except (subprocess.TimeoutExpired, OSError) as e:
        return "", f"<error: {e}>", 1


def repo_root(cwd: Path | None = None) -> Path | None:
    out, _, rc = run_git(["rev-parse", "--show-toplevel"], cwd=cwd)
    return Path(out) if rc == 0 and out else None


def find_repos(root: Path) -> list[Path]:
    """Walk `root`, returning each directory that contains `.git/`.

    Prunes noise dirs and stops descending into a repo once found.
    """
    repos: list[Path] = []
    for dirpath, dirnames, _ in os.walk(root, followlinks=False):
        d = Path(dirpath)
        if (d / ".git").is_dir():
            repos.append(d)
            dirnames[:] = []
            continue
        dirnames[:] = [n for n in dirnames if n not in PRUNE_DIRS and not n.startswith(".git")]
    repos.sort()
    return repos


def worktree_entries(root: Path) -> list[dict]:
    """Parse `git worktree list --porcelain` into dicts with keys:
    path, head, branch (None if detached), bare (bool), is_main (bool).

    The main worktree is flagged (is_main=True) but still returned so callers
    can derive the primary repo path from a `--porcelain` list taken in any
    worktree of the repo. Use `non_main(entries)` for cleanup candidates.
    """
    out, _, rc = run_git(["worktree", "list", "--porcelain"], cwd=root)
    if rc != 0:
        return []
    entries: list[dict] = []
    cur: dict = {}
    for line in out.splitlines():
        if not line:
            if cur:
                entries.append(cur)
                cur = {}
            continue
        if line.startswith("worktree "):
            cur["path"] = Path(line.split(" ", 1)[1])
        elif line.startswith("HEAD "):
            cur["head"] = line.split(" ", 1)[1]
        elif line.startswith("branch "):
            cur["branch"] = line.split(" ", 1)[1].removeprefix("refs/heads/")
        elif line == "bare":
            cur["bare"] = True
        elif line == "detached":
            cur["branch"] = None
    if cur:
        entries.append(cur)
    for i, e in enumerate(entries):
        e["is_main"] = (i == 0)
    return entries


def non_main(entries: list[dict]) -> list[dict]:
    """Filter to entries safe to consider for removal."""
    return [
        e for e in entries
        if not e.get("is_main") and not e.get("bare") and e.get("branch")
    ]


def upstream_gone(root: Path, branch: str) -> bool:
    out, _, rc = run_git(
        ["for-each-ref", "--format=%(upstream:track)", f"refs/heads/{branch}"],
        cwd=root,
    )
    return rc == 0 and out.strip() == "[gone]"


def is_dirty(worktree_path: Path) -> bool:
    out, _, rc = run_git(["status", "--porcelain"], cwd=worktree_path)
    return rc == 0 and bool(out.strip())


def confirm(prompt: str) -> bool:
    if not sys.stdin.isatty():
        print(f"{prompt} [Y/n] yes (non-interactive)")
        return True
    try:
        ans = input(f"{prompt} [Y/n] ").strip().lower()
    except EOFError:
        return False
    return ans in ("", "y", "yes")


def remove_one(root: Path, path: Path, branch: str) -> bool:
    """Remove worktree at `path` (in repo `root`) and force-delete `branch`.
    Returns True on full success; prints progress and any git errors."""
    _, err, rc = run_git(["worktree", "remove", str(path)], cwd=root)
    if rc != 0:
        print(f"  git worktree remove failed: {err}", file=sys.stderr)
        return False
    print(f"  removed worktree: {path}")

    _, err, rc = run_git(["branch", "-D", branch], cwd=root)
    if rc != 0:
        print(f"  git branch -D {branch} failed: {err}", file=sys.stderr)
        return False
    print(f"  deleted branch: {branch}")
    return True


def describe(entry: dict, root: Path) -> str:
    dirty = " [dirty]" if is_dirty(entry["path"]) else ""
    gone = " [upstream gone]" if upstream_gone(root, entry["branch"]) else ""
    return f"{entry['path']}  (branch: {entry['branch']}){gone}{dirty}"


def sweep_repo(root: Path) -> tuple[int, int, int]:
    """Sweep stale-upstream worktrees in `root`. Returns (removed, skipped,
    failed). Prints nothing if there's nothing stale in this repo."""
    stale = [e for e in non_main(worktree_entries(root)) if upstream_gone(root, e["branch"])]
    if not stale:
        return 0, 0, 0

    print(f"# {root}")
    removed = skipped = failed = 0
    for entry in stale:
        print(describe(entry, root))
        if not confirm("  remove?"):
            skipped += 1
            continue
        if remove_one(root, entry["path"], entry["branch"]):
            removed += 1
        else:
            failed += 1
    print()
    return removed, skipped, failed


def mode_targeted(target: Path) -> int:
    """Remove the single worktree at `target` regardless of cwd. The owning
    repo is discovered by asking git from inside the target."""
    probe = target if target.is_dir() else target.parent
    if not probe.is_dir():
        print(f"error: {target} does not exist", file=sys.stderr)
        return 2

    entries = worktree_entries(probe)
    if not entries:
        print(f"error: {target} is not inside a git worktree", file=sys.stderr)
        return 2

    root = entries[0]["path"]  # main worktree = primary repo root
    target_abs = target.resolve()
    match = next(
        (e for e in non_main(entries) if _resolve(e["path"]) == target_abs),
        None,
    )
    if match is None:
        print(
            f"error: {target} is not a removable worktree of {root}",
            file=sys.stderr,
        )
        return 2

    print(describe(match, root))
    if not confirm("  remove this worktree and force-delete its branch?"):
        print("aborted.")
        return 1
    return 0 if remove_one(root, match["path"], match["branch"]) else 1


def _resolve(p: Path) -> Path | None:
    try:
        return p.resolve()
    except FileNotFoundError:
        return None


def mode_sweep_cwd() -> int:
    cwd = Path.cwd()
    root = repo_root(cwd)

    if root is not None:
        removed, skipped, failed = sweep_repo(root)
    else:
        repos = find_repos(cwd)
        if not repos:
            print(f"no git repos at or below {cwd}")
            return 0
        removed = skipped = failed = 0
        for r in repos:
            r_removed, r_skipped, r_failed = sweep_repo(r)
            removed += r_removed
            skipped += r_skipped
            failed += r_failed

    if removed == skipped == failed == 0:
        print("no worktrees with gone upstream — nothing to sweep")
        return 0
    print(f"summary: {removed} removed, {skipped} skipped, {failed} failed")
    return 0 if failed == 0 else 1


def main(argv: list[str]) -> int:
    if len(argv) == 0:
        return mode_sweep_cwd()
    if len(argv) == 1:
        return mode_targeted(Path(argv[0]))

    print("usage: remove-worktree [<path>]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
