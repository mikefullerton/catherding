# Tests for `cc-*` workflow scripts

These tests exercise the workflow scripts under `claude-optimizing/scripts-git/`
against a **real** GitHub repository, not mocks. The sandbox repo is
[`agentic-cookbook/catherdingtests`](https://github.com/agentic-cookbook/catherdingtests),
checked out at `~/projects/tests/catherdingtests`. Tests create real branches,
push real commits, and open real draft PRs, then clean up after themselves.

## Why a real remote

Several of the scripts exist precisely to navigate quirks that mocks cannot
reproduce: `gh` CLI behaviour inside worktrees, GitHub's
`delete_branch_on_merge` setting auto-pruning the head ref before our
explicit `git push --delete` runs, submodule drift, and so on. A mocked
remote would let bugs through that the script is meant to catch.

## Sandbox repo configuration

The sandbox is configured to mirror production conditions:

- `delete_branch_on_merge: true` — matches `temporal` and most production
  repos. This is what surfaces the stale-tracking-ref class of bugs that
  `test_merge_worktree.py` guards against.

If you ever need to flip this back for an experiment, restore it before
committing:

```bash
gh api -X PATCH repos/agentic-cookbook/catherdingtests \
  -F delete_branch_on_merge=true
```

## Coverage

| File | Script under test | Notes |
|------|-------------------|-------|
| `test_branch_hygiene.py`  | `cc-branch-hygiene` | Stale/merged/remote-only/prunable reporting |
| `test_commit_push.py`     | `cc-commit-push`    | Stage + commit + push + draft PR |
| `test_pr_status.py`       | `cc-pr-status`      | PR summary output |
| `test_pr_review.py`       | `cc-pr-review`      | Review state inspection |
| `test_repo_state.py`      | `cc-repo-state`     | Session-start audit |
| `test_merge_worktree.py`  | `cc-merge-worktree` | Squash-merge + full worktree cleanup; **bug-reproduction** for the stale `refs/remotes/origin/<branch>` tracking-ref class |
| `test_repo_hygiene_hook.py` | `cc-repo-hygiene-hook` | Stop hook detects squash-merged orphan remote branches (the `delete_branch_on_merge: false` case that `ExitWorktree action: remove` leaves behind when it skips `cc-merge-worktree`) |

## Running

```bash
cd ~/projects/active/catherding/claude-optimizing
pytest tests/ -v
```

Each `test_pr` test takes ~10s (PR creation + merge + cleanup), so a full
run is on the order of a minute. Tests that need network are skipped
automatically when `gh` is not authenticated.
