#!/usr/bin/env python3
"""repo-cleaner clean — discover repos, process in parallel, report results.

Usage:
    python3 clean.py [--depth N] [--dry-run] [--workers N] [ROOT]

Output (stdout): JSON manifest with all results.
Per-repo progress streams to stderr as repos complete.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

GENERATED_DIRS = re.compile(
    r"(^|/)(node_modules|\.build|dist|__pycache__|\.venv|\.egg-info)/"
)
SPECIAL_BRANCHES = {"gh-pages", "github-pages"}

# thread-safe stderr output
_print_lock = threading.Lock()


def log(msg):
    with _print_lock:
        print(msg, file=sys.stderr, flush=True)


# ── git helpers ─────────────────────────────────────────────────────────

def git(repo, *args):
    r = subprocess.run(
        ["git", "-C", repo, *args],
        capture_output=True, text=True,
    )
    return r.stdout.strip(), r.returncode


def git_ok(repo, *args):
    out, _ = git(repo, *args)
    return out


# ── repo info ───────────────────────────────────────────────────────────

def default_branch(repo):
    ref = git_ok(repo, "symbolic-ref", "refs/remotes/origin/HEAD")
    if ref:
        return ref.split("/")[-1]
    for candidate in ("main", "master"):
        _, rc = git(repo, "rev-parse", "--verify", f"refs/heads/{candidate}")
        if rc == 0:
            return candidate
    return "main"


def current_branch(repo):
    return git_ok(repo, "rev-parse", "--abbrev-ref", "HEAD") or None


def upstream_ref(repo, branch):
    out, rc = git(repo, "rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}")
    return out if rc == 0 else None


def is_special_branch(name):
    return name in SPECIAL_BRANCHES


def is_merged_or_squashed(repo, dflt, branch_ref):
    """Check if branch is merged into dflt via any merge strategy.

    Checks in order:
    1. Regular merge (is-ancestor)
    2. Zero commits ahead (branch is at or behind dflt)
    3. Empty diff (all changes already in dflt, e.g., rebase merge)
    4. Squash merge (commit-tree + cherry detection)
    """
    # regular merge
    _, rc = git(repo, "merge-base", "--is-ancestor", branch_ref, dflt)
    if rc == 0:
        return True
    # zero commits ahead — nothing unique on the branch
    ahead = git_ok(repo, "rev-list", "--count", f"{dflt}..{branch_ref}")
    if ahead.isdigit() and int(ahead) == 0:
        return True
    # empty diff — all changes are already in dflt
    diff = git_ok(repo, "diff", f"{dflt}...{branch_ref}")
    if not diff:
        return True
    # squash merge detection
    merge_base = git_ok(repo, "merge-base", dflt, branch_ref)
    if not merge_base:
        return False
    tree = git_ok(repo, "rev-parse", f"{branch_ref}^{{tree}}")
    if not tree:
        return False
    dangling = git_ok(repo, "commit-tree", tree, "-p", merge_base, "-m", "_")
    if not dangling:
        return False
    cherry = git_ok(repo, "cherry", dflt, dangling)
    return cherry.startswith("-")


# ── discovery ───────────────────────────────────────────────────────────

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
        repo = os.path.dirname(os.path.abspath(dot_git))
        name = os.path.basename(repo)
        if name.endswith("-test") or name.endswith("-tests"):
            continue
        if any(repo.startswith(os.path.join(existing, ".git")) for existing in repos):
            continue
        repos.append(repo)
    return repos


def quick_check(repo):
    """Fast local-only pre-check. Returns list of reasons, or empty if clean."""
    reasons = []

    status, _ = git(repo, "status", "--porcelain")
    if status:
        lines = [l for l in status.splitlines()
                 if not any(s in l for s in ("node_modules/", ".build/", "dist/", "__pycache__/", ".venv/", ".egg-info/"))]
        if lines:
            reasons.append(f"{len(lines)} uncommitted")

    dflt = None
    ref, rc = git(repo, "symbolic-ref", "refs/remotes/origin/HEAD")
    if rc == 0 and ref:
        dflt = ref.split("/")[-1]
    else:
        for candidate in ("main", "master"):
            _, rc = git(repo, "rev-parse", "--verify", f"refs/heads/{candidate}")
            if rc == 0:
                dflt = candidate
                break
    if not dflt:
        dflt = "main"

    branches_out, _ = git(repo, "branch", "--format=%(refname:short)")
    local_branches = [b for b in branches_out.splitlines() if b and b != dflt]
    if local_branches:
        reasons.append(f"{len(local_branches)} local branch(es)")

    local_set = set(local_branches) | {dflt}
    remote_out, _ = git(repo, "branch", "-r", "--format=%(refname:short)")
    remote_only = []
    for rref in remote_out.splitlines():
        if not rref or not rref.startswith("origin/"):
            continue
        name = rref[len("origin/"):]
        if name == "HEAD" or name in local_set:
            continue
        remote_only.append(name)
    if remote_only:
        reasons.append(f"{len(remote_only)} remote branch(es)")

    cur, _ = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    if cur:
        upstream, rc = git(repo, "rev-parse", "--abbrev-ref", f"{cur}@{{upstream}}")
        if rc == 0 and upstream:
            ahead, _ = git(repo, "rev-list", "--count", f"{upstream}..{cur}")
            behind, _ = git(repo, "rev-list", "--count", f"{cur}..{upstream}")
            if ahead.isdigit() and int(ahead) > 0:
                reasons.append(f"{ahead} ahead")
            if behind.isdigit() and int(behind) > 0:
                reasons.append(f"{behind} behind")

    wt_out, _ = git(repo, "worktree", "list", "--porcelain")
    wt_count = sum(1 for line in wt_out.splitlines() if line.startswith("worktree ")) - 1
    if wt_count > 0:
        reasons.append(f"{wt_count} worktree(s)")

    return reasons


# ── process a single repo ───────────────────────────────────────────────

def process_repo(repo, dry_run):
    """Process one repo. Returns result dict. Streams progress to stderr in real-time."""
    name = os.path.basename(repo)

    def out(msg):
        log(f"  [{name}] {msg}")
    dflt = default_branch(repo)
    cur = current_branch(repo)

    # fetch
    out("  Fetching remote...")
    if dry_run:
        out("  [dry-run] Would fetch")
    else:
        _, rc = git(repo, "fetch", "--prune")
        out("  Fetched" if rc == 0 else "  Fetch failed (no remote?)")

    # ensure .DS_Store is gitignored
    gitignore_path = os.path.join(repo, ".gitignore")
    ds_ignored, _ = git(repo, "check-ignore", ".DS_Store")
    if not ds_ignored:
        if dry_run:
            out("  [dry-run] Would add .DS_Store to .gitignore")
        else:
            with open(gitignore_path, "a") as f:
                f.write("\n.DS_Store\n")
            git(repo, "add", ".gitignore")
            git(repo, "commit", "-m", "chore: add .DS_Store to .gitignore")
            git(repo, "push")
            out("  Added .DS_Store to .gitignore, committed and pushed")

    # uncommitted
    status_out = git_ok(repo, "status", "--porcelain")
    uncommitted = []
    if status_out:
        for line in status_out.splitlines():
            path = line[3:]
            if GENERATED_DIRS.search(path):
                continue
            uncommitted.append({"status": line[:2], "path": path})
    out(f"  Checking for uncommitted changes: {len(uncommitted) if uncommitted else 'none'}" +
        (" found" if uncommitted else ""))

    # pull / push
    needs_push = False
    needs_pull = False
    if cur:
        up = upstream_ref(repo, cur)
        if up:
            behind_str, _ = git(repo, "rev-list", "--count", f"{cur}..{up}")
            behind = int(behind_str) if behind_str.isdigit() else 0
            ahead_str, _ = git(repo, "rev-list", "--count", f"{up}..{cur}")
            ahead = int(ahead_str) if ahead_str.isdigit() else 0

            if behind > 0:
                if uncommitted:
                    out(f"  Needs pull: {behind} commit(s) behind — skipped (uncommitted changes)")
                    needs_pull = True
                elif dry_run:
                    out(f"  [dry-run] Would pull {behind} commit(s)")
                else:
                    _, rc = git(repo, "pull", "--ff-only")
                    if rc == 0:
                        out(f"  Pulled {behind} commit(s)")
                    else:
                        out("  Pull failed (not fast-forward?) — skipped")
                        needs_pull = True
            else:
                out("  Pull: up to date")

            if ahead > 0:
                if dry_run:
                    out(f"  [dry-run] Would push {ahead} commit(s)")
                else:
                    _, rc = git(repo, "push")
                    if rc == 0:
                        out(f"  Pushed {ahead} commit(s)")
                    else:
                        out("  Push failed — skipped")
                        needs_push = True
            else:
                out("  Push: up to date")
        else:
            out("  No upstream tracking branch")

    # worktrees
    wt_counts = {"worktree_refs_pruned": 0, "worktrees_removed": 0}
    dirty_wt = []

    prune_out = git_ok(repo, "worktree", "prune", "--dry-run")
    dangling = prune_out.splitlines() if prune_out else []
    if dangling:
        if dry_run:
            out(f"  [dry-run] Would prune {len(dangling)} dangling worktree ref(s)")
        else:
            git(repo, "worktree", "prune")
            out(f"  Pruned {len(dangling)} dangling worktree ref(s)")
        wt_counts["worktree_refs_pruned"] = len(dangling)

    wt_out = git_ok(repo, "worktree", "list", "--porcelain")
    worktrees = []
    current_wt = {}
    for line in wt_out.splitlines():
        if line.startswith("worktree "):
            current_wt = {"path": line.split(" ", 1)[1]}
        elif line.startswith("branch "):
            current_wt["branch"] = line.split("/")[-1]
        elif line == "":
            if current_wt:
                worktrees.append(current_wt)
            current_wt = {}
    if current_wt:
        worktrees.append(current_wt)
    if worktrees:
        worktrees = worktrees[1:]

    for wt in worktrees:
        wt_path = wt.get("path", "")
        wt_branch = wt.get("branch", "")
        if not os.path.isdir(wt_path):
            continue
        is_merged = is_merged_or_squashed(repo, dflt, wt_branch)
        wt_status = git_ok(wt_path, "status", "--porcelain")
        if wt_status:
            out(f"  Worktree {wt_path} ({wt_branch}): dirty — needs attention")
            dirty_wt.append({"path": wt_path, "branch": wt_branch, "merged": is_merged, "status": wt_status})
        elif is_merged:
            if dry_run:
                out(f"  [dry-run] Would remove worktree {wt_path} ({wt_branch}, merged)")
            else:
                git(repo, "worktree", "remove", wt_path)
                git(repo, "branch", "-d", wt_branch)
                out(f"  Removed worktree {wt_path} ({wt_branch}, merged)")
            wt_counts["worktrees_removed"] += 1

    # branches
    br_counts = {"stale_branches_deleted": 0, "merged_branches_deleted": 0}
    flagged = []

    all_out = git_ok(repo, "branch", "--format=%(refname:short)")
    all_branches = [b for b in all_out.splitlines() if b and b != dflt]

    if not all_branches:
        out("  Branches: only default branch")
    else:
        out(f"  Branches: {len(all_branches)} non-default ({', '.join(all_branches)})")

        # gone branches
        vv_out = git_ok(repo, "branch", "-vv")
        gone = set()
        for line in vv_out.splitlines():
            line = line.strip()
            if ": gone]" in line:
                branch = line.lstrip("* ").split()[0]
                gone.add(branch)

        for branch in sorted(gone):
            if is_special_branch(branch):
                out(f"  Evaluating branch {branch}: stale (remote gone) — special, keeping")
                continue
            out(f"  Evaluating branch {branch}: stale (remote gone)")
            if dry_run:
                out(f"    [dry-run] Would delete")
            else:
                _, rc = git(repo, "branch", "-d", branch)
                out(f"    Deleted stale branch {branch}" if rc == 0 else f"    Safe delete failed for {branch} — keeping")
            br_counts["stale_branches_deleted"] += 1

        # merged branches
        merged_out = git_ok(repo, "branch", "--merged", dflt)
        merged_set = {b.strip().lstrip("* ") for b in merged_out.splitlines()}

        for branch in sorted(merged_set):
            if not branch or branch == dflt or branch == cur or branch in gone:
                continue
            if is_special_branch(branch):
                continue
            out(f"  Evaluating branch {branch}: merged into {dflt}")
            if dry_run:
                out(f"    [dry-run] Would delete")
            else:
                _, rc = git(repo, "branch", "-d", branch)
                out(f"    Deleted merged branch {branch}" if rc == 0 else f"    Safe delete failed for {branch}")
            br_counts["merged_branches_deleted"] += 1

        # remaining local branches — check squash merge, flag rest
        ref_out = git_ok(
            repo, "for-each-ref", "--sort=-committerdate",
            "--format=%(refname:short)\t%(committerdate:unix)\t%(committerdate:relative)\t%(subject)",
            "refs/heads/",
        )
        for line in ref_out.splitlines():
            parts = line.split("\t", 3)
            if len(parts) < 4:
                continue
            bname, ts_str, relative, subject = parts
            if bname == dflt or bname in merged_set or bname in gone:
                continue
            if is_special_branch(bname):
                out(f"  Evaluating branch {bname}: special — keeping")
                continue
            if is_merged_or_squashed(repo, dflt, bname):
                out(f"  Evaluating branch {bname}: squash-merged into {dflt}")
                if dry_run:
                    out(f"    [dry-run] Would delete")
                else:
                    _, rc = git(repo, "branch", "-D", bname)
                    out(f"    Deleted squash-merged branch {bname}" if rc == 0 else f"    Delete failed for {bname}")
                br_counts["merged_branches_deleted"] += 1
                continue
            ahead = git_ok(repo, "rev-list", "--count", f"{dflt}..{bname}")
            stat = git_ok(repo, "diff", "--stat", f"{dflt}...{bname}")
            stat_summary = stat.splitlines()[-1].strip() if stat else ""
            out(f"  Evaluating branch {bname}: unmerged ({relative}), {ahead} commits ahead — needs attention")
            flagged.append({
                "branch": bname,
                "last_commit_age": relative,
                "last_commit_subject": subject,
                "commits_ahead": int(ahead) if ahead else 0,
                "diff_stat": stat_summary,
            })

    # remote-only branches
    local_out = git_ok(repo, "branch", "--format=%(refname:short)")
    local_set = {b for b in local_out.splitlines() if b}
    remote_out = git_ok(repo, "branch", "-r", "--format=%(refname:short)")
    gone_set = gone if all_branches else set()

    for rref in remote_out.splitlines():
        if not rref or not rref.startswith("origin/"):
            continue
        rname = rref[len("origin/"):]
        if rname == dflt or rname == "HEAD" or rname in local_set or rname in gone_set:
            continue
        if is_special_branch(rname):
            out(f"  Remote branch {rname}: special — keeping")
            continue
        if is_merged_or_squashed(repo, dflt, rref):
            out(f"  Remote branch {rname}: merged into {dflt}")
            if dry_run:
                out(f"    [dry-run] Would delete remote branch")
            else:
                _, drc = git(repo, "push", "origin", "--delete", rname)
                out(f"    Deleted remote branch {rname}" if drc == 0 else f"    Failed to delete remote branch {rname}")
            br_counts["merged_branches_deleted"] += 1
        else:
            ahead = git_ok(repo, "rev-list", "--count", f"{dflt}..{rref}")
            stat = git_ok(repo, "diff", "--stat", f"{dflt}...{rref}")
            stat_summary = stat.splitlines()[-1].strip() if stat else ""
            relative = git_ok(repo, "log", "-1", "--format=%cr", rref)
            subject = git_ok(repo, "log", "-1", "--format=%s", rref)
            out(f"  Remote branch {rname}: unmerged ({relative}), {ahead} commits ahead — needs attention")
            flagged.append({
                "branch": rname,
                "remote_only": True,
                "last_commit_age": relative,
                "last_commit_subject": subject,
                "commits_ahead": int(ahead) if ahead else 0,
                "diff_stat": stat_summary,
            })

    # remaining branches
    remaining_out = git_ok(repo, "branch", "--format=%(refname:short)")
    remaining = [b for b in remaining_out.splitlines() if b and b != dflt]

    # collect counts and items
    counts = {**wt_counts, **br_counts}
    items = []
    if uncommitted:
        items.append({"type": "uncommitted", "files": uncommitted})
    if needs_pull:
        items.append({"type": "needs_pull"})
    if needs_push:
        items.append({"type": "needs_push"})
    for b in flagged:
        items.append({"type": "branch", **b})
    for wt in dirty_wt:
        items.append({"type": "dirty_worktree", **wt})

    result = {
        "repo": name,
        "path": repo,
        "default_branch": dflt,
        "branch": cur,
        "needs_push": needs_push,
        "needs_pull": needs_pull,
        "branches": remaining,
        "auto_fixed": counts,
        "items": items,
    }

    return result


# ── main ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="repo-cleaner clean")
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()

    root = os.path.abspath(args.root)

    # discover
    repos = discover_repos(root, args.depth)
    if not repos:
        log(f"No git repositories found within depth {args.depth} of {root}")
        json.dump({"all": [], "process": [], "results": []}, sys.stdout, indent=2)
        return

    # quick pre-check
    all_repos = []
    to_process = []
    for repo in repos:
        name = os.path.basename(repo)
        all_repos.append({"repo": name, "path": repo})
        reasons = quick_check(repo)
        if reasons:
            to_process.append(repo)
            log(f"  {name}: {', '.join(reasons)}")

    clean_count = len(repos) - len(to_process)
    log(f"\n{len(repos)} repos found, {len(to_process)} need processing, {clean_count} clean\n")

    if not to_process:
        json.dump({
            "all": all_repos,
            "total": len(repos),
            "clean": clean_count,
            "processed": 0,
            "results": [],
        }, sys.stdout, indent=2)
        return

    # process in parallel
    results = []
    completed = 0
    total = len(to_process)

    def run_one(repo):
        return process_repo(repo, args.dry_run)

    # print start lines so user sees work beginning
    for i, repo in enumerate(to_process, 1):
        log(f"  Queued: {os.path.basename(repo)} ({i}/{total})")

    log("")

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run_one, repo): repo for repo in to_process}
        for future in as_completed(futures):
            repo = futures[future]
            name = os.path.basename(repo)
            completed += 1
            try:
                result = future.result()
                results.append(result)
                fixed = sum(result["auto_fixed"].values())
                remaining = len(result["items"])
                summary_parts = []
                if fixed:
                    summary_parts.append(f"{fixed} auto-fixed")
                if remaining:
                    summary_parts.append(f"{remaining} need attention")
                if not summary_parts:
                    summary_parts.append("clean")
                log(f"  Done: {name} ({completed}/{total}) — {', '.join(summary_parts)}")
            except Exception as e:
                log(f"  ERROR: {name} — {e}")

    # summary
    needs_input = [r for r in results if r["items"]]
    log(f"{'=' * 40}")
    log(f"Processed {total} repo(s), {clean_count} already clean")
    if needs_input:
        n = sum(len(r["items"]) for r in needs_input)
        log(f"{n} item(s) across {len(needs_input)} repo(s) need interactive decisions")
    else:
        log("All clean after deterministic pass")

    json.dump({
        "all": all_repos,
        "total": len(repos),
        "clean": clean_count,
        "processed": total,
        "results": results,
    }, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
