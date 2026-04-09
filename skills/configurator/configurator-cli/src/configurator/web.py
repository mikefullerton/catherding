"""Local web editor for configurator configs."""

from __future__ import annotations

import json
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler

from configurator.cli import save_config


def build_page(
    cfg: dict,
    *,
    deployed_keys: set[str],
    urls: dict[str, str] | None = None,
    live_domains: set[str] | None = None,
) -> str:
    """Build the HTML page with config embedded as JSON."""
    config_json = json.dumps(cfg, indent=2)
    deployed_json = json.dumps(sorted(deployed_keys))
    urls_json = json.dumps(urls or {})
    live_json = json.dumps(sorted(live_domains or set()))

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
.badge {{
    font-size: 0.7rem; padding: 0.1rem 0.4rem; border-radius: 3px; font-weight: 500;
}}
.deployed-badge {{
    background: #e8f5e9; color: #2e7d32;
}}
.live-badge {{
    background: #e3f2fd; color: #1565c0;
}}
.link {{
    font-size: 0.8rem; margin-left: 0.5rem;
}}
.link a {{
    color: #1976d2; text-decoration: none;
}}
.link a:hover {{ text-decoration: underline; }}
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
        <option value="">-- select --</option>
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
<legend>Website
    <span class="badge deployed-badge" id="ws-deployed" style="display:none">deployed</span>
    <span class="badge live-badge" id="ws-live" style="display:none">live</span>
    <span class="link" id="ws-link" style="display:none"><a href="#" target="_blank">open</a></span>
</legend>
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
<legend>Backend
    <span class="badge deployed-badge" id="be-deployed" style="display:none">deployed</span>
    <span class="badge live-badge" id="be-live" style="display:none">live</span>
    <span class="link" id="be-link" style="display:none"><a href="#" target="_blank">open</a></span>
</legend>
<div class="toggle-row">
    <input type="checkbox" id="be-enabled">
    <label for="be-enabled">Enable backend</label>
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
    <span class="badge deployed-badge" id="admin-deployed" style="display:none">deployed</span>
    <span class="badge live-badge" id="admin-live" style="display:none">live</span>
    <span class="link" id="admin-link" style="display:none"><a href="#" target="_blank">open</a></span>
</div>
<div class="sub-field" id="admin-domain-field">
    <label for="admin-domain">Admin domain</label>
    <input type="text" id="admin-domain">
</div>

<div class="toggle-row" style="margin-top: 0.8rem">
    <input type="checkbox" id="dash-enabled">
    <label for="dash-enabled">Dashboard</label>
    <span class="badge deployed-badge" id="dash-deployed" style="display:none">deployed</span>
    <span class="badge live-badge" id="dash-live" style="display:none">live</span>
    <span class="link" id="dash-link" style="display:none"><a href="#" target="_blank">open</a></span>
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
const URLS = {urls_json};
const LIVE = new Set({live_json});

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

function setLink(id, svcKey) {{
    const url = URLS[svcKey];
    if (url) {{
        const el = $(`#${{id}}`);
        el.style.display = "";
        el.querySelector("a").href = url;
    }}
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

    // Lock repo and org when deployed
    if (DEPLOYED.has("repo")) {{
        $("#repo").disabled = true;
    }}
    if (DEPLOYED.has("org")) {{
        $("#org").disabled = true;
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

    // Website deployed state
    if (DEPLOYED.has("website")) {{
        // Lock website type radios
        for (const radio of $$('input[name="ws-type"]')) {{
            radio.disabled = true;
        }}
        $("#ws-deployed").style.display = "";
        setLink("ws-link", "main");
    }}
    if (LIVE.has("main")) {{
        $("#ws-live").style.display = "";
    }}

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

    if (DEPLOYED.has("backend")) {{
        $("#be-enabled").disabled = true;
        $("#be-deployed").style.display = "";
        setLink("be-link", "backend");
    }}
    if (LIVE.has("backend")) {{
        $("#be-live").style.display = "";
    }}

    // Admin sites
    const adminSites = CONFIG.admin_sites || {{}};
    const admin = adminSites.admin || {{}};
    $("#admin-enabled").checked = !!admin.enabled;
    $("#admin-domain").value = admin.domain || "";
    const dash = adminSites.dashboard || {{}};
    $("#dash-enabled").checked = !!dash.enabled;
    $("#dash-domain").value = dash.domain || "";

    if (DEPLOYED.has("admin")) {{
        $("#admin-enabled").disabled = true;
        $("#admin-deployed").style.display = "";
        setLink("admin-link", "admin");
    }}
    if (LIVE.has("admin")) {{
        $("#admin-live").style.display = "";
    }}
    if (DEPLOYED.has("dashboard")) {{
        $("#dash-enabled").disabled = true;
        $("#dash-deployed").style.display = "";
        setLink("dash-link", "dashboard");
    }}
    if (LIVE.has("dashboard")) {{
        $("#dash-live").style.display = "";
    }}

    // Auth
    const providers = CONFIG.auth_providers || [];
    $("#auth-email").checked = providers.includes("email/password");
    $("#auth-github").checked = providers.includes("github");
    $("#auth-google").checked = providers.includes("google");
    $("#auth-apple").checked = providers.includes("apple");

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


class _Handler(BaseHTTPRequestHandler):
    """Handles GET / and PATCH /api/config."""

    def do_GET(self):
        if self.path == "/":
            html = build_page(
                self.server.cfg,
                deployed_keys=self.server.deployed_keys,
                urls=self.server.urls,
                live_domains=self.server.live_domains,
            )
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
    name: str,
    cfg: dict,
    *,
    deployed_keys: set[str],
    urls: dict[str, str] | None = None,
    live_domains: set[str] | None = None,
) -> tuple[HTTPServer, int]:
    """Create and bind the server. Returns (httpd, port)."""
    httpd = HTTPServer(("127.0.0.1", 0), _Handler)
    httpd.config_name = name
    httpd.cfg = cfg
    httpd.deployed_keys = deployed_keys
    httpd.urls = urls or {}
    httpd.live_domains = live_domains or set()
    port = httpd.server_address[1]
    return httpd, port


def serve_editor(
    name: str,
    cfg: dict,
    *,
    deployed_keys: set[str] | None = None,
    urls: dict[str, str] | None = None,
    live_domains: set[str] | None = None,
) -> None:
    """Open the web editor and block until Ctrl+C."""
    if deployed_keys is None:
        deployed_keys = set()
    httpd, port = start_server(
        name, cfg,
        deployed_keys=deployed_keys,
        urls=urls,
        live_domains=live_domains,
    )
    url = f"http://localhost:{port}/"
    print(f"  Editing at {url} — press Ctrl+C when done")
    webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
