---
name: site-manager
description: "Scaffold, deploy, and manage a suite of websites (backend + main + admin + dashboard) as a unified platform. /site-manager init, /site-manager deploy, /site-manager status, /site-manager manifest, /site-manager seed-admin, /site-manager --help"
version: "1.3.0"
argument-hint: "[init|deploy|update|verify|status|manifest|seed-admin|test|--help|--version]"
allowed-tools: Read, Write, Edit, Bash(bash *), Bash(python3 *), Bash(brew *), Bash(npm *), Bash(wrangler *), Bash(railway *), Bash(curl *), Bash(which *), Bash(chmod *), Bash(cat *), Bash(test *), Bash(mkdir *), Bash(jq *), Bash(ls *), Bash(head *), Bash(tail *), Bash(sort *), Bash(column *), Bash(wc *), Bash(grep *), Bash(date *), Bash(docker *), Bash(cd *), Bash(gh *), Bash(dig *), Bash(open *), Bash(site-manager *), AskUserQuestion
model: sonnet
---

# Site Manager v1.1.0

Scaffold, deploy, and manage a suite of 4 websites as a unified platform.

**Architecture per project:**
- **Backend API** — Hono + Drizzle + PostgreSQL (Railway)
- **Main site** (`domain.com`) — React 19 + Vite + Tailwind 4 (Cloudflare Worker)
- **Admin site** (`admin.domain.com`) — React 19 + Vite + Tailwind 4 (Cloudflare Worker)
- **Dashboard** (`dashboard.domain.com`) — React 19 + Vite + D1 SQLite (Cloudflare Worker)

## Startup

**Step 0 — Ensure permissions**: Run `python3 ${CLAUDE_SKILL_DIR}/references/ensure-permissions.py ${CLAUDE_SKILL_DIR}/SKILL.md` to whitelist this skill's tools in `~/.claude/settings.json`. This is silent and idempotent.

**CRITICAL**: The very first thing you output MUST be the version line:

site-manager v1.3.0

If `$ARGUMENTS` is `--version`, respond with exactly:
> site-manager v1.3.0

Then stop.

## Route by argument

| `$ARGUMENTS` | Action |
|---|---|
| `init` or `init <domain>` | Go to **Init** |
| `deploy` or `deploy all` | Go to **Deploy All** |
| `deploy backend` | Go to **Deploy Single** (service=backend) |
| `deploy main` | Go to **Deploy Single** (service=main) |
| `deploy admin` | Go to **Deploy Single** (service=admin) |
| `deploy dashboard` | Go to **Deploy Single** (service=dashboard) |
| `status` or empty | Go to **Status** |
| `manifest` or `manifest show` | Go to **Manifest Show** |
| `manifest validate` | Go to **Manifest Validate** |
| `seed-admin` | Go to **Seed Admin** |
| `update` | Go to **Update** |
| `verify` | Go to **Verify** |
| `test` or `test smoke` | Go to **Test Smoke** |
| `test validate` | Go to **Test Validate** |
| `--help` | Go to **Help** |
| `--version` | Print version (handled in Startup) |
| anything else | Print: "Usage: /site-manager [init\|deploy\|update\|verify\|status\|manifest\|seed-admin\|test\|--help\|--version]" and stop |

---

## Init

**Scaffold a new project with all 4 sites.**

### Step 1: Gather project info

Ask the user for all of the following. If `$ARGUMENTS` contains a domain (e.g., `init foo.com`), use it and skip the domain question.

