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
echo "Updating global CLAUDE.md..."
CLAUDE_MD="$HOME/.claude/CLAUDE.md"
CADDY_BLOCK=$(cat <<'CADDY_EOF'
<!-- BEGIN CADDY -->
## Local Web Server (Caddy) — MANDATORY

An always-on Caddy server serves `~/.local-server/sites/` at `http://localhost:2080`. **Use it instead of spawning one-off HTTP servers** (`python -m http.server`, `npx serve`, etc.).

To serve a page, just copy the HTML file:

```bash
cp my-page.html ~/.local-server/sites/
# Live at http://localhost:2080/my-page.html
# Listed on the home page at http://localhost:2080/
```

To remove it:

```bash
rm ~/.local-server/sites/my-page.html
```

The home page auto-refreshes every 5 seconds to show whatever is in the directory.

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
