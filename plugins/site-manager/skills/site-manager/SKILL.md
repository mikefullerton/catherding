---
name: site-manager
description: "Scaffold, deploy, and manage a suite of websites (backend + main + admin + dashboard) as a unified platform. /site-manager init, /site-manager deploy, /site-manager status, /site-manager manifest, /site-manager seed-admin, /site-manager --help"
version: "1.3.0"
argument-hint: "[init|deploy|update|verify|repair|status|manifest|seed-admin|--help|--version]"
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
| `migrate` or `migrate <domain>` | Go to **Migrate** |
| `go-live` | Go to **Go Live** |
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
| `repair` | Go to **Repair** |
| `--help` | Go to **Help** |
| `--version` | Print version (handled in Startup) |
| anything else | Print usage and stop |

## Manifest location

The project manifest lives at `.site/manifest.json`. If a legacy `site-manifest.json` exists in the project root, migrate it:

```bash
mkdir -p .site && mv site-manifest.json .site/manifest.json
```

All references to "manifest" in this skill mean `.site/manifest.json`.

---

## Init

**Scaffold a new project.**

### Step 1: Gather project info

Ask the user for project info, then determine the site architecture based on their answers. If `$ARGUMENTS` contains a domain (e.g., `init foo.com`), use it and skip the domain question.

**Phase 1 — basics (always ask):**

