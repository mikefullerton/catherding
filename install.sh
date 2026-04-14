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
for pyproject in "$REPO_DIR"/skills/*/*/pyproject.toml; do
    [ -f "$pyproject" ] || continue
    cli_dir="$(dirname "$pyproject")"
    pkg_name="$(grep '^name' "$pyproject" | head -1 | sed 's/.*= *"\(.*\)"/\1/')"
    echo "  $pkg_name ($(basename "$cli_dir"))"
    uv tool install -e "$cli_dir" 2>&1 | sed 's/^/    /'
done

echo ""
echo "Installing workflow scripts to ~/.local/bin/cc-*..."
mkdir -p "$HOME/.local/bin"
for script in "$REPO_DIR"/scripts/*.py; do
    [ -f "$script" ] || continue
    name="$(basename "$script" .py)"
    target="$HOME/.local/bin/cc-$name"
    cp "$script" "$target"
    chmod +x "$target"
    echo "  cc-$name"
done

echo ""
echo "Done."
echo ""
echo "Ensure \$HOME/.local/bin is on your PATH (check ~/.zshrc or ~/.bashrc)."
