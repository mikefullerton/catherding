---
title: "Dependents Branch Pattern"
summary: "Internal dependencies SHOULD maintain a per-consumer dependents/<consumer> branch so each consumer tracks upstream at its own cadence."
triggers: [dependents-branch, integration-branch, consumer-tracking, absorbing-upstream-changes]
tags: [multi-project, dependencies, branching, internal-deps, integration-branch]
---

# Dependents Branch Pattern

For internal dependencies (repos we control), each consumer SHOULD use a dedicated integration branch in the dependency that serves as that consumer's "main". Specified per-entry in `dependencies.json` via the `branch` field.

## What it is

In the dependency repo, a long-lived branch named `dependents/<consumer>` (e.g. `dependents/whippet`). The consumer's `dependencies.json` has `"branch": "dependents/whippet"` and tracks that branch, not the dependency's actual `main`.

## Who maintains it

The consumer owns the maintenance cost. The consumer merges upstream `main` into `dependents/<consumer>` on its own cadence — usually when it's ready to absorb those changes. WIP feature branches in the dependency branch off and merge back to `dependents/<consumer>`, not to `main`.

## Why

- Consumer absorbs upstream changes when it is ready to, not every commit.
- WIP can branch from a stable-for-that-consumer point.
- Multiple consumers can diverge briefly without blocking each other.
- The `last-sha` in `dependencies.json` stays meaningful — the consumer's tracked branch is, by definition, the set of changes the consumer has integrated.

All dependency-sharing schemes pay this maintenance cost somewhere. This pattern concentrates it on the consumer, which has context on what it's ready to absorb.

## When to use it

- **Internal deps only.** Requires write access to the dependency repo. External deps fall back to `branch: main` plus a SHA or `tag` pin.
- **Multi-consumer deps benefit most.** For a dep with one consumer, `branch: main` + auto-bump is simpler. Add the `dependents/<consumer>` branch when a second active consumer appears or when the consumer needs to stabilize against an older upstream point.

## How it's expressed

In `dependencies.json`, set the entry's `branch`:

```json
{
  "repo": "git@github.com:agentic-cookbook/agentictoolkit.git",
  "branch": "dependents/whippet",
  "last-sha": "..."
}
```

All tooling (`cc-deps-sync`, `cc-deps-bump`, `cc-deps-verify`) uses this field. The dependency repo itself MUST have a `dependents/<consumer>` branch published for every consumer listed in any `dependencies.json` that targets it.

**Derived from cookbook:** [optimize-for-change](../../../../agenticcookbook/principles/optimize-for-change.md)
