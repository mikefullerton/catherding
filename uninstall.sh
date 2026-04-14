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
echo "Removing workflow scripts from ~/.local/bin/cc-*..."
for script in "$REPO_DIR"/scripts/*.py; do
    [ -f "$script" ] || continue
    name="$(basename "$script" .py)"
    target="$HOME/.local/bin/cc-$name"
    if [ -L "$target" ] && [ "$(readlink "$target")" = "$script" ]; then
        rm "$target"
        echo "  cc-$name"
    elif [ -L "$target" ]; then
        echo "  SKIP cc-$name (symlink points elsewhere)"
    else
        echo "  SKIP cc-$name (not installed)"
    fi
done

echo ""
echo "Done."
