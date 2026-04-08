---
name: site-manager
description: "Scaffold, deploy, and manage a suite of websites (backend + main + admin + dashboard) as a unified platform. /site-manager init, /site-manager add, /site-manager deploy, /site-manager status, /site-manager manifest, /site-manager seed-admin, /site-manager --help"
version: "1.6.0"
argument-hint: "[init|add|deploy|update|verify|repair|status|manifest|seed-admin|--help|--version]"
allowed-tools: Read, Write, Edit, Bash(bash *), Bash(python3 *), Bash(brew *), Bash(npm *), Bash(wrangler *), Bash(railway *), Bash(curl *), Bash(which *), Bash(chmod *), Bash(cat *), Bash(test *), Bash(mkdir *), Bash(jq *), Bash(ls *), Bash(head *), Bash(tail *), Bash(sort *), Bash(column *), Bash(wc *), Bash(grep *), Bash(date *), Bash(docker *), Bash(cd *), Bash(gh *), Bash(dig *), Bash(open *), Bash(site-manager *), AskUserQuestion
model: sonnet
---

# Site Manager v1.6.0

Scaffold, deploy, and manage a suite of 4 websites as a unified platform.

**Architecture per project:**
- **Backend API** — Hono + Drizzle + PostgreSQL (Railway)
- **Main site** (`domain.com`) — React 19 + Vite + Tailwind 4 (Cloudflare Worker)
- **Admin site** (`admin.domain.com`) — React 19 + Vite + Tailwind 4 (Cloudflare Worker)
- **Dashboard** (`dashboard.domain.com`) — React 19 + Vite + D1 SQLite (Cloudflare Worker)

## Startup

**Step 0 — Ensure permissions**: Run `python3 ${CLAUDE_SKILL_DIR}/references/ensure-permissions.py ${CLAUDE_SKILL_DIR}/SKILL.md` to whitelist this skill's tools in `~/.claude/settings.json`. This is silent and idempotent.

**CRITICAL**: The very first thing you output MUST be the version line:

site-manager v1.6.0

If `$ARGUMENTS` is `--version`, respond with exactly:
> site-manager v1.6.0

Then stop.

## Route by argument

| `$ARGUMENTS` | Action |
|---|---|
| `init` or `init <domain>` | Go to **Init** |
| `migrate` or `migrate <domain>` | Go to **Migrate** |
| `go-live` | Go to **Go Live** |
| `add` or `add <description>` | Go to **Add** |
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

> **CRITICAL: One question at a time.**
>
> You MUST ask exactly ONE question per turn. After asking, STOP and WAIT
> for the user's answer. Do NOT continue to the next step until the user
> responds. Do NOT combine multiple questions. Do NOT present a table of
> fields. Each sub-step that says "Ask" means: ask that single question,
> then STOP. Violating this rule ruins the user experience.

Work through sub-steps 1a through 1k in order. Skip steps whose conditions are not met. Track two internal variables:
- `FLOW` — `"existing"` or `"new"` (set in 1a/1b)
- `SERVICES` — set of selected services (set in 1c)

If `$ARGUMENTS` contains a domain (e.g., `init foo.com`), store it and skip the domain question in step 1k.

#### Step 1a — Silent detection

Run these checks silently before asking any questions:

```bash
ls -la
cat package.json 2>/dev/null
git remote -v 2>/dev/null
git branch --show-current 2>/dev/null
ls .site/manifest.json wrangler.jsonc wrangler.toml 2>/dev/null
```

Check for existing config first:
- If `.site/manifest.json` exists → print "This is already a site-manager project. Use `/site-manager add` to add services." Then **stop**.
- If `wrangler.jsonc` or `wrangler.toml` exists → note it (already configured for Workers).

Run the detection checklist:
- **Git repo**: `.git/` exists, or `git remote -v` succeeds
- **package.json**: file exists
- **Web framework**: dependencies contain `react`, `vue`, `svelte`, `next`, `nuxt`, `astro`, `solid-js`, `preact`, `angular`, `lit`, `qwik`
- **Build tool**: `vite.config.*`, `next.config.*`, `webpack.config.*`, `astro.config.*`, `svelte.config.*`, `nuxt.config.*`, `rollup.config.*`
- **Entry HTML**: `index.html` at root or in `public/`
- **Source files**: `src/` contains `.tsx`, `.jsx`, `.vue`, `.svelte`, or `.astro` files
- **Static assets**: `public/` or `static/` directory exists
- **TypeScript**: `tsconfig.json` exists
- **Build output**: `dist/`, `build/`, `out/`, or `.next/` directory exists

