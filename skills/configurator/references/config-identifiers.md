# Configuration Identifiers

Stable, dot-separated identifiers for every configurable item in the configurator. Used in change history entries, deploy plans, and the `--schema` CLI output.

## Naming Convention

- Format: `feature-id.field-name`
- Use **hyphens** (`-`), never underscores (`_`)
- Feature ID is the human-readable slug (e.g., `ab-testing` not `ab_testing`)
- Field names match the config key, converted to hyphen-case
- Nested fields use additional dots: `backend.environments.staging`
- List-type config items use the feature ID alone: `auth.providers`

## Canonical Source

Each feature plugin declares its identifiers via `config_identifiers()`. Run `configurator --schema` to dump the full list.

## Identifier Registry

### project

| Identifier | Type | Description |
|---|---|---|
| `project.display-name` | string | Display name for the project |
| `project.repo` | string | GitHub repository name |
| `project.org` | string | GitHub organization |
| `project.domain` | string | Primary domain |

### website

| Identifier | Type | Description |
|---|---|---|
| `website.type` | enum | Site type (none, existing, new) |
| `website.domain` | string | Website domain |
| `website.addons` | list | Website addons (sqlite database, kv store, etc.) |

### backend

| Identifier | Type | Description |
|---|---|---|
| `backend.enabled` | bool | Whether backend is enabled |
| `backend.domain` | string | Backend API domain |
| `backend.docs-domain` | string | API documentation domain |
| `backend.environments.staging` | bool | Staging environment enabled |
| `backend.environments.testing` | bool | Testing environment enabled |

### admin

| Identifier | Type | Description |
|---|---|---|
| `admin.enabled` | bool | Admin panel enabled |
| `admin.domain` | string | Admin panel domain |

### dashboard

| Identifier | Type | Description |
|---|---|---|
| `dashboard.enabled` | bool | Dashboard enabled |
| `dashboard.domain` | string | Dashboard domain |

### auth

| Identifier | Type | Description |
|---|---|---|
| `auth.providers` | list | Authentication providers (email/password, github, google) |

### email

| Identifier | Type | Description |
|---|---|---|
| `email.enabled` | bool | Transactional email enabled |
| `email.provider` | string | Email provider (resend, sendgrid, ses) |
| `email.from-address` | string | Sender email address |
| `email.from-name` | string | Sender display name |

### sms

| Identifier | Type | Description |
|---|---|---|
| `sms.enabled` | bool | SMS notifications enabled |
| `sms.provider` | string | SMS provider (twilio, vonage) |
| `sms.from-number` | string | Sender phone number |

### analytics

| Identifier | Type | Description |
|---|---|---|
| `analytics.enabled` | bool | Analytics tracking enabled |
| `analytics.provider` | string | Analytics provider (plausible, posthog) |
| `analytics.site-id` | string | Analytics site identifier |

### ab-testing

| Identifier | Type | Description |
|---|---|---|
| `ab-testing.enabled` | bool | A/B testing enabled |
| `ab-testing.provider` | string | A/B testing provider |
| `ab-testing.client-key` | string | Client-side SDK key |

### feature-flags

| Identifier | Type | Description |
|---|---|---|
| `feature-flags.enabled` | bool | Feature flags enabled |
| `feature-flags.capability-hooks` | bool | Hook into capabilities system |
| `feature-flags.flag-hooks` | bool | Hook into flag evaluation |
| `feature-flags.ab-hooks` | bool | Hook into A/B test variants |

### logging

| Identifier | Type | Description |
|---|---|---|
| `logging.enabled` | bool | Structured logging enabled |
| `logging.provider` | string | Logging provider (axiom, datadog) |
| `logging.level` | string | Default log level |

### login-tracking

| Identifier | Type | Description |
|---|---|---|
| `login-tracking.enabled` | bool | Login tracking enabled |
| `login-tracking.track-users` | bool | Track user login events |
| `login-tracking.track-tokens` | bool | Track token refresh events |
| `login-tracking.retention-days` | int | Days to retain login records |

### pausing

| Identifier | Type | Description |
|---|---|---|
| `pausing.enabled` | bool | Account pausing enabled |
| `pausing.pause-users` | bool | Allow pausing user accounts |
| `pausing.pause-tokens` | bool | Revoke tokens on pause |
| `pausing.auto-unpause` | bool | Auto-unpause on login |

### capabilities

| Identifier | Type | Description |
|---|---|---|
| `capabilities.enabled` | bool | Capabilities/permissions system enabled |
| `capabilities.definitions` | list | Capability definitions |
| `capabilities.user-assignable` | bool | Users can self-assign capabilities |
| `capabilities.token-assignable` | bool | Tokens can carry capabilities |

### theme

| Identifier | Type | Description |
|---|---|---|
| `theme.mode` | enum | Theme mode (system, light, dark) |

### text-size

| Identifier | Type | Description |
|---|---|---|
| `text-size.mode` | enum | Text size mode (system, small, medium, large, custom) |
| `text-size.custom-px` | int | Custom font size in pixels |

### user-settings

| Identifier | Type | Description |
|---|---|---|
| `user-settings.enabled` | bool | User settings page enabled |
| `user-settings.profile` | bool | Profile editing enabled |
| `user-settings.password-change` | bool | Password change enabled |
| `user-settings.theme-preference` | bool | Theme preference in settings |
| `user-settings.notifications` | bool | Notification preferences in settings |

### feedback

| Identifier | Type | Description |
|---|---|---|
| `feedback.enabled` | bool | In-app feedback widget enabled |
| `feedback.destination` | string | Where feedback is sent (email, github, slack) |
| `feedback.screenshots` | bool | Screenshot capture enabled |
