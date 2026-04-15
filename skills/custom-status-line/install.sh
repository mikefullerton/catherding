#!/usr/bin/env bash
# Install the custom-status-line runtime:
#   references/statusline/*.py  → ~/.claude-status-line/statusline/
#   references/scripts/*.py     → ~/.claude-status-line/scripts/
#   references/hooks/*.py       → ~/.claude/hooks/
# Clears pycache, runs pytest unless --skip-tests.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SRC_STATUSLINE="$HERE/references/statusline"
SRC_SCRIPTS="$HERE/references/scripts"
SRC_HOOKS="$HERE/references/hooks"

INSTALLED="$HOME/.claude-status-line"
INSTALLED_STATUSLINE="$INSTALLED/statusline"
INSTALLED_SCRIPTS="$INSTALLED/scripts"
INSTALLED_HOOKS="$HOME/.claude/hooks"

if [ ! -d "$SRC_STATUSLINE" ]; then
    echo "FAIL: $SRC_STATUSLINE not found" >&2
    exit 2
fi

mkdir -p "$INSTALLED_STATUSLINE" "$INSTALLED_SCRIPTS" "$INSTALLED_HOOKS"

copy_tree() {
    local src="$1" dst="$2" count=0
    [ -d "$src" ] || { echo 0; return; }
    shopt -s nullglob
    for f in "$src"/*.py; do
        cp "$f" "$dst/$(basename "$f")"
        count=$((count + 1))
    done
    shopt -u nullglob
    echo "$count"
}

n_sl=$(copy_tree "$SRC_STATUSLINE" "$INSTALLED_STATUSLINE")
n_sc=$(copy_tree "$SRC_SCRIPTS"    "$INSTALLED_SCRIPTS")
n_hk=$(copy_tree "$SRC_HOOKS"      "$INSTALLED_HOOKS")

# Hooks must be executable — Claude Code invokes them as commands.
shopt -s nullglob
for f in "$INSTALLED_HOOKS"/*.py; do chmod +x "$f"; done
shopt -u nullglob

# Clear pycache so a stale .pyc doesn't mask a source change.
find "$INSTALLED" -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true

echo "installed: $n_sl statusline + $n_sc scripts + $n_hk hooks files"

# Run the skill's test suite unless told to skip.
if [ "${1:-}" != "--skip-tests" ]; then
    tests_dir="$HERE/tests"
    if [ -d "$tests_dir" ]; then
        PYTHONPATH="$INSTALLED" python3 -m pytest "$tests_dir" -q 2>&1 | tail -1
    fi
fi
