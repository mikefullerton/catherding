#!/usr/bin/env bash
# Reverse claude-optimizing/install.sh:
#   1. Remove cc-* symlinks from ~/.local/bin/ and ~/.claude/hooks/
#      (only symlinks that actually point into this claude-optimizing/ tree)
#   2. De-register the repo-hygiene Stop hook from ~/.claude/settings.json
#   3. Strip the guidance block from ~/.claude/CLAUDE.md (between markers)
#   4. Unset core.hooksPath if it still points at .githooks
#
# Idempotent — safe to re-run.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$HERE/.." && pwd)"
BIN_DIR="$HOME/.local/bin"
HOOKS_DIR="$HOME/.claude/hooks"
CLAUDE_MD="$HOME/.claude/CLAUDE.md"
SETTINGS_JSON="$HOME/.claude/settings.json"

head1() { printf "\n\033[1m%s\033[0m\n" "$*"; }
info()  { printf "  %s\n" "$*"; }

# ---------- 1. Remove script + hook symlinks ----------------------------------

head1 "Removing cc-* symlinks that point into $REPO_DIR..."
removed=0
for dir in "$BIN_DIR" "$HOOKS_DIR"; do
    [ -d "$dir" ] || continue
    for entry in "$dir"/cc-*; do
        [ -L "$entry" ] || continue
        target="$(readlink "$entry")"
        case "$target" in
            "$HERE"/*)
                rm "$entry"; removed=$((removed + 1)); info "$entry" ;;
        esac
    done
done
info "total: $removed"

# ---------- 2. De-register Stop hook ------------------------------------------

head1 "De-registering Stop + PostToolUse:ExitWorktree + PreToolUse:Bash hooks..."
if [ -f "$SETTINGS_JSON" ]; then
    python3 - "$SETTINGS_JSON" <<'PYEOF'
import json, sys
from pathlib import Path

path = Path(sys.argv[1])
settings = json.loads(path.read_text())

entries = [
    ("Stop",        "/usr/bin/python3 $HOME/.claude/hooks/cc-repo-hygiene-hook.py"),
    ("PostToolUse", "/usr/bin/python3 $HOME/.claude/hooks/cc-exit-worktree-hook.py"),
    ("PreToolUse",  "/usr/bin/python3 $HOME/.claude/hooks/cc-block-pr-close-hook.py"),
]

changed = False
for event, cmd in entries:
    groups = settings.get("hooks", {}).get(event, [])
    new_groups = []
    removed_here = False
    for grp in groups:
        hooks = [h for h in grp.get("hooks", []) if h.get("command") != cmd]
        if len(hooks) != len(grp.get("hooks", [])):
            removed_here = True
        if hooks:
            new_groups.append({**grp, "hooks": hooks})
    if removed_here:
        settings["hooks"][event] = new_groups
        changed = True
        print(f"  {event}: removed")
    else:
        print(f"  {event}: not present")

if changed:
    path.write_text(json.dumps(settings, indent=2) + "\n")
PYEOF
else
    info "skip (no $SETTINGS_JSON)"
fi

# ---------- 3. Strip guidance block from ~/.claude/CLAUDE.md ------------------

head1 "Stripping guidance block from $CLAUDE_MD..."
if [ -f "$CLAUDE_MD" ]; then
    python3 - "$CLAUDE_MD" <<'PYEOF'
import sys
from pathlib import Path

path = Path(sys.argv[1])
BEGIN = "<!-- BEGIN claude-optimizing -->"
END = "<!-- END claude-optimizing -->"

text = path.read_text()
if BEGIN in text and END in text:
    before = text.split(BEGIN, 1)[0].rstrip()
    after  = text.split(END,   1)[1].lstrip("\n")
    out = (before + ("\n\n" + after if after.strip() else "\n")).rstrip() + "\n"
    path.write_text(out)
    print("  removed")
else:
    print("  not present")
PYEOF
else
    info "skip (no $CLAUDE_MD)"
fi

# ---------- 4. Unset pre-commit core.hooksPath --------------------------------

head1 "Unsetting pre-commit core.hooksPath in $REPO_DIR..."
cur="$(git -C "$REPO_DIR" config --get core.hooksPath 2>/dev/null || true)"
if [ "$cur" = ".githooks" ]; then
    git -C "$REPO_DIR" config --unset core.hooksPath
    info "unset"
else
    info "not set to .githooks (current: ${cur:-<unset>})"
fi

head1 "Done."
