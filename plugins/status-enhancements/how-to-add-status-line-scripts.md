# How to Add Status Line Scripts

The status line pipeline at `~/.claude-status-line/` is composable. Any project or plugin can register its own script to contribute information to the Claude Code status line.

## Architecture

```
~/.claude-status-line/
  dispatcher.sh          # Entry point — chains scripts from pipeline.json
  pipeline.json          # Ordered list of scripts to run
  scripts/               # Convention: scripts live here
    base-info.sh         # Built-in: project path, git, model, costs
    repo-cleanup.sh      # Built-in: stale branches, worktree warnings
    yolo-indicator.sh    # Example: YOLO mode indicator (installed by /yolo on)
```

The `dispatcher.sh` is configured as the Claude Code `statusLine` command. It reads `pipeline.json` and runs each script in order, threading a JSON object through the chain.

## Pipeline JSON

```json
{
  "pipeline": [
    {"name": "base-info", "script": "~/.claude-status-line/scripts/base-info.sh"},
    {"name": "repo-cleanup", "script": "~/.claude-status-line/scripts/repo-cleanup.sh"},
    {"name": "yolo-indicator", "script": "~/.claude-status-line/scripts/yolo-indicator.sh"}
  ]
}
```

Scripts run top-to-bottom. Each receives the output of the previous one.

## Script Protocol

Every script receives JSON on stdin and must output JSON on stdout.

### Input

```json
{
  "claude": { /* full claude status JSON — model, context_window, cost, cwd, session_id, etc. */ },
  "lines": ["line 1 so far", "line 2 so far"]
}
```

The `claude` object is the raw status data from Claude Code. The `lines` array contains whatever previous scripts have built up.

### Output

```json
{
  "lines": ["line 1 maybe modified", "line 2 maybe modified"]
}
```

Return only the `lines` array. The dispatcher replaces the current lines with your output.

### Rules

- Read from stdin with `INPUT=$(cat)`
- Parse with `jq` — it's available in all Claude Code environments
- If you have nothing to add, pass through the existing lines unchanged
- Exit 0 on success — non-zero exits or invalid JSON are silently skipped
- Keep execution fast (under 200ms) — the status line refreshes frequently
- Use ANSI colors for styling (the terminal supports 256-color)

## Minimal Example

A script that appends a deployment indicator to line 1:

```bash
#!/bin/bash
INPUT=$(cat)
LINES=$(echo "$INPUT" | jq -c '.lines')

# Check if a deploy is in progress
if [ -f /tmp/deploy-in-progress ]; then
  ORANGE=$'\033[38;5;214m'
  RED=$'\033[38;5;210m'
  RST=$'\033[0m'
  SEP=" ${ORANGE}|${RST} "
  LINES=$(echo "$LINES" | jq -c --arg s "${SEP}${RED}deploying...${RST}" '.[0] = (.[0] // "") + $s')
fi

echo "{\"lines\":$LINES}"
```

## Real Example: YOLO Indicator

The YOLO plugin's `yolo-indicator.sh` checks if YOLO mode is active for the current session and appends `☠ YOLO` to line 1. See `plugins/yolo/skills/yolo/references/yolo-indicator.sh` for the full implementation.

## How to Install a Script from Another Project

To register a new status line script from a skill or automation:

### 1. Write the script to the scripts directory

```bash
mkdir -p ~/.claude-status-line/scripts
# Write your script to ~/.claude-status-line/scripts/my-indicator.sh
chmod +x ~/.claude-status-line/scripts/my-indicator.sh
```

### 2. Register in pipeline.json

Read `~/.claude-status-line/pipeline.json`. Check if your entry already exists (match by `name`). If not, append it to the `pipeline` array:

```json
{"name": "my-indicator", "script": "~/.claude-status-line/scripts/my-indicator.sh"}
```

Write the updated JSON back.

### 3. Guard against missing pipeline

If `~/.claude-status-line/pipeline.json` does not exist, the status line pipeline is not installed. Skip registration silently — don't create the pipeline from scratch.

### 4. Uninstall cleanly

When uninstalling, remove your entry from `pipeline.json` and delete your script. Do not remove other entries or the pipeline directory itself.

## Common Patterns

### Appending to line 1 (project/git line)

```bash
LINES=$(echo "$LINES" | jq -c --arg s " | my text" '.[0] = (.[0] // "") + $s')
```

### Appending to line 2 (model/stats line)

```bash
LINES=$(echo "$LINES" | jq -c --arg s " | my text" '.[1] = (.[1] // "") + $s')
```

### Adding a new line

```bash
LINES=$(echo "$LINES" | jq -c --arg s "my new line" '. + [$s]')
```

### Reading claude status data

```bash
CLAUDE=$(echo "$INPUT" | jq -r '.claude')
MODEL_ID=$(echo "$CLAUDE" | jq -r '.model.id // ""')
SESSION_ID=$(echo "$CLAUDE" | jq -r '.session_id // ""')
CWD=$(echo "$CLAUDE" | jq -r '.cwd // ""')
```

### ANSI color palette (matching built-in scripts)

```bash
BLUE=$'\033[38;5;117m'
YELLOW=$'\033[38;5;229m'
GREEN=$'\033[38;5;151m'
ORANGE=$'\033[38;5;214m'
RED=$'\033[38;5;210m'
DIM=$'\033[38;5;245m'
RST=$'\033[0m'
```
