# Configurator Web Editor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the terminal Q&A flow with a local web form that shows all config options at once, saves on every change, and disables irrelevant fields.

**Architecture:** New `web.py` module using Python stdlib `http.server`. HTML/CSS/JS embedded as a string constant. The CLI calls `serve_editor(name, cfg)` by default, with `--tui` flag for the old terminal flow.

**Tech Stack:** Python stdlib only — `http.server`, `json`, `webbrowser`, `socketserver`

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `src/configurator/web.py` | Create | HTTP server + embedded HTML form |
| `src/configurator/cli.py` | Modify | Add `--tui` flag, call `serve_editor()` from `cmd_configure()` |
| `src/configurator/__init__.py` | Modify | Version bump |
| `tests/test_web.py` | Create | Tests for server request handling and config serialization |

---

### Task 1: Create web.py with HTML template and config-to-form serialization

**Files:**
- Create: `src/configurator/web.py`
- Test: `tests/test_web.py`

This task builds the HTML form template and the function that serializes a config dict into the page. The server is wired up in Task 2.

- [ ] **Step 1: Write the failing test for config embedding**

In `tests/test_web.py`:

```python
"""Tests for the web editor module."""

import json

from configurator.web import build_page


class TestBuildPage:
    def test_embeds_config_as_json(self):
        cfg = {"repo": "my-project", "domain": "example.com"}
        html = build_page(cfg, deployed_keys=set())
        assert "my-project" in html
        assert "example.com" in html

    def test_embeds_deployed_keys(self):
        cfg = {"repo": "test", "backend": {"enabled": True}}
        html = build_page(cfg, deployed_keys={"backend"})
        assert '"backend"' in html

    def test_returns_valid_html(self):
        html = build_page({}, deployed_keys=set())
        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html

    def test_config_is_parseable_json_in_script(self):
        cfg = {"repo": "test", "domain": "test.com", "website": {"type": "existing"}}
        html = build_page(cfg, deployed_keys=set())
        # Extract the JSON from the script tag
        start = html.index("const CONFIG = ") + len("const CONFIG = ")
        end = html.index(";", start)
        parsed = json.loads(html[start:end])
        assert parsed["repo"] == "test"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/configurator/configurator-cli && uv run --extra test pytest tests/test_web.py -v`
Expected: FAIL with "No module named 'configurator.web'"

- [ ] **Step 3: Write build_page and HTML template**

Create `src/configurator/web.py`:

