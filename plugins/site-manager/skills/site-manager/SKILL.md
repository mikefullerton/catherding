---
name: site-manager
description: "Scaffold, deploy, and manage a suite of websites (backend + main + admin + dashboard) as a unified platform. /site-manager init, /site-manager deploy, /site-manager status, /site-manager manifest, /site-manager seed-admin, /site-manager --help"
version: "1.0.0"
argument-hint: "[init|deploy|status|manifest|seed-admin|--help|--version]"
allowed-tools: Read, Write, Edit, Bash(bash *), Bash(brew *), Bash(npm *), Bash(wrangler *), Bash(railway *), Bash(curl *), Bash(which *), Bash(chmod *), Bash(cat *), Bash(test *), Bash(mkdir *), Bash(jq *), Bash(ls *), Bash(head *), Bash(tail *), Bash(sort *), Bash(column *), Bash(wc *), Bash(grep *), Bash(date *), Bash(docker *), Bash(cd *), AskUserQuestion
model: sonnet
---

# Site Manager v1.0.0

Scaffold, deploy, and manage a suite of 4 websites as a unified platform.

**Architecture per project:**
- **Backend API** — Hono + Drizzle + PostgreSQL (Railway)
- **Main site** (`domain.com`) — React 19 + Vite + Tailwind 4 (Cloudflare Worker)
- **Admin site** (`admin.domain.com`) — React 19 + Vite + Tailwind 4 (Cloudflare Worker)
- **Dashboard** (`dashboard.domain.com`) — React 19 + Vite + D1 SQLite (Cloudflare Worker)

## Startup

**Step 0 — Ensure permissions**: Run `bash ${CLAUDE_SKILL_DIR}/references/ensure-permissions.sh ${CLAUDE_SKILL_DIR}/SKILL.md` to whitelist this skill's tools in `~/.claude/settings.json`. This is silent and idempotent.

**CRITICAL**: The very first thing you output MUST be the version line:

site-manager v1.0.0

If `$ARGUMENTS` is `--version`, respond with exactly:
> site-manager v1.0.0

Then stop.

## Route by argument

| `$ARGUMENTS` | Action |
|---|---|
| `init` or `init <domain>` | Go to **Init** |
| `deploy` or `deploy all` | Go to **Deploy** |
| `deploy backend` | Go to **Deploy** (backend only) |
| `deploy main` | Go to **Deploy** (main site only) |
| `deploy admin` | Go to **Deploy** (admin site only) |
| `deploy dashboard` | Go to **Deploy** (dashboard only) |
| `status` or empty | Go to **Status** |
| `manifest` | Go to **Manifest** |
| `manifest show` | Go to **Manifest** (show current) |
| `manifest validate` | Go to **Manifest** (validate) |
| `seed-admin` | Go to **Seed Admin** |
| `--help` | Go to **Help** |
| `--version` | Print version (handled in Startup) |
| anything else | Print: "Usage: /site-manager [init\|deploy\|status\|manifest\|seed-admin\|--help\|--version]" and stop |

---

## Init

**Scaffold a new project with all 4 sites.**

*See Phase 2–6 for full implementation.*

### Step 1: Gather project info

Ask the user for:
- **Project name** (lowercase, alphanumeric + hyphens)
- **Domain** (e.g., `foo.com`)
- **Target directory** (default: `./<project-name>/`)
- **Auth providers** — email/password is always included; optionally add GitHub and/or Google OAuth

### Step 2: Scaffold project

Using templates from `${CLAUDE_SKILL_DIR}/references/templates/`, create the full project structure:

```
<project>/
├── backend/                    # Hono API server
├── sites/
│   ├── main/                   # Public site (domain.com)
│   ├── admin/                  # Admin dashboard (admin.domain.com)
│   └── dashboard/              # Status dashboard (dashboard.domain.com)
├── shared/                     # Shared types, constants, API client
├── site-manifest.json          # Tracks deployment state + features
├── Dockerfile
├── railway.toml
├── docker-compose.yml
└── package.json                # Root workspace
```

