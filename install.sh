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
echo "Installing workflow + skill scripts to ~/.local/bin/cc-* (and Claude Code hooks to ~/.claude/hooks/)..."
mkdir -p "$HOME/.local/bin" "$HOME/.claude/hooks"
for script in "$REPO_DIR"/claude-optimizing/scripts-*/cc-*.py "$REPO_DIR"/skill-scripts/cc-*.py; do
    [ -f "$script" ] || continue
    name="$(basename "$script" .py)"
    dir="$(basename "$(dirname "$script")")"
    case "$name" in
        *-hook)
            # Hook scripts read JSON from stdin and integrate with Claude
            # Code's hook protocol — they don't belong on $PATH.
            target="$HOME/.claude/hooks/$name.py"
            location="claude/hooks"
            ;;
        *)
            target="$HOME/.local/bin/$name"
            location="local/bin"
            ;;
    esac
    cp "$script" "$target"
    chmod +x "$target"
    echo "  $name ($dir → $location)"
done

echo ""
echo "Activating git pre-commit hook..."
git -C "$REPO_DIR" config core.hooksPath .githooks
echo "  core.hooksPath=.githooks"

echo ""
echo "Done."
echo ""
echo "Ensure \$HOME/.local/bin is on your PATH (check ~/.zshrc or ~/.bashrc)."
