#!/bin/bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="$HOME/.claude/skills"

echo "Removing skills..."
for skill in "$REPO_DIR"/skills/*/; do
    name="$(basename "$skill")"
    target="$SKILLS_DIR/$name"
    if [ -L "$target" ] && [ "$(readlink "$target")" = "$skill" ]; then
        rm "$target"
        echo "  $name"
    elif [ -L "$target" ]; then
        echo "  SKIP $name (symlink points elsewhere)"
    else
        echo "  SKIP $name (not installed)"
    fi
done

echo ""
echo "Removing scripts..."
SCRIPTS_BIN="$HOME/.local/bin"
for script in "$REPO_DIR"/scripts/*/; do
    [ -d "$script" ] || continue
    for py in "$script"*.py; do
        [ -f "$py" ] || continue
        name="$(basename "$py" .py)"
        target="$SCRIPTS_BIN/$name"
        if [ -L "$target" ] && [ "$(readlink "$target")" = "$py" ]; then
            rm "$target"
            echo "  $name"
        elif [ -L "$target" ]; then
            echo "  SKIP $name (symlink points elsewhere)"
        else
            echo "  SKIP $name (not installed)"
        fi
    done
done

echo ""
echo "Removing CLIs..."
for pyproject in "$REPO_DIR"/skills/*/*/pyproject.toml; do
    [ -f "$pyproject" ] || continue
    pkg_name="$(grep '^name' "$pyproject" | head -1 | sed 's/.*= *"\(.*\)"/\1/')"
    if uv tool list 2>/dev/null | grep -q "^$pkg_name "; then
        echo "  $pkg_name"
        uv tool uninstall "$pkg_name" 2>&1 | sed 's/^/    /'
    else
        echo "  SKIP $pkg_name (not installed)"
    fi
done

echo ""
echo "Done."
