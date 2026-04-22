---
title: "Dependency Workflow"
summary: "Ritual for working with dependency repos: sync, branch inside, merge-then-bump across repos."
triggers: [dependency-workflow, dependency-bump, cross-repo-change, syncing-dependencies, editing-dependency]
tags: [multi-project, dependencies, workflow, bumping, cross-repo]
---

# Dependency Workflow

Day-to-day ritual for consumer repos that use `dependencies.json`. Applies to projects under `~/projects/`. External repos where you don't control the upstream are out of scope — treat them as read-only pins.

## Initial setup (fresh clone)

After cloning a consumer repo for the first time, run:

```
cc-deps-sync
```

This reads `dependencies.json` and clones each entry into `dependencies/<name>/` on the branch named in the manifest, at `last-sha`. Build should work immediately after.

## Editing code inside a dependency

When changes are needed in `dependencies/<name>/`:

1. **Always branch off the tracked branch.** `cd dependencies/<name> && git switch -c feature/<topic> origin/<branch>`. Never edit on detached HEAD; the dep must remain publishable.
2. **Do NOT `EnterWorktree` inside a dependency clone.** The consumer build expects the dep at `dependencies/<name>/`; a worktree lives at a different path the consumer won't see.
3. Push the feature branch and open a PR against the dependency repo.

## Cross-repo change flow

A change that spans both the consumer and a dependency MUST land in this order:

1. Merge the dependency PR to the dependency's tracked branch first.
2. In the consumer, run `cc-deps-bump <name>` to advance `last-sha` to the merged SHA.
3. Commit and push the bump as part of the consumer PR.
4. Only then mark the consumer PR ready.

The rationale: the consumer MUST NOT point at a SHA that is not reachable from the dependency's published `<branch>`. Other clones would fetch a pin they can't resolve. The Stop hook (`cc-dependencies-hook.py`) enforces this.

## Bumping

- `cc-deps-bump <name>` — reads the current HEAD SHA of `dependencies/<name>/` and writes it to `last-sha` in `dependencies.json`.
- `cc-deps-bump --all` — bump every entry.
- `cc-deps-bump --verify` — after writing, confirm the new SHA is reachable from `origin/<branch>`.

The bump is a normal commit in the consumer, and MUST accompany any consumer change that depends on new behavior in the dep.

## Verification

- `cc-deps-verify` reports per-entry whether `last-sha` is an ancestor of `origin/<branch>`, whether `tag` (if set) resolves to `last-sha`, and whether `ci-guidance` is internally consistent.
- The `cc-dependencies-hook` Stop-event hook blocks turn-end on any of these failures.

**Derived from cookbook:** [fail-fast](../../../../agenticcookbook/principles/fail-fast.md)