Classify the directory:
- **Existing website** — web framework detected in package.json, OR build tool config exists, OR index.html exists with source files
- **Existing code** — package.json or source files exist but no web framework indicators
- **Empty** — no significant files

Store all detection results internally. Do NOT print anything yet — proceed to step 1b or 1c.

#### Step 1b — Deploy or scaffold? *(only if existing website detected)*

**Skip this step if:** the directory is empty or existing-code (not a website). Set `FLOW=new` and print: "I'll scaffold a new project here." Proceed to step 1c.

Print the detection report, then ask ONE question:

```
I found an existing website in this directory:

  Directory:  /path/to/project
  Git repo:   owner/repo (branch: main)
  Framework:  React 19 (from package.json)
  Build tool: Vite 6.x (vite.config.ts)
  Entry:      index.html
  Source:     src/ (14 .tsx files)
  Build cmd:  npm run build (vite build)
  Output dir: dist/

Deploy this existing site to Cloudflare, or scaffold a brand new project?

  1. Deploy this site — configure Cloudflare Workers around your existing code
  2. Start fresh — scaffold a new project from templates
```

**STOP. Wait for the user's answer.**

- If **1**: set `FLOW=existing`
- If **2**: set `FLOW=new`

#### Step 1c — What do you want?

Ask ONE question — checkboxes, pick any combination. Every item is its own line:

```
What would you like to set up?

  [ ] Main site              — your website on Cloudflare Workers
  [ ] Admin site             — admin.<domain> on Cloudflare Workers
  [ ] Dashboard site         — dashboard.<domain> on Cloudflare Workers
  [ ] Backend API            — Hono + PostgreSQL on Railway
  [ ] Auth service           — shared JWT authentication on Railway
  [ ] Hello world starter    — basic index page + styles to get started
  [ ] GitHub repository      — create a new private repo
  [ ] D1 database            — SQLite on Cloudflare (structured data)
  [ ] KV storage             — key-value on Cloudflare (config, cache)
  [ ] R2 storage             — object storage on Cloudflare (files, images)
```

**STOP. Wait for the user's answer.**

Store selections in `SERVICES`. Auto-include dependencies:
- **Admin site** requires **Backend API** — auto-include if not selected, tell user
- **Dashboard site** requires **Backend API** — auto-include if not selected, tell user
- **Hello world starter** only applies if FLOW=new (skip silently for existing sites)
- **GitHub repository** only applies if no git remote was detected in step 1a (skip silently if already in a repo)
- **D1/KV/R2** are recorded as storage selections (replaces step 1f)

Derive the internal project type silently (never show to user):
- Main only → `existing` (if FLOW=existing) or `worker` (if FLOW=new)
- Main + backend → `existing` or `api`
- Main + backend + admin + dashboard → `existing` or `full`
- Backend only → `api`
- Auth service only → `auth-service`

#### Step 1d — Rendering mode *(only if main site in SERVICES)*

**Skip if:** main site was not selected in step 1c.

Auto-detect the rendering mode:
- Next.js without `output: 'export'` → likely SSR
- Nuxt without `ssr: false` → likely SSR
- Astro with `output: 'server'` or `output: 'hybrid'` → SSR
- SvelteKit with `adapter-cloudflare` → SSR
- Plain Vite + React/Vue/Svelte with no SSR adapter → static
- `index.html` at root with no framework → static

If auto-detected, confirm instead of asking open-ended:

```
This looks like a static React + Vite site — pre-built HTML + JS served as
static assets. Correct?
```

If not auto-detected, ask:

```
How does your site render?

  1. Static / SPA — pre-built HTML + JS, served as static assets
  2. Server-side rendered (SSR) — pages rendered on each request
```

**STOP. Wait for the user's answer.**

Record rendering mode (`"static"` or `"ssr"`).

