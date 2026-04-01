#!/bin/bash
# yolo-enable.sh — create session marker (auto-installs hooks if needed)
# Usage: yolo-enable.sh <session_id> <skill_dir>
# Output: JSON with result status

SESSION_ID="$1"
SKILL_DIR="$2"
SETTINGS="$HOME/.claude/settings.json"
MARKER_DIR="$HOME/.claude-yolo-sessions"
MARKER="$MARKER_DIR/${SESSION_ID}.json"
DENY_FILE="$MARKER_DIR/yolo-deny.json"

# Already enabled?
if [ -f "$MARKER" ]; then
  echo '{"status":"already_enabled"}'
  exit 0
fi

# Auto-install if hooks not present
HOOKS_INSTALLED=false
if [ -f "$SETTINGS" ] && jq -e '.hooks.PermissionRequest[]?.hooks[]? | select(.command | contains("yolo-approve-all"))' "$SETTINGS" >/dev/null 2>&1; then
  HOOKS_INSTALLED=true
fi

FRESH_INSTALL=false
if [ "$HOOKS_INSTALLED" = "false" ]; then
  INSTALL_RESULT=$(bash "$SKILL_DIR/references/yolo-install.sh" "$SKILL_DIR")
  INSTALL_STATUS=$(echo "$INSTALL_RESULT" | jq -r '.status')
  if [ "$INSTALL_STATUS" = "installed" ]; then
    FRESH_INSTALL=true
  fi
fi

# Create session marker
mkdir -p "$MARKER_DIR"
NEEDS_RESTART=$FRESH_INSTALL

cat > "$MARKER" <<EOF
{
  "session_id": "${SESSION_ID}",
  "enabled_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "project": "$(pwd)",
  "deny_list": "~/.claude-yolo-sessions/yolo-deny.json",
  "needs_restart": ${NEEDS_RESTART}
}
EOF

DENY_COUNT=0
if [ -f "$DENY_FILE" ]; then
  DENY_COUNT=$(jq '.deny | length' "$DENY_FILE" 2>/dev/null || echo 0)
fi

jq -n \
  --argjson needs_restart "$NEEDS_RESTART" \
  --argjson deny_count "$DENY_COUNT" \
  --argjson fresh_install "$FRESH_INSTALL" \
  '{"status":"enabled","needs_restart":$needs_restart,"deny_count":$deny_count,"fresh_install":$fresh_install}'
