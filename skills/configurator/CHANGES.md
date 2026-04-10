# Configurator Change History

Changes to what the configurator deploys. Each entry represents a new deployment option, improved template, or fix that affects deployed projects. The CLI shows relevant changes when a project's manifest version is behind the current configurator version.

## 1.27.0

- **Simplified Caddy integration**: Web editor HTML is now a single file copied to `~/.local-server/sites/configurator.html` — no caddy_routes, no reverse proxy, no subdirectories. API calls go directly to the backend on port 4040 via CORS.
- **Page metadata**: Added `<meta name="description">` so the Caddy home page listing shows a description.

## 1.26.0

- **Caddy integration**: Web editor HTML is now served via the always-on Caddy server at `localhost:2080/configurator/`. The configurator backend only handles API calls, proxied through Caddy. No more one-off HTTP servers.

## 1.25.0

- **Sidebar nav categories**: Reorganized web editor categories — added "Website" section, moved logging to "Analytics & Flags", renamed "Operations" to "Secrets".
- **Secrets status display**: Credentials page now shows live keychain status (set/missing) per secret with reasons, and a hint to run `--set-credentials` when any are missing.
- **Manifest panel**: New "Manifest" nav section shows the current config as filtered JSON (only set values).
- **Pinned action buttons**: Deploy/Cancel buttons are now fixed to the bottom of the page.

## 1.22.0

- **Two-column layout**: Web editor now uses a two-column grid — infrastructure & deployments on the left, settings & features on the right. Responsive: collapses to single column on narrow screens.
- **Dev-team theme**: Dark theme with gold accents, DM Mono / Instrument Serif / Manrope fonts, grain overlay, matching the Agentic Cookbook design system.
- **Config merge**: Saved config preferences (environments, theme, etc.) are now preserved when rebuilding from a manifest, instead of being discarded.
- **Backend environments**: `manifest_to_config()` now extracts staging/testing environments from manifest services and features sections.

## 0.6.15

- **Display name**: Project config now includes a human-readable display name field.
- **Email config**: New email feature plugin — provider selection (Resend, SendGrid, SES, SMTP), from address/name.
- **SMS config**: New SMS feature plugin — provider selection (Twilio, Vonage, Amazon SNS), from number.
- **Analytics**: New analytics feature plugin — Plausible, PostHog, Cloudflare Web Analytics, Google Analytics.
- **A/B testing**: New A/B testing feature plugin — GrowthBook, LaunchDarkly, Statsig, custom.
- **Logging**: New logging feature plugin — Axiom, Datadog, Logtail, Sentry with configurable log level.
- **Login tracking**: New login tracking feature plugin — track user logins and API token usage with retention.
- **User/token pausing**: New pausing feature plugin — temporary suspension with optional auto-unpause.
- **Credentials**: New credentials feature plugin — track required keychain entries (Cloudflare, Railway, GitHub, DB).
- **Dark/light mode**: New theme feature plugin — system preference, light only, dark only, or user toggle.
- **Text size**: New text size feature plugin — system, small, medium, large, or custom pixel size.
- **User settings panel**: New user settings feature plugin — profile editing, password change, theme, notifications.
- **Feedback/bug reporting**: New feedback feature plugin — report to GitHub Issues, email, or backend API.
- **Capabilities editing**: New capabilities feature plugin — define permission scopes for users and tokens.
- **Feature flags**: New feature flags feature plugin — client-side hooks for capabilities, flags, and A/B tests.

## 0.6.0

- **Feature plugin architecture**: Each configurable feature (project, website, backend, admin, dashboard, auth) is now a self-contained plugin with its own file, version, HTML, JS, and config logic. Adding new features no longer risks regressions in existing ones.
- **Per-feature versioning**: Each feature plugin has its own semver version, independent of the CLI version.
- **Coordinator-based web editor**: The web editor composes the page from feature fragments instead of a single monolithic template.

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
