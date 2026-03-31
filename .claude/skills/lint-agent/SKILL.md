---
name: lint-agent
description: "Lint a Claude Code agent against best practices. Triggers on 'lint this agent', 'check my agent', 'review this agent', or /lint-agent."
argument-hint: "[path-or-name]"
allowed-tools: Read, Glob, Grep, WebFetch, Bash(wc *), AskUserQuestion
context: fork
---

## Version Check

If `$ARGUMENTS` is `--version`, respond with exactly:

> lint-agent v1.1.0

Then stop. Do not continue with the rest of the skill.

Otherwise, print `lint-agent v1.1.0` as the first line of output, then proceed.

**Version check**: Read `${CLAUDE_SKILL_DIR}/SKILL.md` from disk and extract the `version:` field from frontmatter. If it differs from this skill's version (1.0.1), print:

> ⚠ This skill is running v1.1.0 but vA.B.C is installed. Restart the session to use the latest version.

Continue running — do not stop.

---

# Lint Agent

Lint a Claude Code agent file against best practices and structural requirements. Produces a structured report with PASS/WARN/FAIL ratings and actionable recommendations.

## Guards

- **Read-only**: Do NOT modify any files in the reviewed target
- **No output files**: Print the review report to the console only
- **Fail fast**: If the target path is invalid or is not an agent file, stop immediately with a clear error

---

## Step 1: Resolve the Target

Resolve `$ARGUMENTS` to an agent `.md` file.

### If `$ARGUMENTS` is provided:

1. **Path check**: If `$ARGUMENTS` contains `/` or ends with `.md`, treat it as a file path.
   - If the file exists, validate it:
     - Read its frontmatter. If it contains agent frontmatter (`tools`, `disallowedTools`, `permissionMode`, `maxTurns`) — it's an **agent**, use it.
     - If it contains skill frontmatter or is a directory with `SKILL.md`, print: `ERROR: Not an agent — detected a skill. Use /lint-skill instead.` and stop.
     - If it's a plain `.md` without agent frontmatter: `ERROR: Not an agent — no agent frontmatter found. Use /lint-rule instead.` and stop.
   - If the file doesn't exist, print "File not found: <path>" and stop.

2. **Search string**: Otherwise, treat `$ARGUMENTS` as a search string. Use Glob to find `.claude/agents/*.md`. Filter to files whose name contains the search string (case-insensitive).
   - **1 match** → Use it. Print: "Found: <path>"
   - **Multiple matches** → Show up to 4 matches with AskUserQuestion. Each option label is the filename, description is the relative path.
   - **0 matches** → Print "No agents matching '<string>'" and stop.

### If `$ARGUMENTS` is empty:

1. **Session context**: Check if an agent file was recently created, edited, or read in this conversation. If so, offer it with AskUserQuestion: "Lint <filename>?" with options "Yes" and "No, choose another".

2. **Current directory**: Check if the current directory is inside `.claude/agents/` and contains a `.md` file — use it.

3. **Prompt**: If nothing found, use AskUserQuestion: "Which agent? Enter a name or path." The user's response re-enters the search string flow above.

---

## Step 2: Read the Target

1. Read the agent `.md` file
2. Parse the YAML frontmatter — extract all fields
3. Count the total lines

Print a brief header:
```
=== LINT: <name> ===
Type: Agent
Path: <path>
Lines: <line count>
```

---

## Step 3: Fetch Latest Anthropic Guidance

Fetch these URLs using WebFetch to get the latest official guidance:

1. `https://code.claude.com/docs/en/sub-agents`
2. `https://code.claude.com/docs/en/best-practices`

If any fetch fails, note it and continue with the bundled checklist alone.

---

## Step 4: Run the Review

Load the review criteria:
- Read `${CLAUDE_SKILL_DIR}/references/agent-checklist.md`
- Read `${CLAUDE_SKILL_DIR}/references/agent-structure-reference.md`

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
[WARN] S05: Description could use more natural trigger keywords
       -> Add phrases users would say when requesting this agent
...

--- CONTENT QUALITY ---
[PASS] C01: Single responsibility — clear, focused purpose
[WARN] C04: No error handling instructions found
       -> Add guidance for what to do when <specific scenario> fails
...

--- BEST PRACTICES ---
[PASS] B01: Verification method provided
[WARN] B07: No scoping for file exploration — agent could read unbounded files
       -> Add limits on exploration scope
...

--- AGENT CRITERIA ---
[PASS] A01: name and description present
[WARN] A06: No maxTurns set — agent could run indefinitely
       -> Add maxTurns: <suggested-value> for bounded execution
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
