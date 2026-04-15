#!/usr/bin/env bash
# Install the claude-optimizing Claude-Code tool layer end-to-end.
#
# Covers everything in install-readme.md sections 0 (prereq check), 2 (global
# CLAUDE.md guidance), 3 (vendor hooks + symlinks), 4 (hook registration in
# settings.json), and the pre-commit activation from section 1.
#
# Does NOT install the yolo skill — that's a user-facing skill under `skills/`
# at the repo root, installed by the repo's top-level install.sh.
# Does NOT install Claude Code plugins (commit-commands, github, etc.) — those
# require the `/plugin install` flow from inside a live Claude session.
#
# Idempotent: safe to re-run. See uninstall.sh to reverse.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$HERE/.." && pwd)"
BIN_DIR="$HOME/.local/bin"
HOOKS_DIR="$HOME/.claude/hooks"
CLAUDE_MD="$HOME/.claude/CLAUDE.md"
SETTINGS_JSON="$HOME/.claude/settings.json"

warn()  { printf "  \033[33m!\033[0m %s\n" "$*" >&2; }
info()  { printf "  %s\n" "$*"; }
head1() { printf "\n\033[1m%s\033[0m\n" "$*"; }

# ---------- 0. Prereq check ---------------------------------------------------

head1 "Checking prerequisites..."
missing=0
for cmd in git gh python3; do
    if command -v "$cmd" >/dev/null 2>&1; then
        info "$cmd → $(command -v "$cmd")"
    else
        warn "$cmd NOT FOUND (install with: brew install $cmd)"
        missing=$((missing + 1))
    fi
done
if [ "$missing" -gt 0 ]; then
    warn "$missing prerequisite(s) missing — fix and re-run."
    exit 2
fi

case ":$PATH:" in
    *":$BIN_DIR:"*) info "PATH includes $BIN_DIR" ;;
    *)              warn "$BIN_DIR is NOT on PATH — add to ~/.zshrc or ~/.bashrc" ;;
esac

# ---------- 1. Install cc-* scripts + hook scripts ----------------------------

head1 "Installing cc-* scripts..."
mkdir -p "$BIN_DIR" "$HOOKS_DIR"
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
    info "$name → $loc"
done
info "total: $installed"

# ---------- 2. Register Stop hook in ~/.claude/settings.json ------------------

head1 "Registering Stop hook in $SETTINGS_JSON..."
python3 - "$SETTINGS_JSON" <<'PYEOF'
import json, sys
from pathlib import Path

path = Path(sys.argv[1])
settings = json.loads(path.read_text()) if path.exists() else {}

# (event, matcher, command) tuples to register idempotently.
entries = [
    (
        "Stop", "",
        "/usr/bin/python3 $HOME/.claude/hooks/cc-repo-hygiene-hook.py",
    ),
    (
        "PostToolUse", "ExitWorktree",
        "/usr/bin/python3 $HOME/.claude/hooks/cc-exit-worktree-hook.py",
    ),
]

settings.setdefault("hooks", {})
changed = False
for event, matcher, cmd in entries:
    groups = settings["hooks"].setdefault(event, [])
    already = any(
        h.get("command") == cmd
        for grp in groups
        for h in grp.get("hooks", [])
    )
    if already:
        print(f"  {event} ({matcher or 'any'}): already registered")
        continue
    entry = {"hooks": [{"type": "command", "command": cmd}]}
    if matcher:
        entry["matcher"] = matcher
    groups.append(entry)
    print(f"  {event} ({matcher or 'any'}): added")
    changed = True

if changed:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2) + "\n")
PYEOF

# ---------- 3. Merge guidance block into ~/.claude/CLAUDE.md ------------------

head1 "Installing guidance block into $CLAUDE_MD..."
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
        before = existing.split(BEGIN, 1)[0].rstrip() + "\n\n"
        after  = existing.split(END,   1)[1].lstrip("\n")
        out = before + new_block + ("\n" + after if after.strip() else "")
        target.write_text(out.rstrip() + "\n")
        print("  replaced existing block")
    else:
        sep = "" if existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
        target.write_text(existing + sep + new_block)
        print("  appended block")
PYEOF

# ---------- 4. Activate the repo's pre-commit hook ---------------------------

head1 "Activating pre-commit hook in $REPO_DIR..."
if [ -d "$REPO_DIR/.githooks" ]; then
    cur="$(git -C "$REPO_DIR" config --get core.hooksPath || true)"
    if [ "$cur" = ".githooks" ]; then
        info "already pointing at .githooks"
    else
        git -C "$REPO_DIR" config core.hooksPath .githooks
        info "core.hooksPath=.githooks"
    fi
else
    warn "$REPO_DIR/.githooks not found — skipping"
fi

# ---------- 5. Verify ---------------------------------------------------------

head1 "Verifying..."
if command -v cc-doctor >/dev/null 2>&1; then
    if cc-doctor; then
        info "cc-doctor: clean"
    else
        warn "cc-doctor reported problems (see above)"
    fi
else
    warn "cc-doctor not on PATH yet — open a new shell and re-run"
fi

head1 "Done."
cat <<'EOF'

Not covered by this script (run from the repo root if needed):
  • YOLO mode — ./skills/yolo/install.sh
  • Per-repo Bash allow-list — create .claude/settings.local.json in each repo:
        { "permissions": { "allow": ["Bash(git add:*)","Bash(git commit:*)",
          "Bash(git push:*)","Bash(git:*)","Bash(cp:*)"] } }
EOF
