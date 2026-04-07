#!/usr/bin/env python3
"""repo-tools clean — deterministic phase.

Discovers git repos, runs all safe auto-fixes (prune worktrees, delete
gone/merged branches, remove finished worktrees), pushes unpushed commits,
then outputs a JSON manifest of repos that still need interactive decisions.

Usage:
    python3 clean.py [--depth N] [--dry-run] [ROOT]

Output (stdout): JSON object with keys:
    repos_scanned  — int
    auto_fixed     — dict of counts
    interactive    — list of {repo, path, default_branch, branch, items: [...]}

All human-readable progress goes to stderr so stdout stays pure JSON.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time

GENERATED_DIRS = re.compile(
    r"(^|/)(node_modules|\.build|dist|__pycache__|\.venv|\.egg-info)/"
)

# ── helpers ──────────────────────────────────────────────────────────────

def git(repo, *args, check=False):
    """Run a git command in *repo* and return stdout (stripped)."""
    r = subprocess.run(
        ["git", "-C", repo, *args],
        capture_output=True, text=True,
    )
    if check and r.returncode != 0:
        raise subprocess.CalledProcessError(r.returncode, r.args, r.stdout, r.stderr)
    return r.stdout.strip()


def log(msg):
    print(msg, file=sys.stderr)


def default_branch(repo):
    ref = git(repo, "symbolic-ref", "refs/remotes/origin/HEAD")
    if ref:
        return ref.split("/")[-1]
    for candidate in ("main", "master"):
        if git(repo, "rev-parse", "--verify", f"refs/heads/{candidate}"):
            return candidate
    return "main"


def current_branch(repo):
    return git(repo, "rev-parse", "--abbrev-ref", "HEAD") or None


# ── discovery ────────────────────────────────────────────────────────────

def discover_repos(root, depth):
    r = subprocess.run(
        ["find", root, "-maxdepth", str(depth), "-name", ".git", "-type", "d"],
        capture_output=True, text=True,
    )
    raw = sorted(r.stdout.strip().splitlines()) if r.stdout.strip() else []
    repos = []
    for dot_git in raw:
        if "/worktrees/" in dot_git:
            continue
        repo_dir = os.path.dirname(os.path.abspath(dot_git))
        if os.path.basename(repo_dir).endswith("-tests"):
            continue
        repo = os.path.dirname(os.path.abspath(dot_git))
        # skip if nested inside another repo's .git
        if any(repo.startswith(os.path.join(existing, ".git")) for existing in repos):
            continue
        repos.append(repo)
    return repos


# ── scanners ─────────────────────────────────────────────────────────────

def scan_dangling_worktrees(repo):
    out = git(repo, "worktree", "prune", "--dry-run")
    return out.splitlines() if out else []


def scan_gone_branches(repo):
    out = git(repo, "branch", "-vv")
    gone = []
    for line in out.splitlines():
        line = line.strip()
        if ": gone]" in line:
            branch = line.lstrip("* ").split()[0]
            gone.append(branch)
    return gone


def scan_merged_branches(repo, dflt, cur):
    out = git(repo, "branch", "--merged", dflt)
    merged = []
    for line in out.splitlines():
        name = line.strip().lstrip("* ")
        if name and name != dflt and name != cur:
            merged.append(name)
    return merged


def scan_worktrees(repo, dflt):
    out = git(repo, "worktree", "list", "--porcelain")
    worktrees = []
    current = {}
    for line in out.splitlines():
        if line.startswith("worktree "):
            current = {"path": line.split(" ", 1)[1]}
        elif line.startswith("branch "):
            current["branch"] = line.split("/")[-1]
        elif line == "":
            if current:
                worktrees.append(current)
            current = {}
    if current:
        worktrees.append(current)

    # first entry is the main worktree — skip it
    if worktrees:
        worktrees = worktrees[1:]

    finished = []
    dirty = []
    for wt in worktrees:
        path = wt.get("path", "")
        branch = wt.get("branch", "")
        if not os.path.isdir(path):
            # orphaned — will be handled by prune
            continue
        is_merged = git(repo, "merge-base", "--is-ancestor", branch, dflt) == "" and \
            subprocess.run(
                ["git", "-C", repo, "merge-base", "--is-ancestor", branch, dflt],
                capture_output=True
            ).returncode == 0
        status = git(path, "status", "--porcelain")
        if status:
            dirty.append({
                "path": path,
                "branch": branch,
                "merged": is_merged,
                "status": status,
            })
        elif is_merged:
            finished.append(wt)
    return finished, dirty


def scan_uncommitted(repo):
    out = git(repo, "status", "--porcelain")
    if not out:
        return []
    files = []
    for line in out.splitlines():
        path = line[3:]
        if GENERATED_DIRS.search(path):
            continue
        files.append({"status": line[:2], "path": path})
    return files


def scan_inactive_branches(repo, dflt, cur):
    out = git(
        repo, "for-each-ref", "--sort=-committerdate",
        "--format=%(refname:short)\t%(committerdate:unix)\t%(committerdate:relative)\t%(subject)",
        "refs/heads/",
    )
    merged_out = git(repo, "branch", "--merged", dflt)
    merged_set = {b.strip().lstrip("* ") for b in merged_out.splitlines()}

    cutoff = time.time() - 30 * 86400
    inactive = []
    for line in out.splitlines():
        parts = line.split("\t", 3)
        if len(parts) < 4:
            continue
        name, ts_str, relative, subject = parts
        if name == dflt or name == cur or name in merged_set:
            continue
        try:
            ts = int(ts_str)
        except ValueError:
            continue
        if ts < cutoff:
            ahead = git(repo, "rev-list", "--count", f"{dflt}..{name}")
            stat = git(repo, "diff", "--stat", f"{dflt}...{name}")
            stat_summary = stat.splitlines()[-1].strip() if stat else ""
            inactive.append({
                "branch": name,
                "last_commit_age": relative,
                "last_commit_subject": subject,
                "commits_ahead": int(ahead) if ahead else 0,
                "diff_stat": stat_summary,
            })
    return inactive


def scan_unpushed(repo, cur):
    """Check if current branch has commits not pushed to origin."""
    if not cur:
        return False
    upstream = git(repo, "rev-parse", "--abbrev-ref", f"{cur}@{{upstream}}")
    if not upstream:
        # no upstream — check if remote exists at all
        remote_url = git(repo, "remote", "get-url", "origin")
        return bool(remote_url)
    count = git(repo, "rev-list", "--count", f"{upstream}..{cur}")
    try:
        return int(count) > 0
    except ValueError:
        return False


# ── fixers ───────────────────────────────────────────────────────────────

def fix_prune_worktrees(repo, dry_run):
    dangling = scan_dangling_worktrees(repo)
    n = len(dangling)
    if n == 0:
        return 0
    if dry_run:
        log(f"  [dry-run] Would prune {n} dangling worktree ref(s)")
    else:
        git(repo, "worktree", "prune")
        log(f"  Pruned {n} dangling worktree ref(s)")
    return n


def fix_finished_worktrees(repo, finished, dry_run):
    count = 0
    for wt in finished:
        path, branch = wt["path"], wt["branch"]
        if dry_run:
            log(f"  [dry-run] Would remove worktree {path} (branch {branch}, merged)")
        else:
            git(repo, "worktree", "remove", path)
            git(repo, "branch", "-d", branch)
            log(f"  Removed worktree {path} (branch {branch}, merged)")
        count += 1
    return count


def fix_gone_branches(repo, gone, dry_run):
    count = 0
    for branch in gone:
        if dry_run:
            log(f"  [dry-run] Would delete stale branch {branch} (remote gone)")
        else:
            git(repo, "branch", "-d", branch)
            log(f"  Deleted stale branch {branch} (remote gone)")
        count += 1
    return count


def fix_merged_branches(repo, merged, dry_run):
    count = 0
    for branch in merged:
        if dry_run:
            log(f"  [dry-run] Would delete merged branch {branch}")
        else:
            git(repo, "branch", "-d", branch)
            log(f"  Deleted merged branch {branch}")
        count += 1
    return count


def fix_push(repo, cur, dry_run):
    if not scan_unpushed(repo, cur):
        return 0
    if dry_run:
        log(f"  [dry-run] Would push unpushed commits on {cur}")
    else:
        r = subprocess.run(
            ["git", "-C", repo, "push"],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            # try setting upstream
            r2 = subprocess.run(
                ["git", "-C", repo, "push", "-u", "origin", cur],
                capture_output=True, text=True,
            )
            if r2.returncode == 0:
                log(f"  Pushed {cur} (set upstream)")
            else:
                log(f"  Push failed for {cur}: {r2.stderr.strip()}")
                return 0
        else:
            log(f"  Pushed {cur}")
    return 1


# ── main ─────────────────────────────────────────────────────────────────

def process_repo(repo, dry_run):
    dflt = default_branch(repo)
    cur = current_branch(repo)
    name = os.path.basename(repo)

    log(f"\n--- {repo} ({cur or 'detached'}) ---")

    # fetch
    git(repo, "fetch", "--prune")

    # scans
    gone = scan_gone_branches(repo)
    merged = scan_merged_branches(repo, dflt, cur)
    finished_wt, dirty_wt = scan_worktrees(repo, dflt)
    uncommitted = scan_uncommitted(repo)
    inactive = scan_inactive_branches(repo, dflt, cur)

    # auto-fix
    counts = {
        "worktree_refs_pruned": fix_prune_worktrees(repo, dry_run),
        "worktrees_removed": fix_finished_worktrees(repo, finished_wt, dry_run),
        "stale_branches_deleted": fix_gone_branches(repo, gone, dry_run),
        "merged_branches_deleted": fix_merged_branches(repo, merged, dry_run),
        "pushes": fix_push(repo, cur, dry_run),
    }

    total_fixed = sum(counts.values())
    if total_fixed == 0:
        log("  No auto-fixable issues")

    # collect interactive items
    items = []
    if uncommitted:
        items.append({"type": "uncommitted", "files": uncommitted})
    for b in inactive:
        items.append({"type": "inactive_branch", **b})
    for wt in dirty_wt:
        items.append({"type": "dirty_worktree", **wt})

    return counts, {
        "repo": name,
        "path": repo,
        "default_branch": dflt,
        "branch": cur,
        "items": items,
    }


def main():
    parser = argparse.ArgumentParser(description="repo-tools deterministic cleanup")
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    repos = discover_repos(root, args.depth)

    if not repos:
        log(f"No git repositories found within depth {args.depth} of {root}")
        json.dump({"repos_scanned": 0, "auto_fixed": {}, "interactive": []}, sys.stdout, indent=2)
        return

    if len(repos) > 1:
        log(f"Found {len(repos)} repositories:")
        for r in repos:
            log(f"  {r}")

    totals = {
        "worktree_refs_pruned": 0,
        "worktrees_removed": 0,
        "stale_branches_deleted": 0,
        "merged_branches_deleted": 0,
        "pushes": 0,
    }
    interactive_list = []

    all_repos = []

    for repo in repos:
        counts, repo_info = process_repo(repo, args.dry_run)
        for k, v in counts.items():
            totals[k] += v
        all_repos.append(repo_info)

    # summary to stderr
    prefix = "[dry-run] " if args.dry_run else ""
    total_fixed = sum(totals.values())
    log(f"\n{'=' * 40}")
    log(f"{prefix}Auto-fixed across {len(repos)} repo(s): {total_fixed} action(s)")
    for k, v in totals.items():
        if v:
            log(f"  {k}: {v}")
    needs_input = [r for r in all_repos if r["items"]]
    if needs_input:
        n = sum(len(r["items"]) for r in needs_input)
        log(f"{prefix}{n} item(s) across {len(needs_input)} repo(s) need interactive decisions")
    else:
        log("All clean — nothing needs interactive input")

    # JSON to stdout
    json.dump({
        "repos_scanned": len(repos),
        "auto_fixed": totals,
        "repos": all_repos,
    }, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
