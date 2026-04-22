---
title: "Repo Hygiene"
summary: "Commit and push your own work; don't touch pre-existing dirt; worktree lifecycle is user-initiated."
triggers: [committing-code, creating-branch, using-worktree, opening-pr, repo-hygiene-audit]
tags: [git, commits, branches, worktrees, pr-workflow, hygiene]
---

# Repo Hygiene

Two rules about your own work, and a standard workflow for everything else.

## Scope

- Applies to repos under `~/projects/` only.
- External or third-party repos (e.g. `~/projects/external/`) are out of scope — the write access and branch permissions these rules assume can't be taken for granted there.

## 1. Commit and push your own changes

- Commit each logical unit of work as it completes. Don't let your own changes accumulate uncommitted.
- Push every commit immediately — no local-only commits may exist when work pauses or ends.
- **Your own changes MUST be committed and pushed before the turn ends.** This is the one thing the Stop hook enforces.

This rule overrides the default "never commit unless explicitly asked" behavior for changes Claude itself made in the current session.

## 2. Only touch what you changed

- Do not commit, push, stash, discard, or modify files you didn't change this session.
- Pre-existing dirt (uncommitted changes, untracked files, stale branches) is surfaced to the owner, not acted on. No silent stash, commit, or discard.

**Carve-out:** build artifacts orphaned by a change you made this session (e.g. `dist/`, `node_modules/`, `__pycache__/` left behind after deleting a tracked directory) may be cleaned up without asking — they're a direct consequence of your action.

## Worktree & PR workflow

Worktrees and PRs are the standard workflow, but lifecycle steps (enter, exit, merge, cleanup) are **user-initiated** — wait for the user to ask.

- When asked to merge a worktree PR, use `cc-merge-worktree <pr>` from the main worktree (not from inside the worktree being merged). It handles draft-flip, merge, branch + worktree removal.
- After `ExitWorktree`, the non-blocking `cc-exit-worktree-hook` surfaces dangling state — stale worktrees (merged branches still on disk) and orphan remote branches (PR merged, remote branch not deleted). Treat these as information for the user.
- First push of a feature branch should open a **draft PR**; flip to ready when the work is complete.

**Derived from cookbook:** [support-automation](../../../../agenticcookbook/principles/support-automation.md), [small-reversible-decisions](../../../../agenticcookbook/principles/small-reversible-decisions.md)
