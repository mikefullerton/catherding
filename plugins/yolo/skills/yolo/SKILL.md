---
name: yolo
description: "Toggle per-session YOLO mode (auto-approve permissions with configurable deny list). Use when --dangerously-skip-permissions is broken. /yolo on, /yolo off, /yolo configure, /yolo status"
version: "4.5.0"
argument-hint: "[on|off|configure|status|--version]"
allowed-tools: Read, Edit, Write, Bash(bash *), Bash(chmod *), Bash(cat *), Bash(test *), Bash(mkdir *), Bash(rm *), Bash(find *), Bash(ls *), Bash(date *), Bash(jq *), Bash(~/.claude-status-line/progress/update-progress.sh *), Bash($HOME/.claude-status-line/progress/update-progress.sh *), AskUserQuestion
model: sonnet
---

# YOLO Mode v4.5.0

Toggle a per-session PermissionRequest hook that auto-approves all tool calls — a workaround for broken `--dangerously-skip-permissions` in Claude Code v2.1.x.

Each session independently opts in. Other sessions are unaffected.

## Startup

**Step 0 — Ensure permissions**: Run `bash ${CLAUDE_SKILL_DIR}/references/ensure-permissions.sh ${CLAUDE_SKILL_DIR}/SKILL.md` to whitelist this skill's tools in `~/.claude/settings.json`. This is silent and idempotent.

**CRITICAL**: The very first thing you output MUST be the version line:

YOLO v4.5.0

If `$ARGUMENTS` is `--version`, respond with exactly:
> yolo v4.5.0

Then stop.

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

    YOLO v4.5.0

    <contents of warning.txt, verbatim, preserving all indentation>

Every line in the file is indented with 4+ spaces. Preserve this indentation exactly — it prevents markdown interpretation. Do NOT add code fences, do NOT strip indentation.

### Step 2: Ask for confirmation

Use AskUserQuestion:
- Question: "Enable YOLO mode for this session? This auto-approves ALL tool calls with no safety net."
- Option 1: "Yes, enable YOLO mode"
- Option 2: "No, cancel"

If the user selects "No, cancel", print "YOLO mode not enabled." and stop.

### Step 3: Run enable script

Run the enable script in a single command:

```bash
bash ${CLAUDE_SKILL_DIR}/references/yolo-enable.sh "${CLAUDE_SESSION_ID}" "${CLAUDE_SKILL_DIR}"
```

This script atomically: checks if already enabled, installs hook scripts, updates settings.json hooks, sets up status line indicator, copies deny defaults, and creates the session marker. It outputs JSON.

### Step 4: Report result

Parse the JSON output:

- `{"status":"already_enabled"}` → Print: "YOLO mode is already enabled for this session."
- `{"status":"enabled","needs_restart":true,...}` → Print:
  > YOLO mode enabled. Restart this session for it to take effect.
  >
  > Hooks are loaded at session start — they can't activate mid-session.

- `{"status":"enabled","needs_restart":false,...}` → Print:
  > YOLO mode enabled for this session. All permissions will be auto-approved (except deny-listed items).

Also print: "Deny list: ~/.claude-yolo-sessions/yolo-deny.json (N rules). Use /yolo configure to edit." using `deny_count` from the output.

---

## Disable

### Step 1: Run disable script

```bash
bash ${CLAUDE_SKILL_DIR}/references/yolo-disable.sh "${CLAUDE_SESSION_ID}"
```

### Step 2: Report result

- `{"status":"already_disabled"}` → Print: "YOLO mode is already disabled for this session."
- `{"status":"disabled"}` → Print: "YOLO mode disabled for this session. Permission prompts restored."

---

## Status

### Step 1: Run status script

```bash
bash ${CLAUDE_SKILL_DIR}/references/yolo-status.sh "${CLAUDE_SESSION_ID}"
```

### Step 2: Report result

Parse the JSON output and print:

If `active` is true:
> YOLO mode is **ON** for this session.

If `auto_enabled` is true, add: "(auto-enabled via CLAUDE_YOLO=1)"

> Deny list (N rules): <deny_summary>

If `other_sessions` > 0: "N other session(s) also have YOLO active."

If `active` is false:
> YOLO mode is **OFF** for this session. Use `/yolo on` to enable.

If `other_sessions` > 0: "N other session(s) have YOLO active."

If `hooks_installed`: "Hooks: installed (permanent)"
Else: "Hooks: not installed. Run `/yolo on` to install."

---

## Configure

Show and edit the YOLO deny list.

### Step 1: Read current config

Read `~/.claude-yolo-sessions/yolo-deny.json`. If it doesn't exist, print "No deny list found. Run /yolo on to create one." and stop.

### Step 2: Show current rules

Print the current deny rules as a numbered list:

    YOLO Deny List (~/.claude-yolo-sessions/yolo-deny.json)

    1. ExitPlanMode — User should review the plan before execution
    2. Bash: git push --force — Force push is destructive
    ...

### Step 3: Ask what to do

Use AskUserQuestion:
- "What would you like to do?"
- Option 1: "Add a rule" — ask for matcher (tool name), pattern (regex), and reason
- Option 2: "Remove a rule" — show numbered list, ask which to remove
- Option 3: "Reset to defaults" — copy defaults from `${CLAUDE_SKILL_DIR}/references/yolo-deny-defaults.json`
- Option 4: "Done" — stop

After each add/remove, write the updated config to `~/.claude-yolo-sessions/yolo-deny.json` and loop back to Step 2.

---

## Auto-Enable via Environment Variable

After running `/yolo on` at least once (which installs hooks permanently), YOLO can be auto-enabled for new sessions by setting `CLAUDE_YOLO=1`:

```bash
CLAUDE_YOLO=1 claude
```

Suggested shell alias:

```bash
alias claude-yolo='CLAUDE_YOLO=1 claude'
```
