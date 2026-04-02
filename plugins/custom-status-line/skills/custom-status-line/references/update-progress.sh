#!/bin/bash
# Update status line progress bar (per-session)
# Usage: update-progress.sh <title> <subtitle> <count> <max>
#        update-progress.sh --clear
#
# Writes a session-scoped progress file and prints a line to trigger status line refresh.

PROGRESS_DIR="$HOME/.claude-status-line/progress"

# Find Claude session by walking up the process tree
SESSION_ID=""
PID=$$
while [ "$PID" -gt 1 ] 2>/dev/null; do
  if [ -f "$HOME/.claude/sessions/${PID}.json" ]; then
    SESSION_ID=$(jq -r '.sessionId // empty' "$HOME/.claude/sessions/${PID}.json" 2>/dev/null)
    break
  fi
  PID=$(ps -o ppid= -p "$PID" 2>/dev/null | tr -d ' ')
done
if [ -z "$SESSION_ID" ]; then
  echo "Error: could not determine session ID" >&2
  exit 1
fi

PROGRESS_FILE="$PROGRESS_DIR/${SESSION_ID}.json"

if [ "$1" = "--clear" ]; then
  rm -f "$PROGRESS_FILE"
  echo "Progress cleared."
  exit 0
fi

if [ $# -lt 4 ]; then
  echo "Usage: update-progress.sh <title> <subtitle> <count> <max>"
  echo "       update-progress.sh --clear"
  exit 1
fi

TITLE="$1"
SUBTITLE="$2"
COUNT="$3"
MAX="$4"

COLS=$(tput cols 2>/dev/null || echo 80)

mkdir -p "$PROGRESS_DIR"
jq -n --arg t "$TITLE" --arg s "$SUBTITLE" --argjson c "$COUNT" --argjson m "$MAX" --argjson cols "$COLS" --arg sid "$SESSION_ID" \
  '{"title":$t,"subtitle":$s,"count":$c,"max":$m,"cols":$cols,"session_id":$sid}' > "$PROGRESS_FILE"

PCT=$(( COUNT * 100 / MAX ))
echo "${TITLE}: ${SUBTITLE} ${COUNT}/${MAX} (${PCT}%)"
