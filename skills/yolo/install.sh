#!/usr/bin/env bash
# Install YOLO hooks, statusline indicator, and deny defaults.
# Idempotent — safe to run multiple times.
# Writes a one-line JSON status summary to stdout (parsed by SKILL.md).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SETTINGS="$HOME/.claude/settings.json"
MARKER_DIR="$HOME/.claude-yolo-sessions"
DENY_FILE="$MARKER_DIR/yolo-deny.json"
HOOKS_DIR="$HOME/.claude/hooks"

mkdir -p "$HOOKS_DIR" "$MARKER_DIR"

# 1. Copy hook scripts into place (idempotent).
for script in yolo-approve-all.sh yolo-session-cleanup.sh yolo-session-start.sh; do
    src="$HERE/references/$script"
    if [ -f "$src" ]; then
        cp "$src" "$HOOKS_DIR/$script"
        chmod +x "$HOOKS_DIR/$script"
    fi
done

# 2. Register hooks in settings.json (skip if already present).
already_installed=false
if [ -f "$SETTINGS" ] && jq -e '.hooks.PermissionRequest[]?.hooks[]? | select(.command | contains("yolo-approve-all"))' "$SETTINGS" >/dev/null 2>&1; then
    already_installed=true
fi

if [ "$already_installed" != "true" ]; then
    [ -f "$SETTINGS" ] || echo '{}' > "$SETTINGS"
    tmp="$(mktemp)"
    jq '
        .hooks.PermissionRequest = (
            if (.hooks.PermissionRequest // [] | map(.hooks[]?.command) | map(select(contains("yolo-approve-all"))) | length) > 0
            then .hooks.PermissionRequest
            else (.hooks.PermissionRequest // []) + [{"matcher":"","hooks":[{"type":"command","command":"$HOME/.claude/hooks/yolo-approve-all.sh"}]}]
            end
        ) |
        (if (.hooks.SessionEnd // [] | [.[].hooks[]?.command] | map(select(contains("yolo-session-cleanup"))) | length) > 0 then .
         elif (.hooks.SessionEnd // [] | length) > 0
         then .hooks.SessionEnd[0].hooks += [{"type":"command","command":"$HOME/.claude/hooks/yolo-session-cleanup.sh"}]
         else .hooks.SessionEnd = [{"matcher":"","hooks":[{"type":"command","command":"$HOME/.claude/hooks/yolo-session-cleanup.sh"}]}]
         end) |
        (if (.hooks.SessionStart // [] | [.[].hooks[]?.command] | map(select(contains("yolo-session-start"))) | length) > 0 then .
         elif (.hooks.SessionStart // [] | length) > 0
         then .hooks.SessionStart[0].hooks += [{"type":"command","command":"$HOME/.claude/hooks/yolo-session-start.sh"}]
         else .hooks.SessionStart = [{"matcher":"","hooks":[{"type":"command","command":"$HOME/.claude/hooks/yolo-session-start.sh"}]}]
         end)
    ' "$SETTINGS" > "$tmp" && mv "$tmp" "$SETTINGS"
fi

# 3. Wire status line indicator (only if the status line is already installed).
PIPELINE="$HOME/.claude-status-line/pipeline.json"
INDICATOR_SRC="$HERE/references/yolo-indicator.sh"
if [ -f "$PIPELINE" ] && [ -f "$INDICATOR_SRC" ]; then
    SL_SCRIPTS="$HOME/.claude-status-line/scripts"
    mkdir -p "$SL_SCRIPTS"
    # Unlink first in case we're clobbering a broken symlink from a prior install.
    rm -f "$SL_SCRIPTS/yolo-indicator.sh"
    cp "$INDICATOR_SRC" "$SL_SCRIPTS/yolo-indicator.sh"
    chmod +x "$SL_SCRIPTS/yolo-indicator.sh"
    if ! jq -e '.pipeline[] | select(.name == "yolo-indicator")' "$PIPELINE" >/dev/null 2>&1; then
        tmp="$(mktemp)"
        jq '.pipeline += [{"name":"yolo-indicator","script":"~/.claude-status-line/scripts/yolo-indicator.sh"}]' "$PIPELINE" > "$tmp" && mv "$tmp" "$PIPELINE"
    fi
fi

# 4. Seed deny defaults.
DENY_DEFAULTS="$HERE/references/yolo-deny-defaults.json"
if [ ! -f "$DENY_FILE" ] && [ -f "$DENY_DEFAULTS" ]; then
    cp "$DENY_DEFAULTS" "$DENY_FILE"
fi

# Output status JSON.
deny_count=0
[ -f "$DENY_FILE" ] && deny_count="$(jq '.deny | length' "$DENY_FILE" 2>/dev/null || echo 0)"
if [ "$already_installed" = "true" ]; then
    jq -n --argjson deny_count "$deny_count" '{"status":"already_installed","deny_count":$deny_count}'
else
    jq -n --argjson deny_count "$deny_count" '{"status":"installed","deny_count":$deny_count}'
fi
