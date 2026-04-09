#!/bin/bash
# check-cli.sh — check if a CLI tool is installed and get its version
# Usage: check-cli.sh <tool-name> [version-flag]
# Output: JSON { "tool": "...", "installed": true/false, "version": "...", "path": "..." }

TOOL="$1"
VERSION_FLAG="${2:---version}"

if command -v "$TOOL" >/dev/null 2>&1; then
  TOOL_PATH=$(command -v "$TOOL")
  VERSION=$("$TOOL" "$VERSION_FLAG" 2>/dev/null | head -1 | sed 's/^[^0-9]*//')
  jq -n --arg tool "$TOOL" --arg version "$VERSION" --arg path "$TOOL_PATH" \
    '{"tool":$tool,"installed":true,"version":$version,"path":$path}'
else
  jq -n --arg tool "$TOOL" \
    '{"tool":$tool,"installed":false,"version":null,"path":null}'
fi
