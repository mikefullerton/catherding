---
name: install-worktree-rule
version: "1.0.0"
description: "Install or uninstall the worktree-and-PR git workflow rule into a project. Triggers on 'install worktree rule', 'add worktree rule', or /install-worktree-rule."
argument-hint: "[--uninstall] [--version]"
disable-model-invocation: true
allowed-tools: Read, Write, Bash(mkdir *), Bash(ls *), Glob
model: haiku
---

## Version Check

If `$ARGUMENTS` is `--version`, respond with exactly:

> install-worktree-rule v1.0.0

Then stop.

Otherwise, print `install-worktree-rule v1.0.0` as the first line of output, then proceed.

**Version check**: Read `${CLAUDE_SKILL_DIR}/SKILL.md` from disk and extract the `version:` field from frontmatter. Compare to this skill's version (1.0.0). If they differ, print:

> ⚠ This skill is running v1.0.0 but vA.B.C is installed. Restart the session to use the latest version.

Continue running — do not stop.

---

# Install Worktree Rule

Installs the `always-use-worktrees-and-prs.md` rule into the current project's `.claude/rules/` directory. This rule enforces a structured git workflow: every change goes through a worktree, a draft PR, incremental commits, and a squash merge.

## Uninstall Mode

If `$ARGUMENTS` contains `--uninstall`:

1. Check if `.claude/rules/always-use-worktrees-and-prs.md` exists.
2. If it exists, delete it. Print:
   ```
   ✓ Removed .claude/rules/always-use-worktrees-and-prs.md
   ```
3. If it does not exist, print:
   ```
   Nothing to remove — .claude/rules/always-use-worktrees-and-prs.md not found.
   ```
4. Stop.

## Install Mode (default)

### Step 1: Check Prerequisites

1. Verify the current directory is a git repository (check for `.git/` or `.git` file).
   - If not, print `ERROR: Not a git repository.` and stop.

2. Check if `.claude/rules/always-use-worktrees-and-prs.md` already exists.
   - If it exists, read it and compare to the bundled version at `${CLAUDE_SKILL_DIR}/references/always-use-worktrees-and-prs.md`.
   - If identical, print `Already installed and up to date.` and stop.
   - If different, print `Updating .claude/rules/always-use-worktrees-and-prs.md to latest version.` and continue to Step 2.

### Step 2: Install the Rule

1. Create `.claude/rules/` if it doesn't exist.
2. Read the rule content from `${CLAUDE_SKILL_DIR}/references/always-use-worktrees-and-prs.md`.
3. Write it to `.claude/rules/always-use-worktrees-and-prs.md`.

### Step 3: Verify and Report

1. Confirm the file exists and is non-empty.
2. Print:
   ```
   ✓ Installed .claude/rules/always-use-worktrees-and-prs.md

   This rule enforces:
     • All work in git worktrees (never commit to main directly)
     • Draft PR created before any code
     • Atomic commits pushed after each change
     • Squash merge and worktree cleanup

   To remove: /install-worktree-rule --uninstall
   ```

## Error Handling

- If the Write tool fails, print the error and stop.
- If the directory creation fails, print the error and stop.
