# Webinitor v2.0.0 Design Spec

## Context

Webinitor v1.0.0 handles setup, status, and configuration for Cloudflare, Railway, and GoDaddy. v2.0.0 adds operational features: domain portfolio management, DNS record management, and an end-to-end workflow for connecting domains across all three services.

The user manages ~200 domains on a GoDaddy Pro account with a mix of GoDaddy and Cloudflare nameservers. The typical workflow for new sites is GoDaddy → Cloudflare → Railway.

## New Subcommands

| Command | Purpose |
|---------|---------|
| `/webinitor domains [list\|search\|info]` | GoDaddy domain portfolio management |
| `/webinitor dns [list\|add\|update\|delete] <domain>` | DNS record management (auto-routes to GoDaddy or Cloudflare) |
| `/webinitor connect <domain>` | End-to-end: GoDaddy → Cloudflare zone → Railway custom domain |

Existing subcommands (`status`, `setup`, `configure`, `--help`, `--version`) are unchanged except for setup/configure gaining Cloudflare API token support.

---

## 1. Domain Portfolio Management (`/webinitor domains`)

### `/webinitor domains` or `/webinitor domains list`

Calls GoDaddy `GET /v1/domains` with `limit=500` for pagination.

**Output table columns:**
- Domain name
- Status (active, expired, etc.)
- Expiration date
- Auto-renew (on/off)
- Privacy (on/off)
- Nameservers (GoDaddy / Cloudflare / other)

**Optional filters (passed as arguments):**
- `--status <status>` — filter by domain status (e.g., `ACTIVE`)
- `--expiring` — show domains expiring within 30 days

**Pagination:** GoDaddy uses `marker` parameter. The script fetches all pages and combines results. With ~200 domains and `limit=500`, one request suffices.

### `/webinitor domains search <query>`

Fetches full domain list, filters client-side by substring match against domain name. GoDaddy API doesn't support server-side name search.

Example: `/webinitor domains search shop` → matches `myshop.com`, `shopify-test.org`, etc.

### `/webinitor domains info <domain>`

Calls GoDaddy `GET /v1/domains/{domain}` for detailed info.

**Output:**
- Registrar status, creation date, expiration date
- Nameservers (with detection: GoDaddy / Cloudflare / other)
- Auto-renew, privacy, lock status
- Contact info summary

### Reference Script

**`godaddy-domains.sh <action> [args]`**
- `list [--status STATUS] [--expiring]` — paginated domain listing
- `search <query>` — filtered list
- `info <domain>` — single domain detail
- All output as JSON for SKILL.md to format

---

## 2. DNS Record Management (`/webinitor dns`)

### Auto-Routing

DNS records may live in GoDaddy or Cloudflare depending on where the domain's nameservers point.

**Detection logic (`dns-detect.sh <domain>`):**
1. Call GoDaddy `GET /v1/domains/{domain}` to get nameservers
2. If any nameserver contains `cloudflare` → provider is `cloudflare`
3. If nameservers match GoDaddy defaults (`ns*.domaincontrol.com`) → provider is `godaddy`
4. Otherwise → provider is `unknown`, ask user

**Output:** Always print detected provider before showing results:
```
DNS provider: Cloudflare (nameservers: ada.ns.cloudflare.com, bob.ns.cloudflare.com)
```

### `/webinitor dns list <domain>`

Lists all DNS records for the domain via the detected provider.

**Output table:** Type, Name, Value, TTL, Proxied (Cloudflare only)

**GoDaddy path:** `GET /v1/domains/{domain}/records`
**Cloudflare path:** Resolve zone_id via `GET /zones?name=<domain>`, then `GET /zones/{zone_id}/dns_records`

### `/webinitor dns add <domain>`

Interactive flow using AskUserQuestion:
1. Ask record type: A, AAAA, CNAME, MX, TXT, NS, SRV
2. Ask record name (e.g., `@`, `www`, `mail`)
3. Ask record value
4. Ask TTL (default: auto/3600)
5. For Cloudflare: ask if proxied (yes/no)
6. Confirm and create

**GoDaddy path:** `PATCH /v1/domains/{domain}/records` (add to existing)
**Cloudflare path:** `POST /zones/{zone_id}/dns_records`

### `/webinitor dns update <domain>`

1. List current records
2. Ask user which record to update (by number)
3. Show current values, ask what to change
4. Confirm and update

**GoDaddy path:** `PUT /v1/domains/{domain}/records/{type}/{name}`
**Cloudflare path:** `PATCH /zones/{zone_id}/dns_records/{record_id}`

