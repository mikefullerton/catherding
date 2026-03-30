---
name: yolo
description: "Toggle yolo mode (auto-approve all permissions). Use when --dangerously-skip-permissions is broken. /yolo on, /yolo off, /yolo status"
version: "1.3.0"
argument-hint: "[on|off|status|--version]"
allowed-tools: Read, Edit, Write, Bash(chmod *), Bash(cat *), Bash(test *), Bash(mkdir *), AskUserQuestion
---

# Yolo Mode v1.3.0

Toggle a PermissionRequest hook that auto-approves all tool calls — a workaround for broken `--dangerously-skip-permissions` in Claude Code v2.1.x.

## Startup

yolo v1.3.0

**Version check**: Read `${CLAUDE_SKILL_DIR}/SKILL.md` from disk and extract the `version:` field from frontmatter. Compare to this skill's version (1.3.0). If they differ, print:

> ⚠ This skill is running v1.3.0 but vA.B.C is installed. Restart the session to use the latest version.

Then continue running.

If `$ARGUMENTS` is `--version`, respond with exactly:
> yolo v1.3.0

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
| `status` or empty | Go to **Status** |
| `--version` | Print version (handled in Startup) |
| anything else | Print: "Usage: /yolo [on\|off\|status\|--version]" and stop |

---

## Enable

### Step 1: Show warning

Print this warning box exactly (uses ASCII box chars for consistent rendering):

```
+---------------------------------------------------------------+
|                                                               |
|                  ☠  HERE BE DRAGONS  ☠                        |
|                                                               |
|                   ___====-_  _-====___                        |
|             _--^^^#####//      \\#####^^^--_                  |
|          _-^##########// (    ) \\##########^-_               |
|         -############//  |\^^/|  \\############-              |
|       _/############//   (@::@)   \\############\_            |
|      /#############((     \\//     ))#############\           |
|     -###############\\    (oo)    //###############-          |
|    -#################\\  / VV \  //#################-         |
|   -###################\\/      \//###################-        |
|  _#/|##########/\######(   /\   )######/\##########|\#_       |
|  |/ |#/\#/\#/\/  \#/\##\  /  \  /##/\#/  \/\#/\#/\#| \|       |
|  `  |/  V  V '   V  \#\| |    | |/#/  V   ' V  V  \|  '       |
|   `   `   `      `   / | |    | | \   '      '  '   '         |
|                     (  | |    | |  )                          |
|                    __\ | |____| | /__                         |
|                    (vvv(VVV)(VVV)vvv)                         |
|                                                               |
|  Yolo mode auto-approves ALL permission prompts               |
|  with zero safety checks.                                     |
|                                                               |
|  This means Claude can:                                       |
|    - Run any shell command                                    |
|    - Edit or delete any file                                  |
|    - Push to any remote                                       |
|    - Do anything -- without asking                            |
|                                                               |
|  Workaround for known bugs:                                   |
|    anthropics/claude-code#40241                               |
|    anthropics/claude-code#40136                               |
|                                                               |
|  --dangerously-skip-permissions docs:                         |
|  https://code.claude.com/docs/en/permission-modes             |
|                                                               |
+---------------------------------------------------------------+
```

### Step 2: Ask for confirmation

Use AskUserQuestion:
- Question: "Enable yolo mode? This auto-approves ALL tool calls with no safety net."
- Option 1: "Yes, enable yolo mode"
- Option 2: "No, cancel"

If the user selects "No, cancel", print "Yolo mode not enabled." and stop.

### Step 3: Check current state

Read `~/.claude/settings.json`. If `hooks.PermissionRequest` already exists and contains a hook with command referencing `yolo-approve-all.sh`, print:

> Yolo mode is already enabled.

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

> ☠ Yolo mode enabled. All permission prompts will be auto-approved.
>
> If prompts still appear, restart your session for the hook to take effect.

---

## Disable

### Step 1: Check current state

Read `~/.claude/settings.json`. If `hooks.PermissionRequest` does not exist or does not contain a hook referencing `yolo-approve-all.sh`, print:

> Yolo mode is already disabled.

Then stop.

### Step 2: Remove hook from settings.json

Read `~/.claude/settings.json`. Remove the `PermissionRequest` key from `hooks`. Preserve all other hooks.

### Step 3: Confirm

Print:

> Yolo mode disabled. Permission prompts restored.

Do NOT delete the hook script file — it's harmless on disk and avoids needing to recreate it next time.

---

## Status

### Step 1: Check settings

Read `~/.claude/settings.json`. Check if `hooks.PermissionRequest` exists and contains a hook with command referencing `yolo-approve-all.sh`.

### Step 2: Report

If enabled, print:

> ☠ Yolo mode is **ON**. All permission prompts are auto-approved.

If disabled, print:

> Yolo mode is **OFF**. Normal permission prompts are active.
