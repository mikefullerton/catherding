# Local Caddy Server

Always-on lightweight web server for local tools to serve content ad-hoc.

## Setup

Installed via Homebrew, runs as a launchd service that survives reboots.

```
brew install caddy
brew services start caddy
```

## Ports

| Port | Purpose |
|------|---------|
| 2080 | HTTP file server — serves `~/www` with directory browsing |
| 2019 | Admin API — tools register/remove routes at runtime |

## Configuration

- **Caddyfile**: `/opt/homebrew/etc/Caddyfile`
- **Access log**: `/opt/homebrew/var/log/caddy-access.log`
- **Reload after edit**: `caddy reload --config /opt/homebrew/etc/Caddyfile`

## Service Control

```
brew services start caddy
brew services stop caddy
brew services restart caddy
```

## Static Files

Drop anything into `~/www` and browse it at `http://localhost:2080`.

## Dynamic Routes (caddy_routes.py)

Tools can register routes at runtime without touching the Caddyfile.

### CLI

```bash
# Serve a directory at a URL path
python3 caddy_routes.py add /my-tool /path/to/output

# With directory listing
python3 caddy_routes.py add /my-tool /path/to/output --browse

# Remove a route
python3 caddy_routes.py remove /my-tool

# Show all routes
python3 caddy_routes.py list

# Check if Caddy is running
python3 caddy_routes.py status
```

### Python Import

```python
from caddy_routes import add_route, remove_route, list_routes, status

# Register a route
add_route("/my-tool", "/tmp/my-tool-output", browse=True)

# Clean up when done
remove_route("/my-tool")

# Inspect
list_routes()
status()
```

### How It Works

Routes are added via Caddy's Admin API (`localhost:2019`). They persist as long as Caddy is running but are cleared on restart. For permanent routes, add them to the Caddyfile instead.

The script handles:
- Path prefix matching and stripping (so `/my-tool/index.html` maps to `<root>/index.html`)
- Replacing existing routes for the same path (idempotent adds)
- Directory listing opt-in via `--browse`
