# Worktree Branch Cleanup

After a PR is merged, **immediately** delete the remote branch if `gh pr merge --delete-branch` failed to do so (common when merging from inside a worktree).

## Checklist after every merge

1. `git push origin --delete <branch-name>` — remove the remote branch
2. Verify with `git branch -r` — no stale `remotes/origin/worktree-*` branches should exist for merged PRs
3. `ExitWorktree` with `action: "remove"` — clean up the local worktree and branch

## Why this matters

`gh pr merge --delete-branch` silently skips remote branch deletion when run from a worktree (the `fatal: 'main' is already used by worktree` error aborts the local checkout step, which also skips the delete). This leaves stale remote branches that accumulate and trigger the repo hygiene stop hook.
