# Site Manager Plugin — Planning Document

## Vision

A Claude Code plugin (`/site-manager`) that scaffolds, deploys, and manages a **suite of websites** as a unified platform. Based on the proven temporal project architecture and agentic cookbook principles. Uses `/webinitor` for infrastructure management (Cloudflare, Railway, GoDaddy).

For a new site `foo.com`, it deploys:
1. **Backend API** — Hono on Railway + PostgreSQL
2. **Main site** (`foo.com`) — Cloudflare Worker SPA
3. **Admin site** (`admin.foo.com`) — Cloudflare Worker SPA (user/role mgmt, feature flags, messaging)
4. **Dashboard** (`dashboard.foo.com`) — Cloudflare Worker + D1 SQLite (health monitoring, 24/7 uptime)

A `site-manifest.json` tracks what's been created, deployed, and configured — versioned so new features can be added incrementally across all sites.

---

## Architecture (from temporal reference)

```
<project>/
├── backend/                    # Hono API server (Railway + PostgreSQL)
├── sites/
│   ├── main/                   # Public site (foo.com) — CF Worker
│   ├── admin/                  # Admin dashboard (admin.foo.com) — CF Worker
│   └── dashboard/              # Status dashboard (dashboard.foo.com) — CF Worker + D1
├── shared/                     # Shared types, constants, API client
├── site-manifest.json          # Tracks deployment state + features
├── Dockerfile
├── railway.toml
├── docker-compose.yml
└── .github/workflows/
```

---

## site-manifest.json

```json
{
  "version": "1.0.0",
  "project": {
    "name": "foo",
    "domain": "foo.com",
    "created": "2026-04-05T00:00:00Z"
  },
  "services": {
    "backend": {
      "status": "deployed",
      "platform": "railway",
      "url": "https://foo-production.up.railway.app",
      "database": "postgresql",
      "lastDeployed": "2026-04-05T12:00:00Z"
    },
    "main": {
      "status": "deployed",
      "platform": "cloudflare",
      "domain": "foo.com",
      "workerName": "foo-main",
      "lastDeployed": "2026-04-05T12:00:00Z"
    },
    "admin": {
      "status": "deployed",
      "platform": "cloudflare",
      "domain": "admin.foo.com",
      "workerName": "foo-admin",
      "lastDeployed": "2026-04-05T12:00:00Z"
    },
    "dashboard": {
      "status": "deployed",
      "platform": "cloudflare",
      "domain": "dashboard.foo.com",
      "workerName": "foo-dashboard",
      "d1Database": "foo-dashboard-db",
      "lastDeployed": "2026-04-05T12:00:00Z"
    }
  },
  "features": {
    "auth": {
      "enabled": true,
      "providers": ["email", "github"],
      "adminSeeded": true,
      "twoFactor": false,
      "emailVerification": false
    },
    "featureFlags": { "enabled": true },
    "email": { "enabled": false, "provider": null },
    "sms": { "enabled": false, "provider": null },
    "abTesting": { "enabled": false },
    "observability": { "enabled": true, "provider": "built-in" },
    "logging": { "enabled": true, "structured": true }
  },
  "dns": {
    "provider": "cloudflare",
    "zoneId": "abc123",
    "nameservers": ["ada.ns.cloudflare.com", "bob.ns.cloudflare.com"],
    "records": [
      { "type": "CNAME", "name": "foo.com", "target": "foo-main.workers.dev" },
      { "type": "CNAME", "name": "admin.foo.com", "target": "foo-admin.workers.dev" },
      { "type": "CNAME", "name": "dashboard.foo.com", "target": "foo-dashboard.workers.dev" }
    ]
  }
}
```

---

## Features TODO

### v1.0.0 — Foundation (build first)

- [ ] **Plugin structure** — new plugin under `plugins/site-manager/`
- [ ] **site-manifest.json** — schema, read/write, version tracking
- [ ] **`/site-manager init`** — scaffold full suite (backend + 3 sites)
- [ ] **`/site-manager deploy`** — deploy all services
- [ ] **`/site-manager status`** — check all services via manifest
- [ ] **Email + password auth** — registration, login, password hashing (bcrypt)
- [ ] **Admin seed account** — bootstrap first admin during init
- [ ] **User roles** — admin, user (in DB, enforced server-side)
- [ ] **JWT sessions** — short-lived access tokens (15 min) + refresh token rotation
- [ ] **Main site** — hello world with login/register
- [ ] **Admin site** — user list, role editing, basic CRUD
- [ ] **Dashboard site** — health checks, uptime display, D1 SQLite for local persistence
- [ ] **Feature flags** — DB-backed, admin UI toggle, client-side `useFeatureFlag` hook
- [ ] **Health endpoints** — `/health`, `/health/live`, `/health/ready` (with DB check)
- [ ] **Structured logging** — request ID, user ID in all logs
- [ ] **Error handling** — RFC 9457 Problem Details format
- [ ] **CORS** — configured per-site origins
- [ ] **Input validation** — Zod schemas on all endpoints
- [ ] **Secure cookie sessions** — HttpOnly, Secure, SameSite

### v1.1.0 — Communication

- [ ] **Email integration** — Postmark provider (send welcome, notifications)
- [ ] **SMS integration** — Twilio provider (send alerts, notifications)
- [ ] **Message templates** — code-defined templates with `{{variable}}` substitution
- [ ] **Message log** — store all sends (email/SMS) with status
- [ ] **Notification preferences** — per-user opt-in/opt-out
- [ ] **Admin messaging UI** — send email/SMS to users from admin dashboard

