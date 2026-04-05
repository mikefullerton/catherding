---
name: site-manager
description: "Scaffold, deploy, and manage a suite of websites (backend + main + admin + dashboard) as a unified platform. /site-manager init, /site-manager deploy, /site-manager status, /site-manager manifest, /site-manager seed-admin, /site-manager --help"
version: "1.2.0"
argument-hint: "[init|deploy|status|manifest|seed-admin|test|--help|--version]"
allowed-tools: Read, Write, Edit, Bash(bash *), Bash(python3 *), Bash(brew *), Bash(npm *), Bash(wrangler *), Bash(railway *), Bash(curl *), Bash(which *), Bash(chmod *), Bash(cat *), Bash(test *), Bash(mkdir *), Bash(jq *), Bash(ls *), Bash(head *), Bash(tail *), Bash(sort *), Bash(column *), Bash(wc *), Bash(grep *), Bash(date *), Bash(docker *), Bash(cd *), Bash(gh *), AskUserQuestion
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

site-manager v1.2.0

If `$ARGUMENTS` is `--version`, respond with exactly:
> site-manager v1.2.0

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
| `test` or `test smoke` | Go to **Test Smoke** |
| `test validate` | Go to **Test Validate** |
| `--help` | Go to **Help** |
| `--version` | Print version (handled in Startup) |
| anything else | Print: "Usage: /site-manager [init\|deploy\|status\|manifest\|seed-admin\|test\|--help\|--version]" and stop |

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

**Special files:**
- `root/gitignore.tmpl` → write as `.gitignore`
- `root/env.example.tmpl` → write as `.env.example` AND copy to `.env` (so dev works immediately)
- `root/site-manifest.json.tmpl` → write as `site-manifest.json`

### Step 4: Commit and push

```bash
git add -A && git commit -m "feat: initial scaffold from site-manager v1.2.0"
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

Remove custom domain routes from wrangler.jsonc for now (workers.dev URLs will be used until DNS is configured).

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

### Step 10: Run smoke tests

```bash
python3 ${CLAUDE_SKILL_DIR}/references/smoke-test.py smoke \
  --base-url <railway-url> \
  --main-url <main-worker-url> \
  --admin-url <admin-worker-url> \
  --dashboard-url <dashboard-worker-url>
```

If any tests fail, report the failures but continue.

### Step 11: Update manifest and push

Update `site-manifest.json` with:
- All service URLs and statuses set to `"deployed"`
- `lastDeployed` timestamps
- `features.auth.adminSeeded` set to `true`

Commit and push:

```bash
git add -A && git commit -m "chore: update manifest with deployment URLs"
git push
```

### Step 12: Report and open in browser

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

Open all three site URLs in the browser.

---

## Deploy All

**Deploy all services to their platforms.**

### Step 1: Read manifest

Read `site-manifest.json` from the current directory. If not found:
> No site-manifest.json found. Run `/site-manager init` to create a project.

Then stop.

### Step 2: Pre-flight checks

Verify tools are available:

```bash
which railway && which wrangler
```

If either is missing, print:
> Missing required tools. Run `/webinitor setup` to install them.

Then stop.

Check Railway auth:
```bash
railway whoami 2>&1
```

Check Wrangler auth:
```bash
wrangler whoami 2>&1
```

If either is not authenticated, guide the user to authenticate.

### Step 3: Deploy backend

```bash
cd backend && railway up --detach
```

Wait for the deployment to report success. Get the deployment URL:

```bash
railway domain
```

Update `site-manifest.json`:
- `services.backend.status` → `"deployed"`
- `services.backend.url` → the Railway URL
- `services.backend.lastDeployed` → current ISO timestamp

### Step 4: Deploy main site

```bash
cd sites/main && wrangler deploy
```

Update `site-manifest.json`:
- `services.main.status` → `"deployed"`
- `services.main.lastDeployed` → current ISO timestamp

### Step 5: Deploy admin site

```bash
cd sites/admin && wrangler deploy
```

Update `site-manifest.json`:
- `services.admin.status` → `"deployed"`
- `services.admin.lastDeployed` → current ISO timestamp

### Step 6: Deploy dashboard

First, check if D1 database exists:

```bash
wrangler d1 list 2>&1 | grep "<project-name>-dashboard-db"
```

If not found, create it:

```bash
wrangler d1 create <project-name>-dashboard-db
```

Extract the database ID from the output and update `wrangler.jsonc` with the real ID.

Run D1 migrations:

```bash
cd sites/dashboard && wrangler d1 migrations apply <project-name>-dashboard-db
```

Deploy:

```bash
cd sites/dashboard && wrangler deploy
```

Update `site-manifest.json`:
- `services.dashboard.status` → `"deployed"`
- `services.dashboard.lastDeployed` → current ISO timestamp

### Step 7: Health check

For each deployed service with a URL, verify it responds:

```bash
curl -sf <backend-url>/api/health
curl -sf https://<domain>
curl -sf https://admin.<domain>
curl -sf https://dashboard.<domain>
```

### Step 8: Report

```
=== DEPLOYMENT COMPLETE ===

  Backend API        ✅ deployed    <backend-url>
  Main site          ✅ deployed    https://<domain>
  Admin site         ✅ deployed    https://admin.<domain>
  Dashboard          ✅ deployed    https://dashboard.<domain>

Next: /site-manager seed-admin (if not done)
      /webinitor connect <domain> (to configure DNS)