**Static** — Worker serves pre-built assets from `dist/` (or equivalent). The `worker.ts` entry uses the `ASSETS` binding and falls back to `index.html` for SPA routing.

**SSR** — Worker runs the framework's server-side rendering. The `worker.ts` imports the framework's Cloudflare adapter. Wrangler config differences:
- `main` points to framework's worker entry (e.g., `.output/server/index.mjs`)
- `assets.directory` may differ (e.g., `.output/public`)
- Build command may change (e.g., `nuxt build`, `next build`)

#### Step 1e — Auth *(only if backend in SERVICES)*

**Skip if:** backend was not selected in step 1c.

Ask ONE question:

```
How should authentication work?

  1. Shared auth service — validate JWTs from an existing auth service
  2. Built-in auth — email/password + OAuth providers in this backend
  3. No auth — public API, no authentication
```

**STOP. Wait for the user's answer.**

- If **shared**: ask for the auth service URL (one more question, then STOP again).
- If **built-in**: ask which OAuth providers (GitHub, Google, etc.) (one more question, then STOP again).
- If **none**: proceed.

#### Step 1f — *(removed — storage is now covered in step 1c)*

#### Step 1g — Project name

Suggest from `package.json` `name` field, or from the directory name. Ask ONE question:

```
Project name: <suggested-name>?

This is used as the Cloudflare Worker name (<name>-main) and in .site/manifest.json.
Type a different name, or press Enter to confirm.
```

Validation: lowercase, `[a-z0-9-]+`.

**STOP. Wait for the user's answer.**

#### Step 1h — Display name

Derive from project name (title case), or from `package.json` `description`. Ask ONE question:

```
Display name: <Suggested Name>?

This is the human-readable name shown in status output and reports.
Type a different name, or press Enter to confirm.
```

**STOP. Wait for the user's answer.**

#### Step 1i — GitHub org *(only if GitHub repository selected in step 1c)*

**Skip if:** GitHub repository was not selected in step 1c, or git remote already exists.

Ask ONE question:

```
GitHub repository — personal account or organization?

  1. Personal account
  2. Organization — I'll ask which org next
```

**STOP. Wait for the user's answer.**

If **org**: ask for the org name (one more question, then STOP again).

#### Step 1j — Target directory *(only if FLOW=new)*

**Skip if:** FLOW=existing (the project is already in the current directory).

Suggest `./<project-name>/`. Ask ONE question:

```
Target directory: ./<project-name>/?

This is where the project will be created.
Type a different path, or press Enter to confirm.
```

**STOP. Wait for the user's answer.**

#### Step 1k — Domain *(always, asked last)*

**Skip if:** domain was already provided in `$ARGUMENTS`.

Ask ONE question:

```
What's the domain for this project?

This won't be connected yet — run /site-manager go-live when you're ready.
```

**STOP. Wait for the user's answer.**

#### Step 1 — Confirm

Show the full action plan. Be specific — list every file to create, modify, and not touch. List every external action.

**Existing site (static) example:**

```
=== Here's what I'm going to do ===

  Project:     my-cool-site
  Display:     My Cool Site
  Domain:      mycoolsite.com
  Rendering:   static (pre-built assets)
  Git repo:    mikefullerton/my-cool-site (already exists)
  Build:       npm run build -> dist/

  Services:
    [x] Main site (your existing code) -> Cloudflare Worker
    [ ] Backend API
    [ ] Admin dashboard
    [ ] Dashboard

  Files I'll CREATE:
    .site/manifest.json          — project config and deployment state
    wrangler.jsonc               — Cloudflare Worker configuration
    src/worker.ts                — Worker entry point (serves your built assets)

  Files I'll MODIFY:
    package.json                 — add wrangler + @cloudflare/workers-types to devDependencies
    .gitignore                   — add .site/ and .wrangler/

  Files I will NOT touch:
    All your existing source code, HTML, CSS, components, configs

  External actions:
    npm install                  — install new dependencies
    npm run build                — build your site
    npx wrangler deploy          — deploy to Cloudflare Workers

  After deploy, your site will be live at:
    <project-name>-main.<account>.workers.dev

Proceed?
```

**Existing site (SSR) example:**

