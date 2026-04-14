#!/usr/bin/env bash
# Top-level installer. Prompts [Y/n] for each of the three independent
# components this repo ships. Pass --yes to accept every prompt, --no to
# decline every prompt, or answer interactively. Non-tty stdin behaves like
# --yes so CI / pipe-fed installs still work.
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

    # Install any bundled CLI via uv
    for pyproject in "$skill_dir"/*/pyproject.toml; do
        [ -f "$pyproject" ] || continue
        local cli_dir pkg
        cli_dir="$(dirname "$pyproject")"
        pkg="$(grep '^name' "$pyproject" | head -1 | sed 's/.*= *"\(.*\)"/\1/')"
        echo "    uv tool install $pkg ($(basename "$cli_dir"))"
        uv tool install -e "$cli_dir" 2>&1 | sed 's/^/      /'
    done
}

echo ""
echo "cat-herding installer — three independent components:"
echo "  1. Claude optimizations (cc-* scripts, Stop hook, global CLAUDE.md guidance)"
echo "  2. Custom status line"
echo "  3. YOLO mode"
echo ""

# ---- 1. Claude optimizations ------------------------------------------------
if confirm "Install Claude optimizations?"; then
    "$REPO_DIR/claude-optimizing/install.sh"
fi

# ---- 2. Custom status line --------------------------------------------------
if confirm "Install custom status line?"; then
    echo "Installing custom-status-line..."
    install_skill "custom-status-line"
    if command -v cc-install-statusline >/dev/null 2>&1; then
        cc-install-statusline --skip-tests 2>&1 | sed 's/^/    /'
    else
        echo "    (cc-install-statusline not on PATH — run it manually once a shell picks up ~/.local/bin)"
    fi
fi

# ---- 3. YOLO ---------------------------------------------------------------
if confirm "Install YOLO?"; then
    echo "Installing yolo..."
    install_skill "yolo"
fi

echo ""
echo "Done."
