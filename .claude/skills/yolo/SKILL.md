---
name: yolo
description: "Toggle per-session YOLO mode (auto-approve permissions with configurable deny list). Use when --dangerously-skip-permissions is broken. /yolo on, /yolo off, /yolo configure, /yolo status"
version: "4.4.0"
argument-hint: "[on|off|configure|status|--version]"
allowed-tools: Read, Edit, Write, Bash(chmod *), Bash(cat *), Bash(test *), Bash(mkdir *), Bash(rm *), Bash(find *), Bash(ls *), Bash(date *), Bash(jq *), AskUserQuestion
---

# YOLO Mode v4.4.0

Toggle a per-session PermissionRequest hook that auto-approves all tool calls — a workaround for broken `--dangerously-skip-permissions` in Claude Code v2.1.x.

Each session independently opts in. Other sessions are unaffected.

## Startup

**CRITICAL**: The very first thing you output MUST be the version line below. Print it BEFORE anything else — before the warning, before any tool calls, before any other text:

YOLO v4.4.0

**Version check**: Read `${CLAUDE_SKILL_DIR}/SKILL.md` from disk and extract the `version:` field from frontmatter. Compare to this skill's version (4.0.0). If they differ, print:

> ⚠ This skill is running v4.4.0 but vA.B.C is installed. Restart the session to use the latest version.

Then continue running.

If `$ARGUMENTS` is `--version`, respond with exactly:
> yolo v4.4.0

Then stop.

## Constants

- **Hook script path**: `~/.claude/hooks/yolo-approve-all.sh`
- **Cleanup script path**: `~/.claude/hooks/yolo-session-cleanup.sh`
- **Auto-start script path**: `~/.claude/hooks/yolo-session-start.sh`
- **Settings file**: `~/.claude/settings.json`
- **Marker directory**: `~/.claude-yolo-sessions/`
- **Session ID**: `${CLAUDE_SESSION_ID}`
- **Marker file**: `~/.claude-yolo-sessions/${CLAUDE_SESSION_ID}.json`
- **Deny config**: `~/.claude/yolo-deny.json`
- **Deny defaults**: `${CLAUDE_SKILL_DIR}/references/yolo-deny-defaults.json`

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

    YOLO v4.4.0

    <contents of warning.txt, verbatim, preserving all indentation>

Every line in the file is indented with 4+ spaces. Preserve this indentation exactly — it prevents markdown interpretation. Do NOT add code fences, do NOT strip indentation.

### Step 2: Ask for confirmation

Use AskUserQuestion:
- Question: "Enable YOLO mode for this session? This auto-approves ALL tool calls with no safety net."
- Option 1: "Yes, enable YOLO mode"
- Option 2: "No, cancel"

If the user selects "No, cancel", print "YOLO mode not enabled." and stop.

### Step 3: Check current state

Check if the marker file `~/.claude-yolo-sessions/${CLAUDE_SESSION_ID}.json` already exists. If it does, print:

> YOLO mode is already enabled for this session.

Then stop.

### Step 4: One-time hook install

This step ensures the PermissionRequest and SessionEnd hooks are permanently installed. It is idempotent — safe to run every time.

**Track whether hooks were just installed**: Before modifying settings.json, note whether the PermissionRequest hook was already present. Store this as a boolean `HOOKS_ALREADY_INSTALLED` (true if already present, false if you had to add it). This determines the `needs_restart` field in Step 5.

#### Step 4a: Hook scripts

Check if `~/.claude/hooks/` directory exists. If not, create it with `mkdir -p`.

Write the following to `~/.claude/hooks/yolo-approve-all.sh`:

```bash
#!/bin/bash
# YOLO mode hook (v4) — per-session auto-approve via marker files
# Reads session_id from stdin JSON, checks ~/.claude-yolo-sessions/{session_id}.json
# If no marker exists, falls through to normal permission prompt (exit 1)

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty')
TOOL=$(echo "$INPUT" | jq -r '.tool_name // empty')
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# No session ID = can't check marker, fall through
if [ -z "$SESSION_ID" ]; then
  exit 1
fi

MARKER="$HOME/.claude-yolo-sessions/${SESSION_ID}.json"

# No marker = YOLO not active for this session
if [ ! -f "$MARKER" ]; then
  exit 1
fi

# Read deny list path from marker (fallback to global)
DENY_FILE=$(jq -r '.deny_list // empty' "$MARKER" 2>/dev/null)
[ -z "$DENY_FILE" ] && DENY_FILE="$HOME/.claude/yolo-deny.json"
DENY_FILE="${DENY_FILE/#\~/$HOME}"

# No deny file = approve everything
if [ ! -f "$DENY_FILE" ]; then
  echo '{"hookSpecificOutput":{"hookEventName":"PermissionRequest","decision":{"behavior":"allow"}}}'
  exit 0
fi

# Check deny rules
DENIED=""
while IFS= read -r rule; do
  MATCHER=$(echo "$rule" | jq -r '.matcher // empty')
  PATTERN=$(echo "$rule" | jq -r '.pattern // empty')
  REASON=$(echo "$rule" | jq -r '.reason // empty')

  if [ "$MATCHER" != "$TOOL" ]; then
    continue
  fi

  if [ -z "$PATTERN" ]; then
    DENIED="$REASON"
    break
  fi

  if echo "$COMMAND" | grep -qE "$PATTERN"; then
    DENIED="$REASON"
    break
  fi
done < <(jq -c '.deny[]' "$DENY_FILE" 2>/dev/null)

if [ -n "$DENIED" ]; then
  exit 1
else
  echo '{"hookSpecificOutput":{"hookEventName":"PermissionRequest","decision":{"behavior":"allow"}}}'
  exit 0
fi
```

Make it executable: `chmod +x ~/.claude/hooks/yolo-approve-all.sh`

Write the following to `~/.claude/hooks/yolo-session-cleanup.sh`:

```bash
#!/bin/bash
# YOLO session cleanup — runs on SessionEnd
# Deletes this session's marker file and cleans stale markers >24h old

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty')

# Delete this session's marker
if [ -n "$SESSION_ID" ]; then
  rm -f "$HOME/.claude-yolo-sessions/${SESSION_ID}.json"
fi

# Stale cleanup: delete markers older than 24h
find "$HOME/.claude-yolo-sessions" -name "*.json" -mtime +1 -delete 2>/dev/null

exit 0
```

Make it executable: `chmod +x ~/.claude/hooks/yolo-session-cleanup.sh`

Write the following to `~/.claude/hooks/yolo-session-start.sh`:

```bash
#!/bin/bash
# YOLO auto-enable — runs on SessionStart
# If CLAUDE_YOLO=1 is set, creates a session marker file automatically

[ "$CLAUDE_YOLO" != "1" ] && exit 0

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty')

[ -z "$SESSION_ID" ] && exit 0

MARKER_DIR="$HOME/.claude-yolo-sessions"
MARKER="${MARKER_DIR}/${SESSION_ID}.json"

# Already exists (e.g. resumed session)
[ -f "$MARKER" ] && exit 0

mkdir -p "$MARKER_DIR"

CWD=$(echo "$INPUT" | jq -r '.cwd // empty')

cat > "$MARKER" <<MARKER_EOF
{
  "session_id": "${SESSION_ID}",
  "enabled_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "project": "${CWD}",
  "deny_list": "~/.claude/yolo-deny.json",
  "auto_enabled": true,
  "needs_restart": false
}
MARKER_EOF

exit 0
```

Make it executable: `chmod +x ~/.claude/hooks/yolo-session-start.sh`

#### Step 4b: Settings.json hooks

Read `~/.claude/settings.json`.

**PermissionRequest hook**: Check if `hooks.PermissionRequest` exists and contains a hook with command referencing `yolo-approve-all.sh`. If NOT present, add:

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

**SessionEnd cleanup hook**: Check if `hooks.SessionEnd` already has a hook with command referencing `yolo-session-cleanup.sh`. If NOT present, add a new hook entry to the EXISTING SessionEnd matcher's hooks array:

```json
{
  "type": "command",
  "command": "$HOME/.claude/hooks/yolo-session-cleanup.sh"
}
```

Do NOT create a second SessionEnd matcher entry. Append to the existing one's hooks array.

**SessionStart auto-enable hook**: Check if `hooks.SessionStart` already has a hook with command referencing `yolo-session-start.sh`. If NOT present, add a new hook entry to the EXISTING SessionStart matcher's hooks array:

```json
{
  "type": "command",
  "command": "$HOME/.claude/hooks/yolo-session-start.sh"
}
```

