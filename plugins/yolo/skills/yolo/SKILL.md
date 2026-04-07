---
name: yolo
description: "Toggle per-session YOLO mode (auto-approve permissions with configurable deny list). Use when --dangerously-skip-permissions is broken. /yolo on, /yolo off, /yolo install, /yolo uninstall, /yolo configure, /yolo status"
version: "5.0.0"
argument-hint: "[on|off|install|uninstall|configure|status|--version]"
allowed-tools: Read, Edit, Write, Bash(bash *), Bash(chmod *), Bash(cat *), Bash(test *), Bash(mkdir *), Bash(rm *), Bash(find *), Bash(ls *), Bash(date *), Bash(jq *), Bash(~/.claude-status-line/progress/update-progress.py *), Bash($HOME/.claude-status-line/progress/update-progress.py *), AskUserQuestion
model: sonnet
---

# YOLO Mode v5.0.0

Per-session auto-approve for all tool calls — a workaround for broken `--dangerously-skip-permissions` in Claude Code v2.1.x.

Each session independently opts in. Other sessions are unaffected.

## Startup

**Step 0 — Ensure permissions**: Run `bash ${CLAUDE_SKILL_DIR}/references/ensure-permissions.sh ${CLAUDE_SKILL_DIR}/SKILL.md` to whitelist this skill's tools in `~/.claude/settings.json`. This is silent and idempotent.

**CRITICAL**: The very first thing you output MUST be the version line:

YOLO v5.0.0

If `$ARGUMENTS` is `--version`, respond with exactly:
> yolo v5.0.0

Then stop.

## Route by argument

| `$ARGUMENTS` | Action |
|---|---|
| `on` | Go to **Enable** |
| `off` | Go to **Disable** |
| `install` | Go to **Install** |
| `uninstall` | Go to **Uninstall** |
| `configure` | Go to **Configure** |
| `status` or empty | Go to **Status** |
| `--version` | Print version (handled in Startup) |
| anything else | Print: "Usage: /yolo [on\|off\|install\|uninstall\|configure\|status\|--version]" and stop |

---

## Enable

Enables YOLO for the current session. If hooks aren't installed yet, auto-installs them first (with warning + confirmation).

### Step 1: Check if hooks are installed

```bash
jq -e '.hooks.PermissionRequest[]?.hooks[]? | select(.command | contains("yolo-approve-all"))' ~/.claude/settings.json >/dev/null 2>&1
```

If this succeeds, hooks are installed — skip to Step 3.

If this fails, hooks need to be installed. Go to Step 2.

### Step 2: Auto-install (only if hooks not installed)

This path runs only on first use. Show the warning and confirm before installing.

Read `${CLAUDE_SKILL_DIR}/references/warning.txt` FIRST (using the Read tool). Then output a single text block that starts with the version line followed by the file contents:

    YOLO v5.0.0

    <contents of warning.txt, verbatim, preserving all indentation>

Every line in the file is indented with 4+ spaces. Preserve this indentation exactly — it prevents markdown interpretation. Do NOT add code fences, do NOT strip indentation.

Use AskUserQuestion:
- Question: "YOLO hooks are not installed. Install and enable for this session? This auto-approves ALL tool calls with no safety net."
- Option 1: "Yes, install and enable"
- Option 2: "No, cancel"

If the user selects "No, cancel", print "YOLO mode not enabled." and stop.

### Step 3: Run enable script

```bash
bash ${CLAUDE_SKILL_DIR}/references/yolo-enable.sh "${CLAUDE_SESSION_ID}" "${CLAUDE_SKILL_DIR}"
```

This script auto-installs if needed and creates the session marker. It outputs JSON.

### Step 4: Report result

Parse the JSON output:

- `{"status":"already_enabled"}` → Print: "YOLO mode is already enabled for this session."
- `fresh_install` is true and `needs_restart` is true → Print:
  > YOLO mode enabled. Restart this session for it to take effect.
  >
  > Hooks are loaded at session start — they can't activate mid-session.

