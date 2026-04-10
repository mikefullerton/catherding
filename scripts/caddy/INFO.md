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

## caddy_routes.py

Manages published sites and dynamic routes. Two approaches depending on your needs:

### Publishing (recommended for most tools)

Copies content into `~/www/<name>/` where Caddy serves it immediately. No API calls needed — files are served by the catch-all file server. Content survives Caddy restarts.

```bash
# Publish an HTML file — copied as index.html
python3 caddy_routes.py publish my-tool /path/to/output.html

# Publish a directory of files
python3 caddy_routes.py publish my-tool /path/to/output-dir/

# Remove published content
python3 caddy_routes.py unpublish my-tool
```

```python
from caddy_routes import publish, unpublish

# Publish — returns the live URL
url = publish("my-tool", "/path/to/output.html")
# → http://localhost:2080/my-tool/

# Clean up
unpublish("my-tool")
```

### Dynamic Routes (for serving in-place)

Registers a Caddy route pointing at an existing directory without copying. Useful when content changes frequently or is large. Routes are cleared on Caddy restart.

```bash
# Serve a directory at a URL path
python3 caddy_routes.py add /my-tool /path/to/output

# With directory listing
python3 caddy_routes.py add /my-tool /path/to/output --browse

# Remove a route
python3 caddy_routes.py remove /my-tool
```

```python
from caddy_routes import add_route, remove_route

add_route("/my-tool", "/tmp/my-tool-output", browse=True)
remove_route("/my-tool")
```

### Inspection

```bash
# Show published sites and dynamic routes
python3 caddy_routes.py list

# Check if Caddy is running
python3 caddy_routes.py status
```

### When to Use Which

| Approach | Content persists across restart | Copies files | Best for |
|----------|-------------------------------|-------------|----------|
| `publish` | Yes | Yes | Generated HTML, reports, tool output |
| `add` (dynamic route) | No | No | Large dirs, frequently changing content |
