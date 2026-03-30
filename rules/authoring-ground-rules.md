---
title: Authoring Ground Rules
version: 1.0.0
---

# Authoring Ground Rules

Foundation rule for ALL authoring — skills, agents, rules, cookbook content, code. Every other rule in this directory builds on these ground rules. Read and follow this rule first.

---

## 1. Confirm Context

If there is any ambiguity about which project, repo, or directory you should be working in, state the project name and confirm with the user before proceeding.

## 2. Understand Scope

The scope of work MUST be fully understood before starting. Restate what you are going to do and what you are NOT going to do. If scope is unclear, ask — do not infer. A clear scope statement prevents wasted work and unwanted changes.

## 3. Preserve Existing Work

If you encounter unfamiliar content in a file, investigate before overwriting — it may be in-progress work by the user or another session. Do not assume content you don't recognize is outdated or wrong.

## 4. No Unauthorized Changes

You MUST NOT remove, rename, or add anything without permission. Suggestions are welcome — present them, but do not act on them until approved. If the user asks to "fix X", fix X only. Do not also fix Y and Z.

## 5. Plan Before Acting

You MUST present a clear plan before taking action. The plan MUST state:

- What will change
- What will NOT change
- How to verify it worked

Do not begin implementation until the user has explicitly approved the plan. In non-interactive or automated contexts, log the plan and proceed only if `.cookbook/preferences.json` contains `"auto_approve_plans": true`.

## 6. Verify Every Action

Every action MUST have a verification step. If the verification method is not obvious, ask the user what "done" looks like before proceeding. After bulk operations (renames, restructures, migrations), grep for stale references. Do not mark work complete until verification passes.

## 7. Incremental Progress

Work in small steps. Verify and commit each step individually. Do not batch large changes — if something breaks, it should be easy to identify which change caused it. After each step, summarize what was added, modified, and removed.

## 8. When Uncertain, Ask

Do not guess at scope boundaries or which files/features are in play. When the task could reasonably go two ways, ask which one — don't pick silently.

---

## Self-Check

Before marking work complete, confirm:

- [ ] Scope was stated and followed — no unplanned additions or removals
- [ ] Plan was shown and approved before implementation began
- [ ] Existing content was investigated before overwriting
- [ ] Every change has a verification step that passed
- [ ] No unauthorized changes were made (nothing removed, renamed, or added beyond what was requested)
- [ ] Work was committed incrementally

---

## MUST NOT

- Do not start work without confirming you are in the correct project.
- Do not start work without a clear scope statement.
- Do not overwrite unfamiliar content without investigating it first.
- Do not remove, rename, or add anything the user did not ask for.
- Do not skip the plan step — even for "small" changes.
- Do not skip verification.
- Do not batch many changes into one large uncommitted set.
- Do not guess when you can ask.
