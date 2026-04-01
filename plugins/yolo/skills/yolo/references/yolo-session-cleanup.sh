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
find "$HOME/.claude-yolo-sessions" -name "*.json" -not -name "yolo-deny.json" -mtime +1 -delete 2>/dev/null

exit 0
