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
echo "Installing scripts..."
SCRIPTS_BIN="$HOME/.local/bin"
mkdir -p "$SCRIPTS_BIN"
for script in "$REPO_DIR"/scripts/*/; do
    [ -d "$script" ] || continue
    for py in "$script"*.py; do
        [ -f "$py" ] || continue
        name="$(basename "$py" .py)"
        target="$SCRIPTS_BIN/$name"
        if [ -L "$target" ]; then
            rm "$target"
        elif [ -e "$target" ]; then
            echo "  SKIP $name (non-symlink exists, remove manually)"
            continue
        fi
        ln -s "$py" "$target"
        echo "  $name -> $py"
    done
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
echo "Done."
