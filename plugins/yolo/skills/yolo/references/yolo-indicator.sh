#!/bin/bash
# Pipeline script: append YOLO indicator to line 1 if active
# Input: {"claude": <claude_json>, "lines": [...]}
# Output: {"lines": [...]}

INPUT=$(cat)
CLAUDE=$(echo "$INPUT" | jq -r '.claude')
LINES=$(echo "$INPUT" | jq -c '.lines')

SESSION_ID=$(echo "$CLAUDE" | jq -r '.session_id // empty')
CWD=$(echo "$CLAUDE" | jq -r '.cwd // empty')

# No session ID = can't check
if [ -z "$SESSION_ID" ]; then
  echo "{\"lines\":$LINES}"
  exit 0
fi

MARKER="$HOME/.claude-yolo-sessions/${SESSION_ID}.json"

# Fallback: check for project-level marker (handles /compact changing session_id)
if [ ! -f "$MARKER" ]; then
  FALLBACK=$(grep -rl "\"project\": \"${CWD}\"" "$HOME/.claude-yolo-sessions/" 2>/dev/null | head -1)
  [ -n "$FALLBACK" ] && MARKER="$FALLBACK"
fi

if [ -f "$MARKER" ]; then
  RED=$'\033[38;5;210m'
  RST=$'\033[0m'
  DIM=$'\033[38;5;245m'
  NEEDS_RESTART=$(jq -r '.needs_restart // false' "$MARKER" 2>/dev/null)
  if [ "$NEEDS_RESTART" = "true" ]; then
    YOLO=" ${RED}☠ YOLO${RST} ${DIM}(needs restart)${RST}"
  else
    YOLO=" ${RED}☠ YOLO${RST}"
  fi
  LINES=$(echo "$LINES" | jq -c --arg y "$YOLO" '.[0] = (.[0] // "") + $y')
fi

echo "{\"lines\":$LINES}"
