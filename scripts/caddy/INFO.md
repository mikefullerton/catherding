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
| 2080 | HTTP file server — serves `~/www` |
| 2019 | Admin API (Caddy internal) |

## Configuration

- **Caddyfile**: `/opt/homebrew/etc/Caddyfile`
- **Access log**: `/opt/homebrew/var/log/caddy-access.log`
- **Reload after edit**: `caddy reload --config /opt/homebrew/etc/Caddyfile`
- **Service control**: `brew services start/stop/restart caddy`

## How It Works

Everything lives under `~/www`. Each subdirectory is a site, immediately served by Caddy at `http://localhost:2080/<name>/`. The root `index.html` auto-refreshes every 5 seconds to show all published sites.

No dynamic routing, no API calls — just files in a directory.

## caddy_routes

CLI and Python API for publishing content.

### CLI

```bash
caddy_routes publish my-tool /path/to/output.html    # single file -> ~/www/my-tool/
caddy_routes publish my-tool /path/to/output-dir/     # directory -> ~/www/my-tool/
caddy_routes unpublish my-tool                        # remove ~/www/my-tool/
caddy_routes list                                     # show all published sites
caddy_routes status                                   # check if Caddy is running
```

### Python

```python
from caddy_routes import publish, unpublish, list_sites, status

url = publish("my-tool", "/path/to/output.html")  # returns live URL
unpublish("my-tool")
list_sites()
status()
```

### What publish Does

1. Copies the file or directory into `~/www/<name>/`
2. If a single file, also copies it as `index.html`
3. Rebuilds `~/www/index.html` with links to all sites
4. Prints the live URL

### Manual Publishing

You don't even need the script. Just:

```bash
mkdir -p ~/www/my-tool
cp output.html ~/www/my-tool/index.html
# Live at http://localhost:2080/my-tool/
```
