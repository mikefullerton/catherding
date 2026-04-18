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

    # Fetch (with timeout, non-blocking on failure)
    if has_remote:
        run(["git", "-C", cwd, "fetch", "origin", "--quiet"], timeout=10)

    violations = []

    # Check 1: Staged changes
    _, rc = run(["git", "-C", cwd, "diff", "--cached", "--quiet"])
    if rc != 0:
        violations.append("Staged changes not committed")

    # Check 2: Unstaged changes
    _, rc = run(["git", "-C", cwd, "diff", "--quiet"])
    if rc != 0:
        violations.append("Unstaged changes to tracked files")

    # Check 3: Untracked files
    out, _ = run(["git", "-C", cwd, "ls-files", "--others", "--exclude-standard"])
    if out:
        count = len(out.splitlines())
        violations.append(f"{count} untracked file(s) not in .gitignore")

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

    # Check 7: Stale worktrees
    out, _ = run(["git", "-C", cwd, "worktree", "list", "--porcelain"])
    if out:
        worktrees = []
        current_wt = {}
        for line in out.splitlines():
            if line.startswith("worktree "):
                if current_wt:
                    worktrees.append(current_wt)
                current_wt = {"path": line[len("worktree "):]}
            elif line.startswith("branch "):
                current_wt["branch"] = line[len("branch refs/heads/"):]
        if current_wt:
            worktrees.append(current_wt)

        # Skip the first worktree (main working tree)
        for wt in worktrees[1:]:
            branch = wt.get("branch")
            path = wt.get("path", "?")
            if not branch:
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
