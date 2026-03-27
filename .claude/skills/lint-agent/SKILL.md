---
name: lint-agent
description: "Lint a Claude Code agent against best practices. Triggers on 'lint this agent', 'check my agent', 'review this agent', or /lint-agent."
argument-hint: "<path-to-agent-file>"
allowed-tools: Read, Glob, Grep, WebFetch, Bash(wc *)
context: fork
---

## Version Check

If `$ARGUMENTS` is `--version`, respond with exactly:

> lint-agent v1.0

Then stop. Do not continue with the rest of the skill.

---

# Lint Agent

Lint a Claude Code agent file against best practices and structural requirements. Produces a structured report with PASS/WARN/FAIL ratings and actionable recommendations.

## Guards

- **Read-only**: Do NOT modify any files in the reviewed target
- **No output files**: Print the review report to the console only
- **Fail fast**: If the target path is invalid or is not an agent file, stop immediately with a clear error

---

## Step 1: Resolve the Target

Use `$ARGUMENTS` as the path to the agent to review.

### If `$ARGUMENTS` is provided:
1. Check if the path points to a `.md` file — read its frontmatter
2. If it contains agent frontmatter (`tools`, `disallowedTools`, `permissionMode`, `maxTurns`) — it's an **agent**
3. If it contains skill frontmatter or is a directory with `SKILL.md`, print an error:
   ```
   ERROR: Not an agent — detected a skill. Use /lint-skill instead.
   ```
4. If it's a plain `.md` without agent frontmatter, it may be a rule:
   ```
   ERROR: Not an agent — no agent frontmatter found. Use /lint-rule instead.
   ```

### If `$ARGUMENTS` is empty:
1. Check if the current directory is inside `.claude/agents/` and contains a `.md` file — use it
2. If nothing found, print an error and **STOP**:
   ```
   ERROR: No agent found. Provide a path: /lint-agent <path>
   ```

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
