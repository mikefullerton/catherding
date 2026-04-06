# Site Manager Plugin v1.0.0 — Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan phase-by-phase.

**Goal:** Create a `/site-manager` Claude Code plugin that scaffolds, deploys, and manages a suite of 4 websites (backend + main + admin + dashboard) as a unified platform.

**Spec:** `docs/superpowers/specs/2026-04-05-site-manager-planning.md`
**Approved plan:** `.claude/plans/lazy-weaving-boot.md`

---

## Quick Reference

**Tech Stack:** Hono + Drizzle + PostgreSQL (backend), React 19 + Vite + Tailwind 4 + Tanstack Query/Router (frontends), Cloudflare Workers (edge), D1 SQLite (dashboard)

**Plugin location:** `plugins/site-manager/`

**Template location:** `plugins/site-manager/skills/site-manager/references/templates/`

**Reference projects:**
- `~/projects/active/temporal` — full architecture reference (admin, dashboard, auth, flags, messaging)
- `~/projects/active/official-agent-registry` — simpler Hono + CF Worker reference
- `~/projects/active/cookbook` — principles and guidelines

**Existing webinitor templates (reusable patterns):** `plugins/webinitor/skills/webinitor/references/templates/`

---

## Phase 1: Plugin Shell + Manifest

**Create the plugin skeleton. No templates yet — just the structure and SKILL.md routing.**

- [x] Create `plugins/site-manager/.claude-plugin/plugin.json` (name, version 1.0.0, author, MIT)
- [x] Create `plugins/site-manager/skills/site-manager/SKILL.md` — frontmatter + routing table + Init/Deploy/Status/Manifest/SeedAdmin/Help sections (section bodies can be stubs that say "See Phase N")
- [x] Create `plugins/site-manager/README.md`
- [x] Add entry to `.claude-plugin/marketplace.json`
- [x] Create `plugins/site-manager/skills/site-manager/references/templates/` directory structure
- [x] Define `site-manifest.json` schema as a template (`root/site-manifest.json.tmpl`)
- [x] Commit: `feat(site-manager): initial plugin structure and manifest schema` (6674e0e, 6806906)

**Allowed tools for SKILL.md frontmatter:**
```yaml
allowed-tools: Read, Write, Edit, Bash(bash *), Bash(brew *), Bash(npm *), Bash(wrangler *), Bash(railway *), Bash(curl *), Bash(which *), Bash(chmod *), Bash(cat *), Bash(test *), Bash(mkdir *), Bash(jq *), Bash(ls *), Bash(head *), Bash(tail *), Bash(sort *), Bash(column *), Bash(wc *), Bash(grep *), Bash(date *), Bash(docker *), Bash(cd *), AskUserQuestion
```

---

## Phase 2: Backend Templates

**The Hono API server — auth, admin, feature flags, messaging, health.**

### Core
- [x] `backend/package.json.tmpl` — hono, @hono/node-server, drizzle-orm, pg, jose, zod, bcrypt
- [x] `backend/tsconfig.json.tmpl`
- [x] `backend/drizzle.config.ts.tmpl`
- [x] `backend/src/index.ts.tmpl` — Hono node server on PORT
- [x] `backend/src/app.ts.tmpl` — Hono app: CORS, logger, error handler, route mounting
- [x] `backend/src/config/env.ts.tmpl` — Zod schema (DATABASE_URL, PORT, CORS_ORIGIN, CLIENT_URL, JWT_SECRET, admin email, optional OAuth + messaging env vars)

### Database
- [x] `backend/src/db/schema.ts.tmpl` — users, oauth_accounts, refresh_tokens, feature_flags, message_log, feedback_submissions
- [x] `backend/src/db/client.ts.tmpl` — Drizzle PostgreSQL client
- [x] `backend/src/db/migrate.ts.tmpl` — Run drizzle migrations
- [x] `backend/src/db/seed.ts.tmpl` — Seed admin account (read email/password from env or prompt)