| Field | Validation | Default |
|-------|-----------|---------|
| Project name | lowercase, `[a-z0-9-]+` | derived from domain (e.g., `foo` from `foo.com`) |
| Display name | free text | title-cased project name (e.g., `Foo`) |
| Domain | valid domain name | — (required) |
| Target directory | absolute or relative path | `./<project-name>/` |
| GitHub repo | yes/no | yes |
| GitHub org | org name or personal | personal (user's account) |
| GitHub repo name | string | `<project-name>` |

**Phase 2 — architecture:**

Ask: **What kind of project is this?**

| Choice | Description |
|--------|-------------|
| **Auth service** | Shared authentication service for all your sites |
| **Full site** | Multi-user site with backend, auth, admin, and dashboard |
| **API site** | Single-user site with a backend API |
| **Worker site** | Frontend-only Cloudflare Worker |

Based on the choice:

**Auth service** — scaffolds a Railway backend + Postgres focused entirely on authentication. RS256 JWT, JWKS endpoint, user management API. This is the **"auth-service"** project type. Only one of these is needed across all your projects.

**Full site** — ask: **Do you have a shared auth service?**
- If yes: ask for the auth service URL. Scaffolds backend + main + admin + dashboard, all validating JWTs from the auth service. No local auth code.
- If no: ask about auth providers (GitHub OAuth, Google OAuth). Scaffolds with built-in auth (legacy mode). This is the **"full"** project type.

**API site** — ask: **Do you have a shared auth service?**
- If yes: ask for the auth service URL. Backend validates JWTs from the auth service.
- If no: scaffolds without auth.
This is the **"api"** project type.

**Worker site** — ask: **Do you need persistent storage?**

| Storage | Use case |
|---------|----------|
| D1 SQLite | Structured data (lists, records, settings) |
| KV | Key-value (config, cache, simple state) |
| R2 | Files and blobs (images, uploads, exports) |
| None | Static site or external APIs only |

Multiple storage options can be selected. This is the **"worker"** project type.

**Phase 3 — confirm:**

Wait for the user to confirm before proceeding. Display a summary appropriate to the project type:

Auth service:
```
Project:   my-auth
Name:      My Auth Service
Type:      auth-service (Railway + Postgres)
Directory: ./my-auth/
GitHub:    mikefullerton/my-auth (private)
JWT:       RS256 (asymmetric)
Endpoints: login, register, refresh, verify, me, JWKS
```

Full project (with auth service):
```
Project:   foo
Name:      Foo Bar
Domain:    foo.com
Type:      full (backend + main + admin + dashboard)
Auth:      https://my-auth-production.up.railway.app
Directory: ./foo/
GitHub:    mikefullerton/foo (private)
```

Full project (built-in auth, legacy):
```
Project:   foo
Name:      Foo Bar
Domain:    foo.com
Type:      full (backend + main + admin + dashboard)
Auth:      built-in (email/password, GitHub OAuth)
Directory: ./foo/
GitHub:    mikefullerton/foo (private)
```

API project:
```
Project:   foo
Name:      Foo Bar
Domain:    foo.com
Type:      api (backend + main site)
Auth:      https://my-auth-production.up.railway.app (or: none)
Directory: ./foo/
GitHub:    mikefullerton/foo (private)
```

Worker project:
```
Project:   foo
Name:      Foo Bar
Domain:    foo.com
Type:      worker (Cloudflare Worker)
Storage:   D1 SQLite, KV
Directory: ./foo/
GitHub:    mikefullerton/foo (private)
```

Record the project type in `.site/manifest.json` as `project.type` (`auth-service`, `full`, `api`, or `worker`).

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

Then create the subdirectory structure based on project type:

**Auth service:**
```bash
mkdir -p src/{config,db,auth,routes,middleware}
```

**Full project:**
```bash
mkdir -p {backend/src/{config,db,auth,routes/admin,services,middleware},shared/src,sites/{main,admin,dashboard}/src}
```

**API project:**
```bash
mkdir -p {backend/src/{config,db,routes,services,middleware},shared/src,sites/main/src}
```

**Worker project:**
```bash
mkdir -p src
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
| `{{PROJECT_TYPE}}` | Project type: `auth-service`, `full`, `api`, or `worker` |
| `{{AUTH_SERVICE_URL}}` | Auth service URL (if using external auth, else empty) |
| `{{SITE_MANAGER_VERSION}}` | Current site-manager version (e.g., `1.3.0`) |

**Template mapping** — which templates to copy depends on project type:

**Auth service** — no templates exist yet, scaffold directly:

The auth service is a standalone Hono + Drizzle + Postgres app (same stack as the backend). Generate these files directly (not from templates):

```
<target>/
  package.json              — hono, drizzle-orm, pg, jose (for RS256 JWT)
  tsconfig.json
  drizzle.config.ts
  Dockerfile                — same as backend template
  railway.toml
  .env.example              — DATABASE_URL, JWT_PRIVATE_KEY, JWT_PUBLIC_KEY
  .gitignore
  .site/manifest.json       — project type: auth-service
  src/
    index.ts                — Hono app entry point
    config/
      env.ts                — environment variable loading
      keys.ts               — load RS256 key pair from env
    db/
      client.ts             — Drizzle + Postgres connection
      schema.ts             — users table, refresh_tokens table
      migrate.ts            — migration runner
      seed.ts               — seed initial admin user
    auth/
      jwt.ts                — sign/verify with RS256, token generation
      password.ts           — bcrypt hash/verify
      session.ts            — refresh token management
    routes/
      auth.ts               — POST /login, /register, /refresh, /logout
      users.ts              — GET /me, admin user management
      jwks.ts               — GET /.well-known/jwks.json (public key)
      health.ts             — GET /health
    middleware/
      cors.ts
      error.ts              — RFC 9457 error responses
      logger.ts
      auth.ts               — JWT verification middleware (for protected routes)
```

**Database schema (users table):**
```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'user',  -- 'admin' | 'user'
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE refresh_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  token_hash TEXT NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**JWT details:**
- Algorithm: RS256 (asymmetric)
- Access token: 4 hour expiry, contains `{sub: userId, email, role}`
- Refresh token: 30 day expiry, stored hashed in Postgres
- Key pair: generated during init, stored as `JWT_PRIVATE_KEY` and `JWT_PUBLIC_KEY` env vars (PEM format)

**JWKS endpoint** (`GET /.well-known/jwks.json`):
Returns the public key in JWK format. Any service can fetch this to verify tokens. Response is cacheable (Cache-Control: max-age=3600).

**API endpoints:**
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /api/auth/register | none | Create account (email + password) |
| POST | /api/auth/login | none | Get access + refresh tokens |
| POST | /api/auth/refresh | none | Exchange refresh token for new pair |
| POST | /api/auth/logout | bearer | Revoke refresh token |
| GET | /api/auth/me | bearer | Get current user |
| GET | /api/admin/users | bearer (admin) | List all users |
| PATCH | /api/admin/users/:id | bearer (admin) | Update user role |
| DELETE | /api/admin/users/:id | bearer (admin) | Delete user |
| GET | /.well-known/jwks.json | none | Public key for JWT verification |
| GET | /api/health | none | Health check |

**Full project** — all templates:

| Template directory | Output directory |
|---|---|
| `templates/root/*` | `<target>/` |
| `templates/backend/*` | `<target>/backend/` |
| `templates/shared/*` | `<target>/shared/` |
| `templates/sites/main/*` | `<target>/sites/main/` |
| `templates/sites/admin/*` | `<target>/sites/admin/` |
| `templates/sites/dashboard/*` | `<target>/sites/dashboard/` |
| `templates/github/*` | `<target>/.github/workflows/` |

**API project** — backend + main site only:

| Template directory | Output directory |
|---|---|
| `templates/root/*` | `<target>/` |
| `templates/backend/*` | `<target>/backend/` (skip `auth/`, `routes/admin/`) |
| `templates/shared/*` | `<target>/shared/` |
| `templates/sites/main/*` | `<target>/sites/main/` (skip auth context/hooks) |
| `templates/github/*` | `<target>/.github/workflows/` (skip admin/dashboard workflows) |

**Worker project** — single worker site:

For worker projects, scaffold a minimal Cloudflare Worker with Vite + React + Tailwind. Use the `templates/sites/main/` templates as a base, writing to the project root (no `sites/` subdirectory). Skip backend, shared, admin, and dashboard templates.

| Template directory | Output directory |
|---|---|
| `templates/sites/main/package.json.tmpl` | `<target>/package.json` |
| `templates/sites/main/vite.config.ts.tmpl` | `<target>/vite.config.ts` |
| `templates/sites/main/wrangler.jsonc.tmpl` | `<target>/wrangler.jsonc` |
| `templates/sites/main/tailwind.config.ts.tmpl` | `<target>/tailwind.config.ts` |
| `templates/sites/main/index.html.tmpl` | `<target>/index.html` |
| `templates/sites/main/tsconfig.json.tmpl` | `<target>/tsconfig.json` |
| `templates/sites/main/src/*` | `<target>/src/` (skip auth context/hooks) |

If D1 was selected, add D1 binding to `wrangler.jsonc` and create a `migrations/` directory.
If KV was selected, add KV binding to `wrangler.jsonc`.
If R2 was selected, add R2 binding to `wrangler.jsonc`.

Strip the `.tmpl` extension from output filenames. Preserve directory structure within each template directory.

**Conditional templates (full project type only):**
- `backend/src/auth/github.ts.tmpl` — only if GitHub OAuth selected. Remove `{{#IF_GITHUB_OAUTH}}` / `{{/IF_GITHUB_OAUTH}}` wrappers when including; skip entire file when not.
- `backend/src/auth/google.ts.tmpl` — only if Google OAuth selected. Same conditional wrapper logic.
- If GitHub OAuth is selected, add `"github"` to `features.auth.providers` in `.site/manifest.json`.
- If Google OAuth is selected, add `"google"` to `features.auth.providers` in `.site/manifest.json`.

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
- `root/site-manifest.json.tmpl` → write as `.site/manifest.json` (create `.site/` dir first)

### Step 4: Commit and push

```bash
git add -A && git commit -m "feat: initial scaffold from site-manager v1.3.0"
```

If a GitHub repo was created in Step 2, push the initial commit:

```bash
git push -u origin main
```

### Step 5: Install dependencies and build

**Auth service:**
```bash
npm install
```

**Full and API projects:**
```bash
npm install
npm run build:shared
```

**Worker projects:**
```bash
npm install
```

If this fails, print the error and stop — something is wrong with the scaffold.

### Step 6: Generate initial database migration

**Skip for worker and API projects.**

**Auth service:**
```bash
npx drizzle-kit generate
```

**Full project:**
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

**Skip for worker projects.**

Create Railway project and Postgres:

```bash
railway init --name <project-name>
railway add --database postgres
railway add --service backend
railway link --project <project-id> --service backend --environment production
```

Set environment variables:

**Auth service** — generate RS256 key pair:
```bash
# Generate RSA key pair
openssl genpkey -algorithm RSA -out /tmp/jwt-private.pem -pkeyopt rsa_keygen_bits:2048
openssl rsa -in /tmp/jwt-private.pem -pubout -out /tmp/jwt-public.pem

# Set as env vars (single-line PEM with \n preserved)
railway variables set JWT_PRIVATE_KEY="$(cat /tmp/jwt-private.pem)"
railway variables set JWT_PUBLIC_KEY="$(cat /tmp/jwt-public.pem)"
railway variables set NODE_ENV=production
railway variables set CORS_ORIGIN="*"
railway variables set DATABASE_URL='${{Postgres.DATABASE_URL}}'

# Clean up local keys
rm /tmp/jwt-private.pem /tmp/jwt-public.pem
```

Save the public key to `.site/jwt-public.pem` for other projects to use:
```bash
railway variables get JWT_PUBLIC_KEY > .site/jwt-public.pem
```

**Full and API projects (built-in auth):**
```bash
railway variables set JWT_SECRET="$(openssl rand -hex 32)"
railway variables set NODE_ENV=production
railway variables set CORS_ORIGIN="*"
railway variables set DATABASE_URL='${{Postgres.DATABASE_URL}}'
```

**Full and API projects (external auth service):**
```bash
railway variables set AUTH_SERVICE_URL="<auth-service-url>"
railway variables set AUTH_PUBLIC_KEY="<public-key-from-auth-service>"
railway variables set NODE_ENV=production
railway variables set CORS_ORIGIN="*"
railway variables set DATABASE_URL='${{Postgres.DATABASE_URL}}'
```

The public key can be fetched from the auth service's JWKS endpoint:
```bash
curl -s <auth-service-url>/.well-known/jwks.json
```

Deploy:

```bash
railway up --detach
railway domain
```

Wait for the deployment to become healthy (poll `/api/health` every 10 seconds, timeout after 3 minutes).

### Step 8: Seed admin account

**Auth service and full projects only.** Skip for API and worker projects.

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

**Skip for auth-service projects** (no frontend).

Remove custom domain routes from wrangler.jsonc for the initial deploy (they will be re-added after DNS is configured via go-live).

**Full project:**

Update all wrangler.jsonc files with the real Railway backend URL. Build and deploy each site:

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

**API project:**

Update wrangler.jsonc with the real Railway backend URL. Deploy main site only:

```bash
cd sites/main && npx vite build && npx wrangler deploy
```

**Worker project:**

If D1 was selected, create the database first:
```bash
npx wrangler d1 create <project-name>-db
```
Update `wrangler.jsonc` with the real D1 database ID, then apply migrations if any.

If KV was selected:
```bash
npx wrangler kv namespace create <project-name>-kv
```
Update `wrangler.jsonc` with the KV namespace ID.

If R2 was selected:
```bash
npx wrangler r2 bucket create <project-name>-storage
```

Build and deploy:
```bash
npx vite build && npx wrangler deploy
```

Capture all deployed URLs from the wrangler output.

### Step 10: Run smoke tests

**Full and API projects only.** Skip for worker projects (no backend to test).

```bash
site-manager verify --smoke
```

If any tests fail, report the failures but continue.

### Step 11: Update manifest and push

**Read the existing `.site/manifest.json` first, then merge changes into it — do NOT rewrite from scratch.** Specifically preserve `project.displayName`, `project.name`, `project.domain`, and `project.created`.

Update these fields:
- `project.type` — set to the project type (`full`, `api`, or `worker`)
- `_site_manager_version` — set to the current site-manager version
- All service URLs and statuses set to `"deployed"` (only services that exist for this project type)
- `lastDeployed` timestamps
- `features.auth.adminSeeded` set to `true` (full projects only)
- `storage` — for worker projects, record which storage options were selected (e.g., `{"d1": true, "kv": false, "r2": false}`)

Commit and push:

```bash
git add -A && git commit -m "chore: update manifest with deployment URLs"
git push
```

### Step 12: Verify and repair loop

Run the full verification suite:

```bash
site-manager verify
```

This writes any issues to `.site/issues.json`. If there are failures:

1. Read `.site/issues.json`
2. For each issue, apply the fix:
   - **Missing manifest fields:** Update `.site/manifest.json`
   - **OAuth routes (404):** Add missing import/route to `backend/src/app.ts`, rebuild, redeploy backend
   - **OAuth login buttons missing:** Add buttons per conditional wiring in Step 3, rebuild, redeploy affected site(s)
   - **Dark theme missing:** Re-copy templates, rebuild, redeploy
   - **DNS/CNAME missing:** Suggest `webinator dns add <domain>` or note pending propagation
   - **CORS headers missing:** Add CORS middleware to backend, rebuild, redeploy
   - **Error format wrong:** Add RFC 9457 error handler to backend, rebuild, redeploy
3. Re-run `site-manager verify`
4. Repeat until all blocking checks pass or only warnings remain

DNS/SSL warnings may take time to resolve (nameserver propagation). If DNS is still pending, print:
> DNS zone is pending activation. Custom domains will work once Cloudflare verifies the nameservers (up to 24-48h). Sites are accessible via workers.dev URLs.

### Step 13: Report and open in browser

Print the final summary appropriate to the project type.

**Auth service:**
```
=== {{DISPLAY_NAME}} is deployed! ===

  Type:          auth-service (Railway + Postgres)
  Auth API:      <railway-url>
  JWKS:          <railway-url>/.well-known/jwks.json
  Public key:    .site/jwt-public.pem
  GitHub:        <repo-url>

  Admin login:
    Email:    <admin-email>
    Password: <admin-password>

  To use in other projects:
    /site-manager init --auth <railway-url>
```

**Full project:**
```
=== {{DISPLAY_NAME}} is deployed! ===

  Type:          full (backend + main + admin + dashboard)
  Main site:     <project>-main.<account>.workers.dev
  Admin site:    <project>-admin.<account>.workers.dev
  Dashboard:     <project>-dashboard.<account>.workers.dev
  Backend API:   <railway-url>
  GitHub:        <repo-url>

  Admin login:
    Email:    <admin-email>
    Password: <admin-password>

  To connect your custom domain:
    /site-manager go-live
```

**API project:**
```
=== {{DISPLAY_NAME}} is deployed! ===

  Type:          api (backend + main site)
  Main site:     <project>-main.<account>.workers.dev
  Backend API:   <railway-url>
  GitHub:        <repo-url>

  To connect your custom domain:
    /site-manager go-live
```

**Worker project:**
```
=== {{DISPLAY_NAME}} is deployed! ===

  Type:          worker
  Site:          <project>.<account>.workers.dev
  Storage:       <D1, KV, R2, or none>
  GitHub:        <repo-url>

  To connect your custom domain:
    /site-manager go-live
```

Open deployed site URLs in the browser:

```bash
open <workers-dev-url>
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

Read `.site/manifest.json`. Verify:
- `services.backend.status` is `"deployed"` — if not, print:
  > Backend is not deployed. Run `/site-manager deploy backend` first.
- `features.auth.adminSeeded` is not `true` — if already seeded, print:
  > Admin account already seeded. Check .site/manifest.json for details.

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

Update `.site/manifest.json`:
- `features.auth.adminSeeded` → `true`

### Step 5: Report

```
✅ Admin account created

  Email: <email>
  Role:  admin

  Login at: https://admin.<domain>/login
```

---

## Go Live

**Connect a custom domain to an already-deployed project.** The project must be deployed to workers.dev first (via `init` or `migrate`).

Read `.site/manifest.json`. If `project.domain` is not set, ask the user for the domain.

If `dns.status` is already `"live"`, print:
> Custom domain is already connected. Run `site-manager verify --dns` to check.

Then stop.

### Step 1: Get Cloudflare credentials

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

### Step 2: Get or create Cloudflare zone

Check if the zone already exists:

```bash
curl -s "https://api.cloudflare.com/client/v4/zones?name=<domain>" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" | jq '.result[0]'
```

If no zone exists, create one:

```bash
curl -s -X POST "https://api.cloudflare.com/client/v4/zones" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"<domain>","account":{"id":"<account-id>"},"type":"full"}'
```

Extract `zone_id` and `name_servers`.

### Step 3: Update GoDaddy nameservers

Requires GoDaddy API credentials (from webinator config or environment).

```bash
curl -s -X PATCH "https://api.godaddy.com/v1/domains/<domain>" \
  -H "Authorization: sso-key $GODADDY_API_KEY:$GODADDY_API_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"nameServers":["<ns1>","<ns2>"]}'
