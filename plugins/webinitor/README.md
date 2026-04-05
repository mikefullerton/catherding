# Webinitor

Website infrastructure management plugin for Claude Code. Manages setup, status, configuration, domain portfolio, DNS records, and end-to-end workflows for three services:

- **Cloudflare** — DNS, zones, Workers via API + Wrangler CLI
- **Railway** — App hosting and databases via Railway CLI
- **GoDaddy** — Domain portfolio management via REST API

## Commands

| Command | Description |
|---------|-------------|
| `/webinitor` | Show status of all services |
| `/webinitor status` | Show status of all services |
| `/webinitor setup` | Interactive setup for all services |
| `/webinitor setup cloudflare` | Setup Cloudflare (CLI + API token) |
| `/webinitor setup railway` | Setup Railway CLI |
| `/webinitor setup godaddy` | Setup GoDaddy API credentials |
| `/webinitor configure` | Edit service configuration |
| `/webinitor configure godaddy` | Edit GoDaddy API credentials |
| `/webinitor configure cloudflare` | Edit Cloudflare API token |
| `/webinitor domains` | List all domains |
| `/webinitor domains list` | List domains (supports --status, --expiring) |
| `/webinitor domains search <query>` | Search domains by name |
| `/webinitor domains info <domain>` | Show detailed domain info |
| `/webinitor dns list <domain>` | List DNS records (auto-detects GoDaddy vs Cloudflare) |
| `/webinitor dns add <domain>` | Add a DNS record |
| `/webinitor dns update <domain>` | Update a DNS record |
| `/webinitor dns delete <domain>` | Delete a DNS record |
| `/webinitor connect <domain>` | End-to-end: GoDaddy → Cloudflare → Railway |
| `/webinitor --help` | Show help |
| `/webinitor --version` | Show version |

## Configuration

Credentials are stored at `~/.webinitor/config.json` with restricted permissions (directory mode 700, file mode 600):

- **GoDaddy**: API key + secret
- **Cloudflare**: API token + account ID (auto-fetched)
- **Railway**: Uses its own CLI auth (`railway login`)

## Installation

```bash
# From the cat-herding marketplace
claude plugin install webinitor@cat-herding

# Or load directly for development
claude --plugin-dir ./plugins/webinitor
```