```
=== Here's what I'm going to do ===

  Project:     my-next-site
  Display:     My Next Site
  Domain:      mynextsite.com
  Rendering:   SSR (server-side rendered via Next.js)
  Git repo:    mikefullerton/my-next-site (already exists)
  Build:       npm run build (next build)

  Services:
    [x] Main site (your existing code) -> Cloudflare Worker (SSR)
    [ ] Backend API
    [ ] Admin dashboard
    [ ] Dashboard

  Files I'll CREATE:
    .site/manifest.json          — project config and deployment state
    wrangler.jsonc               — Cloudflare Worker configuration (SSR mode)

  Files I'll MODIFY:
    package.json                 — add wrangler, @cloudflare/workers-types, @opennextjs/cloudflare
    .gitignore                   — add .site/ and .wrangler/

  No worker.ts needed — Next.js provides its own Cloudflare entry point.

  Files I will NOT touch:
    All your existing source code, pages, components, configs

  External actions:
    npm install                  — install new dependencies
    npm run build                — build your site
    npx wrangler deploy          — deploy to Cloudflare Workers

  After deploy, your site will be live at:
    <project-name>-main.<account>.workers.dev

Proceed?
```

**New project examples** — adapt the confirmation to show the project type and all scaffolded files. For full/api/worker/auth-service types, list the template directories that will be created, the backend setup steps, and all external actions.

If backend/admin/dashboard were selected alongside an existing site, the confirmation also lists those additional services, the template directories (`backend/`, `sites/admin/`, `sites/dashboard/`), Railway setup steps, and all external actions.

If the user says "change something" → ask what they want to change, loop back to that sub-step, then return here.

**STOP. Wait for the user to confirm.**

Once confirmed, record the project type in `.site/manifest.json` as `project.type` (`auth-service`, `full`, `api`, `worker`, or `existing`). If FLOW=existing, go to **Step 3E**. Otherwise, continue to **Step 2**.

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

### Step 3E: Configure existing site for Cloudflare (existing type only)

**This step replaces Step 2 and Step 3 for existing projects. Do NOT create directories, copy templates, or scaffold content files.**

**3E.1 — Detect build configuration:**

Read `package.json` to determine:
- **Build command**: Look for `scripts.build`. Common patterns:
  - `vite build` → output: `dist/`
  - `next build` → output: `.next/` (needs `next export` for static, or use `out/`)
  - `npm run build` → check what it runs
  - No build script → treat as static site, assets in current directory or `public/`

- **Output directory**: Look for build tool config:
  - `vite.config.*` → `build.outDir` (default: `dist`)
  - `next.config.*` → check for `output: 'export'` (uses `out/`)
  - If unclear, default to `dist/`

Record the build command and output directory for wrangler config.

**3E.2 — Create `.site/manifest.json`:**

```json
{
  "version": "1.0.0",
  "_site_manager_version": "<current version>",
  "project": {
    "name": "<project-name>",
    "displayName": "<display-name>",
    "domain": "<domain>",
    "type": "existing",
    "created": "<ISO 8601 timestamp>"
  },
  "services": {
    "main": {
      "platform": "cloudflare",
      "status": "scaffolded",
      "directory": ".",
      "rendering": "<static or ssr>",
      "buildCommand": "<detected build command, e.g. npx vite build>"
    }
  },
  "features": {},
  "dns": {
    "provider": "cloudflare",
    "zoneId": null,
    "nameservers": [],
    "status": "pending",
    "records": []
  },
  "storage": {
    "d1": false,
    "kv": false,
    "r2": false
  }
}
```

If backend/admin/dashboard were selected in step 1c, add those service entries too (with `"status": "scaffolded"` and appropriate platform).

**3E.3 — Create `wrangler.jsonc`:**

Only create if `wrangler.jsonc` and `wrangler.toml` do not already exist.

**Static site:**

```jsonc
{
  "name": "<project-name>-main",
  "main": "src/worker.ts",
  "compatibility_date": "2024-12-01",
  "assets": {
    "directory": "<detected output dir, e.g. dist>",
    "binding": "ASSETS"
  },
  "routes": [
    {
      "pattern": "<domain>",
      "custom_domain": true
    }
  ]
}
```

