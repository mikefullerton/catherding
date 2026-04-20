#!/usr/bin/env python3
# Repo hygiene Stop hook — blocks turn if git repo is dirty
# Checks: uncommitted changes, untracked files, merged branches, stale worktrees, main sync

import json
import os
import subprocess
import sys


def run(cmd, cwd=None, timeout=10):
    """Run a git command, return (stdout, returncode)."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout
        )
        return result.stdout.strip(), result.returncode
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return "", 1


def _find_squash_merged_orphans(cwd, default_branch):
    """Remote branches that correspond to a merged PR but still exist on origin.

    Two-step filter to keep the gh call off the hot path when nothing looks
    orphaned:
      1. Enumerate remote tracking refs with no matching local branch (the
         only candidates for "orphan"; co-existing local/remote pairs are
         normal in-progress work).
      2. If any, ask gh for merged PR head refs in one call and intersect.

    Returns branch names with no `origin/` prefix.
    """
    refs_out, _ = run(
        ["git", "-C", cwd, "for-each-ref",
         "--format=%(refname:short)", "refs/remotes/origin/"]
    )
    local_out, _ = run(
        ["git", "-C", cwd, "for-each-ref",
         "--format=%(refname:short)", "refs/heads/"]
    )
    local_branches = {b.strip() for b in local_out.splitlines() if b.strip()}

    remote_only = []
    for ref in refs_out.splitlines():
        ref = ref.strip()
        if not ref:
            continue
        if not ref.startswith("origin/"):
            continue
        name = ref[len("origin/"):]
        if name in ("HEAD", default_branch) or not name:
            continue
        if name in local_branches:
            continue
        remote_only.append(name)

    if not remote_only:
        return []

    gh_out, gh_rc = run(
        ["gh", "pr", "list", "--state", "merged", "--limit", "100",
         "--json", "headRefName"],
        cwd=cwd, timeout=15,
    )
    if gh_rc != 0 or not gh_out:
        return []
    try:
        merged_heads = {pr["headRefName"] for pr in json.loads(gh_out)}
    except (json.JSONDecodeError, KeyError, TypeError):
        return []

    return [name for name in remote_only if name in merged_heads]


def main():
    input_json = json.loads(sys.stdin.read())

    # Guard: prevent infinite loop — if hook already blocked once, allow stop
    if input_json.get("stop_hook_active"):
        sys.exit(0)

    cwd = input_json.get("cwd", "")
    if not cwd:
        sys.exit(0)

    # Guard: only enforce for ~/projects/ but NOT ~/projects/external/
    home = os.path.expanduser("~")
    projects_root = os.path.join(home, "projects")
    external_root = os.path.join(home, "projects", "external")
    abs_cwd = os.path.realpath(cwd)
    in_projects = abs_cwd.startswith(projects_root + os.sep) or abs_cwd == projects_root
    in_external = abs_cwd.startswith(external_root + os.sep) or abs_cwd == external_root
    if not in_projects or in_external:
        sys.exit(0)

    # Guard: not a git repo
    _, rc = run(["git", "-C", cwd, "rev-parse", "--is-inside-work-tree"])
    if rc != 0:
        sys.exit(0)

    # Detect default branch
    default_branch = None
    out, rc = run(["git", "-C", cwd, "symbolic-ref", "refs/remotes/origin/HEAD"])
    if rc == 0 and out:
        default_branch = out.replace("refs/remotes/origin/", "")
    else:
        for candidate in ("main", "master"):
            _, rc = run(
                ["git", "-C", cwd, "show-ref", "--verify", "--quiet", f"refs/heads/{candidate}"]
            )
            if rc == 0:
                default_branch = candidate
                break

    # Detect remote
    _, rc = run(["git", "-C", cwd, "remote", "get-url", "origin"])
    has_remote = rc == 0

    # Fetch with --prune so tombstone tracking refs (refs/remotes/origin/<b>
    # where origin no longer has <b>) are cleaned up before later checks
    # enumerate them. Without --prune, Check 5b sees a stale tracking ref
    # for a deleted remote branch and falsely flags it as an orphan.
    if has_remote:
        run(["git", "-C", cwd, "fetch", "origin", "--prune", "--quiet"], timeout=10)

    # Parse worktrees once so later checks can cross-reference. A worktree
    # with uncommitted changes or untracked files is still "in use" even if
    # its branch has been reset to an ancestor of main by cc-merge-worktree —
    # subsequent checks skip such worktrees/branches to avoid false positives.
    wt_out, _ = run(["git", "-C", cwd, "worktree", "list", "--porcelain"])
    worktrees = []
    current_wt = {}
    for line in wt_out.splitlines():
        if line.startswith("worktree "):
            if current_wt:
                worktrees.append(current_wt)
            current_wt = {"path": line[len("worktree "):]}
        elif line.startswith("branch "):
            current_wt["branch"] = line[len("branch refs/heads/"):]
    if current_wt:
        worktrees.append(current_wt)

    def _worktree_dirty(path):
        porcelain, rc = run(["git", "-C", path, "status", "--porcelain"])
        return rc == 0 and bool(porcelain)

    # Branches backing a dirty worktree (excluding the main worktree itself —
    # dirtiness there is handled by Checks 1–3 on the session cwd).
    active_dirty_branches = set()
    for wt in worktrees[1:]:
        b = wt.get("branch")
        p = wt.get("path")
        if b and p and _worktree_dirty(p):
            active_dirty_branches.add(b)

    violations = []

    # Check 1: Staged changes
    out, _ = run(["git", "-C", cwd, "diff", "--cached", "--name-only"])
    staged_paths = [p for p in out.splitlines() if p]
    if staged_paths:
        violations.append(
            "Staged changes not committed: " + ", ".join(staged_paths)
        )

    # Check 2: Unstaged changes
    out, _ = run(["git", "-C", cwd, "diff", "--name-only"])
    unstaged_paths = [p for p in out.splitlines() if p]
    if unstaged_paths:
        violations.append(
            "Unstaged changes to tracked files: " + ", ".join(unstaged_paths)
        )

    # Check 3: Untracked files
    out, _ = run(["git", "-C", cwd, "ls-files", "--others", "--exclude-standard"])
    untracked_paths = [p for p in out.splitlines() if p]
    if untracked_paths:
        violations.append(
            f"{len(untracked_paths)} untracked file(s) not in .gitignore: "
            + ", ".join(untracked_paths)
        )

    if default_branch:
        # Check 4: Local branches merged into default
        out, _ = run(["git", "-C", cwd, "branch", "--merged", default_branch])
        if out:
            default_sha, _ = run(["git", "-C", cwd, "rev-parse", default_branch])
            merged = []
            for b in out.splitlines():
                name = b.strip().lstrip("*+ ")
                if name == default_branch:
                    continue
                # Skip detached HEAD entries from submodules e.g. "(HEAD detached at ...)"
                if name.startswith("("):
                    continue
                # Skip branches at the same commit as default — they're new, not stale
                b_sha, _ = run(["git", "-C", cwd, "rev-parse", name])
                if b_sha and default_sha and b_sha == default_sha:
                    continue
                # Skip branches backing an in-use (dirty) worktree.
                if name in active_dirty_branches:
                    continue
                merged.append(name)
            if merged:
                violations.append(
                    f"Local branches already merged into {default_branch}: {', '.join(merged)}"
                )

        # Check 5: Remote branches merged into default
        if has_remote:
            out, _ = run(["git", "-C", cwd, "branch", "-r", "--merged", default_branch])
            if out:
                merged = [
                    b.strip()
                    for b in out.splitlines()
                    if b.strip()
                    and f"origin/{default_branch}" not in b
                    and "origin/HEAD" not in b
                ]
                if merged:
                    violations.append(
                        f"Remote branches already merged into {default_branch}: {', '.join(merged)}"
                    )

        # Check 5b: Remote branches whose PR was squash-merged. `git branch
        # -r --merged` (Check 5) compares by SHA reachability and misses
        # squash-merges, because the squash commit on default has a
        # different SHA than the branch tip. This catches the orphan left
        # behind when a repo has `delete_branch_on_merge: false` and the
        # user's exit ritual skipped `cc-merge-worktree` (e.g.
        # ExitWorktree action:remove directly).
        if has_remote:
            orphans = _find_squash_merged_orphans(cwd, default_branch)
            if orphans:
                violations.append(
                    "Remote branches with merged PRs not deleted: "
                    f"{', '.join(orphans)} "
                    "(run: git push origin --delete <branch>)"
                )

        # Check 6: Default branch behind remote
        if has_remote:
            local_sha, _ = run(["git", "-C", cwd, "rev-parse", default_branch])
            remote_sha, _ = run(["git", "-C", cwd, "rev-parse", f"origin/{default_branch}"])
            if local_sha and remote_sha and local_sha != remote_sha:
                behind, _ = run(
                    ["git", "-C", cwd, "rev-list", "--count", f"{default_branch}..origin/{default_branch}"]
                )
                if behind and int(behind) > 0:
                    violations.append(
                        f"{default_branch} is {behind} commit(s) behind origin/{default_branch}"
                    )

    # Check 7: Stale worktrees (reuses worktrees parsed above).
    # Skip the first worktree (main working tree).
    for wt in worktrees[1:]:
        branch = wt.get("branch")
        path = wt.get("path", "?")
        if not branch:
            continue
        # A worktree with uncommitted changes or untracked files is in use
        # regardless of how its branch pointer sits relative to main — skip.
        if branch in active_dirty_branches:
            continue
        # Check if branch still exists
        _, rc = run(
            ["git", "-C", cwd, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"]
        )
        if rc != 0:
            violations.append(f"Stale worktree at {path} — branch '{branch}' no longer exists")
        elif default_branch:
            # A worktree branch that points to the same commit as the default
            # branch is newly created (not yet diverged) — not stale.
            branch_sha, _ = run(["git", "-C", cwd, "rev-parse", branch])
            default_sha, _ = run(["git", "-C", cwd, "rev-parse", default_branch])
            if branch_sha and default_sha and branch_sha == default_sha:
                continue
            _, rc = run(
                ["git", "-C", cwd, "merge-base", "--is-ancestor", branch, default_branch]
            )
            if rc == 0:
                violations.append(
                    f"Stale worktree at {path} — branch '{branch}' is already merged into {default_branch}"
                )

    # Output result
    if not violations:
        sys.exit(0)

    reason = "Repo hygiene violations: " + "; ".join(violations)
    json.dump({"decision": "block", "reason": reason}, sys.stdout)
    sys.exit(0)


if __name__ == "__main__":
    main()
