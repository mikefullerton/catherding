# Site Manager

Scaffold, deploy, and manage a suite of websites (backend + main + admin + dashboard) as a unified platform. Built on Cloudflare Workers, Railway, and modern TypeScript.

## Architecture

For a domain like `foo.com`, Site Manager creates:

| Service | Platform | URL |
|---------|----------|-----|
| Backend API | Railway + PostgreSQL | `foo-production.up.railway.app` |
| Main site | Cloudflare Worker | `foo.com` |
| Admin site | Cloudflare Worker | `admin.foo.com` |
| Dashboard | Cloudflare Worker + D1 | `dashboard.foo.com` |

## Tech Stack

- **Backend**: Hono + Drizzle ORM + PostgreSQL + Zod
- **Frontends**: React 19 + Vite + Tailwind CSS 4 + Tanstack Query/Router
- **Edge**: Cloudflare Workers
- **Dashboard DB**: D1 SQLite (independent of backend)
- **Auth**: Email/password (always) + GitHub/Google OAuth (optional)

## Commands

| Command | Description |
|---------|-------------|
| `/site-manager init [domain]` | Scaffold a new project (backend + 3 sites) |
| `/site-manager deploy [service]` | Deploy all or specific service |
| `/site-manager status` | Check status of all services |
| `/site-manager manifest` | View site-manifest.json |
| `/site-manager manifest validate` | Validate manifest schema |
| `/site-manager seed-admin` | Create initial admin account |
| `/site-manager --help` | Show help |
| `/site-manager --version` | Show version |

## Prerequisites

- [Webinitor](/webinitor) configured for Cloudflare + Railway
- Node.js 20+
- Wrangler CLI
- Railway CLI

## Installation

```bash
# From the cat-herding marketplace
claude plugin install site-manager@cat-herding

# Or load directly for development
claude --plugin-dir ./plugins/site-manager
```
