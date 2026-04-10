# Local Caddy Server

Always-on web server at `http://localhost:2080`. Drop HTML files into `~/.local-server/sites/` and they appear on the home page. Delete them and they're gone.

## Setup

```
brew install caddy
brew services start caddy
```

## Usage

```bash
cp my-page.html ~/.local-server/sites/
# Live at http://localhost:2080/my-page.html
# Listed on the home page at http://localhost:2080/

rm ~/.local-server/sites/my-page.html
# Gone immediately
```

## Configuration

- **Sites directory**: `~/.local-server/sites/`
- **Browse template**: `~/.local-server/browse.html`
- **Caddyfile**: `/opt/homebrew/etc/Caddyfile`
- **Service control**: `brew services start/stop/restart caddy`