### Auth
- [x] `backend/src/auth/password.ts.tmpl` — bcrypt hash + verify
- [x] `backend/src/auth/session.ts.tmpl` — JWT create (15 min TTL), verify, refresh token rotation
- [x] `backend/src/auth/middleware.ts.tmpl` — extractAuth, requireAuth, requireAdmin
- [x] `backend/src/auth/github.ts.tmpl` — GitHub OAuth (conditional)
- [x] `backend/src/auth/google.ts.tmpl` — Google OAuth with refresh tokens (conditional)
- [x] `backend/src/routes/auth.ts.tmpl` — POST /register, /login, /refresh, /logout, /me

### Admin Routes
- [x] `backend/src/routes/admin/users.ts.tmpl` — GET /admin/users (paginated, search), PATCH /admin/users/:id/role
- [x] `backend/src/routes/admin/flags.ts.tmpl` — GET/POST/PATCH/DELETE /admin/flags
- [x] `backend/src/routes/admin/messaging.ts.tmpl` — POST /admin/messaging/send, GET /admin/messaging/log
- [x] `backend/src/routes/admin/feedback.ts.tmpl` — GET /admin/feedback, PATCH /admin/feedback/:id

### Services
- [x] `backend/src/services/feature-flags.ts.tmpl` — getAll, get, set, delete
- [x] `backend/src/services/messaging.ts.tmpl` — sendEmail, sendSms (Postmark + Twilio abstraction)
- [x] `backend/src/services/settings.ts.tmpl` — Settings key registry (centralized constants)

### Middleware
- [x] `backend/src/middleware/error.ts.tmpl` — RFC 9457 Problem Details
- [x] `backend/src/middleware/logger.ts.tmpl` — Structured logging with requestId, userId MDC
- [x] `backend/src/middleware/rate-limit.ts.tmpl` — Per-IP rate limiting
- [x] `backend/src/middleware/cors.ts.tmpl` — Environment-driven CORS with dev-friendly localhost support

### Health + Public
- [x] `backend/src/routes/health.ts.tmpl` — /health, /health/live, /health/ready (DB check)
- [x] `backend/src/routes/public.ts.tmpl` — Public API endpoints (feature flags for client)

### Commit: `feat(site-manager): add backend API templates`

---

## Phase 3: Shared Package Templates

- [x] `shared/package.json.tmpl`
- [x] `shared/tsconfig.json.tmpl`
- [x] `shared/src/index.ts.tmpl` — re-exports
- [x] `shared/src/types.ts.tmpl` — User, FeatureFlag, MessageLog, FeedbackSubmission API types
- [x] `shared/src/constants.ts.tmpl` — Settings keys registry, feature flag key constants
- [x] `shared/src/api-client.ts.tmpl` — Typed fetch wrapper with exponential backoff + jitter, circuit breaker

### Commit: `feat(site-manager): add shared package templates` (d850bf0)

---

## Phase 4: Main Site Templates

**The public-facing site at foo.com — React SPA served by CF Worker.**