**SSR site:**

The wrangler config depends on the framework. The key difference is `main` points to the framework's server entry point, not a custom `worker.ts`.

- **Next.js** (with `@opennextjs/cloudflare`): `"main": ".open-next/worker.ts"`, assets from `.open-next/assets/`
- **Nuxt**: `"main": ".output/server/index.mjs"`, assets from `.output/public/`
- **Astro** (with `@astrojs/cloudflare`): `"main": "dist/_worker.js"`, assets from `dist/`
- **SvelteKit** (with `@sveltejs/adapter-cloudflare`): `"main": ".svelte-kit/cloudflare/_worker.js"`, assets from `.svelte-kit/cloudflare/`

```jsonc
{
  "name": "<project-name>-main",
  "main": "<framework-specific entry, see above>",
  "compatibility_date": "2024-12-01",
  "assets": {
    "directory": "<framework-specific assets dir>",
    "binding": "ASSETS"
  },
  "compatibility_flags": ["nodejs_compat"],
  "routes": [
    {
      "pattern": "<domain>",
      "custom_domain": true
    }
  ]
}
```

SSR sites typically need `nodejs_compat` for Node.js API access. Check the framework's Cloudflare adapter docs for exact config.

If backend was selected, add `"vars": { "API_BACKEND_URL": "" }` (will be filled after Railway deploy).

If D1 was selected, add `d1_databases` binding (placeholder ID — real ID after `wrangler d1 create`).
If KV was selected, add `kv_namespaces` binding.
If R2 was selected, add `r2_buckets` binding.

**3E.4 — Create worker entry point (static sites only):**

**Skip this step for SSR sites.** SSR frameworks provide their own Cloudflare worker entry point via their adapter — no custom `worker.ts` is needed. The `wrangler.jsonc` `main` field already points to the framework's output (see 3E.3).

**For static sites only:**

Only create if `src/worker.ts` does not already exist. If the user's source files are in `src/`, use a different path like `worker.ts` at the root and update `wrangler.jsonc` `main` to match.

**Without backend:**

```typescript
interface Env {
  ASSETS: Fetcher;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const response = await env.ASSETS.fetch(request);
    if (response.status === 404) {
      return env.ASSETS.fetch(new URL("/index.html", request.url));
    }
    return response;
  },
};
```

**With backend:**

```typescript
interface Env {
  API_BACKEND_URL: string;
  ASSETS: Fetcher;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/auth/")) {
      const backendUrl = new URL(url.pathname + url.search, env.API_BACKEND_URL);
      const headers = new Headers(request.headers);
      headers.set("X-Forwarded-For", request.headers.get("cf-connecting-ip") ?? "");
      headers.set("X-Forwarded-Proto", "https");
      return fetch(backendUrl.toString(), {
        method: request.method,
        headers,
        body: request.body,
      });
    }

    const response = await env.ASSETS.fetch(request);
    if (response.status === 404) {
      return env.ASSETS.fetch(new URL("/index.html", request.url));
    }
    return response;
  },
};
```

**3E.5 — Update `package.json`:**

Merge these dependencies into the existing `package.json` (do not overwrite other fields):

```json
{
  "devDependencies": {
    "wrangler": "^4.0.0",
    "@cloudflare/workers-types": "^4.0.0"
  }
}
```

If `package.json` doesn't have a `build` script, add one based on what was detected. If it already has one, leave it alone.

**For SSR sites**, also add the framework's Cloudflare adapter if not already installed:

- **Next.js**: `@opennextjs/cloudflare` in devDependencies
- **Nuxt**: `nitro-preset-cloudflare` or check if `nitro.preset` is already set to `cloudflare` in `nuxt.config.*`
- **Astro**: `@astrojs/cloudflare` in dependencies
- **SvelteKit**: `@sveltejs/adapter-cloudflare` in devDependencies

Check the framework's Cloudflare deployment docs for the correct adapter and any required config changes.

**3E.6 — Update `.gitignore`:**

Append these lines if not already present:

```
.site/
.wrangler/
```

**3E.7 — Scaffold backend/admin/dashboard (if selected):**

If the user selected additional services in step 1c:

