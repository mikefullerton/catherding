---
name: good-skill
description: "A well-structured example skill for testing the linter. Triggers on 'test good skill' or /good-skill."
argument-hint: "<path>"
allowed-tools: Read, Glob, Grep
context: fork
---

## Version Check

If `$ARGUMENTS` is `--version`, respond with exactly:

> good-skill v1.0.0

Then stop.

Otherwise, print `good-skill v1.0.0` as the first line of output, then proceed.

---

# Good Skill

A focused skill that does one thing well: reads a file and summarizes it.

## Guards

- **Read-only**: Do NOT modify any files
- **Fail fast**: If the target path is invalid, stop with a clear error

## Step 1: Resolve the Target

Resolve `$ARGUMENTS` to a file path.

1. If `$ARGUMENTS` is a valid file path, use it.
2. If the file does not exist, print an error and stop.

## Step 2: Read and Summarize

1. Read the target file using the Read tool.
2. Print a summary of the file contents.

## Step 3: Verify

Confirm the summary was printed. The skill is complete.

## Error Handling

- If the file cannot be read, print: `ERROR: Could not read <path>`
- If `$ARGUMENTS` is empty, print: `ERROR: No file specified. Usage: /good-skill <path>`

## Example

```
/good-skill README.md
```
