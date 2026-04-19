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
}

POLICY_SKILLS=(
    new-repo-scaffold
    file-organization-policies
    llm-integration-policies
    setup-and-install-scripts
    apple-and-xcode-policies
)

echo ""
echo "catherding uninstaller — independent components:"
echo "  1. Claude optimizations"
echo "  2. YOLO mode"
echo "  3. Developer-policy skills"
echo ""

if confirm "Uninstall Claude optimizations?"; then
    "$REPO_DIR/claude-optimizing/uninstall.sh"
fi

if confirm "Uninstall YOLO?"; then
    echo "Removing yolo..."
    "$REPO_DIR/skills/yolo/uninstall.sh" 2>&1 | sed 's/^/    /'
    uninstall_skill "yolo"
fi

if confirm "Uninstall developer-policy skills?"; then
    echo "Removing policy skills..."
    for skill in "${POLICY_SKILLS[@]}"; do
        uninstall_skill "$skill"
    done
fi

echo ""
echo "Done."