- [x] `sites/main/wrangler.jsonc.tmpl` — worker name, custom domain routes
- [x] `sites/main/package.json.tmpl` — react, vite, tailwindcss, @tanstack/react-query, @tanstack/react-router, wrangler
- [x] `sites/main/vite.config.ts.tmpl`
- [x] `sites/main/tailwind.config.ts.tmpl`
- [x] `sites/main/tsconfig.json.tmpl`
- [x] `sites/main/src/worker.ts.tmpl` — proxy /api/*, /auth/* → Railway, SPA fallback
- [x] `sites/main/src/main.tsx.tmpl` — React entry with QueryClient + RouterProvider
- [x] `sites/main/src/router.tsx.tmpl` — Tanstack Router with routes
- [x] `sites/main/src/index.html.tmpl`
- [x] `sites/main/src/context/auth.tsx.tmpl` — AuthContext with login/register/logout
- [x] `sites/main/src/context/feature-flags.tsx.tmpl` — FeatureFlagContext
- [x] `sites/main/src/hooks/use-auth.ts.tmpl`
- [x] `sites/main/src/hooks/use-feature-flag.ts.tmpl`
- [x] `sites/main/src/api/auth.ts.tmpl` — Tanstack Query hooks for auth endpoints
- [x] `sites/main/src/api/flags.ts.tmpl` — Tanstack Query hook for feature flags
- [x] `sites/main/src/routes/index.tsx.tmpl` — Home page
- [x] `sites/main/src/routes/login.tsx.tmpl` — Login form
- [x] `sites/main/src/routes/register.tsx.tmpl` — Registration form
- [x] `sites/main/src/components/layout.tsx.tmpl` — App shell with nav

### Commit: `feat(site-manager): add main site templates` (3a1c5e9)

---

## Phase 5: Admin Site Templates

**Admin dashboard at admin.foo.com — same auth, requires admin role.**

- [x] `sites/admin/wrangler.jsonc.tmpl`
- [x] `sites/admin/package.json.tmpl`
- [x] `sites/admin/vite.config.ts.tmpl`
- [x] `sites/admin/tailwind.config.ts.tmpl`
- [x] `sites/admin/tsconfig.json.tmpl`
- [x] `sites/admin/src/worker.ts.tmpl` — proxy + SPA
- [x] `sites/admin/src/main.tsx.tmpl`
- [x] `sites/admin/src/router.tsx.tmpl`
- [x] `sites/admin/src/index.html.tmpl`
- [x] `sites/admin/src/context/auth.tsx.tmpl` — same auth, but redirects non-admin to error
- [x] `sites/admin/src/api/admin.ts.tmpl` — Tanstack Query hooks for admin endpoints
- [x] `sites/admin/src/routes/index.tsx.tmpl` — Admin dashboard home
- [x] `sites/admin/src/routes/users.tsx.tmpl` — User table + role editing
- [x] `sites/admin/src/routes/flags.tsx.tmpl` — Feature flag list + toggles
- [x] `sites/admin/src/routes/messaging.tsx.tmpl` — Send email/SMS, view message log
- [x] `sites/admin/src/routes/feedback.tsx.tmpl` — Feedback submissions table
- [x] `sites/admin/src/routes/login.tsx.tmpl` — Admin login (same form, role-checked after)
- [x] `sites/admin/src/components/layout.tsx.tmpl` — Admin shell with sidebar nav

### Commit: `feat(site-manager): add admin site templates` (48df02b)

---

## Phase 6: Dashboard Templates

**Status dashboard at dashboard.foo.com — CF Worker + D1 SQLite, runs independently.**

- [x] `sites/dashboard/wrangler.jsonc.tmpl` — D1 binding, cron triggers (every min, every 5 min, hourly)
- [x] `sites/dashboard/package.json.tmpl`
- [x] `sites/dashboard/vite.config.ts.tmpl`
- [x] `sites/dashboard/tsconfig.json.tmpl`
- [x] `sites/dashboard/worker/index.ts.tmpl` — CF Worker: serves API routes + cron handlers (health check ping, deployment sync, metrics rollup)
- [x] `sites/dashboard/migrations/0001_health_checks.sql.tmpl`
- [x] `sites/dashboard/migrations/0002_incidents.sql.tmpl`
- [x] `sites/dashboard/migrations/0003_deployments.sql.tmpl`
- [x] `sites/dashboard/migrations/0004_metrics.sql.tmpl`
- [x] `sites/dashboard/src/main.tsx.tmpl`
- [x] `sites/dashboard/src/router.tsx.tmpl`
- [x] `sites/dashboard/src/index.html.tmpl`
- [x] `sites/dashboard/src/routes/health.tsx.tmpl` — Service status cards, uptime chart
- [x] `sites/dashboard/src/routes/incidents.tsx.tmpl` — Incident timeline
- [x] `sites/dashboard/src/routes/deployments.tsx.tmpl` — Deployment history table
- [x] `sites/dashboard/src/context/auth.tsx.tmpl` — Auth (admin-only access)
- [x] `sites/dashboard/src/components/layout.tsx.tmpl`

### Commit: `feat(site-manager): add dashboard templates with D1` (3da7402)

---

## Phase 7: Root + CI Templates

- [x] `root/package.json.tmpl` — root build scripts (build:all, deploy:all, dev)
- [x] `root/Dockerfile.tmpl` — multi-stage Node 22 Alpine (builds shared → backend)
- [x] `root/railway.toml.tmpl` — builder: dockerfile, health check
- [x] `root/docker-compose.yml.tmpl` — PostgreSQL 16 for local dev
- [x] `root/env.example.tmpl` — all env vars with comments
- [x] `root/gitignore.tmpl`
- [x] `root/site-manifest.json.tmpl` — initial manifest with all services as not_created (Phase 1)
- [x] `github/deploy-main.yml.tmpl` — GH Actions: deploy main site on push
- [x] `github/deploy-admin.yml.tmpl` — GH Actions: deploy admin site on push
- [x] `github/deploy-dashboard.yml.tmpl` — GH Actions: deploy dashboard on push

### Commit: `feat(site-manager): add root config and CI templates` (6b412b8)

---

## Phase 8: SKILL.md Sections

**Fill in the SKILL.md stub sections with full implementation instructions.**

- [x] **Init section** — full interactive flow: project name, domain, auth providers, admin seed, generate files, write manifest, offer /webinitor connect
- [x] **Deploy section** — read manifest, pre-flight checks, deploy backend (railway up), deploy 3 sites (wrangler deploy), update manifest, health check
- [x] **Deploy <service> section** — deploy single service
- [x] **Status section** — read manifest, check each service health, report
- [x] **Manifest section** — show/validate site-manifest.json
- [x] **Seed Admin section** — create admin account via backend seed script
- [x] **Help section** — full command listing
- [x] **Routing table** — all subcommands
- [x] Update plugin.json, README.md (verified — already correct)

### Commit: `feat(site-manager): complete SKILL.md with all sections (v1.0.0)`

---

## Phase 9: Verification + Install

- [x] Install plugin: `claude plugin install site-manager@cat-herding`
- [x] Test `/site-manager init` in a temp directory
- [x] Verify generated project builds (backend + all sites) — fixed 26 template files (3392c72)
- [x] Test seed admin account — seeded via public DB URL
- [x] Test login flow — smoke test passes (register, login, refresh, me, logout)
- [x] Test admin dashboard — admin CRUD tests pass (users, flags, feedback, messaging)
- [x] Test feature flag toggle — create/toggle/delete all pass
- [x] Test `/site-manager deploy` — deployed to Railway + 2 CF Workers, all healthy
- [x] Test `/site-manager status` — health endpoints all return 200
- [x] Test dashboard health checks (D1) — skipped (CF API token lacks D1 permissions)

---

## Notes for Implementation

1. **Reuse webinitor template patterns** — the existing templates at `plugins/webinitor/skills/webinitor/references/templates/` have working patterns for wrangler.jsonc, Dockerfile, worker.ts, etc. Copy and extend, don't start from scratch.

2. **Reference temporal code directly** — read the actual files from `~/projects/active/temporal` for admin routes, feature flags, messaging, auth patterns. The temporal project is the production reference.

3. **Template placeholders**: `{{PROJECT_NAME}}`, `{{CUSTOM_DOMAIN}}`, `{{API_BACKEND_URL}}`, `{{PACKAGE_SCOPE}}`, `{{ADMIN_EMAIL}}`, `{{DB_NAME}}`

4. **Each phase is independently committable and testable** — don't batch phases.

5. **The dashboard Worker is the most complex template** — it has cron triggers, D1 database, API routes, AND serves a React SPA. Reference `~/projects/active/temporal/admin-apps/status-website/` closely.
