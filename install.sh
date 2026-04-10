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
echo "Installing scripts..."
SCRIPTS_BIN="$HOME/.local/bin"
mkdir -p "$SCRIPTS_BIN"
for script in "$REPO_DIR"/scripts/*/; do
    [ -d "$script" ] || continue
    for py in "$script"*.py; do
        [ -f "$py" ] || continue
        name="$(basename "$py" .py)"
        target="$SCRIPTS_BIN/$name"
        if [ -L "$target" ]; then
            rm "$target"
        elif [ -e "$target" ]; then
            echo "  SKIP $name (non-symlink exists, remove manually)"
            continue
        fi
        ln -s "$py" "$target"
        echo "  $name -> $py"
    done
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

An always-on Caddy server is available for tools that need to serve web content locally. **Use it instead of spawning one-off HTTP servers** (`python -m http.server`, `npx serve`, etc.).

Use `caddy_routes` (installed to `~/.local/bin/`) to publish and manage content:

```bash
caddy_routes publish my-tool /path/to/output.html   # copy to ~/www/my-tool/, live at localhost:2080/my-tool/
caddy_routes publish my-tool /path/to/output-dir/    # publish a directory
caddy_routes unpublish my-tool                       # remove ~/www/my-tool/
caddy_routes add /my-tool /path/to/dir --browse      # dynamic route (serves in-place, cleared on restart)
caddy_routes remove /my-tool                         # remove dynamic route
caddy_routes list                                    # show published sites and dynamic routes
caddy_routes status                                  # check if Caddy is running
```

```python
from caddy_routes import publish, unpublish

url = publish("my-tool", "/path/to/output.html")  # returns live URL
unpublish("my-tool")
```

- **Publish** (`~/www/<name>/`) for generated HTML, reports, tool output — persists across restarts
- **Dynamic routes** for large or frequently changing dirs — cleared on Caddy restart
- **Service control**: `brew services start/stop/restart caddy`
- **Caddyfile**: `/opt/homebrew/etc/Caddyfile` — for permanent routes
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
