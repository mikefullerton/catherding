---
name: install-status-enhancements
description: "Install enhanced Claude Code status line with project info, git stats, worktree detection, and YOLO indicator"
version: "1.0.0"
argument-hint: "[--version]"
allowed-tools: Read, Write, Edit, Bash(chmod *), Bash(mkdir *), Bash(test *), AskUserQuestion
---

# Install Status Enhancements v1.0.0

Install an enhanced status line for Claude Code that shows project info, git branch/stats, worktree detection, and YOLO mode indicator.

## Startup

**CRITICAL**: Print the version line first:

install-status-enhancements v1.0.0

**Version check**: Read `${CLAUDE_SKILL_DIR}/SKILL.md` from disk and extract the `version:` field from frontmatter. Compare to this skill's version (1.0.0). If they differ, print:

> ⚠ This skill is running v1.0.0 but vA.B.C is installed. Restart the session to use the latest version.

Then continue running.

If `$ARGUMENTS` is `--version`, respond with exactly:
> install-status-enhancements v1.0.0

Then stop.

## Constants

- **Script source**: `${CLAUDE_SKILL_DIR}/references/statusline.sh`
- **Script destination**: `~/.claude/scripts/statusline.sh`
- **Settings file**: `~/.claude/settings.json`

## Install

### Step 1: Check current state

Read `~/.claude/settings.json`. Check if `statusLine` is already configured.

If it exists and references `statusline.sh`, print:

> Status line is already installed. Updating script to latest version.

### Step 2: Write script

Create the directory if needed: `mkdir -p ~/.claude/scripts`

Read the reference script from `${CLAUDE_SKILL_DIR}/references/statusline.sh`. Write it to `~/.claude/scripts/statusline.sh`.

Make it executable: `chmod +x ~/.claude/scripts/statusline.sh`

### Step 3: Configure settings.json

Read `~/.claude/settings.json`. If the `statusLine` key does not exist, add it:

```json
"statusLine": {
  "type": "command",
  "command": "$HOME/.claude/scripts/statusline.sh"
}
```

If it already exists and points to a different script, ask the user:

Use AskUserQuestion:
- "A status line is already configured pointing to a different script. Replace it?"
- Option 1: "Yes, replace with enhanced status line"
- Option 2: "No, keep existing"

If the user says no, print "Keeping existing status line." and stop.

### Step 4: Confirm

Print:

> Status line enhancements installed. Restart your session for changes to take effect.
>
> Features:
> - Project path (collapsed worktree paths)
> - Git branch with ahead/behind/dirty stats
> - Worktree indicator
> - YOLO mode indicator with restart detection
