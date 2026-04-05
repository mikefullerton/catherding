# Site Manager Smoke & Validation Test System

## Goal

Add a `/site-manager test` command that validates a deployed site-manager project end-to-end. Two test suites: **smoke** (essential health + auth) and **validate** (comprehensive CRUD + edge cases). Python stdlib only, zero external dependencies.

Also: convert the lone shell script (`ensure-permissions.sh`) to Python, establishing Python as the scripting language for site-manager going forward.

## Test Project

For Phase 9 verification, deploy a real test project:
- **Name:** `sm-smoke-test-deleteme`
- **Domain:** `squarepoopstudios.com`
- **Location:** `/tmp/sm-smoke-test-deleteme/`
- **Auth:** email/password only (no OAuth)
- **Infrastructure:** Railway (backend + PostgreSQL), Cloudflare Workers (3 sites)
- **Teardown:** delete Railway project, CF workers, and local files when done

## New Command

```
/site-manager test [smoke|validate] [--base-url <url>] [--admin-email <email>] [--admin-password <password>]
```

- `smoke` (default) — 10 essential tests
- `validate` — all 25 tests (includes smoke)
- `--base-url` — backend API URL (reads from `site-manifest.json` if omitted)
- `--admin-email` / `--admin-password` — for admin-level tests (prompts if omitted)

## Files

| Action | File | Purpose |
|--------|------|---------|
| Create | `references/smoke-test.py` | Test runner (both suites) |
| Create | `references/ensure-permissions.py` | Replace ensure-permissions.sh |
| Delete | `references/ensure-permissions.sh` | Replaced by Python version |
| Modify | `SKILL.md` | Add `test` route, update ensure-permissions call |

## Test Runner (`smoke-test.py`)

### Interface

```bash
python3 smoke-test.py smoke --base-url https://example.up.railway.app \
  --main-url https://example.com \
  --admin-url https://admin.example.com \
  --dashboard-url https://dashboard.example.com \
  --admin-email admin@example.com \
  --admin-password secretpassword
```

- Exit code 0: all tests pass
- Exit code 1: any test fails
- `--verbose`: show request/response details on failure

### Auth State Management

The runner manages its own auth lifecycle:
1. Register a test user: `smoke-test-{timestamp}@test.local`
2. Login to get tokens
3. Use access token for authenticated requests
4. Test refresh flow
5. For admin tests: login with provided admin credentials
6. Cleanup: test user stays (no delete endpoint in v1 — admin can remove via dashboard)

### Output Format

```
=== SITE MANAGER SMOKE TESTS ===
Target: https://sm-smoke-test-deleteme-production.up.railway.app

 1/10 PASS  Backend health endpoint
 2/10 PASS  Backend readiness check
 3/10 FAIL  Register user
             Expected: 201, Got: 500
             Response: {"type":"about:blank","title":"Internal Server Error",...}
 ...

Results: 8/10 passed, 2 failed
```

### Smoke Tests (10)

| # | Test | Method | Endpoint | Expected |
|---|------|--------|----------|----------|
| 1 | Backend health | GET | `/api/health` | 200, `{"status":"ok"}` |
| 2 | Backend readiness | GET | `/api/health/ready` | 200 |
| 3 | Main site responds | GET | main URL | 200, HTML |
| 4 | Admin site responds | GET | admin URL | 200, HTML |
| 5 | Dashboard responds | GET | dashboard URL | 200, HTML |
| 6 | Register user | POST | `/api/auth/register` | 201, tokens in body |
| 7 | Login | POST | `/api/auth/login` | 200, tokens in body |
| 8 | Token refresh | POST | `/api/auth/refresh` | 200, new tokens |
| 9 | Get current user | GET | `/api/auth/me` | 200, user object |
| 10 | Non-admin blocked | GET | `/api/admin/users` | 403 |

### Validation Tests (15 additional)

| # | Test | Method | Endpoint | Expected |
|---|------|--------|----------|----------|
| 11 | Admin login | POST | `/api/auth/login` | 200, tokens |
| 12 | Admin list users | GET | `/api/admin/users` | 200, array with pagination |
| 13 | Create feature flag | POST | `/api/admin/flags` | 201, flag object |
| 14 | Toggle feature flag | PATCH | `/api/admin/flags/:id` | 200 |
| 15 | Delete feature flag | DELETE | `/api/admin/flags/:id` | 200 |
| 16 | List feedback | GET | `/api/admin/feedback` | 200, array |
| 17 | Send message | POST | `/api/admin/messaging/send` | 200 or 422 (no provider configured is OK) |
| 18 | Message log | GET | `/api/admin/messaging/log` | 200, array |
| 19 | Public feature flags | GET | `/api/flags` | 200, array |
| 20 | CORS headers | OPTIONS | `/api/health` | Access-Control-Allow-Origin present |
| 21 | Rate limit headers | GET | `/api/health` | X-RateLimit-* headers present |
| 22 | Error format (404) | GET | `/api/nonexistent` | 404, RFC 9457 Problem Details shape |
| 23 | Dashboard API | GET | dashboard `/api/health` | 200 |
| 24 | Logout | POST | `/api/auth/logout` | 200 |
| 25 | Token invalid after logout | GET | `/api/auth/me` | 401 |

## ensure-permissions.py

Direct port of `ensure-permissions.sh` — reads the SKILL.md frontmatter, extracts `allowed-tools`, and updates `~/.claude/settings.json` to whitelist them. Idempotent, silent on success.

## SKILL.md Changes

Add to routing table:

```
| `test` or `test smoke`         | Go to **Test Smoke** |
| `test validate`                | Go to **Test Validate** |
```

Add Test section that:
1. Reads `site-manifest.json` for URLs (or accepts CLI overrides)
2. Prompts for admin credentials if running validate suite
3. Runs `python3 ${CLAUDE_SKILL_DIR}/references/smoke-test.py <suite> <args>`
4. Reports results

Update Startup to call `python3 ... ensure-permissions.py` instead of `bash ... ensure-permissions.sh`.

## End-to-End Test Plan

1. Scaffold to `/tmp/sm-smoke-test-deleteme/` using init flow
2. Create Railway project + PostgreSQL addon
3. Deploy backend to Railway
4. Run DB migrations + seed admin
5. Deploy 3 CF Worker sites (main, admin, dashboard)
6. Update manifest with real URLs
7. Run smoke tests
8. Run validation tests
9. Fix any template issues found
10. Tear down: delete Railway project, CF workers, `/tmp/` directory
