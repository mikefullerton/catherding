#!/usr/bin/env bash
# Remove the custom-status-line runtime.
#   default: delete files in ~/.claude-status-line/{statusline,scripts}/
#            plus ~/.claude/hooks/session-tracker.py
#   --all:   also nuke ~/.claude-status-line/ entirely (pipeline, progress, sessions)
set -euo pipefail

INSTALLED="$HOME/.claude-status-line"
SESSION_TRACKER="$HOME/.claude/hooks/session-tracker.py"
MODE="${1:-}"

removed=0

wipe_py() {
    local dir="$1"
    [ -d "$dir" ] || return 0
    shopt -s nullglob
    for f in "$dir"/*.py; do
        rm "$f"
        removed=$((removed + 1))
    done
    shopt -u nullglob
}

if [ "$MODE" = "--all" ] && [ -d "$INSTALLED" ]; then
    rm -rf "$INSTALLED"
    echo "removed $INSTALLED (entire tree)"
    removed=1
else
    wipe_py "$INSTALLED/statusline"
    wipe_py "$INSTALLED/scripts"
fi

if [ -f "$SESSION_TRACKER" ]; then
    rm "$SESSION_TRACKER"
    echo "removed $SESSION_TRACKER"
    removed=$((removed + 1))
fi

if [ "$removed" -eq 0 ]; then
    echo "custom-status-line not installed; nothing to remove"
else
    echo "custom-status-line uninstalled"
fi
