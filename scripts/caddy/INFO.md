# Local Caddy Server

Always-on web server at `http://localhost:2080`. Drop HTML files or directories into `~/.local-server/sites/` and they appear on the home page. Delete them and they're gone.

## Setup

Handled by `install.sh` — installs Caddy, writes the Caddyfile, copies the browse template, starts the service.

## Usage

```bash
# Single HTML file
cp my-page.html ~/.local-server/sites/
# Live at http://localhost:2080/my-page.html

# Directory with assets (must contain index.html)
cp -r my-app/ ~/.local-server/sites/
# Live at http://localhost:2080/my-app/

# Remove
rm ~/.local-server/sites/my-page.html
rm -rf ~/.local-server/sites/my-app
```

## HTML Metadata

The home page reads `<title>` and `<meta name="description">` from each file (or a directory's `index.html`) to build readable list items. Include both:

```html
<title>My Dashboard</title>
<meta name="description" content="Real-time metrics for the auth service">
```

Falls back to the filename if missing.

## Files

- `browse.html` — Caddy browse template (source of truth in repo, copied to `~/.local-server/` by install.sh)
- `INFO.md` — this file

## Configuration

- **Sites directory**: `~/.local-server/sites/`
- **Browse template**: `~/.local-server/browse.html`
- **Caddyfile**: `/opt/homebrew/etc/Caddyfile`
- **Service control**: `brew services start/stop/restart caddy`
