#!/usr/bin/env bash
# Top-level installer. Prompts [Y/n] for each of the independent components
# this repo ships. Pass --yes to accept every prompt, --no to decline every
# prompt, or answer interactively. Non-tty stdin behaves like --yes so CI /
# pipe-fed installs still work.
#
# Extra flags forwarded to claude-optimizing/install.sh: --repair (strip stale
# unmarked sections from ~/.claude/CLAUDE.md before reinstalling the block).
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="$HOME/.claude/skills"

# Policy skills: read-time skills (no runtime install step, just symlink).
POLICY_SKILLS=(
    new-repo-scaffold
    file-organization-policies
    llm-integration-policies
    setup-and-install-scripts
    apple-and-xcode-policies
)

mode="ask"
forward_args=()
if [ ! -t 0 ]; then
    mode="yes"   # non-interactive default; explicit --no/--yes overrides below
fi
for arg in "$@"; do
    case "$arg" in
        --yes|-y) mode="yes" ;;
        --no|-n)  mode="no"  ;;
        --repair) forward_args+=(--repair) ;;
    esac
done

confirm() {
    # confirm "<prompt>" — return 0 for yes, 1 for no. Default yes.
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

install_skill() {
    local name="$1"
    local skill_dir="$REPO_DIR/skills/$name"
    [ -d "$skill_dir" ] || { echo "    skill dir not found: $skill_dir"; return 1; }
    mkdir -p "$SKILLS_DIR"
    local target="$SKILLS_DIR/$name"
    if [ -L "$target" ]; then
        rm "$target"
    elif [ -e "$target" ]; then
        echo "    SKIP symlink (non-symlink exists at $target, remove manually)"
    fi
    ln -sfn "$skill_dir" "$target"
    echo "    $name → ~/.claude/skills/$name"
}

echo ""
echo "cat-herding installer — independent components:"
echo "  1. Claude optimizations (cc-* scripts, Stop hook, global CLAUDE.md guidance)"
echo "  2. YOLO mode"
echo "  3. Developer-policy skills (global-install, read-time only)"
echo ""

# ---- 1. Claude optimizations ------------------------------------------------
if confirm "Install Claude optimizations?"; then
    "$REPO_DIR/claude-optimizing/install.sh" ${forward_args[@]+"${forward_args[@]}"}
fi

# ---- 2. YOLO ---------------------------------------------------------------
if confirm "Install YOLO?"; then
    echo "Installing yolo..."
    install_skill "yolo"
    "$REPO_DIR/skills/yolo/install.sh" 2>&1 | sed 's/^/    /'
fi

# ---- 3. Developer-policy skills --------------------------------------------
if confirm "Install developer-policy skills?"; then
    echo "Installing policy skills..."
    for skill in "${POLICY_SKILLS[@]}"; do
        install_skill "$skill"
    done
fi

echo ""
echo "Done."