### v1.2.0 — Feature Management

- [ ] **A/B testing** — experiment definition, variant assignment, results tracking
- [ ] **Feature gating** — gate features by user role, percentage rollout, user list
- [ ] **Admin feature flag UI** — create/edit/delete flags with description
- [ ] **Admin A/B test UI** — create experiments, view results

### v1.3.0 — Observability

- [ ] **Metrics** — Micrometer/OTLP counters and timers (auth, API, sync)
- [ ] **Dashboard metrics** — request latency, error rates, active users
- [ ] **Dashboard incidents** — manual incident creation, status updates
- [ ] **Dashboard deployment tracking** — sync Railway/CF deploys
- [ ] **Cron health checks** — dashboard Worker polls backend every minute
- [ ] **Alerts** — email/SMS when health check fails

### v1.4.0 — Security Hardening

- [ ] **Email verification** — verify email before account activation
- [ ] **Two-factor auth (2FA)** — TOTP (Google Authenticator, etc.)
- [ ] **Password reset** — email-based reset flow
- [ ] **Rate limiting** — per-IP and per-user rate limits
- [ ] **Account lockout** — after N failed login attempts
- [ ] **Audit log** — admin actions logged with timestamp, actor, action

### v1.5.0 — OAuth Providers

- [ ] **GitHub OAuth** — optional, added alongside email/password
- [ ] **Google OAuth** — optional, with refresh tokens
- [ ] **Account linking** — link OAuth to existing email account
- [ ] **Admin OAuth config UI** — enable/disable providers

### Future Versions

- [ ] **API keys** — for programmatic access (scoped, revocable)
- [ ] **Webhooks** — notify external services on events
- [ ] **File uploads** — R2 storage integration
- [ ] **i18n** — internationalization support
- [ ] **Themes** — admin-configurable site theming
- [ ] **Multi-tenant** — one backend serving multiple projects
- [ ] **CLI** — `site-manager` CLI for non-Claude usage

---

## Cookbook Principles to Follow

From `~/projects/agentic-cookbook/cookbook/`:

| Principle | Application |
|-----------|-------------|
| **Separation of Concerns** | Auth, feature flags, logging are independent services with clean interfaces |
| **Dependency Injection** | All services injected — swap providers (Postmark→SES, Twilio→SNS) without code changes |
| **Design for Deletion** | Each feature is independently removable via manifest flags |
| **Fail Fast** | Validate at system boundaries (Zod), detect invalid state immediately |
| **Idempotency** | Admin operations and deployments safe to repeat |
| **Manage Complexity Through Boundaries** | Ports (interfaces) for auth, messaging, flags; adapters for implementations |

## Security Guidelines to Follow

| Guideline | Application |
|-----------|-------------|
| **OAuth 2.0 PKCE** | For SPA clients (admin, dashboard) |
| **Server-side authorization only** | Client checks are UX, not security |
| **Deny by default** | New endpoints locked down |
| **No PII in logs** | Mask tokens, emails in structured logs |
| **Parameterized queries** | Drizzle ORM handles this |
| **Short-lived access tokens** | 15 min TTL, refresh rotation |
| **HttpOnly Secure cookies** | Never localStorage for tokens |
| **RFC 9457 errors** | Problem Details for all API errors |

## API Design Guidelines

| Convention | Example |
|-----------|---------|
| Lowercase hyphens | `/order-items` not `/orderItems` |
| Plural nouns | `/users`, `/flags` |
| No verbs | HTTP method is the verb |
| Max 2 levels nesting | `/users/{id}/roles` |
| Query params for filtering | `/users?status=active&sort=-created_at` |

---

## How /site-manager Uses /webinitor

`/site-manager` delegates infrastructure to `/webinitor`:
- Domain purchase/lookup → `/webinitor domains`
- DNS management → `/webinitor dns`
- Cloudflare zone setup → `/webinitor connect`
- Service status → `/webinitor status`
- GoDaddy nameserver pointing → `/webinitor connect`

`/site-manager` owns:
- Application scaffolding (code generation)
- Deployment orchestration (railway up, wrangler deploy)
- Feature management (manifest, auth, flags)
- Admin/dashboard app generation

---

## Suggested Additions (from cookbook recipes)

Based on the cookbook, these should be included early:

1. **Settings keys registry** (`recipes/infrastructure/settings-keys.md`) — centralized constants for all config keys, prevents scattered string literals
2. **Categorized logging** (`recipes/infrastructure/logging.md`) — `Log.auth.info()`, `Log.api.debug()`, etc.
3. **Debug panel** (`recipes/ui/panels/debug-panel.md`) — dev-only panel with feature flag toggles, analytics log, A/B variant picker, environment info
4. **Retry with backoff** (`guidelines/networking/retry-and-resilience.md`) — exponential backoff + jitter for all API calls, circuit breaker for cascading failures
5. **Error responses** (`guidelines/networking/error-responses.md`) — RFC 9457 Problem Details from day one

---

## Open Questions

1. **Backend language**: Stick with TypeScript/Hono (consistent with webinitor templates) or switch to Kotlin/Ktor (temporal's stack)?
2. **Dashboard D1 scope**: What data should the dashboard store independently in D1 vs fetch from backend?
3. **Admin auth**: Same auth as main site, or separate admin credentials?
4. **Deployment strategy**: Auto-deploy all 4 services together, or independent?
