---
name: webinitor
description: "Website infrastructure management — setup, status, and configuration for Cloudflare (Wrangler), Railway, GoDaddy, and GitHub. /webinitor status, /webinitor setup, /webinitor configure, /webinitor --help"
version: "2.3.0"
argument-hint: "[status|setup|configure|domains|dns|connect|deploy|--help|--version]"
allowed-tools: Read, Write, Edit, Bash(bash *), Bash(brew *), Bash(npm *), Bash(wrangler *), Bash(railway *), Bash(gh *), Bash(curl *), Bash(which *), Bash(chmod *), Bash(cat *), Bash(test *), Bash(mkdir *), Bash(jq *), Bash(ls *), Bash(head *), Bash(tail *), Bash(sort *), Bash(column *), Bash(wc *), Bash(grep *), Bash(date *), Bash(docker *), AskUserQuestion
model: sonnet
---

# Webinitor v2.3.0

Website infrastructure management for Cloudflare, Railway, GoDaddy, and GitHub.

## Startup

**Step 0 — Ensure permissions**: Run `bash ${CLAUDE_SKILL_DIR}/references/ensure-permissions.sh ${CLAUDE_SKILL_DIR}/SKILL.md` to whitelist this skill's tools in `~/.claude/settings.json`. This is silent and idempotent.

**CRITICAL**: The very first thing you output MUST be the version line:

webinitor v2.3.0

If `$ARGUMENTS` is `--version`, respond with exactly:
> webinitor v2.3.0

Then stop.

## Route by argument

| `$ARGUMENTS` | Action |
|---|---|
| `status` or empty | Go to **Status** |
| `setup` | Go to **Setup All** |
| `setup cloudflare` | Go to **Setup Cloudflare** |
| `setup railway` | Go to **Setup Railway** |
| `setup godaddy` | Go to **Setup GoDaddy** |
| `setup github` | Go to **Setup GitHub** |
| `configure` | Go to **Configure** |
| `configure godaddy` | Go to **Configure GoDaddy** |
| `configure cloudflare` | Go to **Configure Cloudflare** |
| `domains` or `domains list` | Go to **Domains List** |
| `domains list --status <S>` | Go to **Domains List** (with status filter) |
| `domains list --expiring` | Go to **Domains List** (expiring filter) |
| `domains list --privacy-off` | Go to **Domains List** (privacy off filter) |
| `domains list --autorenew-off` | Go to **Domains List** (auto-renew off filter) |
| `domains list --name <pattern>` | Go to **Domains List** (name filter) |
| `domains search <query>` | Go to **Domains Search** |
| `domains info <domain>` | Go to **Domains Info** |
| `domains privacy-check` | Go to **Domains Privacy Check** |
| `domains chat` | Go to **Domains Chat** |
| `dns list <domain>` | Go to **DNS List** |
| `dns add <domain>` | Go to **DNS Add** |
| `dns update <domain>` | Go to **DNS Update** |
| `dns delete <domain>` | Go to **DNS Delete** |
| `connect <domain>` | Go to **Connect** |
| `deploy init` | Go to **Deploy Init** |
| `deploy init --config-only` | Go to **Deploy Init** (config-only mode) |
| `deploy push` | Go to **Deploy Push** |
| `deploy status` | Go to **Deploy Status** |
| `--help` | Go to **Help** |
| `--version` | Print version (handled in Startup) |
| anything else | Print: "Usage: /webinitor [status\|setup\|configure\|domains\|dns\|connect\|deploy\|--help\|--version]" and stop |

---

## Status

Show the unified status of all three services.

### Step 1: Run status check

```bash
bash ${CLAUDE_SKILL_DIR}/references/status-all.sh
```

### Step 2: Format and display

Parse the JSON output and print a formatted status report:

```
=== WEBINITOR STATUS ===

Cloudflare (Wrangler)
  CLI:  <installed (vX.X.X)> or <not installed>
  Auth: <authenticated (account-name)> or <not authenticated — reason>
  API:  <configured (token: abcd...efgh)> or <not configured — reason>

Railway
  CLI:  <installed (vX.X.X)> or <not installed>
  Auth: <authenticated (account-name)> or <not authenticated — reason>

GoDaddy (API)
  Env:  <production> or <ote>
  Auth: <configured (key: abcd...efgh)> or <not configured — reason>

GitHub (gh)
  CLI:  <installed (vX.X.X)> or <not installed>
  Auth: <authenticated (username)> or <not authenticated — reason>
```

If any service has issues, add an **Issues** section at the bottom:

```
Issues:
  - Wrangler CLI not installed → /webinitor setup cloudflare
  - Cloudflare API not configured → /webinitor setup cloudflare
  - Railway not authenticated → /webinitor setup railway
  - GoDaddy API not configured → /webinitor setup godaddy
  - GitHub CLI not installed → /webinitor setup github
  - GitHub not authenticated → /webinitor setup github
```

If everything is healthy, print: "All services ready."

---

## Setup All

Interactive setup that walks through all three services in sequence. Skip any service that is already fully configured (CLI installed + authenticated).

