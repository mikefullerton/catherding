#!/usr/bin/env bash
# Remove YOLO hooks, statusline indicator, and (with --all) session data.
# Idempotent — writes a one-line JSON status summary to stdout.
set -euo pipefail

REMOVE_ALL=false
[ "${1:-}" = "--all" ] && REMOVE_ALL=true

SETTINGS="$HOME/.claude/settings.json"
HOOKS_DIR="$HOME/.claude/hooks"
PIPELINE="$HOME/.claude-status-line/pipeline.json"
INDICATOR="$HOME/.claude-status-line/scripts/yolo-indicator.sh"
SESSIONS_DIR="$HOME/.claude-yolo-sessions"

REMOVED_HOOKS=false
REMOVED_SCRIPTS=false
REMOVED_INDICATOR=false
REMOVED_SESSIONS=false

# 1. Strip YOLO hook entries from settings.json.
if [ -f "$SETTINGS" ] && jq -e '.hooks.PermissionRequest[]?.hooks[]? | select(.command | contains("yolo-approve-all"))' "$SETTINGS" >/dev/null 2>&1; then
    tmp="$(mktemp)"
    jq '
        .hooks.PermissionRequest = [.hooks.PermissionRequest[]? | .hooks = [.hooks[]? | select(.command | contains("yolo-approve-all") | not)]] |
        .hooks.PermissionRequest = [.hooks.PermissionRequest[]? | select(.hooks | length > 0)] |
        if (.hooks.PermissionRequest | length) == 0 then del(.hooks.PermissionRequest) else . end |
        .hooks.SessionEnd = [.hooks.SessionEnd[]? | .hooks = [.hooks[]? | select(.command | contains("yolo-session-cleanup") | not)]] |
        .hooks.SessionEnd = [.hooks.SessionEnd[]? | select(.hooks | length > 0)] |
        if (.hooks.SessionEnd | length) == 0 then del(.hooks.SessionEnd) else . end |
        .hooks.SessionStart = [.hooks.SessionStart[]? | .hooks = [.hooks[]? | select(.command | contains("yolo-session-start") | not)]] |
        .hooks.SessionStart = [.hooks.SessionStart[]? | select(.hooks | length > 0)] |
        if (.hooks.SessionStart | length) == 0 then del(.hooks.SessionStart) else . end |
        if (.hooks | keys | length) == 0 then del(.hooks) else . end
    ' "$SETTINGS" > "$tmp" && mv "$tmp" "$SETTINGS"
    REMOVED_HOOKS=true
fi

# 2. Delete hook script files.
for script in yolo-approve-all.sh yolo-session-cleanup.sh yolo-session-start.sh; do
    if [ -f "$HOOKS_DIR/$script" ]; then
        rm -f "$HOOKS_DIR/$script"
        REMOVED_SCRIPTS=true
    fi
done

# 3. Remove statusline indicator (pipeline entry + script).
if [ -f "$PIPELINE" ] && jq -e '.pipeline[] | select(.name == "yolo-indicator")' "$PIPELINE" >/dev/null 2>&1; then
    tmp="$(mktemp)"
    jq '.pipeline = [.pipeline[] | select(.name != "yolo-indicator")]' "$PIPELINE" > "$tmp" && mv "$tmp" "$PIPELINE"
    REMOVED_INDICATOR=true
fi
[ -f "$INDICATOR" ] && rm -f "$INDICATOR"

# 4. Optionally nuke session markers + deny config.
if [ "$REMOVE_ALL" = "true" ] && [ -d "$SESSIONS_DIR" ]; then
    rm -rf "$SESSIONS_DIR"
    REMOVED_SESSIONS=true
fi

if [ "$REMOVED_HOOKS" = "false" ] && [ "$REMOVED_SCRIPTS" = "false" ]; then
    echo '{"status":"not_installed"}'
else
    jq -n \
        --argjson removed_hooks "$REMOVED_HOOKS" \
        --argjson removed_scripts "$REMOVED_SCRIPTS" \
        --argjson removed_indicator "$REMOVED_INDICATOR" \
        --argjson removed_sessions "$REMOVED_SESSIONS" \
        '{"status":"uninstalled","removed_hooks":$removed_hooks,"removed_scripts":$removed_scripts,"removed_indicator":$removed_indicator,"removed_sessions":$removed_sessions}'
fi
