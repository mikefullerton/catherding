#!/bin/bash
# install-cli.sh — install a CLI tool via brew or npm
# Usage: install-cli.sh <tool-name> <package-name> <brew|npm>
# Output: JSON { "tool": "...", "status": "installed|failed", "method": "...", "version": "..." }

TOOL="$1"
PACKAGE="$2"
METHOD="$3"

case "$METHOD" in
  brew)
    if ! command -v brew >/dev/null 2>&1; then
      jq -n --arg tool "$TOOL" '{"tool":$tool,"status":"failed","method":"brew","error":"homebrew not installed"}'
      exit 1
    fi
    OUTPUT=$(brew install "$PACKAGE" 2>&1)
    ;;
  npm)
    if ! command -v npm >/dev/null 2>&1; then
      jq -n --arg tool "$TOOL" '{"tool":$tool,"status":"failed","method":"npm","error":"npm not installed"}'
      exit 1
    fi
    OUTPUT=$(npm install -g "$PACKAGE" 2>&1)
    ;;
  *)
    jq -n --arg tool "$TOOL" '{"tool":$tool,"status":"failed","error":"unknown install method, use brew or npm"}'
    exit 1
    ;;
esac

if command -v "$TOOL" >/dev/null 2>&1; then
  VERSION=$("$TOOL" --version 2>/dev/null | head -1 | sed 's/^[^0-9]*//')
  jq -n --arg tool "$TOOL" --arg method "$METHOD" --arg version "$VERSION" \
    '{"tool":$tool,"status":"installed","method":$method,"version":$version}'
else
  jq -n --arg tool "$TOOL" --arg method "$METHOD" --arg output "$OUTPUT" \
    '{"tool":$tool,"status":"failed","method":$method,"error":$output}'
fi