```python
"""Local web editor for configurator configs."""

from __future__ import annotations

import json


def _deployed_label(field: str, deployed_keys: set[str]) -> str:
    """Return 'disabled' attribute if field is deployed."""
    return "disabled" if field in deployed_keys else ""


def build_page(cfg: dict, *, deployed_keys: set[str]) -> str:
    """Build the HTML page with config embedded as JSON."""
    config_json = json.dumps(cfg, indent=2)
    deployed_json = json.dumps(sorted(deployed_keys))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Configurator</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: #f5f5f5; color: #333; padding: 2rem;
}}
.container {{ max-width: 40rem; margin: 0 auto; }}
h1 {{ font-size: 1.4rem; margin-bottom: 1.5rem; font-weight: 600; }}
fieldset {{
    border: 1px solid #ddd; border-radius: 8px; padding: 1.2rem;
    margin-bottom: 1rem; background: #fff;
}}
legend {{ font-weight: 600; font-size: 0.95rem; padding: 0 0.4rem; }}
.field {{ margin-bottom: 0.8rem; }}
.field:last-child {{ margin-bottom: 0; }}
label {{ display: block; font-size: 0.85rem; color: #555; margin-bottom: 0.2rem; }}
input[type="text"], select {{
    width: 100%; padding: 0.4rem 0.6rem; border: 1px solid #ccc;
    border-radius: 4px; font-size: 0.9rem; font-family: inherit;
}}
input[type="text"]:disabled, select:disabled {{
    background: #f0f0f0; color: #999;
}}
.checkbox-group {{ display: flex; flex-wrap: wrap; gap: 0.6rem; margin-top: 0.3rem; }}
.checkbox-group label {{
    display: flex; align-items: center; gap: 0.3rem;
    font-size: 0.9rem; color: #333; cursor: pointer;
}}
.checkbox-group input:disabled + span {{ color: #999; }}
.toggle-row {{
    display: flex; align-items: center; gap: 0.5rem;
    margin-bottom: 0.6rem;
}}
.toggle-row label {{ margin-bottom: 0; font-size: 0.9rem; color: #333; }}
.deployed-badge {{
    font-size: 0.7rem; background: #e8f5e9; color: #2e7d32;
    padding: 0.1rem 0.4rem; border-radius: 3px; font-weight: 500;
}}
.radio-group {{ display: flex; gap: 1rem; margin-top: 0.3rem; }}
.radio-group label {{
    display: flex; align-items: center; gap: 0.3rem;
    font-size: 0.9rem; color: #333; cursor: pointer;
}}
.sub-field {{ margin-left: 1.4rem; margin-top: 0.4rem; }}
.readonly {{ font-size: 0.9rem; color: #666; padding: 0.4rem 0; }}
.saved-indicator {{
    position: fixed; top: 1rem; right: 1rem; font-size: 0.8rem;
    color: #888; opacity: 0; transition: opacity 0.3s;
}}
.saved-indicator.visible {{ opacity: 1; }}
</style>
</head>
<body>
<div class="container">
<h1>Configurator</h1>

<!-- Project -->
<fieldset>
<legend>Project</legend>
<div class="field">
    <label for="repo">Repository name</label>
    <input type="text" id="repo" data-key="repo">
</div>
<div class="field">
    <label for="org">Organization</label>
    <select id="org" data-key="org">
        <option value="">— select —</option>
        <option value="mikefullerton">mikefullerton</option>
        <option value="agentic-cookbook">agentic-cookbook</option>
        <option value="other">other</option>
    </select>
</div>
<div class="field" id="org-other-field" style="display:none">
    <label for="org-other">Organization name</label>
    <input type="text" id="org-other">
</div>
<div class="field">
    <label for="domain">Domain</label>
    <input type="text" id="domain" data-key="domain">
</div>
<div class="field" id="local-path-field" style="display:none">
    <label>Local path</label>
    <div class="readonly" id="local-path"></div>
</div>
</fieldset>

<!-- Website -->
<fieldset>
<legend>Website</legend>
<div class="field">
    <label>Type</label>
    <div class="radio-group">
        <label><input type="radio" name="ws-type" value="new"> <span>New</span></label>
        <label><input type="radio" name="ws-type" value="existing"> <span>Existing</span></label>
        <label><input type="radio" name="ws-type" value="none"> <span>None</span></label>
    </div>
</div>
<div id="ws-options">
    <div class="field">
        <label for="ws-domain">Website domain</label>
        <input type="text" id="ws-domain">
    </div>
    <div class="field">
        <label>Addons</label>
        <div class="checkbox-group">
            <label><input type="checkbox" id="addon-d1" value="sqlite database"> <span>SQLite database</span></label>
            <label><input type="checkbox" id="addon-kv" value="key-value storage"> <span>Key-value storage</span></label>
            <label><input type="checkbox" id="addon-r2" value="file storage"> <span>File storage</span></label>
        </div>
    </div>
</div>
</fieldset>

<!-- Backend -->
<fieldset>
<legend>Backend</legend>
<div class="toggle-row">
    <input type="checkbox" id="be-enabled">
    <label for="be-enabled">Enable backend</label>
    <span class="deployed-badge" id="be-deployed" style="display:none">deployed</span>
</div>
<div id="be-options">
    <div class="field">
        <label for="be-domain">Backend domain</label>
        <input type="text" id="be-domain">
    </div>
    <div class="field">
        <div class="toggle-row">
            <input type="checkbox" id="be-docs-enabled">
            <label for="be-docs-enabled">API docs site</label>
        </div>
        <div class="sub-field" id="be-docs-domain-field">
            <label for="be-docs-domain">Docs domain</label>
            <input type="text" id="be-docs-domain">
        </div>
    </div>
    <div class="field">
        <label>Additional environments</label>
        <div class="checkbox-group">
            <label><input type="checkbox" id="env-staging" value="staging"> <span>Staging</span></label>
            <label><input type="checkbox" id="env-testing" value="testing"> <span>Testing</span></label>
        </div>
    </div>
</div>
</fieldset>

<!-- Admin Sites -->
<fieldset>
<legend>Admin Sites</legend>
<div class="toggle-row">
    <input type="checkbox" id="admin-enabled">
    <label for="admin-enabled">Admin site</label>
    <span class="deployed-badge" id="admin-deployed" style="display:none">deployed</span>
</div>
<div class="sub-field" id="admin-domain-field">
    <label for="admin-domain">Admin domain</label>
    <input type="text" id="admin-domain">
</div>

<div class="toggle-row" style="margin-top: 0.8rem">
    <input type="checkbox" id="dash-enabled">
    <label for="dash-enabled">Dashboard</label>
    <span class="deployed-badge" id="dash-deployed" style="display:none">deployed</span>
</div>
<div class="sub-field" id="dash-domain-field">
    <label for="dash-domain">Dashboard domain</label>
    <input type="text" id="dash-domain">
</div>
</fieldset>

<!-- Auth -->
<fieldset>
<legend>Authentication</legend>
<div class="field">
    <label>Providers</label>
    <div class="checkbox-group">
        <label><input type="checkbox" id="auth-email" value="email/password"> <span>Email/password</span></label>
        <label><input type="checkbox" id="auth-github" value="github"> <span>GitHub</span></label>
        <label><input type="checkbox" id="auth-google" value="google"> <span>Google</span></label>
        <label><input type="checkbox" id="auth-apple" value="apple"> <span>Apple</span></label>
    </div>
</div>
</fieldset>

</div>

<div class="saved-indicator" id="saved">Saved</div>

<script>
const CONFIG = {config_json};
const DEPLOYED = new Set({deployed_json});

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

let saveTimer = null;

function debounceSave() {{
    clearTimeout(saveTimer);
    saveTimer = setTimeout(saveConfig, 300);
}}

function saveConfig() {{
    const cfg = readForm();
    fetch("/api/config", {{
        method: "PATCH",
        headers: {{"Content-Type": "application/json"}},
        body: JSON.stringify(cfg),
    }}).then(() => {{
        const el = $("#saved");
        el.classList.add("visible");
        setTimeout(() => el.classList.remove("visible"), 1500);
    }});
}}

function readForm() {{
    const cfg = {{}};

    // Project
    const repo = $("#repo").value.trim();
    if (repo) cfg.repo = repo;

    const orgSel = $("#org").value;
    if (orgSel === "other") {{
        const custom = $("#org-other").value.trim();
        if (custom) cfg.org = custom;
    }} else if (orgSel) {{
        cfg.org = orgSel;
    }}

    const domain = $("#domain").value.trim();
    if (domain) cfg.domain = domain;

    // Local path (read-only, pass through)
    if (CONFIG.local_path) cfg.local_path = CONFIG.local_path;
    if (CONFIG.create_repo) cfg.create_repo = CONFIG.create_repo;

    // Website
    const wsType = document.querySelector('input[name="ws-type"]:checked');
    const ws = {{ type: wsType ? wsType.value : "none" }};
    if (ws.type !== "none") {{
        const wsDomain = $("#ws-domain").value.trim();
        if (wsDomain) ws.domain = wsDomain;
        const addons = [];
        if ($("#addon-d1").checked) addons.push("sqlite database");
        if ($("#addon-kv").checked) addons.push("key-value storage");
        if ($("#addon-r2").checked) addons.push("file storage");
        if (addons.length) ws.addons = addons;
    }}
    cfg.website = ws;

    // Backend
    const be = {{}};
    if ($("#be-enabled").checked) {{
        be.enabled = true;
        be.type = "full";
        const beDomain = $("#be-domain").value.trim();
        if (beDomain) be.domain = beDomain;
        if ($("#be-docs-enabled").checked) {{
            const docsDomain = $("#be-docs-domain").value.trim();
            if (docsDomain) be.docs_domain = docsDomain;
        }}
        const environments = {{}};
        if ($("#env-staging").checked) environments.staging = true;
        if ($("#env-testing").checked) environments.testing = true;
        if (Object.keys(environments).length) be.environments = environments;
    }} else {{
        be.enabled = false;
    }}
    cfg.backend = be;

    // Admin sites
    const adminSites = {{}};
    for (const [key, prefix] of [["admin", "admin"], ["dashboard", "dash"]]) {{
        const s = {{}};
        if ($(`#${{prefix}}-enabled`).checked) {{
            s.enabled = true;
            const d = $(`#${{prefix}}-domain`).value.trim();
            if (d) s.domain = d;
        }} else {{
            s.enabled = false;
        }}
        adminSites[key] = s;
    }}
    cfg.admin_sites = adminSites;

    // Auth
    const providers = [];
    if ($("#auth-email").checked) providers.push("email/password");
    if ($("#auth-github").checked) providers.push("github");
    if ($("#auth-google").checked) providers.push("google");
    if ($("#auth-apple").checked) providers.push("apple");
    if (providers.length) cfg.auth_providers = providers;

    return cfg;
}}

