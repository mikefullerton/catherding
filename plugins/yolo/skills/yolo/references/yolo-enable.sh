#!/bin/bash
# yolo-enable.sh — atomic YOLO enable: install hooks, create marker, setup indicator
# Usage: yolo-enable.sh <session_id> <skill_dir>
# Output: JSON with result status
# Exit 0 = success, exit 1 = already enabled

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

# --- Hook scripts (idempotent) ---
mkdir -p "$HOME/.claude/hooks" "$MARKER_DIR"

# Install hook scripts from skill references (always overwrite to stay current)
for script in yolo-approve-all.sh yolo-session-cleanup.sh yolo-session-start.sh; do
  if [ -f "$SKILL_DIR/references/$script" ]; then
    cp "$SKILL_DIR/references/$script" "$HOME/.claude/hooks/$script"
    chmod +x "$HOME/.claude/hooks/$script"
  fi
done

# --- Settings.json hooks ---
HOOKS_ALREADY_INSTALLED=false
if [ -f "$SETTINGS" ]; then
  if jq -e '.hooks.PermissionRequest[]?.hooks[]? | select(.command | contains("yolo-approve-all"))' "$SETTINGS" >/dev/null 2>&1; then
    HOOKS_ALREADY_INSTALLED=true
  fi
fi

if [ "$HOOKS_ALREADY_INSTALLED" = "false" ] && [ -f "$SETTINGS" ]; then
  # Add all three hooks atomically
  jq '
    # PermissionRequest
    .hooks.PermissionRequest = (
      if (.hooks.PermissionRequest // [] | map(.hooks[]?.command) | map(select(contains("yolo-approve-all"))) | length) > 0
      then .hooks.PermissionRequest
      else (.hooks.PermissionRequest // []) + [{"matcher":"","hooks":[{"type":"command","command":"$HOME/.claude/hooks/yolo-approve-all.sh"}]}]
      end
    ) |
    # SessionEnd
    (if (.hooks.SessionEnd // [] | [.[].hooks[]?.command] | map(select(contains("yolo-session-cleanup"))) | length) > 0
     then .
     else
       if (.hooks.SessionEnd | length) > 0
       then .hooks.SessionEnd[0].hooks += [{"type":"command","command":"$HOME/.claude/hooks/yolo-session-cleanup.sh"}]
       else .hooks.SessionEnd = [{"matcher":"","hooks":[{"type":"command","command":"$HOME/.claude/hooks/yolo-session-cleanup.sh"}]}]
       end
     end) |
    # SessionStart
    (if (.hooks.SessionStart // [] | [.[].hooks[]?.command] | map(select(contains("yolo-session-start"))) | length) > 0
     then .
     else
       if (.hooks.SessionStart | length) > 0
       then .hooks.SessionStart[0].hooks += [{"type":"command","command":"$HOME/.claude/hooks/yolo-session-start.sh"}]
       else .hooks.SessionStart = [{"matcher":"","hooks":[{"type":"command","command":"$HOME/.claude/hooks/yolo-session-start.sh"}]}]
       end
     end)
  ' "$SETTINGS" > "${SETTINGS}.tmp" && mv "${SETTINGS}.tmp" "$SETTINGS"
fi

# --- Status line indicator ---
PIPELINE="$HOME/.claude-status-line/pipeline.json"
if [ -f "$PIPELINE" ] && [ -f "$SKILL_DIR/references/yolo-indicator.sh" ]; then
  cp "$SKILL_DIR/references/yolo-indicator.sh" "$HOME/.claude-status-line/scripts/yolo-indicator.sh"
  chmod +x "$HOME/.claude-status-line/scripts/yolo-indicator.sh"
  if ! jq -e '.pipeline[] | select(.name == "yolo-indicator")' "$PIPELINE" >/dev/null 2>&1; then
    jq '.pipeline += [{"name":"yolo-indicator","script":"~/.claude-status-line/scripts/yolo-indicator.sh"}]' "$PIPELINE" > "${PIPELINE}.tmp" && mv "${PIPELINE}.tmp" "$PIPELINE"
  fi
fi

# --- Deny config ---
DENY_COUNT=0
if [ ! -f "$DENY_FILE" ] && [ -f "$SKILL_DIR/references/yolo-deny-defaults.json" ]; then
  cp "$SKILL_DIR/references/yolo-deny-defaults.json" "$DENY_FILE"
fi
if [ -f "$DENY_FILE" ]; then
  DENY_COUNT=$(jq '.deny | length' "$DENY_FILE" 2>/dev/null || echo 0)
fi

# --- Session marker ---
NEEDS_RESTART=false
if [ "$HOOKS_ALREADY_INSTALLED" = "false" ]; then
  NEEDS_RESTART=true
fi

cat > "$MARKER" <<EOF
{
  "session_id": "${SESSION_ID}",
  "enabled_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "project": "$(pwd)",
  "deny_list": "~/.claude-yolo-sessions/yolo-deny.json",
  "needs_restart": ${NEEDS_RESTART}
}
EOF

# Output result
jq -n \
  --argjson needs_restart "$NEEDS_RESTART" \
  --argjson deny_count "$DENY_COUNT" \
  --argjson hooks_installed "$HOOKS_ALREADY_INSTALLED" \
  '{"status":"enabled","needs_restart":$needs_restart,"deny_count":$deny_count,"hooks_were_installed":$hooks_installed}'
