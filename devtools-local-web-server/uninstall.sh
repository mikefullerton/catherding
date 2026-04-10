#!/bin/bash
set -euo pipefail

echo "Removing local Caddy server..."

# Stop and unload site watcher daemon
PLIST_LABEL="com.local-server.site-watcher"
PLIST_DST="$HOME/Library/LaunchAgents/$PLIST_LABEL.plist"
if launchctl list 2>/dev/null | grep -q "$PLIST_LABEL"; then
    launchctl unload "$PLIST_DST" 2>/dev/null || true
    echo "  Site watcher stopped"
fi
rm -f "$PLIST_DST"

# Stop Caddy
if brew services list 2>/dev/null | grep -q 'caddy.*started'; then
    brew services stop caddy 2>&1 | sed 's/^/  /'
fi

# Remove server files (but preserve sites directory contents)
rm -f "$HOME/.local-server/browse.html"
rm -f "$HOME/.local-server/site_watcher.py"
rm -f "$HOME/.local-server/activity.log"
rm -f "$HOME/.local-server/site-watcher.out.log"
rm -f "$HOME/.local-server/site-watcher.err.log"
rm -f "$HOME/.local-server/sites/activity.log"
echo "  Removed ~/.local-server/ server files"

if [ -d "$HOME/.local-server/sites" ] && [ "$(ls -A "$HOME/.local-server/sites" 2>/dev/null)" ]; then
    echo "  KEPT ~/.local-server/sites/ (not empty — remove manually if desired)"
else
    rm -rf "$HOME/.local-server"
    echo "  Removed ~/.local-server/"
fi

# Remove Caddyfile
CADDY_ETC="/opt/homebrew/etc"
if [ -f "$CADDY_ETC/Caddyfile" ]; then
    rm -f "$CADDY_ETC/Caddyfile"
    echo "  Removed $CADDY_ETC/Caddyfile"
fi

# Remove Caddy section from global CLAUDE.md
echo ""
echo "Updating global CLAUDE.md..."
CLAUDE_MD="$HOME/.claude/CLAUDE.md"
if [ -f "$CLAUDE_MD" ] && grep -q '<!-- BEGIN CADDY -->' "$CLAUDE_MD"; then
    python3 -c "
import re
text = open('$CLAUDE_MD').read()
text = re.sub(r'\n*<!-- BEGIN CADDY -->.*?<!-- END CADDY -->\n*', '\n\n', text, flags=re.DOTALL)
open('$CLAUDE_MD', 'w').write(text.strip() + '\n')
"
    echo "  Removed Caddy section"
else
    echo "  SKIP (no Caddy section found)"
fi

echo ""
echo "Local web server uninstalled."
