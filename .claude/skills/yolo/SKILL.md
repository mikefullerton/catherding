---
name: yolo
description: "Toggle YOLO mode (auto-approve permissions with configurable deny list). Use when --dangerously-skip-permissions is broken. /yolo on, /yolo off, /yolo configure, /yolo status"
version: "3.0.0"
argument-hint: "[on|off|configure|status|--version]"
allowed-tools: Read, Edit, Write, Bash(chmod *), Bash(cat *), Bash(test *), Bash(mkdir *), AskUserQuestion
---

# YOLO Mode v3.0.0

Toggle a PermissionRequest hook that auto-approves all tool calls — a workaround for broken `--dangerously-skip-permissions` in Claude Code v2.1.x.

## Startup

**CRITICAL**: The very first thing you output MUST be the version line below. Print it BEFORE anything else — before the warning, before any tool calls, before any other text:

YOLO v3.0.0

**Version check**: Read `${CLAUDE_SKILL_DIR}/SKILL.md` from disk and extract the `version:` field from frontmatter. Compare to this skill's version (3.0.0). If they differ, print:

> ⚠ This skill is running v3.0.0 but vA.B.C is installed. Restart the session to use the latest version.

Then continue running.

If `$ARGUMENTS` is `--version`, respond with exactly:
> yolo v3.0.0

Then stop.

## Constants

- **Hook script path**: `~/.claude/hooks/yolo-approve-all.sh`
- **Settings file**: `~/.claude/settings.json`
- **Hook key**: `PermissionRequest`

## Route by argument

| `$ARGUMENTS` | Action |
|---|---|
| `on` | Go to **Enable** |
| `off` | Go to **Disable** |
| `configure` | Go to **Configure** |
| `status` or empty | Go to **Status** |
| `--version` | Print version (handled in Startup) |
| anything else | Print: "Usage: /yolo [on\|off\|configure\|status\|--version]" and stop |

---

## Enable

### Step 1: Show warning

Read `${CLAUDE_SKILL_DIR}/references/warning.txt` FIRST (using the Read tool). Then output a single text block that starts with the version line followed by the file contents:

    YOLO v3.0.0

    <contents of warning.txt, verbatim, preserving all indentation>

Every line in the file is indented with 4+ spaces. Preserve this indentation exactly — it prevents markdown interpretation. Do NOT add code fences, do NOT strip indentation.

### Step 2: Ask for confirmation

Use AskUserQuestion:
- Question: "Enable YOLO mode? This auto-approves ALL tool calls with no safety net."
- Option 1: "Yes, enable YOLO mode"
- Option 2: "No, cancel"

If the user selects "No, cancel", print "YOLO mode not enabled." and stop.

### Step 3: Check current state

Read `~/.claude/settings.json`. If `hooks.PermissionRequest` already exists and contains a hook with command referencing `yolo-approve-all.sh`, print:

> YOLO mode is already enabled.

Then stop.

### Step 4: Create hook script

Check if `~/.claude/hooks/` directory exists. If not, create it with `mkdir -p`.

Write the following to `~/.claude/hooks/yolo-approve-all.sh`:

```bash
#!/bin/bash
echo '{"hookSpecificOutput":{"hookEventName":"PermissionRequest","decision":{"behavior":"allow"}}}'
exit 0
```

Make it executable: `chmod +x ~/.claude/hooks/yolo-approve-all.sh`

### Step 4b: Create deny config

Check if `~/.claude/yolo-deny.json` exists. If not, copy the defaults from `${CLAUDE_SKILL_DIR}/references/yolo-deny-defaults.json` to `~/.claude/yolo-deny.json`.

If it already exists, leave it as-is (user may have customized it).

Print: "Deny list: ~/.claude/yolo-deny.json (N rules). Use /yolo configure to edit."

### Step 5: Add hook to settings.json

Read `~/.claude/settings.json`. Add the following under the `hooks` key, preserving all existing hooks:

```json
"PermissionRequest": [
  {
    "matcher": "",
    "hooks": [
      {
        "type": "command",
        "command": "$HOME/.claude/hooks/yolo-approve-all.sh"
      }
    ]
  }
]
```

If the `hooks` key does not exist, create it. Do NOT overwrite existing hook entries (SessionStart, UserPromptSubmit, etc.).

### Step 6: Confirm

Print:

> YOLO mode enabled. All permission prompts will be auto-approved.
>
> If prompts still appear, restart your session for the hook to take effect.

---

## Disable

Print: "Disabling YOLO mode..."

### Step 1: Check current state

Read `~/.claude/settings.json`. If `hooks.PermissionRequest` does not exist or does not contain a hook referencing `yolo-approve-all.sh`, print:

> YOLO mode is already disabled.

Then stop.

### Step 2: Remove hook from settings.json

Read `~/.claude/settings.json`. Remove the `PermissionRequest` key from `hooks`. Preserve all other hooks.

### Step 3: Confirm

Print:

> YOLO mode disabled. Permission prompts restored.

Do NOT delete the hook script file — it's harmless on disk and avoids needing to recreate it next time.

---

## Status

### Step 1: Check settings

Read `~/.claude/settings.json`. Check if `hooks.PermissionRequest` exists and contains a hook with command referencing `yolo-approve-all.sh`.

### Step 2: Report

If enabled, print:

> YOLO mode is **ON**. All permission prompts are auto-approved (except deny-listed items).

If disabled, print:

> YOLO mode is **OFF**. Normal permission prompts are active.

If enabled, also read `~/.claude/yolo-deny.json` and print the deny list summary:

> Deny list (N rules): ExitPlanMode, git push --force, git reset --hard, ...

---

## Configure

Show and edit the YOLO deny list.

### Step 1: Read current config

Read `~/.claude/yolo-deny.json`. If it doesn't exist, print "No deny list found. Run /yolo on to create one." and stop.

### Step 2: Show current rules

Print the current deny rules as a numbered list:

    YOLO Deny List (~/.claude/yolo-deny.json)

    1. ExitPlanMode — User should review the plan before execution
    2. Bash: git push --force — Force push is destructive
    3. Bash: git reset --hard — Discards uncommitted work
    ...

### Step 3: Ask what to do

Use AskUserQuestion:
- "What would you like to do?"
- Option 1: "Add a rule" — ask for matcher (tool name), pattern (regex), and reason
- Option 2: "Remove a rule" — show numbered list, ask which to remove
- Option 3: "Reset to defaults" — copy defaults from `${CLAUDE_SKILL_DIR}/references/yolo-deny-defaults.json`
- Option 4: "Done" — stop

After each add/remove, write the updated config to `~/.claude/yolo-deny.json` and loop back to Step 2.
