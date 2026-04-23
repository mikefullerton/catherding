#!/usr/bin/env bash
# Install check-repos as ~/.local/bin/check-repos.
# Standalone — no dependency on the cc-* scripts or claude-optimizing/.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"

target="$BIN_DIR/check-repos"
rm -f "$target"
cp "$HERE/check-repos.py" "$target"
chmod +x "$target"
echo "check-repos -> $target"

case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) echo "  warn: $BIN_DIR is not on PATH — add it to your shell rc" >&2 ;;
esac
