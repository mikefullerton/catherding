#!/usr/bin/env python3
"""Merge a worktree PR and clean up.

Usage: merge-worktree.py <pr-number> [--branch <branch-name>]

Runs the full worktree-exit ritual in one call. Auto-syncs drifted
submodule pointers so a recent rebase that bumped a submodule SHA
doesn't block the gate.

  1. Locate the main-worktree checkout (auto-switches if called from the
     main repo; REFUSES if called from inside the worktree being merged —
     removing that worktree would rip the caller's cwd out, so the caller
     must cd back to the main repo first)
  2. Mark PR ready if it's a draft, then merge via gh (squash)
  3. Pull default branch
  4. Gate: verify MERGED state + main==origin/main + clean tracked
     (tracked changes that already match origin/<default> are discarded)
  5. Remove worktree directory
  6. Delete local branch
  7. Delete remote branch
  8. Final verification

Exits non-zero on any gate failure (including the caller-cwd gate). Safe
to re-run if a step failed midway.
"""
import argparse
import os
import subprocess
import sys


def run(cmd, check=True, capture=True, cwd=None):
    """Run a command, return (stdout, returncode). Exit on non-zero if check=True."""
    result = subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        timeout=60,
        cwd=cwd,
    )
    if check and result.returncode != 0:
        print(f"FAIL: {' '.join(cmd)}", file=sys.stderr)
        print(result.stderr or result.stdout, file=sys.stderr)
        sys.exit(result.returncode)
    return result.stdout.strip(), result.returncode


def find_main_worktree(default_branches=("main", "master")):
    """Return (path, branch) of the main-branch worktree for the current repo."""
    wt_list, _ = run(["git", "worktree", "list", "--porcelain"])
    cur_path = None
    for line in wt_list.splitlines():
        if line.startswith("worktree "):
            cur_path = line[len("worktree "):]
        elif line.startswith("branch refs/heads/"):
            branch = line[len("branch refs/heads/"):]
            if branch in default_branches:
                return cur_path, branch
    return None, None


def drifted_submodules() -> list[str]:
    """Submodules whose checked-out SHA differs from the parent's recorded SHA.

    `git submodule status` prefixes a `+` to drifted entries. Returns just
    the submodule paths.
    """
    out, _ = run(["git", "submodule", "status"], check=False)
    drifted: list[str] = []
    for line in out.splitlines():
        if line.startswith("+"):
            # Format: "+<sha> <path> [(<describe>)]"
            parts = line[1:].split()
            if len(parts) >= 2:
                drifted.append(parts[1])
    return drifted


def only_dirty_paths_are(allowed: list[str]) -> bool:
    """True iff every uncommitted tracked path is in `allowed`."""
    status, _ = run(["git", "status", "--porcelain=v1"], check=False)
    allowed_set = set(allowed)
    for line in status.splitlines():
        if not line or line.startswith("??"):
            continue
        path = line[3:].strip()
        if path not in allowed_set:
            return False
    return True


def discard_if_matches_upstream(default_branch, cwd):
    """Discard tracked changes that already match origin/<default_branch>.

    Returns True if the working tree is clean (or made clean) afterwards, False otherwise.
    """
    run(["git", "fetch", "origin", default_branch], cwd=cwd)

    # Bypass run()'s .strip() — porcelain=v1 lines are "XY filename" where
    # X/Y may be spaces. Stripping eats the leading space and shifts the
    # filename slice by one, corrupting the path.
    status = subprocess.run(
        ["git", "status", "--porcelain=v1"],
        capture_output=True, text=True, check=True, cwd=cwd,
    ).stdout
    dirty_paths = []
    for line in status.splitlines():
        if not line or line.startswith("??"):
            continue
        dirty_paths.append(line[3:])

    if not dirty_paths:
        return True

    diff_vs_upstream, _ = run(
        ["git", "diff", f"origin/{default_branch}", "--", *dirty_paths],
        cwd=cwd,
    )
    if diff_vs_upstream.strip():
        return False

    print(f"  discarding {len(dirty_paths)} tracked change(s) already in origin/{default_branch}")
    run(["git", "checkout", "--", *dirty_paths], cwd=cwd)
    return True


