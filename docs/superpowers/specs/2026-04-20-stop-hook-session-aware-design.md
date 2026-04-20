# Session-aware Stop hook

## Problem

`cc-repo-hygiene-hook.py` blocks the Stop event on any staged, unstaged, or untracked file in the repo. It can't distinguish between:

1. Files the current Claude Code session edited and failed to commit (the case the hook is meant to catch).
2. Files left dirty by a prior session or an external process (out of scope for "only touch what you changed" — surfacing them every turn is noise).

Treating both cases identically causes Stop to block on state Claude didn't create, forcing the user to repeatedly dispose of pre-existing dirt before any session can end cleanly.

## Goal

Split Checks 1–3 (staged / unstaged / untracked) by session origin:

- **This session** touched the path → **block**, as today.
- **Another session** left it → **warn** via stderr, exit 0.

Checks 4–7 (merged branches, default-branch sync, stale worktrees) are session-agnostic and keep their current blocking behavior.

## Approach

### Session-touched detection

The Stop hook input JSON already contains `transcript_path`. The transcript is JSONL; each Claude tool invocation is a `tool_use` block with known parameters.

Build a set of paths this session touched by streaming the transcript:

1. For every `tool_use` with `name` in `{"Edit", "Write", "NotebookEdit"}`, add `input.file_path` to the set.
2. For every `tool_use` with `name == "Bash"`, treat `input.command` as a raw string. For each dirty path, check whether either its absolute form or its repo-relative form appears as a substring of the command. Any match adds that dirty path to the "this-session" set.

Path normalization:

- `Edit` / `Write` / `NotebookEdit` `file_path` inputs are absolute in Claude Code; resolve via `realpath` and compare directly to the absoluted dirty paths.
- Bash commands are free-form text and may reference paths as relative (e.g. `src/foo.py`) or absolute. Match each dirty path against the command string in both forms, so `git status`'s repo-relative paths and the user's natural invocations both classify correctly.

The Bash substring check is deliberately conservative — it errs toward classifying as this-session. False positives (warn-eligible paths promoted to block-eligible) are safe; false negatives (Claude-touched paths demoted to warn) are the dangerous direction because they'd let genuine session dirt slip past Stop with only a warning.

### Classification and output

After building the this-session set, partition the dirty paths from Checks 1–3:

| Dirty path | In this-session set | Action |
|---|---|---|
| Yes (staged/unstaged/untracked) | Yes | Add to `violations` → block (existing path) |
| Yes | No | Add to `warnings` → stderr, exit 0 |

Mixed case (some of each) → still block; the stderr warning is also printed so Claude sees both.

Output shape:

- **Block**: unchanged — `{"decision": "block", "reason": "Repo hygiene violations: ..."}` on stdout.
- **Warn-only**: stderr line `⚠ Uncommitted files from prior sessions (not blocking):` followed by one path per line, then exit 0.
- **Block + warn**: the block JSON on stdout and the warn block on stderr.

### Edge cases

- **Pre-dirty file that Claude also edited** — path is dirty AND in the transcript AND the snapshot of pre-session state would show it dirty. Classify as this-session (block). Rationale: editing a file that already had uncommitted changes from another session is itself the mistake; the fix is to commit the prior changes before editing. A file, once touched, is owned by this session regardless of its pre-existing state.

- **Transcript missing, unreadable, or malformed** — fail closed: treat the this-session set as "all dirty paths." This preserves current blocking behavior when we can't classify. Log a one-line stderr note so the failure is visible.

- **No dirty paths at all** — fast path: skip transcript parsing entirely.

- **Untracked files created by Bash redirects** — covered by the Bash substring check. If the user's session ran `python generate.py > out.json`, `out.json` appears in the Bash command string and classifies as this-session.

- **Paths outside the repo referenced in the transcript** — ignored; classification only considers paths returned by `git status`.

## Non-goals

- A PreToolUse hook that prevents editing already-dirty files from another session. Separate concern; if needed, a separate change.
- Per-file granular block/warn in the output. The existing check output lumps all staged/unstaged/untracked together; this change continues to lump within each bucket.
- Changing Checks 4–7.

## Testing

Tests live in `claude-optimizing/tests/` and use the existing pytest harness.

| Scenario | Expectation |
|---|---|
| Dirty path from this session only | Block, no warning |
| Dirty path from another session only | Exit 0, stderr warning with the path |
| Mixed: one of each | Block + stderr warning |
| Untracked from another session | Warn |
| Untracked from Bash redirect in this session | Block |
| Transcript missing | Block (fail closed) |
| Transcript malformed (bad JSON line) | Block (fail closed) |
| Pre-dirty file subsequently edited | Block |
| Checks 4–7 triggered while session set is empty | Block (unchanged behavior) |

Transcripts for tests can be synthetic JSONL fixtures — the hook only reads a subset of fields.

## Implementation sketch

New helper in `cc-repo-hygiene-hook.py`:

```
def _session_touched_paths(transcript_path, candidate_paths, cwd):
    # Returns subset of candidate_paths touched by tool_use entries.
    # Fail-closed on any error: return set(candidate_paths).
```

Main flow change around the existing Checks 1–3:

1. Collect `candidate_paths` = staged ∪ unstaged ∪ untracked (with absolute paths).
2. `touched = _session_touched_paths(transcript_path, candidate_paths, cwd)`.
3. Split each of staged/unstaged/untracked into `touched` / `untouched`.
4. Append `touched` buckets to `violations` with existing messages.
5. Append `untouched` paths to a new `warnings` list, emitted on stderr at end.

The blocking-output branch stays the same. A new stderr-emit step runs regardless of whether `violations` is empty.