Do NOT create a second SessionStart matcher entry. Append to the existing one's hooks array.

If the `hooks` key does not exist, create it. Do NOT overwrite existing hook entries.

#### Step 4c: Deny config

Check if `~/.claude/yolo-deny.json` exists. If not, copy the defaults from `${CLAUDE_SKILL_DIR}/references/yolo-deny-defaults.json` to `~/.claude/yolo-deny.json`.

If it already exists, leave it as-is (user may have customized it).

Print: "Deny list: ~/.claude/yolo-deny.json (N rules). Use /yolo configure to edit."

### Step 5: Create session marker

Create the marker directory if it doesn't exist: `mkdir -p ~/.claude-yolo-sessions`

Write the session marker file to `~/.claude-yolo-sessions/${CLAUDE_SESSION_ID}.json`:

```json
{
  "session_id": "${CLAUDE_SESSION_ID}",
  "enabled_at": "<current ISO 8601 timestamp>",
  "project": "<current working directory>",
  "deny_list": "~/.claude/yolo-deny.json",
  "needs_restart": <true if HOOKS_ALREADY_INSTALLED is false, otherwise false>
}
```

Use `date -u +%Y-%m-%dT%H:%M:%SZ` for the timestamp.

Set `needs_restart` based on whether hooks were already installed BEFORE this invocation (from the `HOOKS_ALREADY_INSTALLED` flag in Step 4). If hooks were already present, the session loaded them at startup and YOLO works immediately — no restart needed.

### Step 6: Confirm

If `needs_restart` is true, print:

> YOLO mode enabled. Restart this session for it to take effect.
>
> Hooks are loaded at session start — they can't activate mid-session. After restarting, YOLO will auto-approve all permissions (except deny-listed items) for this session only.

If `needs_restart` is false, print:

> YOLO mode enabled for this session. All permissions will be auto-approved (except deny-listed items).

---

## Disable

Print: "Disabling YOLO mode for this session..."

### Step 1: Check current state

Check if the marker file `~/.claude-yolo-sessions/${CLAUDE_SESSION_ID}.json` exists. If it does NOT exist, print:

> YOLO mode is already disabled for this session.

Then stop.

### Step 2: Delete marker file

Delete the marker file: `rm -f ~/.claude-yolo-sessions/${CLAUDE_SESSION_ID}.json`

### Step 3: Confirm

Print:

> YOLO mode disabled for this session. Permission prompts restored.

Do NOT remove hooks from settings.json — they stay permanently installed.

---

## Status

### Step 1: Check session marker

Check if the marker file `~/.claude-yolo-sessions/${CLAUDE_SESSION_ID}.json` exists.

### Step 2: Count active sessions

Count all marker files: `ls ~/.claude-yolo-sessions/*.json 2>/dev/null | wc -l`

### Step 3: Report

If marker exists for this session, read the marker file and print:

> YOLO mode is **ON** for this session.

If the marker contains `"auto_enabled": true`, also print:

> (auto-enabled via CLAUDE_YOLO=1)

Also read `~/.claude/yolo-deny.json` and print the deny list summary:

> Deny list (N rules): ExitPlanMode, git push --force, git reset --hard, ...

If other sessions also have markers (count > 1), add:

> N other session(s) also have YOLO active.

If marker does NOT exist for this session, print:

> YOLO mode is **OFF** for this session. Use `/yolo on` to enable.

If other sessions have markers (count > 0), add:

> N other session(s) have YOLO active.

### Step 4: Hook status

Check if `hooks.PermissionRequest` exists in `~/.claude/settings.json` referencing `yolo-approve-all.sh`.

If installed, print:

> Hooks: installed (permanent)

If NOT installed, print:

> Hooks: not installed. Run `/yolo on` to install.

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

---

## Auto-Enable via Environment Variable

After running `/yolo on` at least once (which installs hooks permanently), YOLO can be auto-enabled for new sessions by setting `CLAUDE_YOLO=1`:

```bash
CLAUDE_YOLO=1 claude
```

The SessionStart hook checks for this environment variable and creates the session marker file automatically — no `/yolo on` needed. The session still gets full deny-list protection and auto-cleanup on exit.

Suggested shell alias:

```bash
alias claude-yolo='CLAUDE_YOLO=1 claude'
```