- **Backend**: Create `backend/` directory and copy templates from `${CLAUDE_SKILL_DIR}/references/templates/backend/` (same as Init Step 3 for full/api types). Also copy `root/Dockerfile.tmpl`, `root/railway.toml.tmpl`, and `root/docker-compose.yml.tmpl` to the project root. Copy `shared/` templates to `shared/`. Add `"workspaces"` to root package.json if not present.
- **Admin**: Create `sites/admin/` and copy templates from `${CLAUDE_SKILL_DIR}/references/templates/sites/admin/`.
- **Dashboard**: Create `sites/dashboard/` and copy templates from `${CLAUDE_SKILL_DIR}/references/templates/sites/dashboard/`.

Do NOT create `sites/main/` — the main site stays at the project root.

After Step 3E, proceed to Step 4 (commit and push), then Step 5 (install dependencies), then:
- If backend was selected: follow Steps 6-8 (database migration, Railway deploy, seed admin)
- Then go to **Step 9E** for Cloudflare deployment.
- If no backend: skip Steps 6-8, go directly to **Step 9E**.

### Step 4: Commit and push

```bash
git add -A && git commit -m "feat: initial scaffold from site-manager v1.6.0"
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

### Step 9E: Deploy existing site to Cloudflare (existing type only)

**This step replaces Steps 7-9 for existing projects without additional services.**

Remove the `routes` block from `wrangler.jsonc` for the initial deploy (routes are re-added during go-live after DNS is configured).

Install dependencies and build:

```bash
npm install
```

If a build command exists:
```bash
npm run build
```

Create Cloudflare resources if storage was selected:

- D1: `npx wrangler d1 create <project-name>-db` → update wrangler.jsonc with real database ID
- KV: `npx wrangler kv namespace create <project-name>-kv` → update wrangler.jsonc with namespace ID
- R2: `npx wrangler r2 bucket create <project-name>-storage`

Deploy:

```bash
npx wrangler deploy
```

Capture the deployed URL from wrangler output.

**If backend was also selected**, follow Init Steps 7-8 for the backend (Railway setup, deploy, seed admin) before this step.

**If admin/dashboard were also selected**, deploy those after the main site using Init Step 9's instructions for those sites (they live in `sites/admin/` and `sites/dashboard/` as usual).

After deployment, proceed to Step 10.

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

**Existing project (site only):**
```
=== {{DISPLAY_NAME}} is deployed! ===

  Type:          existing (your code on Cloudflare Workers)
  Site:          <project>-main.<account>.workers.dev
  Storage:       <D1, KV, R2, or none>
  GitHub:        <repo-url>

  Files added:
    .site/manifest.json
    wrangler.jsonc
    src/worker.ts (or worker.ts)
    (package.json updated)

  To connect your custom domain:
    /site-manager go-live
```

**Existing project (with backend):**
```
=== {{DISPLAY_NAME}} is deployed! ===

  Type:          existing (your code + backend API)
  Site:          <project>-main.<account>.workers.dev
  Backend API:   <railway-url>
  GitHub:        <repo-url>

  Admin login:
    Email:    <admin-email>
    Password: <admin-password>

  To connect your custom domain:
    /site-manager go-live
```

**Existing project (full suite):**
```
=== {{DISPLAY_NAME}} is deployed! ===

  Type:          existing (your code + full suite)
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

Open deployed site URLs in the browser:

```bash
open <workers-dev-url>
```

---

## Add

Add capabilities to an existing project. Reads `.site/manifest.json` to determine what's already present, offers what's missing.

### Step 1: Read manifest

```bash
cat .site/manifest.json
```

If `.site/manifest.json` does not exist, print:
> This is not a site-manager project. Run `/site-manager init` first.

Then stop.

Parse the manifest to determine:
- `project.type` — the project type (auth-service, full, api, worker)
- `services` — which services exist and their status
- `features` — which features are enabled
- `dns` — whether DNS/go-live is configured

### Step 2: Determine what's addable

Compare the manifest against the addable catalog. An item is **addable** if it's not already present/enabled and is compatible with the project.

**Addable catalog:**

