---
name: lint-skill
description: "Lint a Claude Code skill against best practices. Triggers on 'lint this skill', 'check my skill', 'review this skill', or /lint-skill."
argument-hint: "[path-or-name]"
allowed-tools: Read, Glob, Grep, WebFetch, Bash(wc *), AskUserQuestion
context: fork
---

## Version Check

If `$ARGUMENTS` is `--version`, respond with exactly:

> lint-skill v1.1.0

Then stop. Do not continue with the rest of the skill.

Otherwise, print `lint-skill v1.1.0` as the first line of output, then proceed.

**Version check**: Read `${CLAUDE_SKILL_DIR}/SKILL.md` from disk and extract the `version:` field from frontmatter. If it differs from this skill's version (1.0.1), print:

> ⚠ This skill is running v1.1.0 but vA.B.C is installed. Restart the session to use the latest version.

Continue running — do not stop.

---

# Lint Skill

Lint a Claude Code skill against best practices and structural requirements. Produces a structured report with PASS/WARN/FAIL ratings and actionable recommendations.

## Guards

- **Read-only**: Do NOT modify any files in the reviewed target
- **No output files**: Print the review report to the console only
- **Fail fast**: If the target path is invalid or has no `SKILL.md`, stop immediately with a clear error

---

## Step 1: Resolve the Target

Resolve `$ARGUMENTS` to a skill directory containing `SKILL.md`.

### If `$ARGUMENTS` is provided:

1. **Path check**: If `$ARGUMENTS` contains `/` or points to a directory:
   - If the path is a directory containing `SKILL.md`, use it.
   - If the path points directly to a `SKILL.md` file, use its parent directory.
   - If no `SKILL.md` found, check if it's an agent or rule file and print a helpful error:
     ```
     ERROR: Not a skill — no SKILL.md found. Use /lint-agent or /lint-rule instead.
     ```

2. **Search string**: Otherwise, treat `$ARGUMENTS` as a search string. Use Glob to find `.claude/skills/*/SKILL.md`. Filter to directories whose name contains the search string (case-insensitive).
   - **1 match** → Use it. Print: "Found: <path>"
   - **Multiple matches** → Show up to 4 matches with AskUserQuestion. Each option label is the skill name, description is the directory path.
   - **0 matches** → Print "No skills matching '<string>'" and stop.

### If `$ARGUMENTS` is empty:

1. **Session context**: Check if a skill was recently created, edited, or read in this conversation. If so, offer it with AskUserQuestion: "Lint <skill-name>?" with options "Yes" and "No, choose another".

2. **Current directory**: Check if the current directory contains `SKILL.md` — use it.

3. **Prompt**: If nothing found, use AskUserQuestion: "Which skill? Enter a name or path." The user's response re-enters the search string flow above.

---

## Step 2: Read All Target Files

1. Read `SKILL.md`
2. Read all files in the skill directory recursively (references/, scripts/, examples/)
3. Parse the YAML frontmatter — extract all fields
4. Count the total lines of `SKILL.md`
5. List all supporting files found

Print a brief header:
```
=== LINT: <name> ===
Type: Skill
Path: <path>
Files: <count> (<file list>)
Lines: <SKILL.md line count>
```

---

## Step 3: Fetch Latest Anthropic Guidance

Fetch these URLs using WebFetch to get the latest official guidance:

1. `https://code.claude.com/docs/en/skills`
2. `https://code.claude.com/docs/en/best-practices`

If any fetch fails, note it and continue with the bundled checklist alone.

---

## Step 4: Run the Review

Load the review criteria:
- Read `${CLAUDE_SKILL_DIR}/references/skill-checklist.md`
- Read `${CLAUDE_SKILL_DIR}/references/skill-structure-reference.md`

Evaluate every criterion from the checklist against the target. For each check:

1. Determine the result: **PASS**, **WARN**, **FAIL**, or **N/A**
2. For WARN and FAIL results, write a specific finding explaining what's wrong
3. For WARN and FAIL results, write an actionable recommendation
4. For subjective checks (C01 single responsibility, B02 native capabilities), explain your reasoning and prefer WARN over FAIL when uncertain

---

## Step 5: Print the Review Report

```
--- STRUCTURE & FORMAT ---
[PASS] S01: YAML frontmatter present
[FAIL] S06: SKILL.md exceeds 500 lines (currently 627)
       -> Move detailed content to references/ files
[WARN] S10: $ARGUMENTS used but no argument-hint in frontmatter
       -> Add argument-hint: "<expected-input>" to frontmatter
...

--- CONTENT QUALITY ---
[PASS] C01: Single responsibility — clear, focused purpose
[WARN] C04: No error handling instructions found
       -> Add guidance for what to do when <specific scenario> fails
...

--- BEST PRACTICES ---
[PASS] B01: Verification method provided
[WARN] B03: Side-effect skill without disable-model-invocation
       -> Add disable-model-invocation: true to prevent auto-invocation
...
```

After all sections, print the summary:

```
=== SUMMARY ===
Pass: <n> | Warn: <n> | Fail: <n> | N/A: <n>
```

If there are any WARN or FAIL results, print a prioritized recommendations list (FAILs first, then WARNs, max 10).

---

## Step 6: Done

The review is complete. Do not modify any files.
