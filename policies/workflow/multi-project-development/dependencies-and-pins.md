---
title: "Dependencies and Pins"
summary: "Dependency repos are cloned inside the consumer and gitignored; a dependencies.json manifest records intent and pins."
triggers: [multi-project-setup, dependency-manifest, dependencies-json, adding-dependency, replacing-submodule]
tags: [multi-project, dependencies, dependencies-json, manifest, pins]
---

# Dependencies and Pins

When one repo depends on another repo's source (not a binary release), the consumer MUST clone the dependency inside itself at `dependencies/<name>/` and track it via a `dependencies.json` manifest at the repo root.

## Why this, not submodules or peer directories

- **Submodules** are brittle: `.git` file awkwardness, worktree quirks, forced rigid SHA pinning that doesn't match real dev flow, easy to desync.
- **Peer directories** (sibling dirs under `~/projects/active/`) break because Xcode/SPM use relative paths from the consumer — one consumer's layout conflicts with another's, and each consumer's state leaks into shared siblings.
- **Dependency repos inside the consumer** give stable relative paths, no cross-pollution between consumers, and an explicit human-readable snapshot of what the consumer is building against.

## Layout

- Every dependency is cloned at `dependencies/<repo-basename>/` (repo URL basename minus `.git`).
- `dependencies/` MUST be in `.gitignore`. The clone is not tracked by the consumer.
- `dependencies.json` MUST live at the repo root (sibling of README). It is committed.

## `dependencies.json` schema

The file is a JSON array of entries:

```json
[
  {
    "repo": "git@github.com:agentic-cookbook/agentictoolkit.git",
    "branch": "dependents/whippet",
    "last-sha": "227052b7da9769da975fd3fc39c64d8a78381ec2",
    "tag": "v0.1.0",
    "ci-guidance": {
      "mode": "sha",
      "sha": "227052b7da9769da975fd3fc39c64d8a78381ec2"
    }
  }
]
```

| Field | Required | Meaning |
|---|---|---|
| `repo` | yes | Git URL (SSH or HTTPS). Clone source. |
| `branch` | yes | The branch the consumer tracks. May be `main`, a `dependents/<consumer>` integration branch, or any other branch. See [dependents-branch-pattern](dependents-branch-pattern.md). |
| `last-sha` | yes | SHA the consumer was last known to build against. Always populated, even when `tag` is set. Updated by `cc-deps-bump`. |
| `tag` | no | Optional named pin. When present, `cc-deps-sync --lock` may resolve the tag instead of `last-sha`. Useful for external deps where tags are the stable surface. |
| `ci-guidance` | no | How CI should materialize the dep. `mode`: `"sha"` \| `"branch"` \| `"tag"`, with a matching sibling field (`sha`, `branch`, or `tag`). If absent, CI defaults to `mode: sha` using `last-sha`. |

## Identity and uniqueness

- An entry's identity is its `repo` URL.
- The on-disk clone directory name is the URL basename minus `.git`.
- Two entries MUST NOT share a clone directory.

**Derived from cookbook:** [explicit-over-implicit](../../../../agenticcookbook/principles/explicit-over-implicit.md), [small-reversible-decisions](../../../../agenticcookbook/principles/small-reversible-decisions.md)
