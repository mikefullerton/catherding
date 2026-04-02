# status-enhancements

Enhanced Claude Code status line showing project info, git branch/stats, worktree detection, repo cleanup status, and YOLO mode indicator.

## Skills

- `/install-status-enhancements` — Install the enhanced status line
- `/uninstall-status-enhancements` — Remove the enhanced status line

## What it shows

- Project path, git branch, dirty file count, commits ahead/behind
- Repo cleanup status (stale branches, merged branches, prunable worktrees)
- YOLO mode indicator
- Model name, context remaining, duration, changes made, cost, rate limits
- Per-session progress bar display

## Progress Display

Show a progress bar in the status line from any skill or agent using the helper script:

```bash
~/.claude-status-line/progress/update-progress.sh "Building App" "Step" 3 5
```

This renders a boxed progress display below the status lines:

```
|-------------------------------------------------------------------------------|
|                                                                               |
|                              Building App                                     |
|  [=============================================                            ]  |
|                              Step 3/5 (60%)                                   |
|-------------------------------------------------------------------------------|
```

Update progress as work advances — each call prints output that triggers a status line refresh:

```bash
~/.claude-status-line/progress/update-progress.sh "Building App" "Step" 1 5
~/.claude-status-line/progress/update-progress.sh "Building App" "Step" 2 5
# ...
~/.claude-status-line/progress/update-progress.sh "Building App" "Step" 5 5
```

Clear when done:

```bash
~/.claude-status-line/progress/update-progress.sh --clear
```

Progress is scoped per session — other Claude sessions won't see it. The helper discovers the session ID automatically by walking the process tree to find the Claude parent process.

### JSON format

The helper writes `~/.claude-status-line/progress/<session_id>.json`:

```json
{"title": "Building App", "subtitle": "Step", "count": 3, "max": 5, "cols": 120, "session_id": "..."}
```

### Permissions

Add to `~/.claude/settings.json` `permissions.allow` to avoid prompts:

```json
"Bash($HOME/.claude-status-line/progress/update-progress.sh *)",
"Bash(~/.claude-status-line/progress/update-progress.sh *)"
```
