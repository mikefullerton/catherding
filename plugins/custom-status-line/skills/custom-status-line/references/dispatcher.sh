#!/bin/bash
# Status line pipeline dispatcher
# Chains scripts from pipeline.json, each transforming the status line output
# Each script receives: {"claude": <original_input>, "lines": [...]}
# Each script outputs: {"lines": [...]}

CLAUDE_INPUT=$(cat)
CONFIG="$HOME/.claude-status-line/pipeline.json"

# Auto-create default pipeline.json if missing
if [ ! -f "$CONFIG" ]; then
  mkdir -p "$HOME/.claude-status-line/scripts"
  cat > "$CONFIG" <<'DEFAULTS'
{
  "pipeline": [
    {"name": "base-info", "script": "~/.claude-status-line/scripts/base-info.sh"},
    {"name": "repo-cleanup", "script": "~/.claude-status-line/scripts/repo-cleanup.sh"}
  ]
}
DEFAULTS
fi

# Seed: empty lines, full claude input
CURRENT=$(jq -n --argjson c "$CLAUDE_INPUT" '{"claude": $c, "lines": []}')

# Run each script in order
while IFS= read -r script; do
  script="${script/#\~/$HOME}"
  if [ -x "$script" ]; then
    OUTPUT=$(echo "$CURRENT" | "$script" 2>/dev/null)
    if [ $? -eq 0 ] && [ -n "$OUTPUT" ]; then
      # Validate output has .lines array
      LINES=$(echo "$OUTPUT" | jq -c '.lines // empty' 2>/dev/null)
      if [ -n "$LINES" ] && [ "$LINES" != "null" ]; then
        CURRENT=$(echo "$CURRENT" | jq -c --argjson l "$LINES" '.lines = $l')
      fi
    fi
  fi
done < <(jq -r '.pipeline[].script' "$CONFIG" 2>/dev/null)

# Output final lines as plain text
echo "$CURRENT" | jq -r '.lines[]'
