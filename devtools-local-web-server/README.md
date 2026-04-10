# Local Web Server (Caddy + Site Watcher)

An always-on local web server for development. Drop HTML files or directories into a single folder and they're instantly served at `http://localhost:2080`. A companion site watcher daemon logs installs/removals and provides a delete API.

## Architecture

| Component | Role |
|-----------|------|
| **Caddy** | Static file server on port 2080 with directory browse template |
| **site_watcher.py** | Polls `~/.local-server/sites/`, logs activity, serves a DELETE API on port 2081 |
| **browse.html** | Custom Caddy browse template — live-updating dashboard with site metadata, age timers, activity log, and trash buttons |

```
http://localhost:2080/          -> browse.html (site listing)
http://localhost:2080/<file>    -> serves file from ~/.local-server/sites/
http://localhost:2080/_api/<n>  -> proxied to site_watcher DELETE API (port 2081)
```

## Prerequisites

- macOS with Homebrew
- Python 3 (system `/usr/bin/python3` is fine)

## Installation

### 1. Install Caddy

```bash
brew install caddy
```

### 2. Create the directory structure

```bash
mkdir -p ~/.local-server/sites
```

### 3. Install the browse template and site watcher

Copy both files from `site-template/` into `~/.local-server/`:

```bash
cp site-template/browse.html ~/.local-server/browse.html
cp site-template/site_watcher.py ~/.local-server/site_watcher.py
chmod +x ~/.local-server/site_watcher.py
```

### 4. Configure Caddy

Write the Caddyfile to Homebrew's config location:

```bash
cat > /opt/homebrew/etc/Caddyfile << 'EOF'
{
	admin localhost:2019
}

:2080 {
	handle_path /_api/* {
		reverse_proxy localhost:2081
	}

	root * ~/.local-server/sites
	file_server {
		browse ~/.local-server/browse.html
	}
	encode gzip

	log {
		output file /opt/homebrew/var/log/caddy-access.log
		format console
	}
}
EOF
```

> **Note:** Replace `/opt/homebrew` with your Homebrew prefix if on Intel (`/usr/local`).

### 5. Start Caddy

```bash
brew services start caddy
```

### 6. Install the site watcher as a launchd daemon

```bash
cat > ~/Library/LaunchAgents/com.local-server.site-watcher.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.local-server.site-watcher</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>$HOME/.local-server/site_watcher.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$HOME/.local-server/site-watcher.out.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/.local-server/site-watcher.err.log</string>
</dict>
</plist>
EOF

launchctl load ~/Library/LaunchAgents/com.local-server.site-watcher.plist
```

### 7. Verify

Open `http://localhost:2080` in a browser. You should see the "Local Sites" dashboard (empty on first run).

## Usage

### Serve a single HTML file

```bash
cp my-page.html ~/.local-server/sites/
# Live at http://localhost:2080/my-page.html
```

### Serve a directory (must contain index.html)

```bash
cp -r my-app/ ~/.local-server/sites/
# Live at http://localhost:2080/my-app/
```

### Remove a site

Either delete the file directly:

```bash
rm ~/.local-server/sites/my-page.html
rm -rf ~/.local-server/sites/my-app
```

Or click the trash button on the browse page.

### HTML metadata (optional but recommended)

The browse page extracts `<title>` and `<meta name="description">` from each site's HTML to display readable names and descriptions:

```html
<title>My Dashboard</title>
<meta name="description" content="Real-time metrics for the auth service">
```

Without these, the filename is shown instead.

## Service Management

```bash
# Caddy
brew services start caddy
brew services stop caddy
brew services restart caddy

# Site watcher
launchctl load ~/Library/LaunchAgents/com.local-server.site-watcher.plist
launchctl unload ~/Library/LaunchAgents/com.local-server.site-watcher.plist
```

## Ports

| Port | Service |
|------|---------|
| 2080 | Caddy — serves sites and browse page |
| 2081 | site_watcher.py — DELETE API (proxied via `/_api/` on 2080) |
| 2019 | Caddy admin API (default) |

## File Layout

```
~/.local-server/
  browse.html              # Caddy browse template
  site_watcher.py          # File watcher + DELETE API daemon
  activity.log             # JSON-lines activity log (auto-created)
  site-watcher.out.log     # Daemon stdout
  site-watcher.err.log     # Daemon stderr
  sites/                   # Drop files here to serve them
    activity.log -> ../activity.log   # Symlink (auto-created by watcher)
```

## Troubleshooting

**Port 2080 already in use:** Check for other processes with `lsof -i :2080` and stop them, or change the port in the Caddyfile.

**Browse page shows raw directory listing:** Caddy can't find `browse.html`. Verify the path in the Caddyfile matches where you placed the file.

**Sites don't appear on the dashboard:** The browse page polls every 5 seconds. Wait a moment, or check that the file is in `~/.local-server/sites/` and not a subdirectory of a subdirectory.

**Activity log not updating:** Check that the site watcher is running: `launchctl list | grep site-watcher`. If not loaded, re-run the `launchctl load` command.
