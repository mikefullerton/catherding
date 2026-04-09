"""End-to-end browser verification using Playwright.

Launches a real browser, navigates deployed sites, verifies content,
clicks through key flows, and takes screenshots.
"""

import json
import sys
from pathlib import Path

from site_manager.check import CheckRecorder


SUITE = "e2e"


def count_checks(manifest: dict) -> int:
    """Return the number of checks that will be run for this manifest."""
    domain = manifest.get("project", {}).get("domain", "")
    backend_url = (manifest.get("services", {}).get("backend") or {}).get("url", "")
    total = 0
    for name in ("main", "admin", "dashboard"):
        if domain:
            total += 4  # loads, screenshot, title, display name
            if name in ("main", "admin"):
                total += 2  # login page, login form
    if backend_url:
        total += 1
    return total


class E2ERunner:
    def __init__(self, manifest: dict, recorder: CheckRecorder,
                 screenshot_dir: str = "/tmp/site-manager-e2e"):
        self.manifest = manifest
        self.rec = recorder
        self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

        project = manifest.get("project", {})
        self.display_name = project.get("displayName", "")
        self.domain = project.get("domain", "")

        self.backend_url = (manifest.get("services", {}).get("backend") or {}).get("url", "").rstrip("/")
        self.main_url = f"https://{self.domain}" if self.domain else ""
        self.admin_url = f"https://admin.{self.domain}" if self.domain else ""
        self.dashboard_url = f"https://dashboard.{self.domain}" if self.domain else ""

    def run(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print("error: playwright not installed", file=sys.stderr)
            print("Run: pip install playwright && python -m playwright install chromium", file=sys.stderr)
            sys.exit(1)

        self.rec.section("E2E Browser Verification")
        print(f"  Screenshots: {self.screenshot_dir}")

        sites = []
        if self.main_url:
            sites.append(("main", self.main_url))
        if self.admin_url:
            sites.append(("admin", self.admin_url))
        if self.dashboard_url:
            sites.append(("dashboard", self.dashboard_url))

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                ignore_https_errors=True,
            )

            for site_name, url in sites:
                page = context.new_page()
                self._check_site(page, site_name, url)
                page.close()

            if self.backend_url:
                page = context.new_page()
                self._check_api_via_browser(page)
                page.close()

            browser.close()

    def _check_site(self, page, site_name: str, url: str):
        try:
            response = page.goto(url, wait_until="networkidle", timeout=30000)
            loaded = response is not None and response.status == 200
        except Exception as e:
            self.rec.record(f"{site_name}: loads", False, detail=str(e), suite=SUITE)
            self.rec.skip(f"{site_name}: screenshot", "Site did not load", suite=SUITE)
            self.rec.skip(f"{site_name}: has page title", "Site did not load", suite=SUITE)
            self.rec.skip(f"{site_name}: display name in content", "Site did not load", suite=SUITE)
            if site_name in ("main", "admin"):
                self.rec.skip(f"{site_name}: login page reachable", "Site did not load", suite=SUITE)
                self.rec.skip(f"{site_name}: login form has inputs", "Site did not load", suite=SUITE)
            return

        self.rec.record(f"{site_name}: loads", loaded, suite=SUITE,
                        detail="" if loaded else f"Expected 200, got {response.status if response else 'no response'}")

        if not loaded:
            self.rec.skip(f"{site_name}: screenshot", "Site did not load with 200", suite=SUITE)
            self.rec.skip(f"{site_name}: has page title", "Site did not load with 200", suite=SUITE)
            self.rec.skip(f"{site_name}: display name in content", "Site did not load with 200", suite=SUITE)
            if site_name in ("main", "admin"):
                self.rec.skip(f"{site_name}: login page reachable", "Site did not load with 200", suite=SUITE)
                self.rec.skip(f"{site_name}: login form has inputs", "Site did not load with 200", suite=SUITE)
            return

        screenshot_path = self.screenshot_dir / f"{site_name}.png"
        try:
            page.screenshot(path=str(screenshot_path), full_page=True)
            self.rec.record(f"{site_name}: screenshot", True, suite=SUITE)
        except Exception as e:
            self.rec.record(f"{site_name}: screenshot", False, detail=str(e), suite=SUITE)

        title = page.title()
        has_title = bool(title and title.strip())
        self.rec.record(f"{site_name}: has page title", has_title, suite=SUITE,
                        detail="" if has_title else "Page title is empty")

        if self.display_name:
            content = page.content()
            body_text = page.locator("body").inner_text()
            found = self.display_name in content or self.display_name in body_text
            self.rec.record(f"{site_name}: display name in content", found, suite=SUITE,
                            detail="" if found else f'"{self.display_name}" not found in page HTML or visible text')
        else:
            self.rec.skip(f"{site_name}: display name in content", "No displayName in manifest", suite=SUITE)

        if site_name in ("main", "admin"):
            self._check_login_page(page, site_name, url)

    def _check_login_page(self, page, site_name: str, base_url: str):
        login_url = f"{base_url.rstrip('/')}/login"
        try:
            response = page.goto(login_url, wait_until="networkidle", timeout=15000)
            loaded = response is not None and response.status == 200
        except Exception:
            loaded = False

        if not loaded:
            page.goto(base_url, wait_until="networkidle", timeout=15000)
            login_link = page.locator('a:has-text("Login"), a:has-text("Sign in"), a:has-text("Log in"), button:has-text("Login"), button:has-text("Sign in")')
            if login_link.count() > 0:
                login_link.first.click()
                page.wait_for_load_state("networkidle")
                loaded = True

        self.rec.record(f"{site_name}: login page reachable", loaded, suite=SUITE,
                        detail="" if loaded else f"Could not reach login page at {login_url} or via link")

        if not loaded:
            self.rec.skip(f"{site_name}: login form has inputs", "Login page not reachable", suite=SUITE)
            return

        screenshot_path = self.screenshot_dir / f"{site_name}-login.png"
        page.screenshot(path=str(screenshot_path))

        email_input = page.locator('input[type="email"], input[name="email"], input[placeholder*="email" i]')
        password_input = page.locator('input[type="password"]')
        has_form = email_input.count() > 0 and password_input.count() > 0
        self.rec.record(f"{site_name}: login form has inputs", has_form, suite=SUITE,
                        detail="" if has_form else "Could not find email and password input fields")

    def _check_api_via_browser(self, page):
        url = f"{self.backend_url}/api/health"
        try:
            response = page.goto(url, wait_until="networkidle", timeout=10000)
            if response and response.status == 200:
                body = page.locator("body").inner_text()
                try:
                    data = json.loads(body)
                    ok = data.get("status") == "ok"
                except (json.JSONDecodeError, ValueError):
                    ok = False
            else:
                ok = False
            self.rec.record("backend: API health via browser", ok, suite=SUITE,
                            detail="" if ok else f"Expected 200 {{status:ok}} at {url}")
        except Exception as e:
            self.rec.record("backend: API health via browser", False, detail=str(e), suite=SUITE)


def run_e2e(output_json: bool = False) -> None:
    p = Path("site-manifest.json")
    if not p.exists():
        print("error: no site-manifest.json found", file=sys.stderr)
        sys.exit(1)

    manifest = json.loads(p.read_text())
    project = manifest.get("project", {})
    total = count_checks(manifest)
    rec = CheckRecorder(total)

    print(f"\n=== E2E BROWSER VERIFICATION ===")
    print(f"Project: {project.get('name', '?')} ({project.get('domain', '?')})")

    runner = E2ERunner(manifest, rec)
    runner.run()

    if output_json:
        print(rec.to_json())
    else:
        rec.summary()
    sys.exit(0 if rec.summary() else 1)
