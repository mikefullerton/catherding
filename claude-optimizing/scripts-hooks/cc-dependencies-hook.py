#!/usr/bin/env python3
# Dependencies Stop hook — blocks turn if any dependencies.json pin is unpublishable
# Checks: last-sha reachable from origin/<branch>, tag resolves to last-sha,
# ci-guidance internally consistent. Mirrors cc-deps-verify semantics.

import json
import os
import subprocess
import sys


def run(cmd, cwd=None, timeout=10):
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout
        )
        return result.stdout.strip(), result.returncode
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return "", 1


def clone_name(repo_url):
    basename = repo_url.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1]
    if basename.endswith(".git"):
        basename = basename[: -len(".git")]
    return basename


def check_entry(entry, cwd):
    repo = entry.get("repo", "")
    branch = entry.get("branch", "")
    last_sha = entry.get("last-sha", "")
    tag = entry.get("tag")
    ci = entry.get("ci-guidance")

    if not repo or not branch or not last_sha:
        return [f"{clone_name(repo) or '?'}: missing required field (repo, branch, last-sha)"]

    name = clone_name(repo)
    clone = os.path.join(cwd, "dependencies", name)
    if not os.path.isdir(clone) or not os.path.exists(os.path.join(clone, ".git")):
        # Missing clone is a sync problem, not a pin-correctness problem. Skip.
        return []

    # Fetch so reachability check is authoritative.
    run(["git", "-C", clone, "fetch", "origin", "--tags", "--quiet"], timeout=15)

    failures = []
    _, rc = run(["git", "-C", clone, "cat-file", "-e", f"{last_sha}^{{commit}}"])
    if rc != 0:
        failures.append(f"{name}: last-sha {last_sha[:12]} does not resolve in clone")
        return failures

    _, rc = run(["git", "-C", clone, "rev-parse", "--verify", f"refs/remotes/origin/{branch}"])
    if rc != 0:
        failures.append(f"{name}: origin/{branch} does not exist")
        return failures

    _, rc = run(
        ["git", "-C", clone, "merge-base", "--is-ancestor", last_sha, f"origin/{branch}"]
    )
    if rc != 0:
        failures.append(
            f"{name}: last-sha {last_sha[:12]} not on origin/{branch} — "
            f"merge the dep PR, then cc-deps-bump {name}"
        )

    if tag is not None:
        tag_sha, rc = run(["git", "-C", clone, "rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}"])
        if rc != 0:
            failures.append(f"{name}: tag {tag!r} does not resolve in clone")
        elif tag_sha != last_sha:
            failures.append(
                f"{name}: tag {tag!r} resolves to {tag_sha[:12]}, not last-sha {last_sha[:12]}"
            )

    if ci is not None:
        if not isinstance(ci, dict):
            failures.append(f"{name}: ci-guidance must be an object")
        else:
            mode = ci.get("mode")
            if mode not in ("sha", "branch", "tag"):
                failures.append(
                    f"{name}: ci-guidance.mode must be 'sha', 'branch', or 'tag' (got {mode!r})"
                )
            elif mode not in ci:
                failures.append(
                    f"{name}: ci-guidance.mode={mode!r} requires sibling field {mode!r}"
                )
            elif mode == "sha":
                _, rc = run(["git", "-C", clone, "cat-file", "-e", f"{ci['sha']}^{{commit}}"])
                if rc != 0:
                    failures.append(
                        f"{name}: ci-guidance.sha {ci['sha'][:12]} does not resolve in clone"
                    )

    return failures


def main():
    input_json = json.loads(sys.stdin.read())

    # Guard: prevent infinite loop
    if input_json.get("stop_hook_active"):
        sys.exit(0)

    cwd = input_json.get("cwd", "")
    if not cwd:
        sys.exit(0)

    # Guard: ~/projects/ only, NOT ~/projects/external/
    home = os.path.expanduser("~")
    projects_root = os.path.join(home, "projects")
    external_root = os.path.join(home, "projects", "external")
    abs_cwd = os.path.realpath(cwd)
    in_projects = abs_cwd.startswith(projects_root + os.sep) or abs_cwd == projects_root
    in_external = abs_cwd.startswith(external_root + os.sep) or abs_cwd == external_root
    if not in_projects or in_external:
        sys.exit(0)

    # Guard: must be a git repo
    _, rc = run(["git", "-C", cwd, "rev-parse", "--is-inside-work-tree"])
    if rc != 0:
        sys.exit(0)

    # Fast path: no manifest, nothing to check
    manifest_path = os.path.join(cwd, "dependencies.json")
    if not os.path.isfile(manifest_path):
        sys.exit(0)

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            entries = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        json.dump(
            {"decision": "block", "reason": f"dependencies.json unreadable: {e}"},
            sys.stdout,
        )
        sys.exit(0)

    if not isinstance(entries, list):
        json.dump(
            {"decision": "block", "reason": "dependencies.json must be a JSON array"},
            sys.stdout,
        )
        sys.exit(0)

    violations = []
    for entry in entries:
        if not isinstance(entry, dict):
            violations.append("dependencies.json entry is not an object")
            continue
        violations.extend(check_entry(entry, cwd))

    if not violations:
        sys.exit(0)

    reason = "dependencies.json violations: " + "; ".join(violations)
    json.dump({"decision": "block", "reason": reason}, sys.stdout)
    sys.exit(0)


if __name__ == "__main__":
    main()