function populateForm() {{
    // Project
    $("#repo").value = CONFIG.repo || "";
    const org = CONFIG.org || "";
    const orgSelect = $("#org");
    const knownOrgs = [...orgSelect.options].map(o => o.value);
    if (org && !knownOrgs.includes(org)) {{
        orgSelect.value = "other";
        $("#org-other").value = org;
        $("#org-other-field").style.display = "";
    }} else {{
        orgSelect.value = org;
    }}
    $("#domain").value = CONFIG.domain || "";
    if (CONFIG.local_path) {{
        $("#local-path").textContent = CONFIG.local_path;
        $("#local-path-field").style.display = "";
    }}

    // Website
    const ws = CONFIG.website || {{}};
    const wsType = ws.type || "none";
    const wsRadio = document.querySelector(`input[name="ws-type"][value="${{wsType}}"]`);
    if (wsRadio) wsRadio.checked = true;
    $("#ws-domain").value = ws.domain || CONFIG.domain || "";
    const addons = ws.addons || [];
    $("#addon-d1").checked = addons.includes("sqlite database");
    $("#addon-kv").checked = addons.includes("key-value storage");
    $("#addon-r2").checked = addons.includes("file storage");

    // Backend
    const be = CONFIG.backend || {{}};
    $("#be-enabled").checked = !!be.enabled;
    $("#be-domain").value = be.domain || "";
    if (be.docs_domain) {{
        $("#be-docs-enabled").checked = true;
        $("#be-docs-domain").value = be.docs_domain;
    }}
    const envs = be.environments || {{}};
    $("#env-staging").checked = !!envs.staging;
    $("#env-testing").checked = !!envs.testing;

    // Admin sites
    const adminSites = CONFIG.admin_sites || {{}};
    const admin = adminSites.admin || {{}};
    $("#admin-enabled").checked = !!admin.enabled;
    $("#admin-domain").value = admin.domain || "";
    const dash = adminSites.dashboard || {{}};
    $("#dash-enabled").checked = !!dash.enabled;
    $("#dash-domain").value = dash.domain || "";

    // Auth
    const providers = CONFIG.auth_providers || [];
    $("#auth-email").checked = providers.includes("email/password");
    $("#auth-github").checked = providers.includes("github");
    $("#auth-google").checked = providers.includes("google");
    $("#auth-apple").checked = providers.includes("apple");

    // Deployed badges and locks
    if (DEPLOYED.has("backend")) {{
        $("#be-enabled").disabled = true;
        $("#be-deployed").style.display = "";
    }}
    if (DEPLOYED.has("admin")) {{
        $("#admin-enabled").disabled = true;
        $("#admin-deployed").style.display = "";
    }}
    if (DEPLOYED.has("dashboard")) {{
        $("#dash-enabled").disabled = true;
        $("#dash-deployed").style.display = "";
    }}

    updateVisibility();
}}

