#!/usr/bin/env python3
"""Process a single git repo: fetch, sync heads, clean branches.

Usage:
    python3 process-repo.py [--dry-run] <repo-path>

Output (stdout): JSON object with repo status and remaining issues.
Step-by-step progress goes to stderr.
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

def git(repo, *args):
    """Run a git command in *repo* and return (stdout, returncode)."""
    r = subprocess.run(
        ["git", "-C", repo, *args],
        capture_output=True, text=True,
    )
    return r.stdout.strip(), r.returncode


def git_ok(repo, *args):
    """Run a git command and return stdout. Ignore failures."""
    out, _ = git(repo, *args)
    return out


def log(msg):
    print(msg, file=sys.stderr)


# ── repo info ────────────────────────────────────────────────────────────

def default_branch(repo):
    ref = git_ok(repo, "symbolic-ref", "refs/remotes/origin/HEAD")
    if ref:
        return ref.split("/")[-1]
    for candidate in ("main", "master"):
        out, rc = git(repo, "rev-parse", "--verify", f"refs/heads/{candidate}")
        if rc == 0:
            return candidate
    return "main"


def current_branch(repo):
    return git_ok(repo, "rev-parse", "--abbrev-ref", "HEAD") or None


def upstream_ref(repo, branch):
    """Return upstream tracking ref for branch, or None."""
    out, rc = git(repo, "rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}")
    return out if rc == 0 else None


# ── step: fetch ──────────────────────────────────────────────────────────

def step_fetch(repo, dry_run):
    log("  Fetching remote...")
    if dry_run:
        log("  [dry-run] Would fetch")
        return
    _, rc = git(repo, "fetch", "--prune")
    if rc == 0:
        log("  Fetched")
    else:
        log("  Fetch failed (no remote?)")


# ── step: uncommitted changes ────────────────────────────────────────────

def step_uncommitted(repo):
    out = git_ok(repo, "status", "--porcelain")
    if not out:
        log("  Checking for uncommitted changes: none")
        return []
    files = []
    for line in out.splitlines():
        path = line[3:]
        if GENERATED_DIRS.search(path):
            continue
        files.append({"status": line[:2], "path": path})
    log(f"  Checking for uncommitted changes: {len(files)} found")
    return files


# ── step: pull / push ───────────────────────────────────────────────────

def step_sync(repo, cur, has_uncommitted, dry_run):
    """Pull and push to sync heads. Returns (needs_push, needs_pull)."""
    if not cur:
        log("  Detached HEAD — skipping sync")
        return False, False

    up = upstream_ref(repo, cur)
    if not up:
        log("  No upstream tracking branch")
        return False, False

    # check behind (needs pull)
    behind_str, _ = git(repo, "rev-list", "--count", f"{cur}..{up}")
    behind = int(behind_str) if behind_str.isdigit() else 0

    # check ahead (needs push)
    ahead_str, _ = git(repo, "rev-list", "--count", f"{up}..{cur}")
    ahead = int(ahead_str) if ahead_str.isdigit() else 0

    needs_pull = behind > 0
    needs_push = ahead > 0

    # pull
    if needs_pull:
        if has_uncommitted:
            log(f"  Needs pull: {behind} commit(s) behind — skipped (uncommitted changes)")
        elif dry_run:
            log(f"  [dry-run] Would pull {behind} commit(s)")
        else:
            _, rc = git(repo, "pull", "--ff-only")
            if rc == 0:
                log(f"  Pulled {behind} commit(s)")
                needs_pull = False
            else:
                log(f"  Pull failed (not fast-forward?) — skipped")
    else:
        log("  Pull: up to date")

    # push
    if needs_push:
        if dry_run:
            log(f"  [dry-run] Would push {ahead} commit(s)")
        else:
            _, rc = git(repo, "push")
            if rc == 0:
                log(f"  Pushed {ahead} commit(s)")
                needs_push = False
            else:
                log(f"  Push failed — skipped")
    else:
        log("  Push: up to date")

    return needs_push, needs_pull


# ── step: worktrees ─────────────────────────────────────────────────────

def step_worktrees(repo, dflt, dry_run):
    """Prune dangling refs, remove finished worktrees, flag dirty ones."""
    counts = {"worktree_refs_pruned": 0, "worktrees_removed": 0}
    dirty = []

    # prune dangling
    prune_out = git_ok(repo, "worktree", "prune", "--dry-run")
    dangling = prune_out.splitlines() if prune_out else []
    if dangling:
        if dry_run:
            log(f"  [dry-run] Would prune {len(dangling)} dangling worktree ref(s)")
        else:
            git(repo, "worktree", "prune")
            log(f"  Pruned {len(dangling)} dangling worktree ref(s)")
        counts["worktree_refs_pruned"] = len(dangling)

    # list worktrees
    out = git_ok(repo, "worktree", "list", "--porcelain")
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

    # skip main worktree
    if worktrees:
        worktrees = worktrees[1:]

    for wt in worktrees:
        path = wt.get("path", "")
        branch = wt.get("branch", "")
        if not os.path.isdir(path):
            continue

        _, rc = git(repo, "merge-base", "--is-ancestor", branch, dflt)
        is_merged = rc == 0
        status = git_ok(path, "status", "--porcelain")

        if status:
            log(f"  Worktree {path} ({branch}): dirty — needs attention")
            dirty.append({
                "path": path,
                "branch": branch,
                "merged": is_merged,
                "status": status,
            })
        elif is_merged:
            if dry_run:
                log(f"  [dry-run] Would remove worktree {path} ({branch}, merged)")
            else:
                git(repo, "worktree", "remove", path)
                git(repo, "branch", "-d", branch)
                log(f"  Removed worktree {path} ({branch}, merged)")
            counts["worktrees_removed"] += 1
        else:
            log(f"  Worktree {path} ({branch}): clean, not merged — keeping")

    return counts, dirty


# ── step: branches ──────────────────────────────────────────────────────

SPECIAL_BRANCHES = {"gh-pages", "github-pages"}


def is_special_branch(name):
    """Branches that should never be flagged for deletion."""
    return name in SPECIAL_BRANCHES


def step_branches(repo, dflt, cur, dry_run):
    """Delete gone/merged branches, flag all remaining for decision."""
    counts = {"stale_branches_deleted": 0, "merged_branches_deleted": 0}
    flagged = []

    # all local branches
    all_out = git_ok(repo, "branch", "--format=%(refname:short)")
    all_branches = [b for b in all_out.splitlines() if b and b != dflt]

    if not all_branches:
        log("  Branches: only default branch")
        return counts, flagged, []

    log(f"  Branches: {len(all_branches)} non-default ({', '.join(all_branches)})")

    # gone branches (remote deleted)
    vv_out = git_ok(repo, "branch", "-vv")
    gone = set()
    for line in vv_out.splitlines():
        line = line.strip()
        if ": gone]" in line:
            branch = line.lstrip("* ").split()[0]
            gone.add(branch)

    for branch in sorted(gone):
        if is_special_branch(branch):
            log(f"  Evaluating branch {branch}: stale (remote gone) — special, keeping")
            continue
        log(f"  Evaluating branch {branch}: stale (remote gone)")
        if dry_run:
            log(f"    [dry-run] Would delete")
        else:
            _, rc = git(repo, "branch", "-d", branch)
            if rc == 0:
                log(f"    Deleted stale branch {branch}")
            else:
                log(f"    Safe delete failed for {branch} — keeping")
        counts["stale_branches_deleted"] += 1

    # merged branches
    merged_out = git_ok(repo, "branch", "--merged", dflt)
    merged_set = {b.strip().lstrip("* ") for b in merged_out.splitlines()}

    for branch in sorted(merged_set):
        if not branch or branch == dflt or branch == cur or branch in gone:
            continue
        if is_special_branch(branch):
            log(f"  Evaluating branch {branch}: merged into {dflt} — special, keeping")
            continue
        log(f"  Evaluating branch {branch}: merged into {dflt}")
        if dry_run:
            log(f"    [dry-run] Would delete")
        else:
            _, rc = git(repo, "branch", "-d", branch)
            if rc == 0:
                log(f"    Deleted merged branch {branch}")
            else:
                log(f"    Safe delete failed for {branch} — keeping")
        counts["merged_branches_deleted"] += 1

    # flag all remaining non-default, non-special branches for interactive decision
    ref_out = git_ok(
        repo, "for-each-ref", "--sort=-committerdate",
        "--format=%(refname:short)\t%(committerdate:unix)\t%(committerdate:relative)\t%(subject)",
        "refs/heads/",
    )
    for line in ref_out.splitlines():
        parts = line.split("\t", 3)
        if len(parts) < 4:
            continue
        name, ts_str, relative, subject = parts
        if name == dflt or name in merged_set or name in gone:
            continue
        if is_special_branch(name):
            log(f"  Evaluating branch {name}: special — keeping")
            continue
        ahead = git_ok(repo, "rev-list", "--count", f"{dflt}..{name}")
        stat = git_ok(repo, "diff", "--stat", f"{dflt}...{name}")
        stat_summary = stat.splitlines()[-1].strip() if stat else ""
        log(f"  Evaluating branch {name}: unmerged ({relative}), {ahead} commits ahead — needs attention")
        flagged.append({
            "branch": name,
            "last_commit_age": relative,
            "last_commit_subject": subject,
            "commits_ahead": int(ahead) if ahead else 0,
            "diff_stat": stat_summary,
        })

    # remote-only branches (exist on origin but not locally)
    local_out = git_ok(repo, "branch", "--format=%(refname:short)")
    local_set = {b for b in local_out.splitlines() if b}
    remote_out = git_ok(repo, "branch", "-r", "--format=%(refname:short)")
    for rref in remote_out.splitlines():
        if not rref or not rref.startswith("origin/"):
            continue
        name = rref[len("origin/"):]
        if name == dflt or name == "HEAD" or name in local_set or name in gone:
            continue
        if is_special_branch(name):
            log(f"  Remote branch {name}: special — keeping")
            continue
        # check if merged into default
        _, rc = git(repo, "merge-base", "--is-ancestor", rref, dflt)
        if rc == 0:
            log(f"  Remote branch {name}: merged into {dflt}")
            if dry_run:
                log(f"    [dry-run] Would delete remote branch")
            else:
                _, drc = git(repo, "push", "origin", "--delete", name)
                if drc == 0:
                    log(f"    Deleted remote branch {name}")
                else:
                    log(f"    Failed to delete remote branch {name}")
            counts["merged_branches_deleted"] += 1
        else:
            ahead = git_ok(repo, "rev-list", "--count", f"{dflt}..{rref}")
            stat = git_ok(repo, "diff", "--stat", f"{dflt}...{rref}")
            stat_summary = stat.splitlines()[-1].strip() if stat else ""
            relative = git_ok(repo, "log", "-1", "--format=%cr", rref)
            subject = git_ok(repo, "log", "-1", "--format=%s", rref)
            log(f"  Remote branch {name}: unmerged ({relative}), {ahead} commits ahead — needs attention")
            flagged.append({
                "branch": name,
                "remote_only": True,
                "last_commit_age": relative,
                "last_commit_subject": subject,
                "commits_ahead": int(ahead) if ahead else 0,
                "diff_stat": stat_summary,
            })

    # remaining branches after cleanup
    remaining_out = git_ok(repo, "branch", "--format=%(refname:short)")
    remaining = [b for b in remaining_out.splitlines() if b and b != dflt]

    return counts, flagged, remaining


# ── main ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Process a single git repo")
    parser.add_argument("repo", help="Path to the git repository")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    repo = os.path.abspath(args.repo)
    dry_run = args.dry_run

    dflt = default_branch(repo)
    cur = current_branch(repo)

    # fetch
    step_fetch(repo, dry_run)

    # uncommitted
    uncommitted = step_uncommitted(repo)

    # pull / push
    needs_push, needs_pull = step_sync(repo, cur, len(uncommitted) > 0, dry_run)

    # worktrees
    wt_counts, dirty_wt = step_worktrees(repo, dflt, dry_run)

    # branches
    br_counts, flagged_branches, remaining_branches = step_branches(repo, dflt, cur, dry_run)

    # combine counts
    counts = {**wt_counts, **br_counts}

    # collect interactive items
    items = []
    if uncommitted:
        items.append({"type": "uncommitted", "files": uncommitted})
    if needs_pull:
        items.append({"type": "needs_pull"})
    if needs_push:
        items.append({"type": "needs_push"})
    for b in flagged_branches:
        items.append({"type": "branch", **b})
    for wt in dirty_wt:
        items.append({"type": "dirty_worktree", **wt})

    result = {
        "repo": os.path.basename(repo),
        "path": repo,
        "default_branch": dflt,
        "branch": cur,
        "needs_push": needs_push,
        "needs_pull": needs_pull,
        "branches": remaining_branches,
        "auto_fixed": counts,
        "items": items,
    }

    json.dump(result, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
