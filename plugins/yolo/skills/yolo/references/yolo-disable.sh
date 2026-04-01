#!/bin/bash
# yolo-disable.sh — remove session marker
# Usage: yolo-disable.sh <session_id>

SESSION_ID="$1"
MARKER="$HOME/.claude-yolo-sessions/${SESSION_ID}.json"

if [ ! -f "$MARKER" ]; then
  echo '{"status":"already_disabled"}'
  exit 0
fi

rm -f "$MARKER"
echo '{"status":"disabled"}'