### Step 1: Run status check

```bash
bash ${CLAUDE_SKILL_DIR}/references/status-all.sh
```

### Step 2: Determine what needs setup

Parse the JSON. For each service, check if it needs CLI installation or authentication.

### Step 3: Walk through services

For each service that needs setup, run its individual setup section (below). If a service is fully configured, print:
> Cloudflare: already configured. Skipping.

After all services, run the Status section to show final state.

---

## Setup Cloudflare

### Step 1: Check CLI

```bash
bash ${CLAUDE_SKILL_DIR}/references/check-cli.sh wrangler --version
```

If installed, print the version and skip to Step 3.

### Step 2: Install CLI

Use AskUserQuestion:
- Question: "Wrangler CLI is not installed. How would you like to install it?"
- Option 1: "brew" — Install via Homebrew
- Option 2: "npm" — Install via npm globally
- Option 3: "Skip" — Skip Cloudflare setup

If "Skip", print "Cloudflare setup skipped." and stop this section.

Run the install:
```bash
bash ${CLAUDE_SKILL_DIR}/references/install-cli.sh wrangler wrangler <brew|npm>
```

Parse the JSON output. If `status` is `failed`, print the error and stop this section.

### Step 3: Check auth

```bash
bash ${CLAUDE_SKILL_DIR}/references/check-auth.sh cloudflare
```

If authenticated, print: "Cloudflare: authenticated as <account>." and stop this section.

### Step 4: Guide authentication

Print:
> Wrangler needs to authenticate with Cloudflare. This opens a browser window.
>
> Type `! wrangler login` in the prompt to authenticate.

Use AskUserQuestion:
- Question: "Have you completed `wrangler login`?"
- Option 1: "Yes, check again"
- Option 2: "Skip for now"

If "Yes, check again":
```bash
bash ${CLAUDE_SKILL_DIR}/references/check-auth.sh cloudflare
```

Report the result. If still not authenticated, print the error and suggest trying again or running `/webinitor setup cloudflare` later.

If "Skip for now", print: "Cloudflare auth skipped. Run `/webinitor setup cloudflare` later."

### Step 5: Check Cloudflare API token

```bash
bash ${CLAUDE_SKILL_DIR}/references/check-auth.sh cloudflare_api
```

If authenticated, print: "Cloudflare API: configured." and stop this section.

### Step 6: Guide API token creation

Print:
> Cloudflare API token is needed for DNS and zone management.
>
> To create a token:
> 1. Go to https://dash.cloudflare.com/profile/api-tokens
> 2. Click "Create Token"
> 3. Use the "Edit zone DNS" template, or create a custom token with:
>    - **Zone:Zone:Read** and **Zone:DNS:Edit** permissions
> 4. Copy the token — it's only shown once

Use AskUserQuestion:
- Question: "Enter your Cloudflare API token (or type 'skip' to skip):"
- Option 1: "Skip" — Skip Cloudflare API setup
- (User will type their token in "Other")

If "Skip", print "Cloudflare API setup skipped." and stop this section.

### Step 7: Save and test API token

```bash
bash ${CLAUDE_SKILL_DIR}/references/configure-cloudflare.sh set <TOKEN>
```

Parse the JSON output:
- If `status` is `saved`, print: "Cloudflare API configured. Account: <account_name>. Zones: <zones>."
- If `status` is `failed`, print the error and use AskUserQuestion:
  - "Cloudflare API token test failed. What would you like to do?"
  - Option 1: "Re-enter token" — Go back to Step 6
  - Option 2: "Skip for now"

---

## Setup Railway

### Step 1: Check CLI

```bash
bash ${CLAUDE_SKILL_DIR}/references/check-cli.sh railway version
```

If installed, print the version and skip to Step 3.

### Step 2: Install CLI

Use AskUserQuestion:
- Question: "Railway CLI is not installed. How would you like to install it?"
- Option 1: "brew" — Install via Homebrew
- Option 2: "npm" — Install via npm (package: @railway/cli)
- Option 3: "Skip" — Skip Railway setup

If "Skip", print "Railway setup skipped." and stop this section.

Run the install:
```bash
bash ${CLAUDE_SKILL_DIR}/references/install-cli.sh railway <railway|@railway/cli> <brew|npm>
```

Note: brew package is `railway`, npm package is `@railway/cli`.

Parse the JSON output. If `status` is `failed`, print the error and stop this section.

### Step 3: Check auth

```bash
bash ${CLAUDE_SKILL_DIR}/references/check-auth.sh railway
```

If authenticated, print: "Railway: authenticated as <account>." and stop this section.

### Step 4: Guide authentication

Print:
> Railway needs to authenticate. This displays a pairing code and opens a browser.
>
> Type `! railway login` in the prompt to authenticate.

Use AskUserQuestion:
- Question: "Have you completed `railway login`?"
- Option 1: "Yes, check again"
- Option 2: "Skip for now"

If "Yes, check again":
```bash
bash ${CLAUDE_SKILL_DIR}/references/check-auth.sh railway
```

