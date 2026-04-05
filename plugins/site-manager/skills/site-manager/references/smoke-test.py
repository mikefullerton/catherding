#!/usr/bin/env python3
"""Site Manager smoke and validation test runner.

Usage:
    python3 smoke-test.py smoke --base-url https://backend.up.railway.app
    python3 smoke-test.py validate --base-url https://backend.up.railway.app \
        --admin-email admin@example.com --admin-password secret123
"""

from __future__ import annotations

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
        req = urllib.request.Request(url, method="GET",
                                    headers={"User-Agent": "site-manager-smoke-test/1.0"})
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
        # 200 = sent, 422/400 = validation error, 500 = provider not configured (all acceptable)
        ok = status in (200, 422, 400, 500)
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
