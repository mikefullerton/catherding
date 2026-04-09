#!/bin/bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="$HOME/.claude/skills"

mkdir -p "$SKILLS_DIR"

echo "Installing skills..."
for skill in "$REPO_DIR"/skills/*/; do
    name="$(basename "$skill")"
    target="$SKILLS_DIR/$name"
    if [ -L "$target" ]; then
        rm "$target"
    elif [ -e "$target" ]; then
        echo "  SKIP $name (non-symlink exists, remove manually)"
        continue
    fi
    ln -s "$skill" "$target"
    echo "  $name -> $skill"
done

echo ""
echo "Installing CLIs..."
for cli_dir in "$REPO_DIR"/skills/*/cli/; do
    [ -d "$cli_dir" ] || continue
    name="$(basename "$(dirname "$cli_dir")")"
    echo "  $name CLI"
    uv tool install -e "$cli_dir" 2>&1 | sed 's/^/    /'
done

echo ""
echo "Done."