Report the result. If still not authenticated, print the error and suggest trying again.

If "Skip for now", print: "Railway auth skipped. Run `/webinitor setup railway` later."

---

## Setup GoDaddy

### Step 1: Check auth

```bash
bash ${CLAUDE_SKILL_DIR}/references/check-auth.sh godaddy
```

If authenticated, print: "GoDaddy: API configured." and stop this section.

### Step 2: Guide API key creation

Print:
> GoDaddy uses API keys for authentication (no CLI needed).
>
> To get your API keys:
> 1. Go to https://developer.godaddy.com/keys
> 2. Create a new API key (Production environment)
> 3. Copy both the **Key** and **Secret** — the secret is only shown once
>
> Note: DNS/Management API access requires 10+ domains or an active Domain Pro Plan.

### Step 3: Collect credentials

Use AskUserQuestion:
- Question: "Enter your GoDaddy API Key (or type 'skip' to skip):"
- Option 1: "Skip" — Skip GoDaddy setup
- (User will type their key in "Other")

If "Skip", print "GoDaddy setup skipped." and stop this section.

Then use AskUserQuestion:
- Question: "Enter your GoDaddy API Secret:"
- (User will type their secret in "Other")

### Step 4: Choose environment

Use AskUserQuestion:
- Question: "Which GoDaddy API environment should be used?"
- Option 1: "Production (Recommended)" — Uses api.godaddy.com for real domains
- Option 2: "OTE (Test)" — Uses api.ote-godaddy.com for testing

### Step 5: Save and test

```bash
bash ${CLAUDE_SKILL_DIR}/references/configure-godaddy.sh set <API_KEY> <API_SECRET>
```

If user chose OTE:
```bash
bash ${CLAUDE_SKILL_DIR}/references/configure-godaddy.sh set-env ote
```

Then test the connection:
```bash
bash ${CLAUDE_SKILL_DIR}/references/configure-godaddy.sh test
```

If `status` is `ok`, print: "GoDaddy API configured and verified. Found <N> domain(s)."

If `status` is `failed`, print the error and use AskUserQuestion:
- Question: "GoDaddy API test failed. What would you like to do?"
- Option 1: "Re-enter credentials" — Go back to Step 3
- Option 2: "Skip for now" — Keep saved credentials and continue

---

## Setup GitHub

### Step 1: Check CLI

```bash
bash ${CLAUDE_SKILL_DIR}/references/check-cli.sh gh --version
```

If installed, print the version and skip to Step 3.

### Step 2: Install CLI

Use AskUserQuestion:
- Question: "GitHub CLI (gh) is not installed. How would you like to install it?"
- Option 1: "brew" — Install via Homebrew
- Option 2: "Skip" — Skip GitHub setup

If "Skip", print "GitHub setup skipped." and stop this section.

Run the install:
```bash
bash ${CLAUDE_SKILL_DIR}/references/install-cli.sh gh gh brew
```

Parse the JSON output. If `status` is `failed`, print the error and stop this section.

### Step 3: Check auth

```bash
bash ${CLAUDE_SKILL_DIR}/references/check-auth.sh github
```

If authenticated, print: "GitHub: authenticated as <account>." and stop this section.

### Step 4: Guide authentication

Print:
> GitHub CLI needs to authenticate. This opens a browser window.
>
> Type `! gh auth login` in the prompt to authenticate.

Use AskUserQuestion:
- Question: "Have you completed `gh auth login`?"
- Option 1: "Yes, check again"
- Option 2: "Skip for now"

If "Yes, check again":
```bash
bash ${CLAUDE_SKILL_DIR}/references/check-auth.sh github
```

Report the result. If still not authenticated, print the error and suggest trying again or running `/webinitor setup github` later.

If "Skip for now", print: "GitHub auth skipped. Run `/webinitor setup github` later."

---

## Configure

### Step 1: Show current state

```bash
bash ${CLAUDE_SKILL_DIR}/references/configure-godaddy.sh get
```

Print current configuration summary.

### Step 2: Choose what to configure

Use AskUserQuestion:
- Question: "What would you like to configure?"
- Option 1: "GoDaddy API credentials" — Go to **Configure GoDaddy**
- Option 2: "Cloudflare API token" — Go to **Configure Cloudflare**
- Option 3: "GoDaddy environment (production/ote)" — Go to **Configure GoDaddy Environment**
- Option 4: "Done" — Stop

---

## Configure GoDaddy

### Step 1: Show current config

```bash
bash ${CLAUDE_SKILL_DIR}/references/configure-godaddy.sh get
```

Print the current (masked) configuration.

### Step 2: Choose action

Use AskUserQuestion:
- Question: "What would you like to do?"
- Option 1: "Update credentials" — Collect new key/secret (same as Setup GoDaddy Step 3-5)
- Option 2: "Test connection" — Run `configure-godaddy.sh test` and report
- Option 3: "Change environment" — Go to Configure GoDaddy Environment
- Option 4: "Done" — Stop

