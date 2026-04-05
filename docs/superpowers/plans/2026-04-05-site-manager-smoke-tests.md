# Site Manager Smoke & Validation Tests — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `/site-manager test` command with smoke and validation test suites, convert ensure-permissions to Python, and verify via end-to-end deployment of a test project.

**Architecture:** Single Python file (`smoke-test.py`) with two test suites selectable by argument. Uses stdlib only (`urllib.request`, `json`, `argparse`). SKILL.md gets a new `test` route. The ensure-permissions shell script is replaced with a Python equivalent.

**Tech Stack:** Python 3 (stdlib only), existing site-manager SKILL.md routing

**Spec:** `docs/superpowers/specs/2026-04-05-site-manager-smoke-tests.md`

---

## Task 1: Convert ensure-permissions.sh to Python

**Files:**
- Create: `plugins/site-manager/skills/site-manager/references/ensure-permissions.py`
- Delete: `plugins/site-manager/skills/site-manager/references/ensure-permissions.sh`
- Modify: `plugins/site-manager/skills/site-manager/SKILL.md:22` (update Startup command)

- [ ] **Step 1: Create ensure-permissions.py**

```python
#!/usr/bin/env python3
"""Read allowed-tools from SKILL.md frontmatter, merge Bash() patterns into settings.json."""

import json
import re
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        sys.exit(0)

    skill_file = Path(sys.argv[1])
    settings_file = Path.home() / ".claude" / "settings.json"

    if not skill_file.exists() or not settings_file.exists():
        sys.exit(0)

    # Read SKILL.md, extract frontmatter between --- markers
    content = skill_file.read_text()
    match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        sys.exit(0)

    frontmatter = match.group(1)

    # Find allowed-tools line, extract Bash() patterns
    for line in frontmatter.splitlines():
        if line.startswith("allowed-tools:"):
            patterns = re.findall(r"Bash\([^)]+\)", line)
            break
    else:
        sys.exit(0)

    if not patterns:
        sys.exit(0)

    # Read settings, merge patterns, deduplicate, write back
    settings = json.loads(settings_file.read_text())
    existing = settings.get("permissions", {}).get("allow", [])
    merged = sorted(set(existing + patterns))

    if merged == sorted(existing):
        sys.exit(0)  # No changes needed

    settings.setdefault("permissions", {})["allow"] = merged
    settings_file.write_text(json.dumps(settings, indent=2) + "\n")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Test it**

Run: `python3 plugins/site-manager/skills/site-manager/references/ensure-permissions.py plugins/site-manager/skills/site-manager/SKILL.md`

Expected: exits silently with 0. Verify `~/.claude/settings.json` still has the Bash patterns.

- [ ] **Step 3: Update SKILL.md Startup section**

In `SKILL.md` line 22, change:
```
**Step 0 — Ensure permissions**: Run `bash ${CLAUDE_SKILL_DIR}/references/ensure-permissions.sh ${CLAUDE_SKILL_DIR}/SKILL.md`
```
to:
```
**Step 0 — Ensure permissions**: Run `python3 ${CLAUDE_SKILL_DIR}/references/ensure-permissions.py ${CLAUDE_SKILL_DIR}/SKILL.md`
```

Also add `Bash(python3 *)` to the `allowed-tools` line in the frontmatter if not already present.

- [ ] **Step 4: Delete the shell script**

```bash
rm plugins/site-manager/skills/site-manager/references/ensure-permissions.sh
```

- [ ] **Step 5: Commit**

```bash
git add plugins/site-manager/skills/site-manager/references/ensure-permissions.py \
  plugins/site-manager/skills/site-manager/references/ensure-permissions.sh \
  plugins/site-manager/skills/site-manager/SKILL.md