### `/webinitor dns delete <domain>`

1. List current records
2. Ask user which record to delete (by number)
3. Confirm before deleting

**GoDaddy path:** `PUT /v1/domains/{domain}/records/{type}/{name}` with empty array (GoDaddy doesn't have a DELETE for individual records — you replace the set for that type/name). **Warning:** This deletes ALL records matching that type+name pair. If multiple records exist (e.g., multiple MX records), the script must fetch existing records, remove the selected one, and PUT back the remaining records.
**Cloudflare path:** `DELETE /zones/{zone_id}/dns_records/{record_id}`

### Reference Scripts

**`dns-detect.sh <domain>`**
- Checks nameservers via GoDaddy API
- Output: `{"provider":"cloudflare"|"godaddy"|"unknown","nameservers":[...]}`

**`dns-godaddy.sh <action> <domain> [type] [name] [value] [ttl]`**
- `list <domain>` — list all records
- `add <domain> <type> <name> <value> [ttl]` — add a record
- `update <domain> <type> <name> <value> [ttl]` — update a record
- `delete <domain> <type> <name>` — delete a record
- Auth from `~/.webinitor/config.json` godaddy section
- Output: JSON

**`dns-cloudflare.sh <action> <domain> [type] [name] [value] [ttl] [proxied]`**
- `list <domain>` — list all records (resolves zone_id internally)
- `add <domain> <type> <name> <value> [ttl] [proxied]` — create record
- `update <domain> <record_id> <value> [ttl] [proxied]` — update record
- `delete <domain> <record_id>` — delete record
- Auth from `~/.webinitor/config.json` cloudflare section
- Output: JSON

---

## 3. Connect Workflow (`/webinitor connect`)

End-to-end automation for: GoDaddy domain → Cloudflare zone → Railway custom domain.

### Flow

Each step confirms before executing. User can skip any step or stop.

**Step 1: Verify domain**
- Call GoDaddy `GET /v1/domains/{domain}`
- Confirm domain exists and show current state (status, nameservers)

**Step 2: Check/create Cloudflare zone**
- Call Cloudflare `GET /zones?name=<domain>`
- If zone exists, show its status (pending/active) and assigned nameservers
- If no zone, ask to create: `POST /zones {name, account: {id}}` using account_id from config
- Show the Cloudflare-assigned nameservers

**Step 3: Update GoDaddy nameservers**
- Compare current nameservers to Cloudflare-assigned ones
- If already matching, skip
- If different, show the change and confirm: "Update nameservers from [current] to [cloudflare]?"
- Call GoDaddy `PATCH /v1/domains/{domain}` with `{"nameServers": ["ns1.cloudflare.com", "ns2.cloudflare.com"]}`

**Step 4: Check activation**
- Call Cloudflare `GET /zones/{zone_id}` to check status
- If `active`, proceed
- If `pending`, print: "Zone is pending activation. Nameserver changes can take up to 24 hours to propagate. You can check back with `/webinitor dns list <domain>` later."
- Ask if user wants to continue to Railway step or stop here

**Step 5: Configure Railway custom domain (optional)**
- Ask: "Add a custom domain to a Railway service?"
- If yes:
  - Auto-detect: run `railway status --json` to check if current directory is linked to a project
  - If linked, offer it as default. If not, ask user to specify project/service.
  - Run `railway domain` to add the custom domain
  - Create CNAME record in Cloudflare pointing to the Railway domain

**Step 6: Summary**
- Print what was done and current state of all three services for this domain

### Reference Scripts

**`cloudflare-zones.sh <action> <domain>`**
- `get <domain>` — lookup zone by name, return zone_id and status
- `create <domain>` — create new zone
- `check <domain>` — check activation status
- Auth from config cloudflare section
- Output: JSON

**`godaddy-nameservers.sh <action> <domain> [ns1 ns2]`**
- `get <domain>` — return current nameservers
- `set <domain> <ns1> <ns2>` — update nameservers
- Auth from config godaddy section
- Output: JSON

---

## 4. Config & Setup Changes

### Config file (`~/.webinitor/config.json`)

New `cloudflare` section:

```json
{
  "godaddy": {
    "api_key": "...",
    "api_secret": "...",
    "environment": "production"
  },
  "cloudflare": {
    "api_token": "...",
    "account_id": "..."
  },
  "preferences": {
    "install_method": "brew"
  }
}
```

### Setup changes

`/webinitor setup` adds a "Cloudflare API" step after the existing Cloudflare CLI step:

1. Check if Cloudflare API token is configured
2. If not, guide user:
   - Go to https://dash.cloudflare.com/profile/api-tokens
   - Create token with permissions: Zone:Zone:Read, Zone:DNS:Edit
   - Enter token via AskUserQuestion
3. Test token: `GET /zones?per_page=1` with bearer auth
4. Auto-fetch account_id: `GET /accounts?per_page=1`
5. Save to config

`/webinitor setup cloudflare` now does both CLI + API token.

`/webinitor configure` gains "Cloudflare API token" option.

### Reference Script

**`configure-cloudflare.sh <action> [args]`**
- `get` — show masked token + account_id
- `set <token>` — save token, auto-fetch account_id, test connection
- `test` — verify token works
- Same pattern as `configure-godaddy.sh`

---

## 5. New Reference Scripts Summary

| Script | Purpose |
|--------|---------|
| `godaddy-domains.sh` | Domain list/search/info via GoDaddy API |
| `godaddy-nameservers.sh` | Get/set nameservers via GoDaddy API |
| `dns-detect.sh` | Detect DNS provider from nameservers |
| `dns-godaddy.sh` | DNS CRUD via GoDaddy API |
| `dns-cloudflare.sh` | DNS CRUD via Cloudflare API |
| `cloudflare-zones.sh` | Zone create/get/check via Cloudflare API |
| `configure-cloudflare.sh` | Cloudflare API token management |

All scripts:
- Read auth from `~/.webinitor/config.json`
- Output JSON
- Use `curl -s` for API calls
- Use `jq` for JSON processing

---

## 6. Updated SKILL.md Routing Table

| `$ARGUMENTS` | Action |
|---|---|
| `status` or empty | Status |
| `setup [cloudflare\|railway\|godaddy]` | Setup |
| `configure [godaddy\|cloudflare]` | Configure |
| `domains [list\|search\|info]` | Domains |
| `dns [list\|add\|update\|delete] <domain>` | DNS |
| `connect <domain>` | Connect workflow |
| `--help` | Help |
| `--version` | Version |

---

## 7. Updated Frontmatter

```yaml
allowed-tools: Read, Write, Edit, Bash(bash *), Bash(brew *), Bash(npm *), Bash(wrangler *), Bash(railway *), Bash(curl *), Bash(which *), Bash(chmod *), Bash(cat *), Bash(test *), Bash(mkdir *), Bash(jq *), Bash(ls *), AskUserQuestion
```

No changes needed — existing `Bash(curl *)` and `Bash(railway *)` already cover the new operations.

---

## 8. Files to Create/Modify

**New files (7 scripts):**
- `plugins/webinitor/skills/webinitor/references/godaddy-domains.sh`
- `plugins/webinitor/skills/webinitor/references/godaddy-nameservers.sh`
- `plugins/webinitor/skills/webinitor/references/dns-detect.sh`
- `plugins/webinitor/skills/webinitor/references/dns-godaddy.sh`
- `plugins/webinitor/skills/webinitor/references/dns-cloudflare.sh`
- `plugins/webinitor/skills/webinitor/references/cloudflare-zones.sh`
- `plugins/webinitor/skills/webinitor/references/configure-cloudflare.sh`

**Modified files:**
- `plugins/webinitor/skills/webinitor/SKILL.md` — add new sections, update routing, bump to v2.0.0
- `plugins/webinitor/skills/webinitor/references/config-defaults.json` — add cloudflare section
- `plugins/webinitor/skills/webinitor/references/check-auth.sh` — add cloudflare API auth check
- `plugins/webinitor/skills/webinitor/references/status-all.sh` — add cloudflare API status
- `plugins/webinitor/.claude-plugin/plugin.json` — bump version to 2.0.0
- `plugins/webinitor/README.md` — document new commands

---

## 9. Verification

1. `/webinitor setup` — walks through all services including new Cloudflare API token
2. `/webinitor status` — shows Cloudflare API token status alongside CLI and other services
3. `/webinitor domains list` — lists all ~200 domains with status, expiry, auto-renew, privacy, NS
4. `/webinitor domains search <query>` — filters by name
5. `/webinitor domains info <domain>` — shows detailed domain info
6. `/webinitor dns list <domain>` — detects provider, lists DNS records
7. `/webinitor dns add <domain>` — interactive record creation
8. `/webinitor connect <domain>` — end-to-end GoDaddy → Cloudflare → Railway
9. Test with both GoDaddy-NS and Cloudflare-NS domains to verify auto-routing