After each action, loop back to Step 1 to show updated config.

---

## Configure GoDaddy Environment

### Step 1: Show current environment

```bash
bash ${CLAUDE_SKILL_DIR}/references/configure-godaddy.sh get
```

Print the current environment setting.

### Step 2: Choose environment

Use AskUserQuestion:
- Question: "Which GoDaddy API environment?"
- Option 1: "Production" — Uses api.godaddy.com
- Option 2: "OTE (Test)" — Uses api.ote-godaddy.com

### Step 3: Save

```bash
bash ${CLAUDE_SKILL_DIR}/references/configure-godaddy.sh set-env <production|ote>
```

Print: "Environment set to <environment>."

---

## Configure Cloudflare

### Step 1: Show current config

```bash
bash ${CLAUDE_SKILL_DIR}/references/configure-cloudflare.sh get
```

Print the current (masked) configuration.

### Step 2: Choose action

Use AskUserQuestion:
- Question: "What would you like to do?"
- Option 1: "Update API token" — Collect new token (same flow as Setup Cloudflare Step 6-7)
- Option 2: "Test connection" — Run `configure-cloudflare.sh test` and report
- Option 3: "Done" — Stop

After each action, loop back to Step 1 to show updated config.

---

## Domains List

### Step 1: Fetch domains

```bash
bash ${CLAUDE_SKILL_DIR}/references/godaddy-domains.sh list
```

Pass any flags from `$ARGUMENTS` directly. Supported flags can be combined:
- `--status <STATUS>` — filter by domain status (e.g., ACTIVE)
- `--expiring` — domains expiring within 30 days
- `--privacy-off` — domains with WHOIS privacy disabled
- `--autorenew-off` — domains with auto-renew disabled
- `--name <pattern>` — filter by domain name substring

Example:
```bash
bash ${CLAUDE_SKILL_DIR}/references/godaddy-domains.sh list --privacy-off --name fullerton
```

### Step 2: Format and display

Parse the JSON array and print a table:

```
Domain                    Status    Expires      Auto-Renew  Privacy  Nameservers
example.com               ACTIVE    2027-03-15   on          on       Cloudflare
mysite.org                ACTIVE    2026-12-01   on          off      GoDaddy
oldsite.net               ACTIVE    2026-04-20   off         on       GoDaddy
```

Nameserver column logic:
- If any nameserver contains "cloudflare" → "Cloudflare"
- If nameservers contain "domaincontrol" → "GoDaddy"
- Otherwise → "Other"

Print total count at the bottom: "Showing N domain(s)."

---

## Domains Search

### Step 1: Search domains

Extract the query from `$ARGUMENTS` (the word after `domains search`).

```bash
bash ${CLAUDE_SKILL_DIR}/references/godaddy-domains.sh search <query>
```

### Step 2: Format and display

Same table format as Domains List. Print: "Found N domain(s) matching '<query>'."

---

## Domains Info

### Step 1: Get domain info

Extract the domain from `$ARGUMENTS` (the word after `domains info`).

```bash
bash ${CLAUDE_SKILL_DIR}/references/godaddy-domains.sh info <domain>
```

### Step 2: Format and display

Print detailed info:

```
=== <domain> ===

Status:       ACTIVE
Created:      2020-01-15
Expires:      2027-03-15
Auto-Renew:   on
Privacy:      on
Locked:       true

Nameservers:
  - ada.ns.cloudflare.com
  - bob.ns.cloudflare.com

DNS Provider: Cloudflare
```

---

## Domains Privacy Check

Audit all active domains for security and privacy settings.

### Step 1: Run privacy check

```bash
bash ${CLAUDE_SKILL_DIR}/references/godaddy-domains.sh privacy-check
```

### Step 2: Format and display

Parse the JSON output and print a report:

```
=== DOMAIN PRIVACY & SECURITY AUDIT ===

Total active domains: N

Privacy OFF (N):
  - domain1.us
  - domain2.us

Auto-Renew OFF (N):
  - domain3.com
  - domain4.org

Unlocked (N):
  - domain5.com

Expiration Protection OFF (N):
  - (lists domains or "None — all protected")

Transfer Protection OFF (N):
  - (lists domains or "None — all protected")
```

For each category, if the list is empty, print "None — all good."

At the end, print a summary: "N issue(s) found across N domains." or "All domains look good."

---

## Domains Chat

Freeform discussion mode about the user's domain portfolio. Fetch the full domain list first, then answer the user's questions.

### Step 1: Fetch all domains

```bash
bash ${CLAUDE_SKILL_DIR}/references/godaddy-domains.sh list
```

### Step 2: Interactive discussion

Print: "Domain portfolio loaded (N active domains). What would you like to know?"

Use AskUserQuestion:
- Question: "What would you like to discuss about your domains?"
- Option 1: "Find domains by keyword"
- Option 2: "Analyze domain groups/categories"
- Option 3: "Check expiration dates"
- Option 4: "Ask a custom question"

Based on the user's choice, analyze the domain data and respond. If "Ask a custom question", let the user type their question in "Other" and answer it based on the domain data.

