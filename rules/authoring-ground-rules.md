# Authoring Ground Rules

Foundation rule for ALL authoring — skills, agents, rules, cookbook content, code. Every other rule in this directory builds on these ground rules. Read and follow this rule first.

---

## 1. Confirm Context

You MUST verify you are in the correct project directory before making any changes. State the project name. If there is any ambiguity about which project, repo, or directory you should be working in, confirm with the user before proceeding. Never assume the current working directory is correct.

## 2. Understand Scope

The scope of work MUST be fully understood before starting. Restate what you are going to do and what you are NOT going to do. If scope is unclear, ask — do not infer. A clear scope statement prevents wasted work and unwanted changes.

## 3. Read Before Writing

You MUST NOT modify a file you have not read. Understand existing content before changing it. If you encounter unfamiliar content, investigate before overwriting — it may be in-progress work by the user or another session.

## 4. No Unauthorized Changes

You MUST NOT remove, rename, or add anything without permission. Suggestions are welcome — present them, but do not act on them until approved. If the user asks to "fix X", fix X only. Do not also fix Y and Z.

## 5. Plan Before Acting

You MUST present a clear plan before taking action. The plan MUST state:

- What will change
- What will NOT change
- How to verify it worked

Do not begin implementation until the user has seen the plan.

## 6. Verify Every Action

Every action MUST have a verification step. If the verification method is not obvious, ask the user what "done" looks like before proceeding. After bulk operations (renames, restructures, migrations), grep for stale references. Do not mark work complete until verification passes.

## 7. Incremental Progress

Work in small steps. Verify and commit each step individually. Do not batch large changes — if something breaks, it should be easy to identify which change caused it. After each step, summarize what was added, modified, and removed.

## 8. When Uncertain, Ask

Do not guess at intent, file paths, project names, or scope boundaries. A question takes seconds; undoing wrong work takes much longer. "I'm not sure if you want X or Y" is always better than silently choosing wrong.

---

## MUST NOT

- Do not start work without confirming you are in the correct project.
- Do not start work without a clear scope statement.
- Do not modify files you have not read.
- Do not remove, rename, or add anything the user did not ask for.
- Do not skip the plan step — even for "small" changes.
- Do not skip verification.
- Do not batch many changes into one large uncommitted set.
- Do not guess when you can ask.
