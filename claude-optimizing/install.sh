#!/usr/bin/env bash
# Install the claude-optimizing tool layer:
#   1. Symlinks cc-*.py scripts into ~/.local/bin/
#   2. Symlinks cc-*-hook.py scripts into ~/.claude/hooks/
#   3. Registers the repo-hygiene Stop hook in ~/.claude/settings.json
#   4. Appends guidance from claude-optimizing/claude-additions.md into ~/.claude/CLAUDE.md
#      (between <!-- BEGIN claude-optimizing --> / <!-- END claude-optimizing --> markers,
#      so re-installing replaces the block in place)
#
# Idempotent — safe to re-run. See uninstall.sh to reverse.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$HERE/.." && pwd)"
BIN_DIR="$HOME/.local/bin"
HOOKS_DIR="$HOME/.claude/hooks"
CLAUDE_MD="$HOME/.claude/CLAUDE.md"
SETTINGS_JSON="$HOME/.claude/settings.json"

mkdir -p "$BIN_DIR" "$HOOKS_DIR"

# ---------- 1 & 2. Install scripts + hooks ------------------------------------

echo "Installing cc-* scripts..."
installed=0
for script in "$HERE"/scripts-*/cc-*.py; do
    [ -f "$script" ] || continue
    name="$(basename "$script" .py)"
    case "$name" in
        *-hook) target="$HOOKS_DIR/$name.py"; loc=".claude/hooks" ;;
        *)      target="$BIN_DIR/$name";       loc=".local/bin"   ;;
    esac
    ln -sfn "$script" "$target"
    chmod +x "$script"
    installed=$((installed + 1))
    echo "  $name → $loc"
done
echo "  total: $installed"

# ---------- 3. Register Stop hook in settings.json ----------------------------

echo ""
echo "Registering Stop hook in $SETTINGS_JSON..."
python3 - "$SETTINGS_JSON" <<'PYEOF'
import json, sys, os
from pathlib import Path

path = Path(sys.argv[1])
if not path.exists():
    settings = {}
else:
    settings = json.loads(path.read_text())

cmd = "/usr/bin/python3 $HOME/.claude/hooks/cc-repo-hygiene-hook.py"
settings.setdefault("hooks", {}).setdefault("Stop", [])

# Check if any existing Stop group already contains this command.
already = any(
    h.get("command") == cmd
    for grp in settings["hooks"]["Stop"]
    for h in grp.get("hooks", [])
)
if already:
    print("  already registered")
else:
    settings["hooks"]["Stop"].append(
        {"hooks": [{"type": "command", "command": cmd}]}
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2) + "\n")
    print(f"  added: {cmd}")
PYEOF

# ---------- 4. Install guidance into ~/.claude/CLAUDE.md ----------------------

echo ""
echo "Installing guidance block into $CLAUDE_MD..."
python3 - "$CLAUDE_MD" "$HERE/claude-additions.md" <<'PYEOF'
import sys
from pathlib import Path

target = Path(sys.argv[1])
source = Path(sys.argv[2])

BEGIN = "<!-- BEGIN claude-optimizing -->"
END = "<!-- END claude-optimizing -->"

new_block = source.read_text().rstrip() + "\n"
if BEGIN not in new_block or END not in new_block:
    sys.exit(f"FAIL: {source} is missing BEGIN/END markers")

if not target.exists():
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(new_block)
    print(f"  created {target}")
else:
    existing = target.read_text()
    if BEGIN in existing and END in existing:
        # Replace the existing block in place
        before = existing.split(BEGIN, 1)[0].rstrip() + "\n\n"
        after  = existing.split(END,   1)[1].lstrip("\n")
        out = before + new_block + ("\n" + after if after.strip() else "")
        target.write_text(out.rstrip() + "\n")
        print("  replaced existing block")
    else:
        # Append
        sep = "" if existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
        target.write_text(existing + sep + new_block)
        print("  appended block")
PYEOF

echo ""
echo "Done."
echo "Ensure \$HOME/.local/bin is on your PATH (check ~/.zshrc or ~/.bashrc)."
