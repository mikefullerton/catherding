#!/bin/bash
# yolo-uninstall.sh — remove YOLO hooks, statusline indicator
# Usage: yolo-uninstall.sh [--all]
# --all: also remove ~/.claude-yolo-sessions/ (deny config + markers)
# Output: JSON with result status

REMOVE_ALL=false
[ "$1" = "--all" ] && REMOVE_ALL=true

SETTINGS="$HOME/.claude/settings.json"
REMOVED_HOOKS=false
REMOVED_SCRIPTS=false
REMOVED_INDICATOR=false
REMOVED_SESSIONS=false

# --- Remove hook entries from settings.json ---
if [ -f "$SETTINGS" ]; then
  if jq -e '.hooks.PermissionRequest[]?.hooks[]? | select(.command | contains("yolo-approve-all"))' "$SETTINGS" >/dev/null 2>&1; then
    jq '
      # Remove yolo-approve-all from PermissionRequest
      .hooks.PermissionRequest = [.hooks.PermissionRequest[]? | .hooks = [.hooks[]? | select(.command | contains("yolo-approve-all") | not)]] |
      .hooks.PermissionRequest = [.hooks.PermissionRequest[]? | select(.hooks | length > 0)] |
      if (.hooks.PermissionRequest | length) == 0 then del(.hooks.PermissionRequest) else . end |
      # Remove yolo-session-cleanup from SessionEnd
      .hooks.SessionEnd = [.hooks.SessionEnd[]? | .hooks = [.hooks[]? | select(.command | contains("yolo-session-cleanup") | not)]] |
      .hooks.SessionEnd = [.hooks.SessionEnd[]? | select(.hooks | length > 0)] |
      if (.hooks.SessionEnd | length) == 0 then del(.hooks.SessionEnd) else . end |
      # Remove yolo-session-start from SessionStart
      .hooks.SessionStart = [.hooks.SessionStart[]? | .hooks = [.hooks[]? | select(.command | contains("yolo-session-start") | not)]] |
      .hooks.SessionStart = [.hooks.SessionStart[]? | select(.hooks | length > 0)] |
      if (.hooks.SessionStart | length) == 0 then del(.hooks.SessionStart) else . end |
      # Clean up empty hooks object
      if (.hooks | keys | length) == 0 then del(.hooks) else . end
    ' "$SETTINGS" > "${SETTINGS}.tmp" && mv "${SETTINGS}.tmp" "$SETTINGS"
    REMOVED_HOOKS=true
  fi
fi

# --- Remove hook scripts ---
for script in yolo-approve-all.sh yolo-session-cleanup.sh yolo-session-start.sh; do
  if [ -f "$HOME/.claude/hooks/$script" ]; then
    rm -f "$HOME/.claude/hooks/$script"
    REMOVED_SCRIPTS=true
  fi
done

# --- Remove statusline indicator ---
PIPELINE="$HOME/.claude-status-line/pipeline.json"
if [ -f "$PIPELINE" ] && jq -e '.pipeline[] | select(.name == "yolo-indicator")' "$PIPELINE" >/dev/null 2>&1; then
  jq '.pipeline = [.pipeline[] | select(.name != "yolo-indicator")]' "$PIPELINE" > "${PIPELINE}.tmp" && mv "${PIPELINE}.tmp" "$PIPELINE"
  REMOVED_INDICATOR=true
fi
rm -f "$HOME/.claude-status-line/scripts/yolo-indicator.sh"

# --- Optionally remove sessions directory ---
if [ "$REMOVE_ALL" = "true" ] && [ -d "$HOME/.claude-yolo-sessions" ]; then
  rm -rf "$HOME/.claude-yolo-sessions"
  REMOVED_SESSIONS=true
fi

# Was anything installed to begin with?
if [ "$REMOVED_HOOKS" = "false" ] && [ "$REMOVED_SCRIPTS" = "false" ]; then
  echo '{"status":"not_installed"}'
  exit 0
fi

jq -n \
  --argjson removed_hooks "$REMOVED_HOOKS" \
  --argjson removed_scripts "$REMOVED_SCRIPTS" \
  --argjson removed_indicator "$REMOVED_INDICATOR" \
  --argjson removed_sessions "$REMOVED_SESSIONS" \
  '{"status":"uninstalled","removed_hooks":$removed_hooks,"removed_scripts":$removed_scripts,"removed_indicator":$removed_indicator,"removed_sessions":$removed_sessions}'