| Item | Manifest check | Compatible types |
|------|---------------|-----------------|
| Backend API | `services.backend` absent or not deployed | worker |
| Main site | `services.main` absent or not deployed | auth-service |
| Admin site | `services.admin` absent or not deployed | api, worker, auth-service |
| Dashboard | `services.dashboard` absent or not deployed | api, worker, auth-service |
| Built-in auth | `features.auth.enabled` is false/absent | any with backend |
| GitHub OAuth | `"github"` not in `features.auth.providers` | any with auth enabled |
| Google OAuth | `"google"` not in `features.auth.providers` | any with auth enabled |
| External auth service | `features.auth.mode` is not `"external"` | any with backend |
| Feature flags | `features.featureFlags.enabled` is false/absent | any with backend |
| Email service | `features.email.enabled` is false/absent | any with backend |
| SMS service | `features.sms.enabled` is false/absent | any with backend |
| A/B testing | `features.abTesting.enabled` is false/absent | any with backend |
| Observability | `features.observability.enabled` is false/absent | any |
| Structured logging | `features.logging.enabled` is false/absent | any |
| D1 SQLite | no D1 binding in wrangler config | worker |
| KV store | no KV binding in wrangler config | worker |
| R2 bucket | no R2 binding in wrangler config | worker |
| GitHub repo | no `.git` remote | any |
| GitHub Actions | no `.github/workflows/` | any with GitHub repo |
| DNS / go-live | `dns.zoneId` is null/absent | any deployed |

### Step 3: Match or present menu

**If `$ARGUMENTS` contains a description** (e.g., `add github auth`):
- Match the description against addable items using natural language understanding
- If a clear match: proceed to Step 4 with that item
- If ambiguous: show the top 2-3 matches and ask the user to pick
- If no match: "I don't know how to add that. Here's what I can add:" → show full menu

**If no description** (just `add`):
- Build a numbered menu of all addable items (exclude items already present)
- Group by category (Services, Auth, Features, Storage, Infrastructure)
- Present the menu and ask the user to pick one or more (comma-separated numbers)

Menu format:
```
Your project (<type>) can add:

  Services
    1. Admin site (admin.<domain>)
    2. Dashboard (dashboard.<domain>)

  Auth
    3. GitHub OAuth
    4. Google OAuth

  Features
    5. Email service
    6. SMS service

  Infrastructure
    7. GitHub Actions workflows
    8. DNS / go-live

What would you like to add? (enter number, or describe what you want)
```

### Step 4: Confirm

Confirm in plain language what you're about to do:

> Do you want to add GitHub authentication?

Wait for the user to confirm.

### Step 5: Choose execution mode

Ask:

> How would you like to proceed?
>   1. Scaffold, deploy, and verify (default)
>   2. Scaffold only
>   3. Let's chat about it first
>
> (Enter for default)

### Step 6: Execute

**Mode 1 — Scaffold, deploy, and verify:**
1. Scaffold the code (see Scaffold Instructions below)
2. Update `.site/manifest.json` with the new state
3. Commit changes
4. Deploy the affected service(s): `site-manager deploy <service>`
5. The deploy command runs the verify→repair loop automatically

**Mode 2 — Scaffold only:**
1. Scaffold the code (see Scaffold Instructions below)
2. Update `.site/manifest.json` with the new state
3. Commit changes
4. Print: "Code scaffolded and committed. Run `/site-manager deploy <service>` when ready."

**Mode 3 — Chat:**
1. Discuss the addition with the user — answer questions, explain trade-offs
2. When the user is ready, re-enter at Step 5

### Scaffold Instructions

Each addable item has specific scaffold steps. Reference existing scaffold logic from **Init** where applicable.

**Adding a service (admin, dashboard, main, backend):**
- Copy the relevant templates from `${CLAUDE_SKILL_DIR}/references/templates/` (same as Init Step 3)
- Wire the new service into the root `package.json` workspaces array
- Add the service entry to `.site/manifest.json` with `"status": "scaffolded"`
- If adding admin or dashboard: also add the GitHub Actions deploy workflow from `templates/github/`
- Run `npm install` to install dependencies

**Adding GitHub OAuth:**
- Copy `templates/backend/src/auth/github.ts.tmpl` → `backend/src/auth/github.ts`
- Wire into `backend/src/app.ts` (add import and route — see Init Step 3 conditional wiring)
- Add "Sign in with GitHub" button to login pages (main and admin if they exist)
- Add `"github"` to `features.auth.providers` in manifest
- Set `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` env vars on Railway

