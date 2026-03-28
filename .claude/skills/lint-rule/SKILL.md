---
name: lint-rule
description: "Lint a Claude Code rule file against best practices. Triggers on 'lint this rule', 'check my rule', 'review this rule', or /lint-rule."
argument-hint: "<path-to-rule-file>"
allowed-tools: Read, Glob, Grep, WebFetch, Bash(wc *)
context: fork
---

## Version Check

If `$ARGUMENTS` is `--version`, respond with exactly:

> lint-rule v1.0.1

Then stop. Do not continue with the rest of the skill.

Otherwise, print `lint-rule v1.0.1` as the first line of output, then proceed.

**Version check**: Read `${CLAUDE_SKILL_DIR}/SKILL.md` from disk and extract the `version:` field from frontmatter. If it differs from this skill's version (1.0.1), print:

> ⚠ This skill is running v1.0.1 but vA.B.C is installed. Restart the session to use the latest version.

Continue running — do not stop.

---

# Lint Rule

Lint a Claude Code rule file against best practices and structural requirements. Produces a structured report with PASS/WARN/FAIL ratings and actionable recommendations.

## Guards

- **Read-only**: Do NOT modify any files in the reviewed target
- **No output files**: Print the review report to the console only
- **Fail fast**: If the target path is invalid or is not a rule file, stop immediately with a clear error

---

## Step 1: Resolve the Target

Use `$ARGUMENTS` as the path to the rule file to review.

### If `$ARGUMENTS` is provided:
1. Check if the path points to a `.md` file
2. Read its frontmatter — if it contains skill frontmatter (`allowed-tools`, `argument-hint`, `context`) or agent frontmatter (`tools`, `disallowedTools`, `permissionMode`), it is NOT a rule. Print an error and **STOP**:
   ```
   ERROR: Not a rule file — detected <skill|agent> frontmatter. Use /lint-skill or /lint-agent instead.
   ```
3. If it's a directory containing `SKILL.md`, it's a skill. Print an error and **STOP**.
4. Otherwise, treat it as a rule file.

### If `$ARGUMENTS` is empty:
1. Check if the current directory contains a `.md` rule file
2. If nothing found, print an error and **STOP**:
   ```
   ERROR: No rule file found. Provide a path: /lint-rule <path>
   ```

---

## Step 2: Read the Target

1. Read the rule `.md` file
2. Count the total lines
3. Parse YAML frontmatter if present (not required for rules)

Print a brief header:
```
=== LINT: <filename> ===
Type: Rule
Path: <path>
Lines: <line count>
```

---

## Step 3: Fetch Latest Anthropic Guidance

Fetch this URL using WebFetch to get the latest official guidance:

1. `https://code.claude.com/docs/en/best-practices`

If the fetch fails, note it and continue with the bundled checklist alone.

---

## Step 4: Run the Review

Load the review criteria:
- Read `${CLAUDE_SKILL_DIR}/references/rule-checklist.md`
- Read `${CLAUDE_SKILL_DIR}/references/rule-structure-reference.md`

Evaluate every criterion from the checklist against the target. For each check:

1. Determine the result: **PASS**, **WARN**, **FAIL**, or **N/A**
2. For WARN and FAIL results, write a specific finding explaining what's wrong
3. For WARN and FAIL results, write an actionable recommendation

---

## Step 5: Print the Review Report

```
--- CONTENT QUALITY ---
[PASS] C01: Single responsibility — clear, focused purpose
[FAIL] C04: Vague directive found — "handle errors appropriately"
       -> Replace with specific instructions for each error case
...

--- RULE CRITERIA ---
[PASS] R01: Clear title/heading present
[FAIL] R05: File references not explicit — says "read the principles" without listing paths
       -> List every file path the LLM must read
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
