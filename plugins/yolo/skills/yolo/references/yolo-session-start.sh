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
  "deny_list": "~/.claude-yolo-sessions/yolo-deny.json",
  "auto_enabled": true,
  "needs_restart": false
}
MARKER_EOF

exit 0
