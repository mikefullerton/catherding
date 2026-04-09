#!/bin/bash
# ensure-permissions.sh — reads allowed-tools from a SKILL.md and merges
# any Bash() patterns into ~/.claude/settings.json permissions.allow
# Usage: bash ensure-permissions.sh /path/to/SKILL.md

SKILL_FILE="$1"
SETTINGS="$HOME/.claude/settings.json"

[ ! -f "$SKILL_FILE" ] || [ ! -f "$SETTINGS" ] && exit 0

# Extract Bash() patterns from the allowed-tools frontmatter line
PATTERNS=$(sed -n '/^---$/,/^---$/p' "$SKILL_FILE" | grep '^allowed-tools:' | grep -oE 'Bash\([^)]+\)')
[ -z "$PATTERNS" ] && exit 0

# Build JSON array of patterns, merge into settings, deduplicate
NEW=$(echo "$PATTERNS" | jq -R -s 'split("\n") | map(select(length > 0))')
jq --argjson new "$NEW" '
  .permissions.allow = ((.permissions.allow // []) + $new | unique)
' "$SETTINGS" > "${SETTINGS}.tmp" && mv "${SETTINGS}.tmp" "$SETTINGS"