```

### Step 4: Wait for zone activation

Poll zone status every 30 seconds for up to 5 minutes:

```bash
curl -s "https://api.cloudflare.com/client/v4/zones/$ZONE_ID" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" | jq -r '.result.status'
```

If still pending after 5 minutes, proceed anyway — custom domain routes will activate once nameservers propagate.

### Step 5: Add custom domain routes and redeploy

Add custom domain routes based on project type:

**Full project:**
- `sites/main/wrangler.jsonc`: `"routes": [{"pattern": "<domain>", "custom_domain": true}]`
- `sites/admin/wrangler.jsonc`: `"routes": [{"pattern": "admin.<domain>", "custom_domain": true}]`
- `sites/dashboard/wrangler.jsonc`: `"routes": [{"pattern": "dashboard.<domain>", "custom_domain": true}]`

**API project:**
- `sites/main/wrangler.jsonc`: `"routes": [{"pattern": "<domain>", "custom_domain": true}]`

**Worker project:**
- `wrangler.jsonc`: `"routes": [{"pattern": "<domain>", "custom_domain": true}]`

Redeploy all affected workers.

### Step 6: Verify and update manifest

```bash
site-manager verify --dns
```

Update `.site/manifest.json`:
- `dns.status` → `"live"`
- `dns.zoneId` → the Cloudflare zone ID
- `dns.nameservers` → the Cloudflare nameservers array
- `dns.provider` → `"cloudflare"`

Commit and push:

```bash
git add -A && git commit -m "chore: connect custom domain <domain>"
git push
```

Print:
```
=== {{DISPLAY_NAME}} is live at {{DOMAIN}}! ===

  <domain>:              ✅ Connected
  admin.<domain>:        ✅ Connected    (full project only)
  dashboard.<domain>:    ✅ Connected    (full project only)

  Previous workers.dev URLs still work.