**Adding Google OAuth:**
- Same pattern as GitHub OAuth but with `google.ts.tmpl` and Google-specific env vars

**Adding built-in auth:**
- Copy auth templates: `password.ts`, `session.ts`, `routes/auth.ts`
- Wire auth routes into `backend/src/app.ts`
- Add auth middleware to protected routes
- Set `features.auth.enabled: true` and `features.auth.providers: ["email"]` in manifest
- Generate JWT secret: `railway variables set JWT_SECRET="$(openssl rand -hex 32)"`

**Adding external auth service:**
- Ask for the auth service URL
- Fetch the public key from `<auth-service-url>/.well-known/jwks.json`
- Set `AUTH_SERVICE_URL` and `AUTH_PUBLIC_KEY` env vars on Railway
- Add JWT verification middleware using the public key
- Set `features.auth.mode: "external"` in manifest

**Adding feature flags:**
- Copy `templates/backend/src/services/feature-flags.ts.tmpl` and `templates/backend/src/routes/admin/flags.ts.tmpl`
- Wire routes into `backend/src/app.ts`
- If admin site exists, copy `templates/sites/admin/src/routes/flags.tsx.tmpl`
- Set `features.featureFlags.enabled: true` in manifest

**Adding storage (D1, KV, R2):**
- Add the binding to `wrangler.jsonc`
- For D1: also create the database with `wrangler d1 create <name>` and add a `migrations/` directory
- Update manifest accordingly

**Adding GitHub repo:**
- `gh repo create <name> --private`
- `git remote add origin <url>`
- `git push -u origin main`

**Adding GitHub Actions:**
- Copy relevant workflow templates from `templates/github/`
- Only add workflows for services that exist in the project

**Adding DNS / go-live:**
- Delegate to the existing **Go Live** section of this skill

---

## Deploy All

Deploy all services, then verify and repair until clean.

### Step 1: Deploy

```bash
site-manager deploy all
```

If deploy fails for any service, report the error but continue with remaining services.

### Step 2: Verify→repair loop

After deploy completes:

1. Run `site-manager verify`
2. If all checks pass → report success, stop
3. If issues found:
   a. Read `.site/issues.json`
   b. For each issue: diagnose root cause and fix (code, config, env vars, wrangler bindings, etc.)
   c. Re-deploy only the affected services: `site-manager deploy <service>`
   d. Re-run `site-manager verify`
4. Repeat up to 3 iterations
5. If still failing after 3 iterations: report remaining issues to the user and stop

**Important:** Each iteration should fix different issues. If the same issue persists after a fix attempt, investigate deeper rather than retrying the same fix.

---

## Deploy Single

Deploy a single service, then verify and repair until clean.

### Step 1: Deploy

```bash
site-manager deploy <service>
```

### Step 2: Verify→repair loop

After deploy completes, run the same verify→repair loop as Deploy All (up to 3 iterations). Only verify and repair the deployed service's checks — use the relevant verify flags:

- `backend` → `site-manager verify --manifest`
- `main` / `admin` / `dashboard` → `site-manager verify --manifest --dns`

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

**Existing project:**
- Main site: `wrangler.jsonc` (at project root): `"routes": [{"pattern": "<domain>", "custom_domain": true}]`
- If has admin: `sites/admin/wrangler.jsonc`: `"routes": [{"pattern": "admin.<domain>", "custom_domain": true}]`
- If has dashboard: `sites/dashboard/wrangler.jsonc`: `"routes": [{"pattern": "dashboard.<domain>", "custom_domain": true}]`

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

Same questions as Init Step 1 (sub-steps 1a through 1k), but pre-fill what can be detected:
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
Site Manager v1.6.0 — Scaffold, deploy, and manage website suites

Commands (Claude session):
  /site-manager init [domain]       Scaffold a new project
  /site-manager migrate [domain]    Set up in an existing repo
  /site-manager go-live             Connect custom domain to deployed project
  /site-manager add [description]   Add services, auth, features to existing project
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
  existing                          Existing website configured for Cloudflare

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