| Field | Validation | Default |
|-------|-----------|---------|
| Project name | lowercase, `[a-z0-9-]+` | derived from domain (e.g., `foo` from `foo.com`) |
| Display name | free text | title-cased project name (e.g., `Foo`) |
| Domain | valid domain name | — (required) |
| Target directory | absolute or relative path | `./<project-name>/` |
| GitHub repo | yes/no | yes |
| GitHub org | org name or personal | personal (user's account) |
| GitHub repo name | string | `<project-name>` |
| GitHub OAuth | yes/no | no |
| Google OAuth | yes/no | no |

The **display name** is used in page titles, nav headers, and the HTML `<title>` tag. The **project name** is used for package names, worker names, database names, and directory names.

If the user wants a GitHub repo, ask for the org (or personal) and repo name. Skip these questions if they say no to GitHub repo.

Wait for the user to confirm before proceeding. Display a summary:

```
Project:   foo
Name:      Foo Bar
Domain:    foo.com
Directory: ./foo/
GitHub:    mikefullerton/foo (private)
Auth:      email/password, GitHub OAuth
```

### Step 2: Create GitHub repo and set up target directory

**If GitHub repo was requested:**

Create the repo on GitHub first, then clone it as the target directory:

```bash
gh repo create <org>/<repo-name> --private --clone
```

If org is "personal", omit the org prefix:

```bash
gh repo create <repo-name> --private --clone
```

The `--clone` flag clones the repo into `./<repo-name>/`. This becomes `<target>`.

Change the working directory into the cloned repo:

```bash
cd <target>
```

If repo creation fails, print the error and fall back to creating a local directory (Step 2b).

**If no GitHub repo (Step 2b):**

```bash
mkdir -p <target>
cd <target>
```

Then create the subdirectory structure:

```bash
mkdir -p {backend/src/{config,db,auth,routes/admin,services,middleware},shared/src,sites/{main,admin,dashboard}/src}
```

### Step 3: Copy templates

For each template in `${CLAUDE_SKILL_DIR}/references/templates/`, read the `.tmpl` file, perform placeholder substitution, and write the output file.

**Placeholder substitution table:**

| Placeholder | Value |
|------------|-------|
| `{{PROJECT_NAME}}` | Project name (e.g., `foo`) |
| `{{DISPLAY_NAME}}` | Display name (e.g., `Foo Bar`) |
| `{{DOMAIN}}` | Domain (e.g., `foo.com`) |
| `{{DB_NAME}}` | `<project-name>_dev` |
| `{{API_BACKEND_URL}}` | `https://<project-name>-production.up.railway.app` |
| `{{CREATED_AT}}` | Current ISO 8601 timestamp |
| `{{D1_DATABASE_ID}}` | `placeholder-run-wrangler-d1-create` |

**Template mapping** — read each `.tmpl` file and write to the corresponding path:

| Template directory | Output directory |
|---|---|
| `templates/root/*` | `<target>/` |
| `templates/backend/*` | `<target>/backend/` |
| `templates/shared/*` | `<target>/shared/` |
| `templates/sites/main/*` | `<target>/sites/main/` |
| `templates/sites/admin/*` | `<target>/sites/admin/` |
| `templates/sites/dashboard/*` | `<target>/sites/dashboard/` |
| `templates/github/*` | `<target>/.github/workflows/` |

Strip the `.tmpl` extension from output filenames. Preserve directory structure within each template directory.

**Conditional templates:**
- `backend/src/auth/github.ts.tmpl` — only if GitHub OAuth selected. Remove `{{#IF_GITHUB_OAUTH}}` / `{{/IF_GITHUB_OAUTH}}` wrappers when including; skip entire file when not.
- `backend/src/auth/google.ts.tmpl` — only if Google OAuth selected. Same conditional wrapper logic.
- If GitHub OAuth is selected, add `"github"` to `features.auth.providers` in site-manifest.json.
- If Google OAuth is selected, add `"google"` to `features.auth.providers` in site-manifest.json.

**Conditional wiring — after copying templates, modify these files:**

If GitHub OAuth is selected, add to `backend/src/app.ts`:
- Import: `import { githubAuth } from "./auth/github.js";`
- Route: `app.route("/api/auth/github", githubAuth);` (after the `/api/auth` route)

If Google OAuth is selected, add to `backend/src/app.ts`:
- Import: `import { googleAuth } from "./auth/google.js";`
- Route: `app.route("/api/auth/google", googleAuth);` (after the `/api/auth` route)

If GitHub OAuth is selected, add a "Sign in with GitHub" button to `sites/main/src/routes/login.tsx` and `sites/admin/src/routes/login.tsx`:
```tsx
<a
  href="/api/auth/github"
  className="w-full py-2 rounded-lg transition hover:opacity-90 font-medium text-center block"
  style={{ background: "#2a2a36", color: "#e8e6e3", border: "1px solid #3d3d50" }}
>
  Sign in with GitHub
</a>
```

If Google OAuth is selected, add a similar "Sign in with Google" button.

Add a divider between the OAuth buttons and the email/password form:
```tsx
<div className="flex items-center gap-3 my-4">
  <div className="flex-1 h-px" style={{ background: "#2a2a36" }} />
  <span className="text-xs" style={{ color: "#5a5a6a" }}>or</span>
  <div className="flex-1 h-px" style={{ background: "#2a2a36" }} />
</div>
```

**Special files:**
- `root/gitignore.tmpl` → write as `.gitignore`
- `root/env.example.tmpl` → write as `.env.example` AND copy to `.env` (so dev works immediately)
- `root/site-manifest.json.tmpl` → write as `site-manifest.json`

### Step 4: Commit and push

```bash
git add -A && git commit -m "feat: initial scaffold from site-manager v1.3.0"
```

If a GitHub repo was created in Step 2, push the initial commit:

```bash
git push -u origin main
```

### Step 5: Install dependencies and build

```bash
npm install
npm run build:shared
```

If this fails, print the error and stop — something is wrong with the scaffold.

### Step 6: Generate initial database migration

```bash
cd backend && npx drizzle-kit generate && cd ..
```

Commit the migration:

```bash
git add -A && git commit -m "chore: add initial database migration"
```

If a GitHub repo exists, push:

```bash
git push
```

### Step 7: Deploy backend to Railway

Create Railway project and Postgres:

```bash
railway init --name <project-name>
railway add --database postgres
railway add --service backend
railway link --project <project-id> --service backend --environment production
```

Set environment variables:

```bash
railway variables set JWT_SECRET="$(openssl rand -hex 32)"
railway variables set NODE_ENV=production
railway variables set CORS_ORIGIN="*"
railway variables set DATABASE_URL='${{Postgres.DATABASE_URL}}'
```

Deploy:

```bash
railway up --detach
railway domain
```

Wait for the deployment to become healthy (poll `/api/health` every 10 seconds, timeout after 3 minutes).

### Step 8: Seed admin account

Get the public DATABASE_URL from the Postgres service:

```bash
railway link --project <project-id> --service Postgres --environment production
```

Extract `DATABASE_PUBLIC_URL` from `railway variables list --json`.

Ask the user for their admin email and password (min 12 chars).

```bash
cd backend && DATABASE_URL="<public-db-url>" ADMIN_EMAIL="<email>" ADMIN_PASSWORD="<password>" npx tsx src/db/seed.ts
```

Re-link to backend service after seeding:

```bash
railway link --project <project-id> --service backend --environment production
```

### Step 9: Deploy Cloudflare Worker sites

Update all wrangler.jsonc files with the real Railway backend URL.

Remove custom domain routes from wrangler.jsonc for the initial deploy (they will be re-added after DNS is configured in Step 10).

Build and deploy each site:

```bash
cd sites/main && npx vite build && npx wrangler deploy
cd sites/admin && npx vite build && npx wrangler deploy
```

For dashboard, create D1 database first:

```bash
cd sites/dashboard
npx wrangler d1 create <project-name>-dashboard-db
```

Update `wrangler.jsonc` with the real D1 database ID, then:

```bash
npx wrangler d1 migrations apply <project-name>-dashboard-db --remote
npx vite build && npx wrangler deploy
```

Capture all deployed URLs from the wrangler output.

### Step 10: Configure DNS (GoDaddy → Cloudflare)

**Set up Cloudflare as the DNS provider and point GoDaddy nameservers to Cloudflare.**

#### 10a: Get Cloudflare credentials

Extract the Cloudflare API token and account ID. The API token should be available from wrangler's auth or environment:

```bash
CLOUDFLARE_API_TOKEN=$(grep -m1 'oauth_token' ~/.wrangler/config/default.toml 2>/dev/null | cut -d'"' -f2)
```

If not found, check environment variable `CLOUDFLARE_API_TOKEN`. If still not available, ask the user.

Get the account ID:

```bash
curl -s "https://api.cloudflare.com/client/v4/accounts" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" | jq -r '.result[0].id'
```

#### 10b: Get or create Cloudflare zone

Check if the zone already exists:

```bash
curl -s "https://api.cloudflare.com/client/v4/zones?name=<domain>" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" | jq '.result[0]'
```

If no zone exists (result is `null`), create one:

```bash
curl -s -X POST "https://api.cloudflare.com/client/v4/zones" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"<domain>","account":{"id":"<account-id>"},"type":"full"}'
```

Extract and save:
- `zone_id` — for DNS record management and manifest
- `name_servers` — array of Cloudflare nameservers (e.g., `["ada.ns.cloudflare.com","bob.ns.cloudflare.com"]`)

#### 10c: Update GoDaddy nameservers

Requires `GODADDY_API_KEY` and `GODADDY_API_SECRET` from `.env` or environment. If not set, ask the user.

Point GoDaddy's nameservers to Cloudflare:

```bash
curl -s -X PATCH "https://api.godaddy.com/v1/domains/<domain>" \
  -H "Authorization: sso-key $GODADDY_API_KEY:$GODADDY_API_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"nameServers":["<ns1>","<ns2>"]}'
```

Verify the update took effect:

```bash
curl -s "https://api.godaddy.com/v1/domains/<domain>" \
  -H "Authorization: sso-key $GODADDY_API_KEY:$GODADDY_API_SECRET" | jq '.nameServers'
```

#### 10d: Wait for zone activation

Poll Cloudflare zone status until active (nameservers verified). This can be quick (minutes) or slow (up to 24h). Poll every 30 seconds for up to 5 minutes:

```bash
curl -s "https://api.cloudflare.com/client/v4/zones/$ZONE_ID" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" | jq -r '.result.status'
```

Also check with `dig`:

```bash
dig NS <domain> +short
```

If the zone becomes `"active"` within the polling window, proceed immediately. If still `"pending"` after 5 minutes, print a warning and proceed anyway — the custom domain routes may not work until the zone activates, but workers.dev URLs remain functional.

#### 10e: Add custom domain routes and redeploy

Add custom domain routes to each site's `wrangler.jsonc`:

**sites/main/wrangler.jsonc** — add:
```json
"routes": [{"pattern": "<domain>", "custom_domain": true}]
```

**sites/admin/wrangler.jsonc** — add:
```json
"routes": [{"pattern": "admin.<domain>", "custom_domain": true}]
```

**sites/dashboard/wrangler.jsonc** — add:
```json
"routes": [{"pattern": "dashboard.<domain>", "custom_domain": true}]
```

Redeploy all workers with the new routes:

```bash
cd sites/main && npx wrangler deploy
cd sites/admin && npx wrangler deploy
cd sites/dashboard && npx wrangler deploy
```

Cloudflare automatically creates the DNS records when deploying workers with `custom_domain: true`.

#### 10f: Verify DNS configuration

Verify each domain resolves (retry up to 2 minutes if zone is active):

```bash
curl -sf https://<domain> -o /dev/null -w "%{http_code}" --max-time 10
curl -sf https://admin.<domain> -o /dev/null -w "%{http_code}" --max-time 10
curl -sf https://dashboard.<domain> -o /dev/null -w "%{http_code}" --max-time 10
```

Print verification results:

```
=== DNS VERIFICATION ===

  Nameservers:          ✅ Pointing to Cloudflare (<ns1>, <ns2>)
  Zone status:          ✅ Active (zone ID: <zone-id>)
  <domain>:             ✅ Resolves (HTTP 200)
  admin.<domain>:       ✅ Resolves (HTTP 200)
  dashboard.<domain>:   ✅ Resolves (HTTP 200)
```

If zone is still pending:

```
=== DNS VERIFICATION ===

  Nameservers:          ✅ Updated on GoDaddy → Cloudflare (<ns1>, <ns2>)
  Zone status:          ⏳ Pending (waiting for nameserver verification — can take up to 24-48h)
  Custom domain routes: ✅ Configured (will activate when zone becomes active)

  Sites accessible via workers.dev URLs in the meantime.
```

#### 10g: Update manifest with DNS info

Update `site-manifest.json`:
- `dns.zoneId` → the Cloudflare zone ID
- `dns.nameservers` → the Cloudflare nameservers array
- `dns.records` → `[{"type":"CNAME","name":"@","target":"<project>-main.workers.dev"},{"type":"CNAME","name":"admin","target":"<project>-admin.workers.dev"},{"type":"CNAME","name":"dashboard","target":"<project>-dashboard.workers.dev"}]`

Commit:

```bash
git add -A && git commit -m "chore: configure DNS for <domain>"
git push
```

### Step 11: Run smoke tests

```bash
site-manager test smoke
```

If any tests fail, report the failures but continue.

### Step 12: Update manifest and push

**Read the existing `site-manifest.json` first, then merge changes into it — do NOT rewrite from scratch.** Specifically preserve `project.displayName`, `project.name`, `project.domain`, and `project.created`.

Update these fields:
- All service URLs and statuses set to `"deployed"`
- `lastDeployed` timestamps
- `features.auth.adminSeeded` set to `true`

Commit and push:

```bash
git add -A && git commit -m "chore: update manifest with deployment URLs"
git push
```

### Step 13: Post-deployment verification

Run the verification suite:

```bash
site-manager verify
```

If any **blocking** checks fail, fix them before continuing:

- **manifest.displayName fails:** Add/fix the `project.displayName` field in site-manifest.json.
- **oauth.*.route fails (404):** The OAuth route is not mounted in `backend/src/app.ts`. Add the import and route mount per the conditional wiring instructions in Step 3. Rebuild and redeploy the backend.
- **oauth.login_buttons.* fails:** The login pages are missing OAuth buttons. Add the buttons per the conditional wiring instructions in Step 3. Rebuild and redeploy the affected site(s).
- **frontend.*.dark_theme fails:** Re-copy the login/register templates from the plugin, rebuild, and redeploy.

After fixing any failures, re-run verify.py to confirm all fixes took effect.

DNS/SSL warnings should have been resolved by Step 10. If DNS is still pending (zone not yet active), print:
> DNS zone is pending activation. Custom domains will work once Cloudflare verifies the nameservers (up to 24-48h). Sites are accessible via workers.dev URLs.

### Step 14: Report and open in browser

Print the final summary and open all sites in the browser:

```
=== {{DISPLAY_NAME}} is live! ===

  Main site:     <main-worker-url>
  Admin site:    <admin-worker-url>
  Dashboard:     <dashboard-worker-url>
  Backend API:   <railway-url>
  GitHub:        <repo-url>

  Admin login:
    Email:    <admin-email>
    Password: <admin-password>

  Smoke tests: <N>/<N> passed

  To connect your domain:
    /webinitor connect <domain>
```

Open all three site URLs in the browser:

```bash
open <main-url>
open <admin-url>
open <dashboard-url>
```

---

## Deploy All

Delegate to the `site-manager` CLI:

```bash
site-manager deploy all
```

Print the output as-is.

---

## Deploy Single

Delegate to the `site-manager` CLI:

```bash
site-manager deploy <service>
```

Print the output as-is.

---

## Status

Delegate to the `site-manager` CLI:

```bash
site-manager status
```

Print the output as-is.

---

## Manifest Show

Delegate to the `site-manager` CLI:

```bash
site-manager manifest show
```

Print the output as-is.

---

## Manifest Validate

Delegate to the `site-manager` CLI:

```bash
site-manager manifest validate
```

Print the output as-is.

---

## Seed Admin

**Create the initial admin account.**

### Step 1: Check prerequisites

Read `site-manifest.json`. Verify:
- `services.backend.status` is `"deployed"` — if not, print:
  > Backend is not deployed. Run `/site-manager deploy backend` first.
- `features.auth.adminSeeded` is not `true` — if already seeded, print:
  > Admin account already seeded. Check site-manifest.json for details.

  Ask the user if they want to re-seed anyway (this will skip if the email already exists in the DB).

### Step 2: Gather credentials

Ask the user:

| Field | Validation |
|-------|-----------|
| Admin email | valid email address |
| Admin password | minimum 12 characters |

### Step 3: Run seed

Set the environment variables and run the seed script against the deployed backend:

```bash
cd backend && ADMIN_EMAIL="<email>" ADMIN_PASSWORD="<password>" DATABASE_URL="<from Railway>" npm run db:seed
```

To get the DATABASE_URL from Railway:
```bash
cd backend && railway variables --json 2>/dev/null | jq -r '.DATABASE_URL // empty'
```

If the DATABASE_URL can't be retrieved, ask the user to provide it.

### Step 4: Update manifest

Update `site-manifest.json`:
- `features.auth.adminSeeded` → `true`

### Step 5: Report

```
✅ Admin account created

  Email: <email>
  Role:  admin

  Login at: https://admin.<domain>/login
```

---

## Update

**Re-scaffold an existing project with the latest templates, rebuild, and redeploy.**

### Step 1: Read manifest

Read `site-manifest.json` from the current directory. If not found:
> No site-manifest.json found. Run `/site-manager init` to create a project.

Then stop.

Extract project info: `project.name`, `project.domain`, `project.displayName`, and all service URLs/statuses.

### Step 2: Re-scaffold templates

For each template in `${CLAUDE_SKILL_DIR}/references/templates/`, read the `.tmpl` file, perform placeholder substitution (same table as Init Step 3), and **overwrite** the output file.

**Preserve these files** (do not overwrite):
- `.env` and `.env.example` — user may have customized
- `site-manifest.json` — contains deployment state
- `backend/src/db/migrations/` — user's migration history
- `backend/src/db/seed.ts` — user may have customized
- Any file not generated from a template

For all other files, overwrite with the latest template output.

### Step 3: Rebuild

```bash
npm install
npm run build:shared
npm run build:backend
```

### Step 4: Redeploy all services

Follow the same deploy steps as Init Steps 9 (CF Workers) — build and deploy each site.

For the backend, commit and push first (Railway auto-deploys from the repo, or use `railway up`).

```bash
git add -A && git commit -m "chore: update templates to site-manager v1.3.0"
git push
```

Deploy each CF Worker site:

```bash
cd sites/main && npx vite build && npx wrangler deploy
cd sites/admin && npx vite build && npx wrangler deploy
cd sites/dashboard && npx vite build && npx wrangler deploy
```

### Step 5: Verify and update DNS

Check that DNS is still correctly configured. Read `dns.zoneId` from `site-manifest.json`.

**If `dns.zoneId` is set (DNS was previously configured):**

Verify the Cloudflare zone is still active:

```bash
curl -s "https://api.cloudflare.com/client/v4/zones/$ZONE_ID" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" | jq -r '.result.status'
```

Verify custom domain routes are present in each `wrangler.jsonc`. If routes were removed during template re-scaffolding (templates don't include routes), re-add them:

**sites/main/wrangler.jsonc** — add if missing:
```json
"routes": [{"pattern": "<domain>", "custom_domain": true}]
```

**sites/admin/wrangler.jsonc** — add if missing:
```json
"routes": [{"pattern": "admin.<domain>", "custom_domain": true}]
```

**sites/dashboard/wrangler.jsonc** — add if missing:
```json
"routes": [{"pattern": "dashboard.<domain>", "custom_domain": true}]
```

If routes were re-added, redeploy the affected workers:

```bash
cd sites/main && npx wrangler deploy
cd sites/admin && npx wrangler deploy
cd sites/dashboard && npx wrangler deploy
```

Verify each custom domain resolves:

```bash
curl -sf https://<domain> -o /dev/null -w "%{http_code}" --max-time 10
curl -sf https://admin.<domain> -o /dev/null -w "%{http_code}" --max-time 10
curl -sf https://dashboard.<domain> -o /dev/null -w "%{http_code}" --max-time 10
```

Print verification results:

```
=== DNS VERIFICATION ===

  Zone status:          ✅ Active
  <domain>:             ✅ Resolves (HTTP 200)
  admin.<domain>:       ✅ Resolves (HTTP 200)
  dashboard.<domain>:   ✅ Resolves (HTTP 200)
```

If any domain fails to resolve, report the failure but continue to smoke tests.

**If `dns.zoneId` is null (DNS was never configured):**

Skip DNS verification. Print:
> DNS not configured. Run `/site-manager init` or configure manually.

### Step 6: Run smoke tests

```bash
site-manager test smoke
```

### Step 7: Report

Print what was updated. Do **not** auto-open sites in the browser (only Init opens sites).

```
=== UPDATE COMPLETE ===

  Templates updated to site-manager v1.3.0
  DNS:        <✅ verified / ⏳ pending / ⬜ not configured>
  Smoke tests: <N>/<N> passed

  Main site:     <main-url>
  Admin site:    <admin-url>
  Dashboard:     <dashboard-url>
```

---

## Verify

Delegate to the `site-manager` CLI:

```bash
site-manager verify
```

The CLI auto-detects OAuth providers and domain from the manifest.

If there are failures that need auto-fixing (missing OAuth routes, login buttons, dark theme), apply fixes manually:

- **manifest.displayName:** Ask user, update `site-manifest.json`
- **oauth routes (404):** Add missing import and route to `backend/src/app.ts`, rebuild, redeploy
- **oauth login buttons:** Add buttons per conditional wiring instructions, rebuild, redeploy
- **dark theme missing:** Re-copy templates, rebuild, redeploy
- **DNS/SSL warnings:** Suggest `/webinitor connect <domain>`

After fixing, run `site-manager verify` again to confirm.

---

## Test Smoke

Delegate to the `site-manager` CLI:

```bash
site-manager test smoke
```

The CLI reads URLs from `site-manifest.json` automatically.

---

## Test Validate

Ask the user for admin email and password, then delegate:

```bash
site-manager test validate --admin-email <email> --admin-password <password>
```

---

## Help

Print:

```
Site Manager v1.1.0 — Scaffold, deploy, and manage website suites

Commands:
  /site-manager init [domain]       Scaffold a new project (backend + 3 sites)
  /site-manager deploy [service]    Deploy all services (or: backend, main, admin, dashboard)
  /site-manager status              Check status of all services
  /site-manager manifest            View site-manifest.json
  /site-manager manifest validate   Validate manifest schema
  /site-manager seed-admin          Create initial admin account
  /site-manager update              Re-scaffold with latest templates and redeploy
  /site-manager verify              Run post-deployment verification checks
  /site-manager test [smoke]        Run smoke tests (health + auth)
  /site-manager test validate       Run full validation tests (admin CRUD, flags, etc.)
  /site-manager --help              Show this help
  /site-manager --version           Show version

Tech Stack:
  Backend:    Hono + Drizzle + PostgreSQL (Railway)
  Frontends:  React 19 + Vite + Tailwind 4 + Tanstack Query/Router
  Edge:       Cloudflare Workers
  Dashboard:  Cloudflare Workers + D1 SQLite
  Auth:       Email/password + optional GitHub/Google OAuth

Template Placeholders:
  {{PROJECT_NAME}}     Project name (lowercase, hyphens)
  {{DISPLAY_NAME}}     Display name (e.g., My Agentic Projects)
  {{DOMAIN}}           Primary domain (e.g., foo.com)
  {{DB_NAME}}          Database name (<project>_dev)
  {{API_BACKEND_URL}}  Railway backend URL
  {{D1_DATABASE_ID}}   Cloudflare D1 database ID
```
