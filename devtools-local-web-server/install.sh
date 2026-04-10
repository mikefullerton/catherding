#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEMPLATE_DIR="$SCRIPT_DIR/site-template"

echo "Setting up local Caddy server..."

# Install Caddy if missing
if ! command -v caddy &>/dev/null; then
    if command -v brew &>/dev/null; then
        echo "  Installing Caddy via Homebrew..."
        brew install caddy 2>&1 | sed 's/^/    /'
    else
        echo "  ERROR: Caddy not found and Homebrew not available. Install Caddy manually."
    fi
fi

# Create sites directory
mkdir -p "$HOME/.local-server/sites"

# Write Caddyfile
CADDY_ETC="/opt/homebrew/etc"
if [ -d "$CADDY_ETC" ]; then
    sed -e "s|__HOME__|$HOME|g" \
        -e "s|__CADDY_LOG__|/opt/homebrew/var/log|g" \
        "$TEMPLATE_DIR/Caddyfile" > "$CADDY_ETC/Caddyfile"
    echo "  Wrote $CADDY_ETC/Caddyfile"
fi

# Copy browse template
cp "$TEMPLATE_DIR/browse.html" "$HOME/.local-server/browse.html"
echo "  Wrote ~/.local-server/browse.html"

# Start or reload Caddy
if command -v caddy &>/dev/null; then
    if brew services list 2>/dev/null | grep -q 'caddy.*started'; then
        caddy reload --config "$CADDY_ETC/Caddyfile" 2>/dev/null
        echo "  Caddy reloaded"
    else
        brew services start caddy 2>&1 | sed 's/^/  /'
    fi
fi

# Install site watcher daemon
echo ""
echo "Setting up site watcher..."
WATCHER_DST="$HOME/.local-server/site_watcher.py"
cp "$TEMPLATE_DIR/site_watcher.py" "$WATCHER_DST"
chmod +x "$WATCHER_DST"
echo "  Wrote ~/.local-server/site_watcher.py"

PLIST_LABEL="com.local-server.site-watcher"
PLIST_DST="$HOME/Library/LaunchAgents/$PLIST_LABEL.plist"
PYTHON3="$(command -v python3)"

# Unload existing if running
if launchctl list 2>/dev/null | grep -q "$PLIST_LABEL"; then
    launchctl unload "$PLIST_DST" 2>/dev/null || true
fi

# Write plist with paths substituted
sed -e "s|__PYTHON3__|$PYTHON3|g" \
    -e "s|__SITE_WATCHER__|$WATCHER_DST|g" \
    -e "s|__HOME__|$HOME|g" \
    "$TEMPLATE_DIR/com.local-server.site-watcher.plist" > "$PLIST_DST"

launchctl load "$PLIST_DST"
echo "  Site watcher started ($PLIST_LABEL)"

# Update global CLAUDE.md
echo ""
echo "Updating global CLAUDE.md..."
CLAUDE_MD="$HOME/.claude/CLAUDE.md"
CADDY_BLOCK=$(cat <<'CADDY_EOF'
<!-- BEGIN CADDY -->
## Local Web Server (Caddy) — MANDATORY

An always-on Caddy server serves `~/.local-server/sites/` at `http://localhost:2080`. **Use it instead of spawning one-off HTTP servers** (`python -m http.server`, `npx serve`, etc.).

To serve a page, just copy it in:

```bash
# Single HTML file
cp my-page.html ~/.local-server/sites/
# Live at http://localhost:2080/my-page.html

# Directory with assets (must contain index.html)
cp -r my-app/ ~/.local-server/sites/
# Live at http://localhost:2080/my-app/
```

To remove:

```bash
rm ~/.local-server/sites/my-page.html
rm -rf ~/.local-server/sites/my-app
```

The home page polls for changes every 5 seconds without reloading (no blink). It reads metadata from each file (or directory's \`index.html\`) to build the listing:

\`\`\`html
<title>My Dashboard</title>
<meta name="description" content="Real-time metrics for the auth service">
\`\`\`

Both tags are optional — the home page falls back to the filename. Always include them for a readable listing.

- **Service control**: `brew services start/stop/restart caddy`
- **Caddyfile**: `/opt/homebrew/etc/Caddyfile`
<!-- END CADDY -->
CADDY_EOF
)

if [ -f "$CLAUDE_MD" ]; then
    if grep -q '<!-- BEGIN CADDY -->' "$CLAUDE_MD"; then
        python3 -c "
import re, sys
text = open('$CLAUDE_MD').read()
block = '''$CADDY_BLOCK'''
text = re.sub(r'<!-- BEGIN CADDY -->.*?<!-- END CADDY -->', block, text, flags=re.DOTALL)
open('$CLAUDE_MD', 'w').write(text)
"
        echo "  Updated existing Caddy section"
    else
        python3 -c "
text = open('$CLAUDE_MD').read()
block = '''$CADDY_BLOCK'''
marker = '## Repo Hygiene'
if marker in text:
    text = text.replace(marker, block + '\n\n' + marker)
else:
    text = text.rstrip() + '\n\n' + block + '\n'
open('$CLAUDE_MD', 'w').write(text)
"
        echo "  Added Caddy section"
    fi
else
    echo "  SKIP (no $CLAUDE_MD found)"
fi

echo ""
echo "Local web server installed."