function updateVisibility() {{
    // Website options
    const wsType = document.querySelector('input[name="ws-type"]:checked');
    const wsNone = !wsType || wsType.value === "none";
    $("#ws-options").style.display = wsNone ? "none" : "";

    // Backend options
    const beEnabled = $("#be-enabled").checked;
    $("#be-options").style.display = beEnabled ? "" : "none";

    // Backend docs domain
    const docsEnabled = $("#be-docs-enabled").checked;
    $("#be-docs-domain-field").style.display = docsEnabled ? "" : "none";

    // Org other
    $("#org-other-field").style.display = $("#org").value === "other" ? "" : "none";

    // Admin domains
    $("#admin-domain-field").style.display = $("#admin-enabled").checked ? "" : "none";
    $("#dash-domain-field").style.display = $("#dash-enabled").checked ? "" : "none";
}}

// Wire up all inputs
document.addEventListener("DOMContentLoaded", () => {{
    populateForm();

    // All inputs trigger save + visibility update
    for (const el of $$("input, select")) {{
        const event = el.type === "text" ? "input" : "change";
        el.addEventListener(event, () => {{
            updateVisibility();
            debounceSave();
        }});
    }}
}});
</script>
</body>
</html>"""
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd skills/configurator/configurator-cli && uv run --extra test pytest tests/test_web.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add src/configurator/web.py tests/test_web.py
git commit -m "feat(configurator): add web editor HTML template and build_page"
```

---

### Task 2: Add HTTP server to web.py

**Files:**
- Modify: `src/configurator/web.py`
- Test: `tests/test_web.py`

Wire up the HTTP server that serves the form and handles config PATCH requests.

- [ ] **Step 1: Write the failing test for the server**

Append to `tests/test_web.py`:

```python
import threading
import urllib.request

from configurator.web import start_server


class TestServer:
    def test_serves_html_on_get(self, monkeypatch, tmp_path):
        monkeypatch.setattr("configurator.cli.CONFIG_DIR", tmp_path)
        cfg = {"repo": "test-project", "domain": "test.com"}
        httpd, port = start_server("test-project", cfg, deployed_keys=set())
        t = threading.Thread(target=httpd.handle_request)
        t.start()
        try:
            url = f"http://localhost:{port}/"
            resp = urllib.request.urlopen(url)
            html = resp.read().decode()
            assert "test-project" in html
            assert resp.status == 200
        finally:
            httpd.server_close()
            t.join(timeout=2)

    def test_patch_updates_config(self, monkeypatch, tmp_path):
        monkeypatch.setattr("configurator.cli.CONFIG_DIR", tmp_path)
        cfg = {"repo": "test-project"}
        httpd, port = start_server("test-project", cfg, deployed_keys=set())

        def handle_two():
            httpd.handle_request()  # serve initial page (optional)
            httpd.handle_request()  # handle PATCH

        t = threading.Thread(target=handle_two)
        t.start()
        try:
            # PATCH to update config
            import json as json_mod
            data = json_mod.dumps({"repo": "updated", "domain": "new.com"}).encode()
            req = urllib.request.Request(
                f"http://localhost:{port}/api/config",
                data=data,
                method="PATCH",
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req)
            assert resp.status == 200

            # Verify the file was written
            saved = json_mod.loads((tmp_path / "test-project.json").read_text())
            assert saved["repo"] == "updated"
            assert saved["domain"] == "new.com"
        finally:
            httpd.server_close()
            t.join(timeout=2)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd skills/configurator/configurator-cli && uv run --extra test pytest tests/test_web.py::TestServer -v`
Expected: FAIL with "cannot import name 'start_server'"

- [ ] **Step 3: Implement start_server and request handler**

Add to `src/configurator/web.py`:

```python
import socketserver
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler

from configurator.cli import save_config


class _Handler(BaseHTTPRequestHandler):
    """Handles GET / and PATCH /api/config."""

    def do_GET(self):
        if self.path == "/":
            html = build_page(self.server.cfg, deployed_keys=self.server.deployed_keys)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode())
        else:
            self.send_error(404)

    def do_PATCH(self):
        if self.path == "/api/config":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            new_cfg = json.loads(body)
            self.server.cfg.update(new_cfg)
            save_config(self.server.config_name, self.server.cfg)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        pass  # suppress request logging


def start_server(
    name: str, cfg: dict, *, deployed_keys: set[str]
) -> tuple[HTTPServer, int]:
    """Create and bind the server. Returns (httpd, port)."""
    httpd = HTTPServer(("127.0.0.1", 0), _Handler)
    httpd.config_name = name
    httpd.cfg = cfg
    httpd.deployed_keys = deployed_keys
    port = httpd.server_address[1]
    return httpd, port


def serve_editor(name: str, cfg: dict, *, deployed_keys: set[str] | None = None) -> None:
    """Open the web editor and block until Ctrl+C."""
    if deployed_keys is None:
        deployed_keys = set()
    httpd, port = start_server(name, cfg, deployed_keys=deployed_keys)
    url = f"http://localhost:{port}/"
    print(f"  Editing at {url} — press Ctrl+C when done")
    webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd skills/configurator/configurator-cli && uv run --extra test pytest tests/test_web.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/configurator/web.py tests/test_web.py
git commit -m "feat(configurator): add HTTP server for web editor"
```

---

### Task 3: Compute deployed_keys from manifest

**Files:**
- Modify: `src/configurator/cli.py:606-687`
- Test: `tests/test_manifest_to_config.py`

Add a function to extract which features are deployed from the manifest, so the form can lock those toggles.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_manifest_to_config.py`:

```python
from configurator.cli import _deployed_keys_from_manifest


class TestDeployedKeys:
    def test_backend_deployed(self):
        manifest = {"services": {"backend": {"status": "deployed"}}}
        assert "backend" in _deployed_keys_from_manifest(manifest)

    def test_admin_deployed(self):
        manifest = {"services": {"admin": {"status": "deployed"}}}
        assert "admin" in _deployed_keys_from_manifest(manifest)

    def test_dashboard_deployed(self):
        manifest = {"services": {"dashboard": {"domain": "dash.example.com"}}}
        assert "dashboard" in _deployed_keys_from_manifest(manifest)

    def test_main_deployed(self):
        manifest = {"services": {"main": {"domain": "example.com"}}}
        assert "website" in _deployed_keys_from_manifest(manifest)

    def test_nothing_deployed(self):
        manifest = {"services": {}}
        assert _deployed_keys_from_manifest(manifest) == set()

    def test_empty_manifest(self):
        assert _deployed_keys_from_manifest({}) == set()

    def test_api_counts_as_backend(self):
        manifest = {"services": {"api": {"status": "deployed"}}}
        assert "backend" in _deployed_keys_from_manifest(manifest)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd skills/configurator/configurator-cli && uv run --extra test pytest tests/test_manifest_to_config.py::TestDeployedKeys -v`
Expected: FAIL with "cannot import name '_deployed_keys_from_manifest'"

- [ ] **Step 3: Implement _deployed_keys_from_manifest**

Add to `src/configurator/cli.py` after the `_manifest_to_config` function (after line 167):

```python
def _deployed_keys_from_manifest(manifest: dict) -> set[str]:
    """Extract which features are deployed from a manifest."""
    services = manifest.get("services", {})
    keys: set[str] = set()
    if "main" in services:
        keys.add("website")
    if "backend" in services or "api" in services or "api-docs" in services:
        keys.add("backend")
    if "admin" in services:
        keys.add("admin")
    if "dashboard" in services:
        keys.add("dashboard")
    return keys
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd skills/configurator/configurator-cli && uv run --extra test pytest tests/test_manifest_to_config.py::TestDeployedKeys -v`
Expected: 7 PASS

- [ ] **Step 5: Commit**

```bash
git add src/configurator/cli.py tests/test_manifest_to_config.py
git commit -m "feat(configurator): extract deployed keys from manifest"
```

---

### Task 4: Wire web editor into cmd_configure and add --tui flag

**Files:**
- Modify: `src/configurator/cli.py:606-773`
- Modify: `src/configurator/__init__.py`

Replace the default `run_questions()` call with `serve_editor()`, add `--tui` flag.

- [ ] **Step 1: Add --tui flag to arg parser**

In `src/configurator/cli.py`, modify the `main()` function (line 753-773). Add the `--tui` argument and pass it to `cmd_configure`:

```python
def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive project configurator")
    parser.add_argument("--configure", action="store_true", default=True, help="Configure a project (default)")
    parser.add_argument("--show", nargs="?", const="", metavar="NAME", help="Show a configuration")
    parser.add_argument("--delete", nargs="?", const="", metavar="NAME", help="Delete a configuration")
    parser.add_argument("--tui", action="store_true", help="Use terminal Q&A instead of web editor")
    parser.add_argument("--version", action="store_true", help="Show version")
    args = parser.parse_args()

    if args.version:
        print(f"configurator {__version__}")
        return

    if args.show is not None:
        cmd_show(args.show or None)
        return

    if args.delete is not None:
        cmd_delete(args.delete or None)
        return

    cmd_configure(tui=args.tui)
```

- [ ] **Step 2: Modify cmd_configure to accept tui parameter**

Update `cmd_configure()` signature and the manifest-detected branch (lines 606-687). When `tui=False` (default), use the web editor. When `tui=True`, use the existing `run_questions()` flow:

```python
def cmd_configure(*, tui: bool = False) -> None:
    # Check if we're in a deployed project directory
    cwd = Path.cwd()
    manifest = _load_manifest(cwd)

    if manifest:
        project_name = manifest.get("project", {}).get("name", cwd.name)
        manifest_version = manifest.get("configurator_version")

        print(f"  Found deployed project: {project_name}")
        if manifest_version:
            print(f"  Deployed with configurator v{manifest_version}")

        # Show new options if the manifest is behind current version
        if not manifest_version or _parse_version(manifest_version) < _parse_version(__version__):
            _show_new_options(manifest_version)

        # Always create a fresh draft config from the manifest
        cfg = _manifest_to_config(manifest)
        cfg["local_path"] = str(cwd.resolve())
        name = project_name

        # Delete any existing draft config for this project
        delete_config(name)

        save_config(name, cfg)
        print()
        print("  Draft configuration from current deployment:")
        show_config(name)

        if tui:
            try:
                proceed = ask_choice(None, "Edit this configuration?", ["yes", "no"], default="yes")
            except UserQuit:
                delete_config(name)
                return

            if proceed == "no":
                delete_config(name)
                return

            questions_started = False
            try:
                questions_started = True
                name = run_questions(name, cfg)
            except UserQuit:
                if questions_started and name:
                    try:
                        delete_it = ask_choice(None, f"Delete the draft configuration '{name}'?", ["yes", "no"], default="yes")
                    except UserQuit:
                        delete_it = "yes"
                    if delete_it == "yes":
                        delete_config(name)
                        print(f"Draft configuration '{name}' deleted.")
                    else:
                        print(f"Draft configuration '{name}' saved.")
                return

            # Show and confirm
            show_config(name)
            try:
                ok = ask_choice(None, "Does that look ok?", ["yes", "no"], default="yes")
            except UserQuit:
                print(f"Configuration '{name}' saved.")
                return

            if ok == "no":
                cfg = load_config(name)
                try:
                    run_questions(name, cfg)
                    show_config(name)
                except UserQuit:
                    print(f"Configuration '{name}' saved.")
                    return

            command = f"/configurator {name}"
            try:
                subprocess.run(["pbcopy"], input=command.encode(), check=True)
                print(f"To deploy, run '{command}' in Claude (command copied to clipboard)")
            except (FileNotFoundError, subprocess.CalledProcessError):
                print(f"To deploy, run '{command}' in Claude")
        else:
            # Web editor
            from configurator.web import serve_editor
            deployed = _deployed_keys_from_manifest(manifest)
            serve_editor(name, cfg, deployed_keys=deployed)

        return

    # No manifest in cwd — standard flow
    configs = list_configs()
    menu = configs + ["New configuration"]

    try:
        chosen = ask_choice(None, "Choose a configuration:", menu)
    except UserQuit:
        return

    if chosen == "New configuration":
        name = None
        cfg: dict = {}
    else:
        name = chosen
        cfg = load_config(name)

    if tui:
        questions_started = False
        try:
            questions_started = True
            name = run_questions(name, cfg)
        except UserQuit:
            if questions_started and name:
                try:
                    delete_it = ask_choice(None, f"Delete the configuration '{name}'?", ["no", "yes"], default="no")
                except UserQuit:
                    delete_it = "no"
                if delete_it == "yes":
                    delete_config(name)
                    print(f"Configuration '{name}' deleted.")
                else:
                    print(f"Configuration '{name}' saved (partial).")
            return

        # Show the completed config
        show_config(name)

        # Confirm
        try:
            ok = ask_choice(None, "Does that look ok?", ["yes", "no"], default="yes")
        except UserQuit:
            print(f"Configuration '{name}' saved.")
            return

        if ok == "no":
            cfg = load_config(name)
            try:
                run_questions(name, cfg)
                show_config(name)
            except UserQuit:
                print(f"Configuration '{name}' saved.")
                return

        command = f"/configurator {name}"
        try:
            subprocess.run(["pbcopy"], input=command.encode(), check=True)
            print(f"To deploy, run '{command}' in Claude (command copied to clipboard)")
        except (FileNotFoundError, subprocess.CalledProcessError):
            print(f"To deploy, run '{command}' in Claude")
    else:
        # For new configs without a manifest, we need a name first
        if name is None:
            try:
                repo = ask_text(1, "What is the name of the GitHub repo for this project?", required=True)
            except UserQuit:
                return
            name = repo
            cfg["repo"] = repo
            save_config(name, cfg)

        from configurator.web import serve_editor
        serve_editor(name, cfg, deployed_keys=set())
```

- [ ] **Step 3: Bump version**

In `src/configurator/__init__.py`:

```python
__version__ = "0.4.0"
```

This is a minor bump — new feature (web editor).

- [ ] **Step 4: Run full test suite**

Run: `cd skills/configurator/configurator-cli && uv run --extra test pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 5: Manual smoke test**

Run: `cd skills/configurator/configurator-cli && uv run configurator`
Expected: Browser opens with form. Fill in fields, verify JSON file updates at `~/.configurator/<name>.json`. Ctrl+C exits cleanly.

Run: `cd skills/configurator/configurator-cli && uv run configurator --tui`
Expected: Terminal Q&A flow works as before.

- [ ] **Step 6: Commit**

```bash
git add src/configurator/cli.py src/configurator/__init__.py
git commit -m "feat(configurator): wire web editor as default, add --tui flag"
```
