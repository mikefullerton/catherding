#!/usr/bin/env python3
# Repo hygiene Stop hook — blocks turn if the current worktree is dirty
# Checks: this-session staged/unstaged/untracked changes, default branch behind remote

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


def _read_transcript_tool_uses(transcript_path):
    """Return (edit_paths, bash_commands) from the Claude Code transcript.

    edit_paths: set of absolute paths from Edit / Write / NotebookEdit
        tool_use file_path inputs.
    bash_commands: list of command strings from Bash tool_use inputs.

    Returns (None, None) on any failure (missing file, IO error, malformed
    JSON line, or unexpected structure). Callers treat None as "fail
    closed" — classify every dirty path as this-session.
    """
    if not transcript_path:
        return None, None
    try:
        edit_paths = set()
        bash_commands = []
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    return None, None
                msg = obj.get("message") or {}
                content = msg.get("content")
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") != "tool_use":
                        continue
                    name = block.get("name")
                    inp = block.get("input") or {}
                    if not isinstance(inp, dict):
                        continue
                    if name in ("Edit", "Write", "NotebookEdit"):
                        fp = inp.get("file_path")
                        if isinstance(fp, str) and fp:
                            edit_paths.add(os.path.realpath(fp))
                    elif name == "Bash":
                        cmd = inp.get("command")
                        if isinstance(cmd, str) and cmd:
                            bash_commands.append(cmd)
        return edit_paths, bash_commands
    except (OSError, IOError):
        return None, None