After answering, ask if they have more questions. Continue until the user is done.

The key advantage of this mode: you have the full domain list in context and can answer arbitrary questions like:
- "Which domains are expiring soonest?"
- "Group my domains by project/brand"
- "Which TLDs do I have the most of?"
- "Do I have any domains I should probably drop?"
- "Show me all domains related to 'agentic'"

---

## DNS List

### Step 1: Detect provider

Extract the domain from `$ARGUMENTS` (the word after `dns list`).

```bash
bash ${CLAUDE_SKILL_DIR}/references/dns-detect.sh <domain>
```

Parse the JSON. Print: "DNS provider: <Provider> (nameservers: <ns1>, <ns2>)"

### Step 2: Fetch records

If provider is `cloudflare`:
```bash
bash ${CLAUDE_SKILL_DIR}/references/dns-cloudflare.sh list <domain>
```

If provider is `godaddy`:
```bash
bash ${CLAUDE_SKILL_DIR}/references/dns-godaddy.sh list <domain>
```

If provider is `unknown`, use AskUserQuestion:
- "Nameservers don't match GoDaddy or Cloudflare. Which provider manages DNS for this domain?"
- Option 1: "Cloudflare"
- Option 2: "GoDaddy"
- Option 3: "Cancel"

### Step 3: Format and display

For Cloudflare records, print:

```
#   Type    Name              Value                    TTL     Proxied
1   A       example.com       192.168.1.1              auto    yes
2   CNAME   www               example.com              auto    yes
3   MX      example.com       mail.example.com         3600    -
4   TXT     example.com       v=spf1 include:...       auto    -
```