```

---

## Deploy Single

**Deploy a single service.** The service name is extracted from `$ARGUMENTS` (e.g., `deploy backend`).

### Step 1: Read manifest

Same as Deploy All Step 1.

### Step 2: Pre-flight checks

Same as Deploy All Step 2, but only check the tool needed for the target service:
- `backend` → check `railway`
- `main`, `admin`, `dashboard` → check `wrangler`

### Step 3: Deploy

Run the deployment step for the specific service (same as the corresponding step in Deploy All).

### Step 4: Update manifest

Update only the targeted service in `site-manifest.json`.

### Step 5: Report

```
=== DEPLOYED: <service> ===

  <Service name>     ✅ deployed    <url>
```

---

## Status

**Check the status of all services.**

### Step 1: Read manifest

Read `site-manifest.json` from the current directory. If not found:
> No site-manifest.json found. Run `/site-manager init` to create a project.

Then stop.

### Step 2: Check each service

For each service in the manifest:

**Backend** (if status is `"deployed"` and url is set):
```bash
curl -sf <url>/api/health --max-time 5
```
- If response is 200 with `{"status":"ok"}`: mark as ✅ healthy
- If non-200 or timeout: mark as ⚠️ unhealthy
- If url is null: mark as ⬜ not deployed

**Main / Admin / Dashboard** (if status is `"deployed"`):
```bash
curl -sf https://<domain> --max-time 5 -o /dev/null -w "%{http_code}"
```
- If 200: mark as ✅ healthy
- If non-200 or timeout: mark as ⚠️ unhealthy
- If status is `"scaffolded"`: mark as ⬜ not deployed

### Step 3: Report

```
=== SITE MANAGER STATUS ===

Project: <name> (<domain>)
Manifest: v<version>

  Backend API        <status>    <url or "not deployed">
  Main site          <status>    <domain or "not deployed">
  Admin site         <status>    <domain or "not deployed">
  Dashboard          <status>    <domain or "not deployed">

Features:
  Auth               <✅/❌> <providers list>
  Admin seeded       <✅/❌>
  Feature flags      <✅/❌> <enabled/disabled>
  Email              <✅/❌> <provider or "not configured">
  SMS                <✅/❌> <provider or "not configured">
  Observability      <✅/❌> <provider>
  Logging            <✅/❌> <structured: yes/no>
```

---

## Manifest Show

Read and pretty-print `site-manifest.json` from the current directory.

If not found:
> No site-manifest.json found. Run `/site-manager init` to create a project.

Otherwise, read the file and display it formatted with sections:

```
=== SITE MANIFEST ===

Project: <name> (<domain>)
Version: <version>
Created: <created date>

Services:
  backend      <status>  <platform>  <url>
  main         <status>  <platform>  <domain>
  admin        <status>  <platform>  <domain>
  dashboard    <status>  <platform>  <domain>

Features:
  auth:           <enabled> providers=<list> adminSeeded=<bool>
  featureFlags:   <enabled>
  email:          <enabled> provider=<provider>
  sms:            <enabled> provider=<provider>
  abTesting:      <enabled>
  observability:  <enabled> provider=<provider>
  logging:        <enabled> structured=<bool>

DNS:
  provider:     <provider>
  zoneId:       <id or "not set">
  nameservers:  <list or "not set">
  records:      <count> records
```

---

## Manifest Validate

Read `site-manifest.json` and validate its structure.

**Required fields:**
- `version` — must be a semver string
- `project.name` — non-empty string
- `project.domain` — valid domain
- `project.created` — ISO 8601 timestamp
- `services.backend`, `services.main`, `services.admin`, `services.dashboard` — each must have `status`, `platform`
- `features.auth.enabled` — boolean
- `features.auth.providers` — non-empty array

**Report:**

If valid:
```
✅ Manifest is valid (v<version>)
```

If invalid, list each issue:
```
❌ Manifest validation errors:
  - project.domain: missing or empty
  - services.backend.status: invalid value "foo" (expected: scaffolded, deployed, error)
  - features.auth.providers: empty array
```

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

## Test Smoke

**Run essential health and auth tests against a deployed project.**

### Step 1: Resolve URLs

Read `site-manifest.json` from the current directory. Extract:
- `services.backend.url` → `--base-url`
- `project.domain` → derive `--main-url` (`https://<domain>`), `--admin-url` (`https://admin.<domain>`), `--dashboard-url` (`https://dashboard.<domain>`)

If no `site-manifest.json`, ask the user for `--base-url`.

If `services.backend.url` is null or status is not `deployed`, print:
> Backend is not deployed. Run `/site-manager deploy backend` first.

Then stop.

### Step 2: Run tests

```bash
python3 ${CLAUDE_SKILL_DIR}/references/smoke-test.py smoke \
  --base-url <backend-url> \
  --main-url <main-url> \
  --admin-url <admin-url> \
  --dashboard-url <dashboard-url>
```

### Step 3: Report

Display the test output directly — it is self-formatting.

---

## Test Validate

**Run comprehensive validation tests including admin CRUD.**

### Step 1: Resolve URLs

Same as Test Smoke Step 1.

### Step 2: Get admin credentials

Ask the user for:
- Admin email
- Admin password

These are needed for admin endpoint tests (users, flags, messaging, feedback).

### Step 3: Run tests

```bash
python3 ${CLAUDE_SKILL_DIR}/references/smoke-test.py validate \
  --base-url <backend-url> \
  --main-url <main-url> \
  --admin-url <admin-url> \
  --dashboard-url <dashboard-url> \
  --admin-email <email> \
  --admin-password <password>
```

### Step 4: Report

Display the test output directly — it is self-formatting.

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
