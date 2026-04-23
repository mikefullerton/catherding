#!/usr/bin/env bash
# Install remove-worktree as ~/.local/bin/remove-worktree.
# Standalone — no dependency on the cc-* scripts or claude-optimizing/.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"

target="$BIN_DIR/remove-worktree"
rm -f "$target"
cp "$HERE/remove-worktree.py" "$target"
chmod +x "$target"
echo "remove-worktree -> $target"

case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) echo "  warn: $BIN_DIR is not on PATH — add it to your shell rc" >&2 ;;
esac
