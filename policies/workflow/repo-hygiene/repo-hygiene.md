---
title: "Repo Hygiene"
summary: "All work happens on feature branches in worktrees; commits push immediately; branches and worktrees are cleaned up when their PR merges."
triggers: [committing-code, creating-branch, using-worktree, opening-pr, repo-hygiene-audit]
tags: [git, commits, branches, worktrees, pr-workflow, hygiene]
---

# Repo Hygiene

All work happens on feature branches in worktrees; commits push immediately; branches and worktrees are cleaned up when their PR merges.

## Scope

- These rules apply to repos under `~/projects/` only.
- External or third-party repos (e.g. `~/projects/external/`) are out of scope — the write access and branch permissions these rules assume can't be taken for granted there.

## Changes

- You MUST NOT commit, push, or modify files you didn't change this session.
- Pre-existing dirt (uncommitted changes, untracked files, stale branches) MUST be surfaced to the owner before any action. No silent stash, commit, or discard.
- You MUST commit each logical unit of work as it completes. Do not let unstaged changes from your own work accumulate across unrelated steps.
- Every commit MUST be pushed immediately. No local-only commits may exist when work pauses or ends.
- Before starting work, `git status` MUST be clean (or the owner MUST be consulted), and the default branch MUST be synced with the remote.
- Before finishing, you MUST have zero uncommitted changes of your own (staged, unstaged, or untracked).

**Carve-out:** build artifacts orphaned by a change you made this session (e.g. `dist/`, `node_modules/`, `__pycache__/` left behind after deleting a tracked directory) MAY be cleaned up without asking.

## Pull Requests

- The first push of a feature branch SHOULD open a **draft PR**.
- A PR MUST be flipped from draft to ready when the work is complete and tests pass.
- PRs MUST be squash-merged — a single commit per feature on the default branch.
- A merged PR's local and remote branches MUST be deleted.

## Branches

- The default branch MUST NOT receive direct commits. All changes go through a feature branch.
- Feature branches MUST be created via the worktree tooling, not `git checkout -b` or `git switch -c`.
- Local branches that have been merged into the default branch MUST be deleted.
- Remote branches that have been merged MUST be deleted — including **squash-merged** branches whose PR closed without `delete_branch_on_merge` cleaning them up.
- The default branch MUST match its remote at the start and end of every work session. Pull if behind.

## Worktrees

- Feature work MUST happen in a worktree so the main checkout stays usable.
- A worktree whose PR has merged MUST be torn down via the merge-worktree ritual: mark PR ready, squash-merge, pull default, remove worktree, delete local branch, delete remote branch, prune.
- The merge-worktree ritual MUST NOT be hand-rolled. Use the provided tooling — hand-rolled sequences miss submodule-drift auto-sync, squash-merge orphan detection, and the gh-inside-worktree cd quirk.
- Worktrees whose branch has been deleted or already merged into the default branch are **stale** and MUST be removed.

**Derived from cookbook:** [support-automation](../../../../agenticcookbook/principles/support-automation.md), [tight-feedback-loops](../../../../agenticcookbook/principles/tight-feedback-loops.md), [fail-fast](../../../../agenticcookbook/principles/fail-fast.md)