For GoDaddy records, print (no Proxied column, no # id):

```
#   Type    Name    Value                    TTL
1   A       @       192.168.1.1              3600
2   CNAME   www     example.com              3600
3   MX      @       mail.example.com         3600
```

Print total: "N record(s) for <domain>."

---

## DNS Add

### Step 1: Detect provider

Extract the domain from `$ARGUMENTS`.

```bash
bash ${CLAUDE_SKILL_DIR}/references/dns-detect.sh <domain>
```

Print the detected provider.

### Step 2: Collect record details

Use AskUserQuestion:
- Question: "What type of DNS record?"
- Options: "A", "AAAA", "CNAME", "MX", "TXT"

Use AskUserQuestion:
- Question: "Record name (e.g., @, www, mail, subdomain):"
- (User types in "Other")

Use AskUserQuestion:
- Question: "Record value (e.g., IP address, hostname, text):"
- (User types in "Other")

Use AskUserQuestion:
- Question: "TTL (time to live)?"
- Option 1: "Auto (Recommended)" — Use 1 for Cloudflare, 3600 for GoDaddy
- Option 2: "3600 (1 hour)"
- Option 3: "86400 (1 day)"

If provider is `cloudflare`:
Use AskUserQuestion:
- Question: "Proxy through Cloudflare? (orange cloud)"
- Option 1: "Yes (Recommended for web traffic)" — proxied=true
- Option 2: "No (DNS only)" — proxied=false

### Step 3: Confirm and create

Print a summary of what will be created. Use AskUserQuestion to confirm:
- "Create this DNS record?"
- Option 1: "Yes, create it"
- Option 2: "Cancel"

If confirmed, for Cloudflare:
```bash
bash ${CLAUDE_SKILL_DIR}/references/dns-cloudflare.sh add <domain> <type> <name> <value> <ttl> <proxied>
```

For GoDaddy:
```bash
bash ${CLAUDE_SKILL_DIR}/references/dns-godaddy.sh add <domain> <type> <name> <value> <ttl>
```

Report the result.

---

## DNS Update

### Step 1: Detect provider and list records

Extract the domain from `$ARGUMENTS`.

```bash
bash ${CLAUDE_SKILL_DIR}/references/dns-detect.sh <domain>
```

Print the detected provider. Then list records (same as DNS List Step 2-3).

### Step 2: Select record

Use AskUserQuestion:
- Question: "Which record number to update?"
- (User types the number in "Other")

### Step 3: Collect new value

Show the current record values. Use AskUserQuestion:
- Question: "New value for this record:"
- (User types in "Other")

Optionally ask about TTL and proxied changes.

### Step 4: Confirm and update

Print a summary showing old → new. Use AskUserQuestion to confirm.

If confirmed, for Cloudflare (use record id from the list):
```bash
bash ${CLAUDE_SKILL_DIR}/references/dns-cloudflare.sh update <domain> <record_id> <value> <ttl> <proxied>
```

For GoDaddy (use type and name):
```bash
bash ${CLAUDE_SKILL_DIR}/references/dns-godaddy.sh update <domain> <type> <name> <value> <ttl>
```

Report the result.

---

## DNS Delete

### Step 1: Detect provider and list records

Extract the domain from `$ARGUMENTS`.

```bash
bash ${CLAUDE_SKILL_DIR}/references/dns-detect.sh <domain>
```

Print the detected provider. Then list records (same as DNS List Step 2-3).

### Step 2: Select record

Use AskUserQuestion:
- Question: "Which record number to delete?"
- (User types the number in "Other")

### Step 3: Confirm deletion

Show the record that will be deleted. Use AskUserQuestion:
- "Delete this DNS record? This cannot be undone."
- Option 1: "Yes, delete it"
- Option 2: "Cancel"

If confirmed, for Cloudflare:
```bash
bash ${CLAUDE_SKILL_DIR}/references/dns-cloudflare.sh delete <domain> <record_id>
```

For GoDaddy:
```bash
bash ${CLAUDE_SKILL_DIR}/references/dns-godaddy.sh delete <domain> <type> <name> <value>
```

Report the result.

---

## Connect

End-to-end workflow: GoDaddy domain → Cloudflare zone → Railway custom domain.

Extract the domain from `$ARGUMENTS` (the word after `connect`).

### Step 1: Verify domain ownership

```bash
bash ${CLAUDE_SKILL_DIR}/references/godaddy-domains.sh info <domain>
```

If the request fails, print the error and stop.

Print: "Domain: <domain> — Status: <status>, Nameservers: <ns list>"

### Step 2: Check/create Cloudflare zone

```bash
bash ${CLAUDE_SKILL_DIR}/references/cloudflare-zones.sh get <domain>
```

If `found` is true:
- Print: "Cloudflare zone exists. Status: <status>. Nameservers: <ns1>, <ns2>"
- Skip to Step 3.

If `found` is false:
Use AskUserQuestion:
- "Domain <domain> has no Cloudflare zone. Create one?"
- Option 1: "Yes, create zone"
- Option 2: "Skip Cloudflare" — Stop the connect workflow

If yes:
```bash
bash ${CLAUDE_SKILL_DIR}/references/cloudflare-zones.sh create <domain>
```

Print the result including assigned nameservers.

### Step 3: Update GoDaddy nameservers

Get the Cloudflare-assigned nameservers from the zone (from Step 2 output).
Get the current GoDaddy nameservers:

```bash
bash ${CLAUDE_SKILL_DIR}/references/godaddy-nameservers.sh get <domain>
```

Compare. If nameservers already match Cloudflare's, print: "Nameservers already point to Cloudflare. Skipping." and go to Step 4.

If different, print the change clearly:
```
Current nameservers:  ns1.domaincontrol.com, ns2.domaincontrol.com
New nameservers:      ada.ns.cloudflare.com, bob.ns.cloudflare.com
```

Use AskUserQuestion:
- "Update nameservers to Cloudflare? This changes live DNS and may take up to 24h to propagate."
- Option 1: "Yes, update nameservers"
- Option 2: "Skip" — Continue without changing nameservers

If yes:
```bash
bash ${CLAUDE_SKILL_DIR}/references/godaddy-nameservers.sh set <domain> <cf_ns1> <cf_ns2>
```

Report the result.

### Step 4: Check Cloudflare activation

```bash
bash ${CLAUDE_SKILL_DIR}/references/cloudflare-zones.sh check <domain>
```

If status is `active`: Print: "Cloudflare zone is active."
If status is `pending`: Print: "Zone is pending activation. Nameserver changes can take up to 24 hours to propagate. Check back with `/webinitor dns list <domain>` later."

Use AskUserQuestion:
- "Continue to Railway custom domain setup?"
- Option 1: "Yes, configure Railway"
- Option 2: "Done" — Print summary and stop

### Step 5: Configure Railway custom domain

Check if current directory is linked to a Railway project:

```bash
railway status --json 2>/dev/null
```

If linked, print: "Detected Railway project: <project_name>, service: <service_name>"
Use AskUserQuestion:
- "Add <domain> as a custom domain to this Railway service?"
- Option 1: "Yes, use this project"
- Option 2: "Different project" — Ask user to `railway link` in another directory
- Option 3: "Skip Railway" — Go to Step 6

If not linked:
Print: "No Railway project linked in this directory."
Use AskUserQuestion:
- "Would you like to link a Railway project first?"
- Option 1: "Yes" — Tell user to type `! railway link` then check again
- Option 2: "Skip Railway" — Go to Step 6

Once a project is linked, add the custom domain:
```bash
railway domain
```

Note: `railway domain` is interactive. Tell the user: "Type `! railway domain` to add your custom domain. Enter `<domain>` when prompted."

After the domain is added, Railway provides a CNAME target (typically `<service>.up.railway.app`). Create the DNS record in Cloudflare:

```bash
bash ${CLAUDE_SKILL_DIR}/references/dns-cloudflare.sh add <domain> CNAME <name> <railway-target> 1 true
```

### Step 6: Summary

Print a final summary:

```
=== CONNECT SUMMARY: <domain> ===

GoDaddy:    Domain verified ✓
Cloudflare: Zone <active|pending> ✓
            Nameservers: <ns1>, <ns2>
Railway:    Custom domain <configured|skipped>

Next steps:
  - <any pending items, e.g., "Wait for Cloudflare activation">
  - Use /webinitor dns list <domain> to verify DNS records
```

---

## Deploy Init

Scaffold a new full-stack web app: Cloudflare Worker (SPA + proxy) + Hono API on Railway + PostgreSQL.

### Step 1: Detect existing project

```bash
ls wrangler.jsonc railway.toml Dockerfile client/wrangler.jsonc 2>/dev/null
```

If any files found, print what was detected and use AskUserQuestion:
- "Project files already exist. Continue and overwrite?"
- Option 1: "Yes, continue"
- Option 2: "Cancel"

Check if `--config-only` is in `$ARGUMENTS`. If so, set CONFIG_ONLY mode.

### Step 2: Collect project configuration

Use AskUserQuestion:
- Question: "Project name (lowercase, hyphens ok — used for worker name, packages, DB):"
- (User types in "Other")

Validate: lowercase, alphanumeric with hyphens, 2-64 chars. If invalid, ask again.

Use AskUserQuestion:
- Question: "Custom domain (e.g., mysite.com, or 'none'):"
- (User types in "Other")

If not CONFIG_ONLY:
Use AskUserQuestion:
- Question: "Authentication providers:"
- Option 1: "None — no auth"
- Option 2: "GitHub OAuth"
- Option 3: "Google OAuth"
- Option 4: "Both GitHub + Google"

### Step 3: Generate files

Set template variables:
- `{{PROJECT_NAME}}` = user's project name
- `{{CUSTOM_DOMAIN}}` = user's domain (or remove domain routes if 'none')
- `{{API_BACKEND_URL}}` = `https://REPLACE_AFTER_FIRST_DEPLOY.up.railway.app`
- `{{PACKAGE_SCOPE}}` = `@` + project name

**If CONFIG_ONLY**, read and generate only:
- `client/wrangler.jsonc` from `${CLAUDE_SKILL_DIR}/references/templates/client/wrangler.jsonc.tmpl`
- `railway.toml` from `${CLAUDE_SKILL_DIR}/references/templates/root/railway.toml.tmpl`
- `Dockerfile` from `${CLAUDE_SKILL_DIR}/references/templates/root/Dockerfile.tmpl`
- `docker-compose.yml` from `${CLAUDE_SKILL_DIR}/references/templates/root/docker-compose.yml.tmpl`
- `.github/workflows/deploy-client.yml` from `${CLAUDE_SKILL_DIR}/references/templates/github/deploy-client.yml.tmpl`
- `.env.example` from `${CLAUDE_SKILL_DIR}/references/templates/root/env.example.tmpl`

**If full scaffold**, read and generate ALL template files. For each `.tmpl` file under `${CLAUDE_SKILL_DIR}/references/templates/`:
1. Read the template
2. Replace all `{{PLACEHOLDER}}` values with the user's input
3. Write the output file (strip `.tmpl` extension, use the template's relative path)

**Auth-conditional logic:**
- If auth=none: use `schema-no-auth.ts.tmpl` instead of `schema.ts.tmpl`, skip `auth/` directory entirely, remove auth routes from `app.ts` (delete lines between `// AUTH_ROUTES_START` and `// AUTH_ROUTES_END`)
- If auth=github: include `auth/github.ts.tmpl`, `auth/session.ts.tmpl`, `auth/middleware.ts.tmpl`. In `app.ts`, keep GitHub auth route, remove Google auth route.
- If auth=google: include `auth/google.ts.tmpl`, `auth/session.ts.tmpl`, `auth/middleware.ts.tmpl`. In `app.ts`, keep Google auth route, remove GitHub auth route.
- If auth=both: include all auth files, keep all auth routes in `app.ts`.

### Step 4: Post-scaffold summary

Print all generated files grouped by directory.

Print next steps:
```
Next steps:
  1. docker compose up -d              (start local PostgreSQL)
  2. cd server && npm install && npm run migrate && npm run dev
  3. cd client && npm install && npm run dev
  4. Open http://localhost:5173

For auth setup, configure these in server/.env:
  - GITHUB_CLIENT_ID / GITHUB_CLIENT_SECRET (if GitHub)
  - GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET (if Google)
  - SESSION_SECRET (generate with: openssl rand -hex 32)
```

### Step 5: Offer to connect domain

If a custom domain was provided (not 'none'):
Use AskUserQuestion:
- "Wire up DNS for <domain>? This runs the connect workflow (GoDaddy → Cloudflare → Railway)."
- Option 1: "Yes, connect now"
- Option 2: "Later — I'll run /webinitor connect <domain>"

If yes, go to the **Connect** section with the domain.

---

## Deploy Push

Deploy the current project to Railway (server) and Cloudflare (client).

### Step 1: Detect project structure

```bash
ls client/wrangler.jsonc railway.toml Dockerfile 2>/dev/null
```

If `railway.toml` not found: print "No railway.toml found. Run `/webinitor deploy init` first." and stop.

### Step 2: Pre-flight checks

```bash
bash ${CLAUDE_SKILL_DIR}/references/status-all.sh
```

Verify Wrangler and Railway CLIs are installed and authenticated. If any check fails, print the issue and suggest `/webinitor setup`.

Check Railway project link:
```bash
railway status 2>&1
```

If not linked:
Print: "No Railway project linked. Type `! railway link` to link, or `! railway init` to create one."

Use AskUserQuestion:
- "Have you linked a Railway project?"
- Option 1: "Yes, check again"
- Option 2: "Cancel deploy"

If cancel, stop.

### Step 3: Check for placeholder URL

```bash
grep -r "REPLACE_AFTER_FIRST_DEPLOY" client/src/worker.ts 2>/dev/null
```

If found and this is the first deploy, note that the Railway URL will need to be updated after deploy. Proceed anyway — server deploys first.

### Step 4: Deploy server to Railway

Print: "Deploying server to Railway..."

```bash
railway up --detach 2>&1
```

Report the output. After deploy, get the Railway URL:
```bash
railway status 2>&1
```

If the worker.ts still has the placeholder URL, tell the user:
> Update `client/src/worker.ts` — replace `REPLACE_AFTER_FIRST_DEPLOY` with your Railway URL (shown above).

### Step 5: Deploy client to Cloudflare

If `client/wrangler.jsonc` exists:
Print: "Deploying client to Cloudflare..."

```bash
cd client && npm install && npm run build && npx wrangler deploy 2>&1
```

Report the result.

If no client config, skip this step.

### Step 6: Health check

If a custom domain is configured (check `client/wrangler.jsonc` for routes):
```bash
curl -sf https://<domain>/health 2>/dev/null
```

Report health status.

### Step 7: Summary

Print:
```
=== DEPLOY COMPLETE ===

Server (Railway):    deployed
Client (Cloudflare): deployed

Endpoints:
  Frontend: https://<domain>
  Health:   https://<domain>/health
```

---

## Deploy Status

Check deployment status of the current project.

### Step 1: Detect project

```bash
ls client/wrangler.jsonc railway.toml 2>/dev/null
```

If neither found, print: "No deploy configuration found. Run `/webinitor deploy init` first." and stop.

### Step 2: Railway status

```bash
railway status 2>&1
```

Parse and report project name, service, environment.

### Step 3: Cloudflare Worker status

If `client/wrangler.jsonc` exists, extract worker name:
```bash
cat client/wrangler.jsonc | grep -o '"name"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1
```

```bash
cd client && npx wrangler deployments list --limit 1 2>&1
```

Report latest deployment.

### Step 4: Domain & DNS check

Extract custom domain from `client/wrangler.jsonc` (look for domain in routes/custom_domains).

If found:
```bash
bash ${CLAUDE_SKILL_DIR}/references/dns-detect.sh <domain>
```

Report DNS provider status.

### Step 5: Health check

```bash
curl -sf https://<domain>/health 2>/dev/null | jq . 2>/dev/null
```

Report health status or error.

### Step 6: Summary

Print:
```
=== DEPLOY STATUS ===

Railway:
  Project: <name>
  Status:  <status>

Cloudflare Worker:
  Name:    <worker-name>
  Domains: <domain1>, <domain2>

DNS:     <provider> (<ns1>, <ns2>)
Health:  <status>
```

---

## Help

Print:

```
Webinitor v2.2.0

Website infrastructure management — setup, status, and configuration
for Cloudflare (Wrangler + API), Railway, and GoDaddy.

Usage: /webinitor [command]

Commands:
  status                   Show status of all services (default)
  setup                    Interactive setup for all services
  setup cloudflare         Setup Cloudflare (CLI + API token)
  setup railway            Setup Railway CLI
  setup godaddy            Setup GoDaddy API credentials
  configure                Edit service configuration
  configure godaddy        Edit GoDaddy API credentials
  configure cloudflare     Edit Cloudflare API token
  domains                  List all domains
  domains list             List domains (filters below)
    --status <STATUS>        Filter by status (e.g., ACTIVE)
    --expiring               Expiring within 30 days
    --privacy-off            WHOIS privacy disabled
    --autorenew-off          Auto-renew disabled
    --name <pattern>         Filter by domain name
  domains search <query>   Search domains by name
  domains info <domain>    Show detailed domain info
  domains privacy-check    Audit privacy & security settings
  domains chat             Discuss your domain portfolio
  dns list <domain>        List DNS records (auto-detects provider)
  dns add <domain>         Add a DNS record
  dns update <domain>      Update a DNS record
  dns delete <domain>      Delete a DNS record
  connect <domain>         GoDaddy → Cloudflare → Railway workflow
  deploy init              Scaffold full-stack web app
  deploy init --config-only  Config files only (no app code)
  deploy push              Deploy to Railway + Cloudflare
  deploy status            Check deployment health
  --help                   Show this help
  --version                Show version

Services:
  Cloudflare — DNS, zones, Workers via API + Wrangler CLI
  Railway    — App hosting and databases via Railway CLI
  GoDaddy    — Domain portfolio management via REST API

Config: ~/.webinitor/config.json (mode 600)
```
