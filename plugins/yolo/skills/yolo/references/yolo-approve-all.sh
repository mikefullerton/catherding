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
[ -z "$DENY_FILE" ] && DENY_FILE="$HOME/.claude-yolo-sessions/yolo-deny.json"
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