### Step 3: Initialize site-manifest.json

Create `site-manifest.json` from the template with all services in `"scaffolded"` status.

### Step 4: Install dependencies

Run `npm install` in the project root (workspace mode).

### Step 5: Report

Print a summary of what was created and next steps (`/site-manager deploy`, `/site-manager seed-admin`).

---

## Deploy

**Deploy services to their platforms.**

*See Phase 8 for full implementation.*

### Prerequisites

- Project must have a `site-manifest.json` in the current directory
- Webinitor must be configured (`/webinitor status` to check)

### Step 1: Read manifest

Read `site-manifest.json` to determine what needs deploying.

### Step 2: Deploy services

Deploy the requested services (or all if no argument):

1. **Backend** → Railway (via `railway up`)
2. **Main site** → Cloudflare (via `wrangler deploy`)
3. **Admin site** → Cloudflare (via `wrangler deploy`)
4. **Dashboard** → Cloudflare (via `wrangler deploy`, create D1 database if needed)

### Step 3: Update manifest

Update `site-manifest.json` with deployment URLs and timestamps.

### Step 4: Report

Print deployment status for each service.

---

## Status

**Check the status of all services.**

*See Phase 9 for full implementation.*

### Step 1: Read manifest

Read `site-manifest.json` from the current directory. If not found, print:
> No site-manifest.json found. Run `/site-manager init` to create a project.

### Step 2: Check services

For each service in the manifest:
- **Backend**: Hit `/health` endpoint
- **Main/Admin/Dashboard**: Check if Worker is deployed via `wrangler` or HTTP check

### Step 3: Report

```
=== SITE MANAGER STATUS ===

Project: foo (foo.com)
Manifest: v1.0.0

  Backend API        ✅ deployed    https://foo-production.up.railway.app
  Main site          ✅ deployed    https://foo.com
  Admin site         ✅ deployed    https://admin.foo.com
  Dashboard          ✅ deployed    https://dashboard.foo.com

Features:
  Auth               ✅ email, github
  Feature flags      ✅ enabled
  Email              ❌ not configured
  SMS                ❌ not configured
```

---

## Manifest

**View or validate the site-manifest.json.**

### manifest show (default)

Read and pretty-print the current `site-manifest.json`.

### manifest validate

Validate the manifest against the expected schema. Report any missing or invalid fields.

---

## Seed Admin

**Create the initial admin account.**

*See Phase 2 for full implementation.*

### Step 1: Check prerequisites

- Backend must be deployed (check manifest)
- Database must be migrated

### Step 2: Gather credentials

Ask the user for:
- **Admin email**
- **Admin password** (minimum 12 characters)

### Step 3: Seed

Run the backend seed script to create the admin account with the `admin` role.

### Step 4: Update manifest

Set `features.auth.adminSeeded: true` in the manifest.

---

## Help

Print:

```
Site Manager v1.0.0 — Scaffold, deploy, and manage website suites

Commands:
  /site-manager init [domain]     Scaffold a new project (backend + 3 sites)
  /site-manager deploy [service]  Deploy all services (or: backend, main, admin, dashboard)
  /site-manager status            Check status of all services
  /site-manager manifest          View site-manifest.json
  /site-manager manifest validate Validate manifest schema
  /site-manager seed-admin        Create initial admin account
  /site-manager --help            Show this help
  /site-manager --version         Show version

Tech Stack:
  Backend:    Hono + Drizzle + PostgreSQL (Railway)
  Frontends:  React 19 + Vite + Tailwind 4 + Tanstack Query/Router
  Edge:       Cloudflare Workers
  Dashboard:  Cloudflare Workers + D1 SQLite
  Auth:       Email/password + optional GitHub/Google OAuth
```
