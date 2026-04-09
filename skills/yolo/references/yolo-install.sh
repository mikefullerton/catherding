#!/bin/bash
# yolo-install.sh — install YOLO hooks, statusline indicator, and deny defaults
# Usage: yolo-install.sh <skill_dir>
# Output: JSON with result status
# Idempotent — safe to run multiple times

SKILL_DIR="$1"
SETTINGS="$HOME/.claude/settings.json"
MARKER_DIR="$HOME/.claude-yolo-sessions"
DENY_FILE="$MARKER_DIR/yolo-deny.json"

# --- Hook scripts (idempotent) ---
mkdir -p "$HOME/.claude/hooks" "$MARKER_DIR"

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

if [ "$HOOKS_ALREADY_INSTALLED" = "true" ]; then
  DENY_COUNT=0
  if [ -f "$DENY_FILE" ]; then
    DENY_COUNT=$(jq '.deny | length' "$DENY_FILE" 2>/dev/null || echo 0)
  fi
  jq -n --argjson deny_count "$DENY_COUNT" '{"status":"already_installed","deny_count":$deny_count}'
  exit 0
fi

if [ -f "$SETTINGS" ]; then
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

jq -n --argjson deny_count "$DENY_COUNT" '{"status":"installed","deny_count":$deny_count}'