- `needs_restart` is false → Print:
  > YOLO mode **ON**.

Also print: "Deny list: N rules. Use /yolo configure to edit." using `deny_count` from the output.

---

## Disable

### Step 1: Run disable script

```bash
bash ${CLAUDE_SKILL_DIR}/references/yolo-disable.sh "${CLAUDE_SESSION_ID}"
```

### Step 2: Report result

- `{"status":"already_disabled"}` → Print: "YOLO mode is already off."
- `{"status":"disabled"}` → Print: "YOLO mode **OFF**. Permission prompts restored."

---

## Install

Installs YOLO hooks, statusline indicator, and deny defaults without enabling a session. Useful for pre-installing so `CLAUDE_YOLO=1` works on first launch.

### Step 1: Show warning

Read `${CLAUDE_SKILL_DIR}/references/warning.txt` FIRST (using the Read tool). Then output a single text block that starts with the version line followed by the file contents:

    YOLO v5.0.0

    <contents of warning.txt, verbatim, preserving all indentation>

Every line in the file is indented with 4+ spaces. Preserve this indentation exactly — it prevents markdown interpretation. Do NOT add code fences, do NOT strip indentation.

### Step 2: Ask for confirmation

Use AskUserQuestion:
- Question: "Install YOLO hooks? This adds PermissionRequest, SessionStart, and SessionEnd hooks to settings.json."
- Option 1: "Yes, install hooks"
- Option 2: "No, cancel"

If the user selects "No, cancel", print "YOLO hooks not installed." and stop.

### Step 3: Run install script

```bash
bash ${CLAUDE_SKILL_DIR}/references/yolo-install.sh "${CLAUDE_SKILL_DIR}"
```

### Step 4: Report result

Parse the JSON output:

- `{"status":"already_installed",...}` → Print: "YOLO hooks are already installed. Deny list: N rules."
- `{"status":"installed",...}` → Print:
  > YOLO hooks installed. Restart any active sessions for hooks to take effect.
  >
  > Deny list: ~/.claude-yolo-sessions/yolo-deny.json (N rules). Use /yolo configure to edit.
  >
  > Use `/yolo on` to enable for a session, or launch with `CLAUDE_YOLO=1 claude`.

---

## Uninstall

Removes YOLO hooks from settings.json, deletes hook scripts, and removes the statusline indicator.

### Step 1: Run uninstall script (without --all first, to check)

```bash
bash ${CLAUDE_SKILL_DIR}/references/yolo-uninstall.sh
```

If `{"status":"not_installed"}`, print "YOLO hooks are not installed. Nothing to remove." and stop.

### Step 2: Report what was removed

Print: "YOLO hooks uninstalled. Removed from settings.json, hook scripts, and statusline."

### Step 3: Ask about session data

Use AskUserQuestion:
- Question: "Also remove deny list and session data (~/.claude-yolo-sessions/)?"
- Option 1: "Yes, remove everything"
- Option 2: "No, keep deny list and session data"

If "Yes", run:

```bash
bash ${CLAUDE_SKILL_DIR}/references/yolo-uninstall.sh --all
```

Print: "Session data removed."

If "No", print: "Deny list and session data kept at ~/.claude-yolo-sessions/."

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

If `hooks_installed`: "Hooks: installed"
Else: "Hooks: not installed. Run `/yolo install` to set up."

---

## Configure

Show and edit the YOLO deny list.

### Step 1: Read current config

Read `~/.claude-yolo-sessions/yolo-deny.json`. If it doesn't exist, print "No deny list found. Run /yolo install to create one." and stop.

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

After running `/yolo install` (or `/yolo on` which auto-installs), YOLO can be auto-enabled for new sessions by setting `CLAUDE_YOLO=1`:

```bash
CLAUDE_YOLO=1 claude
```

Suggested shell alias:

```bash
alias claude-yolo='CLAUDE_YOLO=1 claude'
```
