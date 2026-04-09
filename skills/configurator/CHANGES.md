# Configurator Change History

Changes to what the configurator deploys. Each entry represents a new deployment option, improved template, or fix that affects deployed projects. The CLI shows relevant changes when a project's manifest version is behind the current configurator version.

## 0.3.0

- **Cookie-based auth**: Refresh tokens stored in httpOnly cookies instead of localStorage. Access tokens kept in memory only. Auto-refresh every 13 minutes with retry on 401.
- **Remember me**: Login and register pages now have a "Remember me" checkbox (1-day vs 30-day refresh token).
- **Unified auth schema**: Single `userAuthMethods` table replaces separate password hash and OAuth account tables. Supports password, GitHub, Google, and Apple providers.
- **API token capabilities**: `scopes` field renamed to `capabilities` on API tokens. New `requireCapability()` middleware for granular permission checks.
- **Capability-based authorization**: API tokens and users can have per-capability permissions (e.g., `messaging:send`, `api:write`).
- **Admin auth improvements**: Admin site uses cookie-based auth (no more localStorage). All admin API helpers use auto-refreshing authenticated fetch.
- **API token management UI**: Capability selection when creating tokens. Capabilities column in token list.

## 0.2.0

- **API backend type**: New "api" backend choice alongside "full backend". Configures an endpoint URL and optional API docs site at `api.<domain>`.
- **API docs site**: Scalar-based OpenAPI 3.1 documentation site. Includes `.well-known/ai-plugin.json` for LLM discovery.
- **OpenAPI endpoint**: Backend serves `/api/openapi.json` with full API specification.
- **Staging/testing environments**: Optional staging and testing environment URLs for backends.
- **Admin settings page**: Toggle "Allow new account registration" from the admin UI.
- **Admin API token page**: Create, list, and revoke API tokens from the admin UI. Secret shown once at creation.
- **Website type "none"**: Backend-only deployments without a user-facing website.

## 0.1.0

- Initial release: interactive CLI wizard for project configuration.
- Full-stack project scaffolding: main site, backend, admin, dashboard.
- Cloudflare Workers deployment for frontend sites.
- Railway deployment for backend API.
- Email/password, GitHub, Google, Apple OAuth authentication.
- SQLite (D1), KV, R2 storage addons for websites.
- Manifest-based deployment tracking at `.site/manifest.json`.
