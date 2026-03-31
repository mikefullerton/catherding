---
name: uninstall-status-enhancements
description: "Remove enhanced Claude Code status line script and configuration"
version: "1.1.0"
argument-hint: "[--version]"
allowed-tools: Read, Edit, Bash(rm *), Bash(test *), AskUserQuestion
---

# Uninstall Status Enhancements v1.0.0

Remove the enhanced status line script and configuration.

## Startup

**CRITICAL**: Print the version line first:

uninstall-status-enhancements v1.1.0

**Version check**: Read `${CLAUDE_SKILL_DIR}/SKILL.md` from disk and extract the `version:` field from frontmatter. Compare to this skill's version (1.0.0). If they differ, print:

> ⚠ This skill is running v1.0.0 but vA.B.C is installed. Restart the session to use the latest version.

Then continue running.

If `$ARGUMENTS` is `--version`, respond with exactly:
> uninstall-status-enhancements v1.1.0

Then stop.

## Constants

- **Script path**: `~/.claude/scripts/statusline.sh`
- **Cleanup script path**: `~/.claude/scripts/repo-cleanup-status.sh`
- **Settings file**: `~/.claude/settings.json`

## Uninstall

### Step 1: Check current state

Read `~/.claude/settings.json`. Check if `statusLine` exists and references `statusline.sh`.

If `statusLine` does not exist or references a different script, print:

> Enhanced status line is not installed. Nothing to remove.

Then stop.

### Step 2: Remove config

Read `~/.claude/settings.json`. Remove the `statusLine` key entirely. Preserve all other settings.

### Step 3: Remove script

Delete the script files: `rm -f ~/.claude/scripts/statusline.sh ~/.claude/scripts/repo-cleanup-status.sh`

### Step 4: Confirm

Print:

> Status line enhancements removed. Restart your session for changes to take effect.