```

---

## Migrate

**Set up site-manager in an existing repository, preserving existing content.**

### Step 1: Detect existing project

Examine the current directory:

```bash
git remote -v                    # repo origin
git branch --show-current        # current branch
ls -la                           # existing files
```

Check for existing hosting:
- **GH Pages:** look for `.github/workflows/*deploy*`, `CNAME` file, or `gh-pages` branch
- **Other hosting:** look for `netlify.toml`, `vercel.json`, `_redirects`, etc.
- **Existing domain:** read `CNAME` file if present

Report what was found:

```
=== Existing project detected ===

  Repo:       mikefullerton/my-site
  Branch:     main
  Hosting:    GitHub Pages (CNAME: example.com)
  Files:      42 files (HTML, CSS, JS)
```

### Step 2: Gather project info

Same Phase 1 and Phase 2 questions as Init Step 1, but pre-fill what can be detected:
- Domain from `CNAME` file or `$ARGUMENTS`
- Project name from repo name
- Display name from existing `<title>` tag or repo description

Ask the user to confirm the project type (full, api, or worker).

### Step 3: Scaffold alongside existing content

Create `.site/manifest.json` and the project structure, but **do not overwrite existing files**. For each template output file:

- If the file doesn't exist → write it
- If the file exists → skip it, note it in the output

For worker projects, the existing content (HTML, CSS, JS) becomes the initial content. Don't replace it with empty templates.

```
Scaffolded:
  ✅ .site/manifest.json (created)
  ✅ wrangler.jsonc (created)
  ✅ vite.config.ts (created)
  ⏭️  index.html (kept existing)
  ⏭️  src/ (kept existing)
  ✅ package.json (merged dependencies)
```

For `package.json`, if one already exists, merge the required dependencies (vite, wrangler, react, tailwind) into the existing file rather than overwriting.

### Step 4: Install, build, and deploy

Same as Init Steps 5-9, adapted for the project type. Deploy to workers.dev only — no DNS changes.

### Step 5: Verify

```bash
site-manager verify
```

Confirm the new deployment works at the workers.dev URL. The existing site (GH Pages, etc.) continues to serve the custom domain undisturbed.

### Step 6: Report

```
=== Migration complete ===

  New site:    <project>.<account>.workers.dev
  Old site:    Still live at <domain> (GitHub Pages)

  Next steps:
    1. Test the new site at the workers.dev URL
    2. When ready, connect your domain:
       /site-manager go-live
    3. After go-live, disable the old hosting:
       - GitHub Pages: Settings → Pages → disable
```

---

## Update

**Re-scaffold an existing project with the latest templates, rebuild, and redeploy.**

### Step 1: Read manifest

Read `.site/manifest.json` from the current directory. If not found:
> No .site/manifest.json found. Run `/site-manager init` to create a project.

Then stop.

Extract project info: `project.name`, `project.domain`, `project.displayName`, and all service URLs/statuses.

### Step 2: Re-scaffold templates

For each template in `${CLAUDE_SKILL_DIR}/references/templates/`, read the `.tmpl` file, perform placeholder substitution (same table as Init Step 3), and **overwrite** the output file.

**Preserve these files** (do not overwrite):
- `.env` and `.env.example` — user may have customized
- `.site/manifest.json` — contains deployment state
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

### Step 5: Verify and repair loop

Run the full verification suite:

```bash
site-manager verify
```

This writes any issues to `.site/issues.json`. If there are failures:

1. Read `.site/issues.json`
2. For each issue, apply the fix (see Init Step 13 for the fix list)
3. Re-run `site-manager verify`
4. Repeat until all blocking checks pass or only warnings remain

### Step 6: Report

Print what was updated. Do **not** auto-open sites in the browser (only Init opens sites).

```
=== UPDATE COMPLETE ===

  Templates updated to site-manager v1.3.0
  Verification: <N>/<N> passed (<W> warnings)

  Main site:     <main-url>
  Admin site:    <admin-url>
  Dashboard:     <dashboard-url>
```

---

## Verify

Run the full verification suite and iterate on any issues:

```bash
site-manager verify
```

This runs all check suites (manifest, DNS, e2e browser, smoke tests) and writes failures to `.site/issues.json`.

If there are issues, apply the verify→repair loop (same as Init Step 13):
1. Read `.site/issues.json`
2. Fix each issue
3. Re-run `site-manager verify`
4. Repeat until clean

---

## Repair

Read `.site/issues.json` and fix all issues. This is the same fix logic as the verify→repair loop but invoked directly.

```bash
site-manager repair
```

The CLI checks for developer mode (`~/.site-manager/developer`). If that file exists, issues are displayed but not fixed — the assumption is the tool developer is testing and fixes belong in the site-manager templates/scripts, not the deployed project.

If developer mode is off (normal users), the CLI delegates to Claude to apply fixes. Apply fixes for each issue (see Init Step 13 for the fix list), then re-run verify to confirm.

If the issues file doesn't exist or has no issues, print:
> No issues to repair. Run `site-manager verify` first.

---

## Help

Print:

```
Site Manager v1.3.0 — Scaffold, deploy, and manage website suites

Commands (Claude session):
  /site-manager init [domain]       Scaffold a new project
  /site-manager migrate [domain]    Set up in an existing repo
  /site-manager go-live             Connect custom domain to deployed project
  /site-manager deploy [service]    Deploy all services (or: backend, main, admin, dashboard)
  /site-manager seed-admin          Create initial admin account
  /site-manager update              Re-scaffold with latest templates and redeploy
  /site-manager verify              Run full verification suite and fix issues
  /site-manager repair              Fix issues from last verify

Commands (terminal or Claude):
  site-manager status               Check health of all services
  site-manager manifest             View .site/manifest.json
  site-manager manifest validate    Validate manifest schema
  site-manager --developer-mode     Toggle tool developer mode (on/off)
  site-manager --help               Show this help
  site-manager --version            Show version

Project types:
  auth-service                      Shared auth service (Railway + Postgres, RS256 JWT)
  full                              Backend + main + admin + dashboard (multi-user)
  api                               Backend + main site (single-user with API)
  worker                            Single Cloudflare Worker (frontend-only)

Project directory:
  .site/manifest.json               Project configuration and deployment state
  .site/issues.json                 Issues from last verify (consumed by repair)

Tech Stack:
  Backend:    Hono + Drizzle + PostgreSQL (Railway)
  Frontends:  React 19 + Vite + Tailwind 4 + Tanstack Query/Router
  Edge:       Cloudflare Workers
  Dashboard:  Cloudflare Workers + D1 SQLite
  Auth:       Email/password + optional GitHub/Google OAuth
```
