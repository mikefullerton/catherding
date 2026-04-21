# Scope hooks to the current session's workflow

## Problem

Yesterday's session-aware change (PR #74) scoped the Stop hook's Checks 1–3 (staged / unstaged / untracked files) to paths this session touched. Checks 4–7 still cross-scan the repo and block on state from other sessions or other worktrees:

- Check 4 — local branches already merged into default
- Check 5 — remote branches already merged into default
- Check 5b — squash-merged orphan remote branches
- Check 6 — default branch behind remote
- Check 7 — stale worktrees on disk

The `cc-exit-worktree-hook` likewise scans every worktree on disk after any `ExitWorktree` call and blocks on any stale finding, regardless of whether the stale state was this session's doing.

This contradicts the intent that the hooks help with the *current session's workflow only*. In practice it causes friction: a session in worktree A gets blocked at Stop because worktree B (another session's) has a merged branch not yet cleaned up.

## Goal

- **Stop hook** — only inspect the current worktree's state. No cross-worktree enumeration. No cross-session branch cleanup enforcement.
- **ExitWorktree hook** — keep the broad scan (it *is* useful as a reminder when you've just exited a worktree), but demote from block to warning.

## Design

### Stop hook (`cc-repo-hygiene-hook.py`)

Remove these checks entirely:

| Check | Rationale for removal |
|---|---|
| 4 — local branches merged into default | Cleanup of branches this session didn't create |
| 5 — remote branches merged into default | Same |
| 5b — squash-merged orphan remotes | Same |
| 7 — stale worktrees | Other worktrees are by definition another session's concern |

Also remove the scaffolding that only supported those checks:

- `git worktree list --porcelain` parsing in `main()`
- `active_dirty_branches` skip-list
- `_worktree_dirty` helper
- `_find_squash_merged_orphans` helper

Keep:

- Checks 1–3 (session-aware uncommitted files) — unchanged from PR #74
- Check 6 (default branch behind remote) — this is a property of the repo the current session is about to work in, not a cross-session artifact

Net effect: the file shrinks by ~120 lines and only runs `git -C <cwd>` commands scoped to the current working tree.

### ExitWorktree hook (`cc-exit-worktree-hook.py`)

Keep the broad scan (stale worktrees + orphan remote branches with merged PRs). Change the output semantics:

- Always print the diagnostic to stderr
- Exit 0 instead of 2 — never blocks the next tool call
- Reword from "you MUST run cc-merge-worktree" to "reminder: cc-merge-worktree can clean these up"

The `--branch <name>` suggestion (added in d1bfe99) stays. `cc-merge-worktree` cross-checks the PR's `headRefName` against the supplied branch as a belt-and-suspenders guard against cross-worktree deletion.

### Trade-off being accepted

Today the ExitWorktree hook blocks when a user does `ExitWorktree action:keep` on a merged branch without then running `cc-merge-worktree`. Under the new design, this becomes a warning. If the user ignores it, the worktree stays on disk until they (or a future session) deal with it; nothing destructive happens automatically.

If this causes real problems in practice, we can later reintroduce targeted blocking specifically for the just-exited branch, using `tool_input` from the hook payload to identify it. Explicitly deferred.

## Tests

### Adjusted

**`test_exit_worktree_hook.py`** — flip return-code expectations from `2` → `0` on all existing cases. Continue asserting stderr carries the diagnostic (stale path, orphan branch name) so the warning content is still verified.

**`test_repo_hygiene_hook.py`** — today it contains exactly one test, `test_hook_flags_squash_merged_orphan_remote_branch`, which asserts Stop blocks on an orphan remote branch. Under the new design the Stop hook should no longer look at remote branches at all, so invert this test: set up the same orphan-remote scenario and assert the Stop hook exits silently (no block, no warning about the orphan).

### New

Add to `test_session_aware_hook.py` (same `hook_local_repo` harness, no real GitHub):

- `test_sibling_worktree_dirty_does_not_block` — create two worktrees of the same repo, dirty a file in the sibling worktree, run the Stop hook from the primary worktree's cwd. Expect exit 0, no `decision: block`, no warning about the sibling's files.
- `test_merged_sibling_branch_does_not_block` — create a second local branch that's merged into default. Run the Stop hook from main cwd. Expect exit 0, no block.

## Docs

`claude-optimizing/claude-additions.md`, section "What the Hook Enforces":

- Trim the enumerated list from 6 items to 4 (staged × 1 + unstaged × 1 + untracked × 1 + default-behind-remote)
- Soften the ExitWorktree hook description: "surfaces a reminder" instead of "blocks the next tool call"

## Non-goals

- Adding a `SessionStart` or other new trigger. Out of scope.
- Transcript-based ownership tracking for branches/worktrees (explicitly chose cwd-scoping over this).
- Reintroducing blocking in the ExitWorktree hook for the just-exited branch. Deferred; revisit if warn-only proves too weak.
- Changes to `cc-merge-worktree.py`. The d1bfe99 fix stands independently.

## Rollout

One PR across two hook files + three test files + one doc file. Symlinks make the install immediate once merged.