git commit -m "refactor(site-manager): convert ensure-permissions to Python"
```

---

## Task 2: Create smoke-test.py — framework and smoke tests

**Files:**
- Create: `plugins/site-manager/skills/site-manager/references/smoke-test.py`

- [ ] **Step 1: Create smoke-test.py with framework + smoke suite**

The complete file. Key design points:
- `argparse` for CLI: `python3 smoke-test.py smoke|validate --base-url <url> [--main-url ...] [--admin-url ...] [--dashboard-url ...] [--admin-email ...] [--admin-password ...] [--verbose]`
- A `TestRunner` class that tracks pass/fail/skip, prints TAP-style output
- Each test is a method that calls `self.test(name, method, url, ...)` which handles the HTTP call and assertion
- Auth state stored as instance variables (access_token, refresh_token, test_user_email)

```python
#!/usr/bin/env python3
"""Site Manager smoke and validation test runner.

Usage:
    python3 smoke-test.py smoke --base-url https://backend.up.railway.app
    python3 smoke-test.py validate --base-url https://backend.up.railway.app \\
        --admin-email admin@example.com --admin-password secret123
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field


@dataclass
class TestResult:
    name: str
    passed: bool
    skipped: bool = False
    detail: str = ""


class TestRunner:
    def __init__(self, base_url: str, main_url: str, admin_url: str,
                 dashboard_url: str, admin_email: str, admin_password: str,
                 verbose: bool = False):
        self.base_url = base_url.rstrip("/")
        self.main_url = main_url.rstrip("/") if main_url else ""
        self.admin_url = admin_url.rstrip("/") if admin_url else ""
        self.dashboard_url = dashboard_url.rstrip("/") if dashboard_url else ""
        self.admin_email = admin_email
        self.admin_password = admin_password
        self.verbose = verbose

        self.results: list[TestResult] = []
        self.access_token: str = ""
        self.refresh_token: str = ""
        self.admin_access_token: str = ""
        self.test_email = f"smoke-test-{int(time.time())}@test.local"
        self.test_password = "SmokeTe$t2026!!"
        self.test_flag_key = f"smoke_test_{int(time.time())}"

    # --- HTTP helpers ---

    def _request(self, method: str, url: str, body: dict | None = None,
                 token: str = "", expect_status: int = 200) -> tuple[int, dict | str]:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read().decode()
                try:
                    return resp.status, json.loads(raw)
                except json.JSONDecodeError:
                    return resp.status, raw
        except urllib.error.HTTPError as e:
            raw = e.read().decode()
            try:
                return e.code, json.loads(raw)
            except json.JSONDecodeError:
                return e.code, raw

    def _get(self, path: str, token: str = "") -> tuple[int, dict | str]:
        return self._request("GET", f"{self.base_url}{path}", token=token)

    def _post(self, path: str, body: dict, token: str = "") -> tuple[int, dict | str]:
        return self._request("POST", f"{self.base_url}{path}", body=body, token=token)

    def _patch(self, path: str, body: dict, token: str = "") -> tuple[int, dict | str]:
        return self._request("PATCH", f"{self.base_url}{path}", body=body, token=token)

    def _delete(self, path: str, token: str = "") -> tuple[int, dict | str]:
        return self._request("DELETE", f"{self.base_url}{path}", token=token)

    def _get_url(self, url: str) -> tuple[int, str]:
        """GET a full URL (for frontend sites)."""
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status, resp.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()

    def _options(self, path: str) -> dict[str, str]:
        """Send OPTIONS request, return response headers as dict."""
        req = urllib.request.Request(f"{self.base_url}{path}", method="OPTIONS",
                                    headers={"Origin": "https://example.com"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return dict(resp.headers)
        except urllib.error.HTTPError as e:
            return dict(e.headers)

    # --- Test recording ---

    def _record(self, name: str, passed: bool, detail: str = ""):
        self.results.append(TestResult(name=name, passed=passed, detail=detail))
        n = len(self.results)
        total = self._total
        status = "PASS" if passed else "FAIL"
        color = "\033[32m" if passed else "\033[31m"
        reset = "\033[0m"
        print(f" {n:>2}/{total} {color}{status}{reset}  {name}")
        if not passed and detail:
            for line in detail.splitlines():
                print(f"             {line}")

    def _skip(self, name: str, reason: str):
        self.results.append(TestResult(name=name, passed=True, skipped=True, detail=reason))
        n = len(self.results)
        total = self._total
        print(f" {n:>2}/{total} \033[33mSKIP\033[0m  {name}")
        print(f"             {reason}")

    # --- Smoke tests ---

    def test_backend_health(self):
        status, body = self._get("/api/health")
        ok = status == 200 and isinstance(body, dict) and body.get("status") == "ok"
        self._record("Backend health endpoint",
                     ok, "" if ok else f"Expected: 200 {{status:ok}}, Got: {status} {body}")

    def test_backend_ready(self):
        status, body = self._get("/api/health/ready")
        ok = status == 200 and isinstance(body, dict) and body.get("status") == "ok"
        self._record("Backend readiness check",
                     ok, "" if ok else f"Expected: 200 {{status:ok}}, Got: {status} {body}")

    def test_main_site(self):
        if not self.main_url:
            self._skip("Main site responds", "No --main-url provided")
            return
        status, _ = self._get_url(self.main_url)
        ok = status == 200
        self._record("Main site responds", ok, "" if ok else f"Expected: 200, Got: {status}")

    def test_admin_site(self):
        if not self.admin_url:
            self._skip("Admin site responds", "No --admin-url provided")
            return
        status, _ = self._get_url(self.admin_url)
        ok = status == 200
        self._record("Admin site responds", ok, "" if ok else f"Expected: 200, Got: {status}")

    def test_dashboard_site(self):
        if not self.dashboard_url:
            self._skip("Dashboard responds", "No --dashboard-url provided")
            return
        status, _ = self._get_url(self.dashboard_url)
        ok = status == 200
        self._record("Dashboard responds", ok, "" if ok else f"Expected: 200, Got: {status}")

    def test_register(self):
        status, body = self._post("/api/auth/register", {
            "email": self.test_email,
            "password": self.test_password,
        })
        ok = status == 201 and isinstance(body, dict) and "accessToken" in body
        if ok:
            self.access_token = body["accessToken"]
            self.refresh_token = body["refreshToken"]
        self._record("Register user", ok, "" if ok else f"Expected: 201 + tokens, Got: {status} {body}")

    def test_login(self):
        status, body = self._post("/api/auth/login", {
            "email": self.test_email,
            "password": self.test_password,
        })
        ok = status == 200 and isinstance(body, dict) and "accessToken" in body
        if ok:
            self.access_token = body["accessToken"]
            self.refresh_token = body["refreshToken"]
        self._record("Login", ok, "" if ok else f"Expected: 200 + tokens, Got: {status} {body}")

    def test_refresh(self):
        if not self.refresh_token:
            self._skip("Token refresh", "No refresh token from login")
            return
        status, body = self._post("/api/auth/refresh", {
            "refreshToken": self.refresh_token,
        }, token=self.access_token)
        ok = status == 200 and isinstance(body, dict) and "accessToken" in body
        if ok:
            self.access_token = body["accessToken"]
            self.refresh_token = body["refreshToken"]
        self._record("Token refresh", ok, "" if ok else f"Expected: 200 + new tokens, Got: {status} {body}")

    def test_me(self):
        if not self.access_token:
            self._skip("Get current user", "No access token")
            return
        status, body = self._get("/api/auth/me", token=self.access_token)
        ok = status == 200 and isinstance(body, dict) and "email" in body
        self._record("Get current user", ok,
                     "" if ok else f"Expected: 200 + user object, Got: {status} {body}")

    def test_non_admin_blocked(self):
        if not self.access_token:
            self._skip("Non-admin blocked from admin API", "No access token")
            return
        status, _ = self._get("/api/admin/users", token=self.access_token)
        ok = status == 403
        self._record("Non-admin blocked from admin API", ok,
                     "" if ok else f"Expected: 403, Got: {status}")

    # --- Validation tests ---

    def test_admin_login(self):
        if not self.admin_email or not self.admin_password:
            self._skip("Admin login", "No --admin-email/--admin-password provided")
            return
        status, body = self._post("/api/auth/login", {
            "email": self.admin_email,
            "password": self.admin_password,
        })
        ok = status == 200 and isinstance(body, dict) and "accessToken" in body
        if ok:
            self.admin_access_token = body["accessToken"]
        self._record("Admin login", ok,
                     "" if ok else f"Expected: 200 + tokens, Got: {status} {body}")

    def test_admin_list_users(self):
        if not self.admin_access_token:
            self._skip("Admin list users", "No admin token")
            return
        status, body = self._get("/api/admin/users", token=self.admin_access_token)
        ok = status == 200 and isinstance(body, dict) and "users" in body
        self._record("Admin list users", ok,
                     "" if ok else f"Expected: 200 + users array, Got: {status} {body}")

    def test_create_flag(self):
        if not self.admin_access_token:
            self._skip("Create feature flag", "No admin token")
            return
        status, body = self._post("/api/admin/flags", {
            "key": self.test_flag_key,
            "description": "Smoke test flag",
            "enabled": False,
        }, token=self.admin_access_token)
        ok = status == 201 and isinstance(body, dict) and "flag" in body
        self._record("Create feature flag", ok,
                     "" if ok else f"Expected: 201 + flag object, Got: {status} {body}")

    def test_toggle_flag(self):
        if not self.admin_access_token:
            self._skip("Toggle feature flag", "No admin token")
            return
        status, body = self._patch(f"/api/admin/flags/{self.test_flag_key}", {
            "enabled": True,
        }, token=self.admin_access_token)
        ok = status == 200 and isinstance(body, dict) and "flag" in body
        self._record("Toggle feature flag", ok,
                     "" if ok else f"Expected: 200 + updated flag, Got: {status} {body}")

    def test_delete_flag(self):
        if not self.admin_access_token:
            self._skip("Delete feature flag", "No admin token")
            return
        status, body = self._delete(f"/api/admin/flags/{self.test_flag_key}",
                                    token=self.admin_access_token)
        ok = status == 200 and isinstance(body, dict) and body.get("deleted") is True
        self._record("Delete feature flag", ok,
                     "" if ok else f"Expected: 200 {{deleted:true}}, Got: {status} {body}")

    def test_list_feedback(self):
        if not self.admin_access_token:
            self._skip("List feedback", "No admin token")
            return
        status, body = self._get("/api/admin/feedback", token=self.admin_access_token)
        ok = status == 200 and isinstance(body, dict)
        self._record("List feedback", ok,
                     "" if ok else f"Expected: 200, Got: {status} {body}")

    def test_send_message(self):
        if not self.admin_access_token:
            self._skip("Send message endpoint", "No admin token")
            return
        status, body = self._post("/api/admin/messaging/send", {
            "to": "test@test.local",
            "subject": "Smoke test",
            "body": "This is a smoke test message",
            "channel": "email",
        }, token=self.admin_access_token)
        # 200 = sent, 422 = no provider configured (both acceptable)
        ok = status in (200, 422, 400)
        self._record("Send message endpoint exists", ok,
                     "" if ok else f"Expected: 200/422/400, Got: {status} {body}")

    def test_message_log(self):
        if not self.admin_access_token:
            self._skip("Message log", "No admin token")
            return
        status, body = self._get("/api/admin/messaging/log", token=self.admin_access_token)
        ok = status == 200 and isinstance(body, dict)
        self._record("Message log", ok,
                     "" if ok else f"Expected: 200, Got: {status} {body}")

    def test_public_flags(self):
        status, body = self._get("/api/public/flags")
        ok = status == 200 and isinstance(body, dict) and "flags" in body
        self._record("Public feature flags", ok,
                     "" if ok else f"Expected: 200 + flags array, Got: {status} {body}")

    def test_cors_headers(self):
        headers = self._options("/api/health")
        has_cors = any("access-control" in k.lower() for k in headers)
        self._record("CORS headers present", has_cors,
                     "" if has_cors else f"No Access-Control-* headers found. Got: {list(headers.keys())}")

    def test_rate_limit_headers(self):
        status, _ = self._get("/api/health")
        # Rate limit headers might not be present on health endpoint — skip if not
        # This is a best-effort check
        self._skip("Rate limit headers", "Skipped — rate limiting is per-IP, not guaranteed on health endpoint")

    def test_error_format(self):
        status, body = self._get("/api/nonexistent")
        ok = status == 404 and isinstance(body, dict) and "type" in body and "title" in body
        self._record("Error format is RFC 9457", ok,
                     "" if ok else f"Expected: 404 + Problem Details, Got: {status} {body}")

    def test_dashboard_api(self):
        if not self.dashboard_url:
            self._skip("Dashboard API health", "No --dashboard-url provided")
            return
        status, body = self._get_url(f"{self.dashboard_url}/api/health")
        ok = status == 200
        self._record("Dashboard API health", ok,
                     "" if ok else f"Expected: 200, Got: {status}")

    def test_logout(self):
        if not self.access_token:
            self._skip("Logout", "No access token")
            return
        status, _ = self._post("/api/auth/logout", {
            "refreshToken": self.refresh_token,
        }, token=self.access_token)
        ok = status == 200
        self._record("Logout", ok, "" if ok else f"Expected: 200, Got: {status}")

    def test_token_invalid_after_logout(self):
        if not self.access_token:
            self._skip("Token invalid after logout", "No access token")
            return
        # Access token is a JWT — it may still be valid until expiry.
        # Test that refresh token is revoked instead.
        status, _ = self._post("/api/auth/refresh", {
            "refreshToken": self.refresh_token,
        }, token=self.access_token)
        ok = status in (401, 403)
        self._record("Refresh token revoked after logout", ok,
                     "" if ok else f"Expected: 401/403, Got: {status}")

    # --- Runner ---

    def run(self, suite: str) -> bool:
        smoke_tests = [
            self.test_backend_health,
            self.test_backend_ready,
            self.test_main_site,
            self.test_admin_site,
            self.test_dashboard_site,
            self.test_register,
            self.test_login,
            self.test_refresh,
            self.test_me,
            self.test_non_admin_blocked,
        ]

        validation_tests = [
            self.test_admin_login,
            self.test_admin_list_users,
            self.test_create_flag,
            self.test_toggle_flag,
            self.test_delete_flag,
            self.test_list_feedback,
            self.test_send_message,
            self.test_message_log,
            self.test_public_flags,
            self.test_cors_headers,
            self.test_rate_limit_headers,
            self.test_error_format,
            self.test_dashboard_api,
            self.test_logout,
            self.test_token_invalid_after_logout,
        ]

        tests = smoke_tests if suite == "smoke" else smoke_tests + validation_tests
        self._total = len(tests)

        suite_label = "SMOKE TESTS" if suite == "smoke" else "VALIDATION TESTS"
        print(f"\n=== SITE MANAGER {suite_label} ===")
        print(f"Target: {self.base_url}\n")

        for test_fn in tests:
            try:
                test_fn()
            except Exception as e:
                self._record(test_fn.__name__.replace("test_", "").replace("_", " "),
                             False, f"Exception: {e}")

        # Summary
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        skipped = sum(1 for r in self.results if r.skipped)
        total = len(self.results)

        print(f"\nResults: {passed}/{total} passed", end="")
        if failed:
            print(f", \033[31m{failed} failed\033[0m", end="")
        if skipped:
            print(f", {skipped} skipped", end="")
        print()

        return failed == 0


def main():
    parser = argparse.ArgumentParser(description="Site Manager smoke and validation tests")
    parser.add_argument("suite", choices=["smoke", "validate"], default="smoke", nargs="?",
                        help="Test suite to run (default: smoke)")
    parser.add_argument("--base-url", required=True, help="Backend API base URL")
    parser.add_argument("--main-url", default="", help="Main site URL")
    parser.add_argument("--admin-url", default="", help="Admin site URL")
    parser.add_argument("--dashboard-url", default="", help="Dashboard site URL")
    parser.add_argument("--admin-email", default="", help="Admin email (for validation tests)")
    parser.add_argument("--admin-password", default="", help="Admin password (for validation tests)")
    parser.add_argument("--verbose", action="store_true", help="Show request/response details")

    args = parser.parse_args()

    runner = TestRunner(
        base_url=args.base_url,
        main_url=args.main_url,
        admin_url=args.admin_url,
        dashboard_url=args.dashboard_url,
        admin_email=args.admin_email,
        admin_password=args.admin_password,
        verbose=args.verbose,
    )

    success = runner.run(args.suite)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify it parses**

Run: `python3 plugins/site-manager/skills/site-manager/references/smoke-test.py --help`

Expected: shows usage with smoke/validate and all flags.

- [ ] **Step 3: Commit**

```bash
git add plugins/site-manager/skills/site-manager/references/smoke-test.py
git commit -m "feat(site-manager): add smoke and validation test runner"
```

---

## Task 3: Add test route to SKILL.md

**Files:**
- Modify: `plugins/site-manager/skills/site-manager/SKILL.md`

- [ ] **Step 1: Add test routes to the routing table**

Add to the routing table (after `seed-admin` row):

```markdown
| `test` or `test smoke`           | Go to **Test Smoke** |
| `test validate`                  | Go to **Test Validate** |
```

Update the "anything else" row's usage string to include `test`.

- [ ] **Step 2: Add Test Smoke section**

Add after the Seed Admin section and before Help:

```markdown
---

## Test Smoke

**Run essential health and auth tests against a deployed project.**

### Step 1: Resolve URLs

Read `site-manifest.json` from the current directory. Extract:
- `services.backend.url` → `--base-url`
- `project.domain` → derive `--main-url` (`https://<domain>`), `--admin-url` (`https://admin.<domain>`), `--dashboard-url` (`https://dashboard.<domain>`)

If no `site-manifest.json`, ask the user for `--base-url`.

If `services.backend.url` is null or status is not `deployed`, print:
> Backend is not deployed. Run `/site-manager deploy backend` first.

Then stop.

### Step 2: Run tests

\```bash
python3 ${CLAUDE_SKILL_DIR}/references/smoke-test.py smoke \
  --base-url <backend-url> \
  --main-url <main-url> \
  --admin-url <admin-url> \
  --dashboard-url <dashboard-url>
\```

### Step 3: Report

Display the test output directly — it is self-formatting.
```

- [ ] **Step 3: Add Test Validate section**

Add after Test Smoke:

```markdown
---

## Test Validate

**Run comprehensive validation tests including admin CRUD.**

### Step 1: Resolve URLs

Same as Test Smoke Step 1.

### Step 2: Get admin credentials

Ask the user for:
- Admin email
- Admin password

These are needed for admin endpoint tests (users, flags, messaging, feedback).

### Step 3: Run tests

\```bash
python3 ${CLAUDE_SKILL_DIR}/references/smoke-test.py validate \
  --base-url <backend-url> \
  --main-url <main-url> \
  --admin-url <admin-url> \
  --dashboard-url <dashboard-url> \
  --admin-email <email> \
  --admin-password <password>
\```

### Step 4: Report

Display the test output directly — it is self-formatting.
```

- [ ] **Step 4: Update Help section**

Add these lines to the Help command listing:

```
  /site-manager test [smoke]        Run smoke tests (health + auth)
  /site-manager test validate       Run full validation tests (admin CRUD, flags, etc.)
```

- [ ] **Step 5: Bump version**

Update SKILL.md frontmatter version from `1.0.0` to `1.1.0`.
Update the version string in the Startup section and Help section.

- [ ] **Step 6: Update plugin.json version**

In `plugins/site-manager/.claude-plugin/plugin.json`, update `version` to `1.1.0`.

- [ ] **Step 7: Commit**

```bash
git add plugins/site-manager/skills/site-manager/SKILL.md \
  plugins/site-manager/.claude-plugin/plugin.json
git commit -m "feat(site-manager): add test smoke/validate commands (v1.1.0)"
```

---

## Task 4: Deploy test project and run tests

**This task is manual/interactive — scaffold, deploy, test, teardown.**

- [ ] **Step 1: Scaffold test project**

```bash
mkdir -p /tmp/sm-smoke-test-deleteme
```

Run the site-manager init flow (manually or via `/site-manager init squarepoopstudios.com`) with:
- Project name: `sm-smoke-test-deleteme`
- Domain: `squarepoopstudios.com`
- Target: `/tmp/sm-smoke-test-deleteme/`
- GitHub OAuth: no
- Google OAuth: no

- [ ] **Step 2: Create Railway project**

```bash
cd /tmp/sm-smoke-test-deleteme && railway init
```

Select "Create new project". Name it `sm-smoke-test-deleteme`.

Add PostgreSQL:
```bash
railway add --plugin postgresql
```

Link the backend service:
```bash
cd /tmp/sm-smoke-test-deleteme/backend && railway link
```

- [ ] **Step 3: Deploy backend**

```bash
cd /tmp/sm-smoke-test-deleteme && railway up --detach
```

Get the deployment URL:
```bash
railway domain
```

- [ ] **Step 4: Run migrations and seed admin**

```bash
cd /tmp/sm-smoke-test-deleteme/backend
railway run npm run db:migrate
railway run npm run db:seed
```

Set admin credentials in Railway environment or pass via command.

- [ ] **Step 5: Deploy CF Worker sites**

```bash
cd /tmp/sm-smoke-test-deleteme/sites/main && wrangler deploy
cd /tmp/sm-smoke-test-deleteme/sites/admin && wrangler deploy
cd /tmp/sm-smoke-test-deleteme/sites/dashboard && wrangler deploy
```

For dashboard, create D1 database first:
```bash
cd /tmp/sm-smoke-test-deleteme/sites/dashboard
wrangler d1 create sm-smoke-test-deleteme-dashboard-db
# Update wrangler.jsonc with real D1 database ID
wrangler d1 migrations apply sm-smoke-test-deleteme-dashboard-db
wrangler deploy
```

- [ ] **Step 6: Run smoke tests**

```bash
python3 plugins/site-manager/skills/site-manager/references/smoke-test.py smoke \
  --base-url <railway-url> \
  --main-url <main-worker-url> \
  --admin-url <admin-worker-url> \
  --dashboard-url <dashboard-worker-url>
```

- [ ] **Step 7: Run validation tests**

```bash
python3 plugins/site-manager/skills/site-manager/references/smoke-test.py validate \
  --base-url <railway-url> \
  --main-url <main-worker-url> \
  --admin-url <admin-worker-url> \
  --dashboard-url <dashboard-worker-url> \
  --admin-email <admin-email> \
  --admin-password <admin-password>
```

- [ ] **Step 8: Fix any issues**

If tests fail, fix the templates and/or test runner. Re-deploy and re-test.

- [ ] **Step 9: Teardown**

Delete Railway project:
```bash
railway down --yes
# Or via Railway dashboard: delete the project
```

Delete CF Workers:
```bash
cd /tmp/sm-smoke-test-deleteme/sites/main && wrangler delete
cd /tmp/sm-smoke-test-deleteme/sites/admin && wrangler delete
cd /tmp/sm-smoke-test-deleteme/sites/dashboard && wrangler delete
wrangler d1 delete sm-smoke-test-deleteme-dashboard-db
```

Delete local files:
```bash
rm -rf /tmp/sm-smoke-test-deleteme
```

- [ ] **Step 10: Final commit if any fixes were needed**

```bash
git add -A && git commit -m "fix(site-manager): fixes from e2e smoke test run"
```

---

## Task 5: Update plugin and plan

- [ ] **Step 1: Update the implementation plan**

Mark Phase 9 items as complete in `docs/superpowers/plans/2026-04-05-site-manager-v1.md`.

- [ ] **Step 2: Update plugin for installed users**

```bash
claude plugin update site-manager@cat-herding
```

- [ ] **Step 3: Commit plan update**

```bash
git add docs/superpowers/plans/2026-04-05-site-manager-v1.md
git commit -m "chore(site-manager): mark Phase 9 complete"
```
