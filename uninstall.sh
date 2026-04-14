#!/usr/bin/env bash
# Top-level uninstaller. Prompts [Y/n] for each of the three components.
# Pass --yes to accept every prompt, --no to decline, or answer interactively.
# Non-tty stdin defaults to --yes.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="$HOME/.claude/skills"

mode="ask"
if [ ! -t 0 ]; then
    mode="yes"   # non-interactive default; explicit --no/--yes overrides below
fi
case "${1:-}" in
    --yes|-y) mode="yes" ;;
    --no|-n)  mode="no"  ;;
esac

confirm() {
    local prompt="$1"
    case "$mode" in
        yes) echo "  $prompt [Y/n] yes (--yes)"; return 0 ;;
        no)  echo "  $prompt [Y/n] no (--no)";   return 1 ;;
    esac
    local ans
    read -r -p "  $prompt [Y/n] " ans
    case "${ans,,}" in
        ""|y|yes) return 0 ;;
        *)        return 1 ;;
    esac
}

uninstall_skill() {
    local name="$1"
    local skill_dir="$REPO_DIR/skills/$name"
    local target="$SKILLS_DIR/$name"

    if [ -L "$target" ] && [ "$(readlink "$target")" = "$skill_dir" ]; then
        rm "$target"
        echo "    unsymlinked ~/.claude/skills/$name"
    elif [ -L "$target" ]; then
        echo "    SKIP unsymlink (points elsewhere: $(readlink "$target"))"
    else
        echo "    SKIP unsymlink (not installed)"
    fi

    for pyproject in "$skill_dir"/*/pyproject.toml; do
        [ -f "$pyproject" ] || continue
        local pkg
        pkg="$(grep '^name' "$pyproject" | head -1 | sed 's/.*= *"\(.*\)"/\1/')"
        if uv tool list 2>/dev/null | grep -q "^$pkg "; then
            echo "    uv tool uninstall $pkg"
            uv tool uninstall "$pkg" 2>&1 | sed 's/^/      /'
        else
            echo "    SKIP $pkg (not installed as uv tool)"
        fi
    done
}

echo ""
echo "cat-herding uninstaller — three independent components:"
echo "  1. Claude optimizations"
echo "  2. Custom status line"
echo "  3. YOLO mode"
echo ""

if confirm "Uninstall Claude optimizations?"; then
    "$REPO_DIR/claude-optimizing/uninstall.sh"
fi

if confirm "Uninstall custom status line?"; then
    echo "Removing custom-status-line..."
    "$REPO_DIR/skills/custom-status-line/uninstall.sh" 2>&1 | sed 's/^/    /'
    uninstall_skill "custom-status-line"
fi

if confirm "Uninstall YOLO?"; then
    echo "Removing yolo..."
    "$REPO_DIR/skills/yolo/uninstall.sh" 2>&1 | sed 's/^/    /'
    uninstall_skill "yolo"
fi

echo ""
echo "Done."