def main():
    ap = argparse.ArgumentParser(description="Merge worktree PR and clean up.")
    ap.add_argument("pr", type=int, help="PR number")
    ap.add_argument("--branch", help="Worktree branch name (auto-detected if omitted)")
    args = ap.parse_args()

    # 1. Locate the main-branch worktree. Run all git ops there so it's safe to
    #    invoke this script from inside a worktree.
    main_path, default_branch = find_main_worktree()
    if not main_path:
        print("FAIL: could not find a main/master worktree for this repo", file=sys.stderr)
        sys.exit(2)

    cwd_at_start = os.getcwd()
    caller_cwd = os.environ.get("PWD") or cwd_at_start
    if os.path.realpath(cwd_at_start) != os.path.realpath(main_path):
        print(f"switching to main worktree: {main_path}")
    os.chdir(main_path)

    # Index worktree paths by branch (used for --branch auto-detect AND for
    # the caller-inside-worktree gate below).
    wt_list, _ = run(["git", "worktree", "list", "--porcelain"])
    wt_path_by_branch: dict[str, str] = {}
    cur_path = None
    for line in wt_list.splitlines():
        if line.startswith("worktree "):
            cur_path = line[len("worktree "):]
        elif line.startswith("branch refs/heads/") and cur_path:
            wt_path_by_branch[line[len("branch refs/heads/"):]] = cur_path

    # 2. Detect worktree branch if not provided
    wt_branch = args.branch
    if not wt_branch:
        for br in wt_path_by_branch:
            if br.startswith("worktree-"):
                wt_branch = br
                break
        if not wt_branch:
            print("FAIL: could not auto-detect worktree branch; pass --branch", file=sys.stderr)
            sys.exit(2)

    # GATE: refuse to proceed if the caller's cwd is inside the worktree we're
    # about to merge. Removing the worktree (step 7) would rip the cwd out
    # from under the calling session; the caller must cd back to the main
    # repo first. Fail fast BEFORE any network calls so retrying is cheap.
    target_wt_path = wt_path_by_branch.get(wt_branch)
    if target_wt_path:
        try:
            caller_real = os.path.realpath(caller_cwd)
            target_real = os.path.realpath(target_wt_path)
        except OSError:
            caller_real = target_real = ""
        if caller_real and (
            caller_real == target_real
            or caller_real.startswith(target_real + os.sep)
        ):
            print(
                f"FAIL: cwd is inside the worktree being merged ({target_real}).\n"
                f"      cd to the main repo ({main_path}) and re-run, or use\n"
                "      ExitWorktree action:keep first.",
                file=sys.stderr,
            )
            sys.exit(2)

    print(f"merging PR #{args.pr} (worktree branch: {wt_branch})")

    # 3. Merge PR (skip if already merged). Mark ready if draft.
    pr_info, _ = run(
        ["gh", "pr", "view", str(args.pr), "--json", "state,isDraft", "-q",
         ".state + \"|\" + (.isDraft|tostring)"],
    )
    pr_state, is_draft = pr_info.split("|", 1)
    if pr_state == "OPEN":
        if is_draft == "true":
            print("  PR is draft — marking ready")
            run(["gh", "pr", "ready", str(args.pr)])
        run(["gh", "pr", "merge", str(args.pr), "--squash"])
        pr_state, _ = run(["gh", "pr", "view", str(args.pr), "--json", "state", "-q", ".state"])

    # 4. Before pulling, discard any tracked changes already present upstream
    #    (a common case: the same edit was made in both the main tree and the
    #    worktree, so the PR diff == the uncommitted diff).
    if not discard_if_matches_upstream(default_branch, cwd=main_path):
        print("FAIL: main worktree has uncommitted changes that differ from origin/"
              f"{default_branch}; refusing to pull", file=sys.stderr)
        sys.exit(3)

    # 5. Pull default branch
    run(["git", "pull", "origin", default_branch])

    # 6. Gate checks
    if pr_state != "MERGED":
        print(f"FAIL: PR state is {pr_state}, expected MERGED", file=sys.stderr)
        sys.exit(3)

    local_head, _ = run(["git", "rev-parse", default_branch])
    remote_head, _ = run(["git", "rev-parse", f"origin/{default_branch}"])
    if local_head != remote_head:
        print(f"FAIL: {default_branch} != origin/{default_branch}", file=sys.stderr)
        sys.exit(3)

    _, unstaged = run(["git", "diff", "--quiet"], check=False)
    _, staged = run(["git", "diff", "--cached", "--quiet"], check=False)
    if unstaged != 0 or staged != 0:
        # Common recoverable case: the only uncommitted entries are submodules
        # whose checked-out SHA drifted from what HEAD records (a rebase or
        # merge updated the parent pointer but didn't sync the submodule
        # working tree). `git submodule update --init <paths>` fixes this
        # without throwing away any user work.
        drifted = drifted_submodules()
        if drifted and only_dirty_paths_are(drifted):
            print(f"  syncing {len(drifted)} drifted submodule(s): {', '.join(drifted)}")
            run(["git", "submodule", "update", "--init", "--recursive", "--", *drifted])
            _, unstaged = run(["git", "diff", "--quiet"], check=False)
            _, staged = run(["git", "diff", "--cached", "--quiet"], check=False)
        if unstaged != 0 or staged != 0:
            print("FAIL: working tree has uncommitted tracked changes", file=sys.stderr)
            sys.exit(3)

    print("gate passed")

    # 7. Remove worktree directory. The caller-inside-worktree case was
    #    rejected up front by the gate above, so the cwd-ripout hazard
    #    can't apply here — we always remove unconditionally.
    wt_path = wt_path_by_branch.get(wt_branch)
    if wt_path:
        run(["git", "worktree", "remove", wt_path, "--force"])

    # 8. Delete local branch
    local_branches, _ = run(["git", "branch", "--list", wt_branch])
    if local_branches:
        run(["git", "branch", "-D", wt_branch])

    # 9. Delete remote branch (harmless if already gone)
    run(["git", "push", "origin", "--delete", wt_branch], check=False)

    # 9b. Prune stale refs/remotes/origin/* tracking refs left behind when
    # the remote branch was deleted by GitHub's delete_branch_on_merge
    # setting (so step 9 was a no-op and didn't auto-prune the local
    # tracking ref as a side effect).
    run(["git", "fetch", "--prune", "origin"], check=False)

    # 10. Final verification
    still_there, _ = run(["git", "ls-remote", "--heads", "origin", wt_branch], check=False)
    if still_there:
        print(f"WARN: remote branch still exists: {still_there}", file=sys.stderr)

    head_msg, _ = run(["git", "log", "--oneline", "-1"])
    print(f"done: {head_msg}")


if __name__ == "__main__":
    main()
