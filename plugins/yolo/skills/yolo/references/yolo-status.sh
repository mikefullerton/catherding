#!/bin/bash
# yolo-status.sh — check YOLO status for current session
# Usage: yolo-status.sh <session_id>

SESSION_ID="$1"
SETTINGS="$HOME/.claude/settings.json"
MARKER_DIR="$HOME/.claude-yolo-sessions"
MARKER="$MARKER_DIR/${SESSION_ID}.json"
DENY_FILE="$MARKER_DIR/yolo-deny.json"

# Session status
ACTIVE=false
AUTO_ENABLED=false
if [ -f "$MARKER" ]; then
  ACTIVE=true
  AUTO_ENABLED=$(jq -r '.auto_enabled // false' "$MARKER" 2>/dev/null)
fi

# Count other active sessions
TOTAL=$(ls "$MARKER_DIR"/*.json 2>/dev/null | grep -v yolo-deny | wc -l | tr -d ' ')
OTHER=$(( TOTAL - (ACTIVE == true ? 1 : 0) ))
[ "$ACTIVE" = "true" ] && OTHER=$(( TOTAL - 1 ))

# Deny list
DENY_COUNT=0
DENY_SUMMARY=""
if [ -f "$DENY_FILE" ]; then
  DENY_COUNT=$(jq '.deny | length' "$DENY_FILE" 2>/dev/null || echo 0)
  DENY_SUMMARY=$(jq -r '.deny[] | if .pattern != "" then .matcher + ": " + .pattern else .matcher end' "$DENY_FILE" 2>/dev/null | paste -sd, - | sed 's/,/, /g')
fi

# Hooks installed?
HOOKS_INSTALLED=false
if [ -f "$SETTINGS" ] && jq -e '.hooks.PermissionRequest[]?.hooks[]? | select(.command | contains("yolo-approve-all"))' "$SETTINGS" >/dev/null 2>&1; then
  HOOKS_INSTALLED=true
fi

jq -n \
  --argjson active "$ACTIVE" \
  --argjson auto_enabled "$AUTO_ENABLED" \
  --argjson other "$OTHER" \
  --argjson deny_count "$DENY_COUNT" \
  --arg deny_summary "$DENY_SUMMARY" \
  --argjson hooks_installed "$HOOKS_INSTALLED" \
  '{"active":$active,"auto_enabled":$auto_enabled,"other_sessions":$other,"deny_count":$deny_count,"deny_summary":$deny_summary,"hooks_installed":$hooks_installed}'