def _classify_paths(rel_paths, cwd, edit_paths, bash_commands):
    """Partition repo-relative paths into (touched, untouched) by session.

    A path is "touched" by the current session if:
      - its absolute form appears in edit_paths (from Edit/Write/
        NotebookEdit tool_use file_path inputs), OR
      - its relative form or absolute form appears as a substring in any
        Bash command string.

    The Bash substring check is intentionally loose: false positives
    (warn-eligible paths promoted to block) are safe; false negatives
    (Claude-touched paths demoted to warn) would let real session dirt
    slip past Stop with only a warning, which is the dangerous direction.
    """
    touched, untouched = [], []
    for rel in rel_paths:
        abs_path = os.path.realpath(os.path.join(cwd, rel))
        is_touched = abs_path in edit_paths
        if not is_touched:
            for cmd in bash_commands:
                if rel in cmd or abs_path in cmd:
                    is_touched = True
                    break
        if is_touched:
            touched.append(rel)
        else:
            untouched.append(rel)
    return touched, untouched


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

    # Fetch with --prune so the origin/<default_branch> tracking ref used
    # by Check 6 reflects what's actually on origin.
    if has_remote:
        run(["git", "-C", cwd, "fetch", "origin", "--prune", "--quiet"], timeout=10)

    transcript_path = input_json.get("transcript_path") or ""
    edit_paths, bash_commands = _read_transcript_tool_uses(transcript_path)
    classify_enabled = edit_paths is not None
    warnings = []

    violations = []

    def _split(rel_paths):
        """Return (this_session, prior_session) for a list of dirty paths.
        If classification is disabled (transcript unreadable), fail closed:
        treat everything as this-session."""
        if not classify_enabled:
            return rel_paths, []
        return _classify_paths(rel_paths, cwd, edit_paths, bash_commands)

    # Check 1: Staged changes
    out, _ = run(["git", "-C", cwd, "diff", "--cached", "--name-only"])
    staged_paths = [p for p in out.splitlines() if p]
    if staged_paths:
        this_sess, prior = _split(staged_paths)
        if this_sess:
            violations.append(
                "Staged changes not committed: " + ", ".join(this_sess)
            )
        if prior:
            warnings.append(
                "Staged changes from prior sessions: " + ", ".join(prior)
            )

    # Check 2: Unstaged changes
    out, _ = run(["git", "-C", cwd, "diff", "--name-only"])
    unstaged_paths = [p for p in out.splitlines() if p]
    if unstaged_paths:
        this_sess, prior = _split(unstaged_paths)
        if this_sess:
            violations.append(
                "Unstaged changes to tracked files: " + ", ".join(this_sess)
            )
        if prior:
            warnings.append(
                "Unstaged changes from prior sessions: " + ", ".join(prior)
            )

    # Check 3: Untracked files
    out, _ = run(["git", "-C", cwd, "ls-files", "--others", "--exclude-standard"])
    untracked_paths = [p for p in out.splitlines() if p]
    if untracked_paths:
        this_sess, prior = _split(untracked_paths)
        if this_sess:
            violations.append(
                f"{len(this_sess)} untracked file(s) not in .gitignore: "
                + ", ".join(this_sess)
            )
        if prior:
            warnings.append(
                f"{len(prior)} untracked file(s) from prior sessions: "
                + ", ".join(prior)
            )

    # Check 4: Default branch behind remote
    if default_branch and has_remote:
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

    # Check 5: Submodule hygiene
    # For each registered submodule: parent's recorded SHA must be reachable
    # from the submodule's origin/<default>. Blocks turn if not. Also warn
    # (non-blocking) if the session touched files beneath a submodule path
    # while the submodule HEAD is detached — that's the "Submodule Workflow"
    # rule violation. Skipped entirely when no .gitmodules exists, so the
    # common no-submodule case stays zero-cost.
    gitmodules_path = os.path.join(cwd, ".gitmodules")
    if os.path.isfile(gitmodules_path):
        out, rc = run(
            ["git", "-C", cwd, "config", "--file", ".gitmodules",
             "--get-regexp", r"submodule\..*\.path"]
        )
        sub_paths = []
        if rc == 0 and out:
            for line in out.splitlines():
                parts = line.split(None, 1)
                if len(parts) == 2:
                    sub_paths.append(parts[1])

        for sub_rel in sub_paths:
            sub_abs = os.path.join(cwd, sub_rel)
            if not os.path.isdir(os.path.join(sub_abs, ".git")) and not os.path.isfile(os.path.join(sub_abs, ".git")):
                # Submodule not checked out; nothing to verify.
                continue

            # Recorded SHA in parent index
            ls_out, rc_ls = run(["git", "-C", cwd, "ls-tree", "HEAD", sub_rel])
            recorded = ""
            if rc_ls == 0 and ls_out:
                parts = ls_out.split()
                if len(parts) >= 3:
                    recorded = parts[2]
            if not recorded:
                continue

            # Fetch origin in the submodule (quiet, bounded).
            run(["git", "-C", sub_abs, "fetch", "origin", "--quiet"], timeout=10)

            # Submodule's default branch.
            sub_head, rc_h = run(
                ["git", "-C", sub_abs, "symbolic-ref", "refs/remotes/origin/HEAD"]
            )
            if rc_h == 0 and sub_head.startswith("refs/remotes/origin/"):
                sub_default = sub_head.replace("refs/remotes/origin/", "")
            else:
                sub_default = "main"

            # Ancestor check: recorded SHA must be on origin/<sub_default>.
            _, rc_anc = run(
                ["git", "-C", sub_abs, "merge-base", "--is-ancestor",
                 recorded, f"origin/{sub_default}"]
            )
            if rc_anc != 0:
                violations.append(
                    f"submodule {sub_rel} pinned to {recorded[:12]} not on "
                    f"origin/{sub_default} — merge the submodule branch, "
                    f"then cc-bump-submodule {sub_rel}"
                )

            # Detached-HEAD warning if the session touched the submodule.
            if classify_enabled:
                sub_real = os.path.realpath(sub_abs)
                touched_sub = any(
                    ep == sub_real or ep.startswith(sub_real + os.sep)
                    for ep in edit_paths
                )
                if not touched_sub:
                    for cmd_str in bash_commands:
                        if sub_rel in cmd_str or sub_real in cmd_str:
                            touched_sub = True
                            break
                if touched_sub:
                    _, rc_branch = run(
                        ["git", "-C", sub_abs, "symbolic-ref",
                         "--short", "-q", "HEAD"]
                    )
                    if rc_branch != 0:
                        warnings.append(
                            f"submodule {sub_rel} edited this session while in "
                            f"detached HEAD — per Submodule Workflow rule, "
                            f"branch off origin/{sub_default} before editing"
                        )

    # Emit warnings to stderr regardless of whether we block — Claude Code
    # surfaces stderr in the transcript so both user and Claude can see
    # pre-existing dirt without it blocking turn-end.
    if warnings:
        print(
            "⚠ Uncommitted files from prior sessions (not blocking):",
            file=sys.stderr,
        )
        for w in warnings:
            print("  - " + w, file=sys.stderr)

    # Output result
    if not violations:
        sys.exit(0)

    reason = "Repo hygiene violations: " + "; ".join(violations)
    json.dump({"decision": "block", "reason": reason}, sys.stdout)
    sys.exit(0)


if __name__ == "__main__":
    main()
