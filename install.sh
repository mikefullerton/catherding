#!/bin/bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="$HOME/.claude/skills"

mkdir -p "$SKILLS_DIR"

echo "Installing skills..."
for skill in "$REPO_DIR"/skills/*/; do
    name="$(basename "$skill")"
    target="$SKILLS_DIR/$name"
    if [ -L "$target" ]; then
        rm "$target"
    elif [ -e "$target" ]; then
        echo "  SKIP $name (non-symlink exists, remove manually)"
        continue
    fi
    ln -s "$skill" "$target"
    echo "  $name -> $skill"
done

echo ""
echo "Installing CLIs..."
for pyproject in "$REPO_DIR"/skills/*/*/pyproject.toml; do
    [ -f "$pyproject" ] || continue
    cli_dir="$(dirname "$pyproject")"
    pkg_name="$(grep '^name' "$pyproject" | head -1 | sed 's/.*= *"\(.*\)"/\1/')"
    echo "  $pkg_name ($(basename "$cli_dir"))"
    uv tool install -e "$cli_dir" 2>&1 | sed 's/^/    /'
done

echo ""
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
    cat > "$CADDY_ETC/Caddyfile" <<'CADDYFILE'
{
	admin localhost:2019
}

:2080 {
	root * {$HOME}/.local-server/sites
	file_server {
		browse {$HOME}/.local-server/browse.html
	}
	encode gzip

	log {
		output file /opt/homebrew/var/log/caddy-access.log
		format console
	}
}
CADDYFILE
    # Expand $HOME in the Caddyfile
    sed -i '' "s|\{\\$HOME\}|$HOME|g" "$CADDY_ETC/Caddyfile"
    echo "  Wrote $CADDY_ETC/Caddyfile"
fi

# Copy browse template
cp "$REPO_DIR/scripts/caddy/browse.html" "$HOME/.local-server/browse.html"
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

The home page auto-refreshes every 5 seconds. It reads metadata from each file (or directory's \`index.html\`) to build the listing:

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
        # Replace existing block
        python3 -c "
import re, sys
text = open('$CLAUDE_MD').read()
block = '''$CADDY_BLOCK'''
text = re.sub(r'<!-- BEGIN CADDY -->.*?<!-- END CADDY -->', block, text, flags=re.DOTALL)
open('$CLAUDE_MD', 'w').write(text)
"
        echo "  Updated existing Caddy section"
    else
        # Insert before Repo Hygiene section (or append)
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
echo "Done."
