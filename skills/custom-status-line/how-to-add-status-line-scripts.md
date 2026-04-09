# How to Add Status Line Scripts

The status line pipeline at `~/.claude-status-line/` is composable. Any project or plugin can register its own script to contribute information to the Claude Code status line.

## Architecture

```
~/.claude-status-line/
  statusline/            # Python package (dispatcher + built-in modules)
    dispatcher.py        # Entry point — runs pipeline stages
    base_info.py         # Built-in: project path, git, model, costs
    repo_cleanup.py      # Built-in: stale branches, worktree warnings
    progress_display.py  # Built-in: per-session progress bar
    formatting.py        # Shared: ANSI colors, column alignment
    db.py                # Shared: SQLite usage tracking
  pipeline.json          # Ordered list of pipeline stages
  scripts/               # Convention: external drop-in scripts live here
    yolo-indicator.sh    # Example: YOLO mode indicator (installed by /yolo on)
```

The Python dispatcher is configured as the Claude Code `statusLine` command. It reads `pipeline.json` and runs each stage in order. Built-in modules are called as Python functions; external scripts are called via subprocess.

## Pipeline JSON

```json
{
  "pipeline": [
    {"name": "base-info", "module": "base_info"},
    {"name": "repo-cleanup", "module": "repo_cleanup"},
    {"name": "progress-display", "module": "progress_display"},
    {"name": "yolo-indicator", "script": "~/.claude-status-line/scripts/yolo-indicator.sh"}
  ]
}
```

Stages run top-to-bottom. Built-in modules use `"module"` keys (Python functions). External drop-in scripts use `"script"` keys (any executable language).

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

### Using the progress bar

The built-in progress display renders a boxed progress bar below the status lines. Use the helper script — no need to write a pipeline script:

```bash
# Update progress (each call prints output to trigger status line refresh)
~/.claude-status-line/progress/update-progress.py "Building App" "Step" 1 5
~/.claude-status-line/progress/update-progress.py "Building App" "Step" 2 5

# Clear when done
~/.claude-status-line/progress/update-progress.py --clear
```

The helper automatically discovers the current Claude session ID by walking the process tree, so progress is scoped per session.

Arguments: `<title> <subtitle> <count> <max>`

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
