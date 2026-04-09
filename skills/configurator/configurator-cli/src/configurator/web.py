"""Local web editor for configurator configs."""

from __future__ import annotations

import json
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler

from configurator.cli import save_config
from configurator import __version__


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
    version = __version__

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Configurator</title>
<style>
:root {{
    --bg: #f5f5f5; --fg: #333; --fg-muted: #555; --fg-dim: #888;
    --card: #fff; --border: #ddd; --input-bg: #fff; --input-border: #ccc;
    --disabled-bg: #f0f0f0; --disabled-fg: #999;
    --link: #1976d2; --accent: #1976d2; --accent-hover: #1565c0;
    --btn-secondary: #e0e0e0; --btn-secondary-fg: #555; --btn-secondary-hover: #d0d0d0;
    --badge-deploy-bg: #e8f5e9; --badge-deploy-fg: #2e7d32;
    --badge-live-bg: #e3f2fd; --badge-live-fg: #1565c0;
}}
@media (prefers-color-scheme: dark) {{
    :root {{
        --bg: #1a1a1a; --fg: #e0e0e0; --fg-muted: #aaa; --fg-dim: #777;
        --card: #2a2a2a; --border: #444; --input-bg: #333; --input-border: #555;
        --disabled-bg: #2a2a2a; --disabled-fg: #666;
        --link: #64b5f6; --accent: #42a5f5; --accent-hover: #2196f3;
        --btn-secondary: #444; --btn-secondary-fg: #ccc; --btn-secondary-hover: #555;
        --badge-deploy-bg: #1b3a1e; --badge-deploy-fg: #66bb6a;
        --badge-live-bg: #1a2e3d; --badge-live-fg: #64b5f6;
    }}
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: var(--bg); color: var(--fg); padding: 2rem;
}}
.container {{ max-width: 40rem; margin: 0 auto; }}
h1 {{ font-size: 1.4rem; margin-bottom: 1.5rem; font-weight: 600; }}
h1 span {{ font-size: 0.8rem; font-weight: 400; color: var(--fg-dim); margin-left: 0.4rem; }}
fieldset {{
    border: 1px solid var(--border); border-radius: 8px; padding: 1.2rem;
    margin-bottom: 1rem; background: var(--card);
}}
legend {{ font-weight: 600; font-size: 0.95rem; padding: 0 0.4rem; }}
.field {{ margin-bottom: 0.8rem; }}
.field:last-child {{ margin-bottom: 0; }}
label {{ display: block; font-size: 0.85rem; color: var(--fg-muted); margin-bottom: 0.2rem; }}
input[type="text"], select {{
    width: 100%; padding: 0.4rem 0.6rem; border: 1px solid var(--input-border);
    border-radius: 4px; font-size: 0.9rem; font-family: inherit;
    background: var(--input-bg); color: var(--fg);
}}
input[type="text"]:disabled, select:disabled {{
    background: var(--disabled-bg); color: var(--disabled-fg);
}}
.checkbox-group {{ display: flex; flex-wrap: wrap; gap: 0.6rem; margin-top: 0.3rem; }}
.checkbox-group label {{
    display: flex; align-items: center; gap: 0.3rem;
    font-size: 0.9rem; color: var(--fg); cursor: pointer;
}}
.checkbox-group input:disabled + span {{ color: var(--disabled-fg); }}
.toggle-row {{
    display: flex; align-items: center; gap: 0.5rem;
    margin-bottom: 0.6rem;
}}
.toggle-row label {{ margin-bottom: 0; font-size: 0.9rem; color: var(--fg); }}
.badge {{
    font-size: 0.7rem; padding: 0.1rem 0.4rem; border-radius: 3px; font-weight: 500;
}}
.deployed-badge {{ background: var(--badge-deploy-bg); color: var(--badge-deploy-fg); }}
.live-badge {{ background: var(--badge-live-bg); color: var(--badge-live-fg); }}
.live-url {{
    font-size: 0.8rem; color: var(--fg-dim); margin-bottom: 0.8rem;
    display: none;
}}
.live-url a {{ color: var(--link); text-decoration: none; }}
.live-url a:hover {{ text-decoration: underline; }}
.radio-group {{ display: flex; gap: 1rem; margin-top: 0.3rem; }}
.radio-group label {{
    display: flex; align-items: center; gap: 0.3rem;
    font-size: 0.9rem; color: var(--fg); cursor: pointer;
}}
.sub-field {{ margin-left: 1.4rem; margin-top: 0.4rem; }}
.readonly {{ font-size: 0.9rem; color: var(--fg-dim); padding: 0.4rem 0; }}
.actions {{
    display: flex; justify-content: flex-end; gap: 0.8rem;
    margin-top: 0.5rem; margin-bottom: 2rem;
}}
.btn {{
    padding: 0.5rem 1.4rem; border: none; border-radius: 6px;
    font-size: 0.9rem; font-weight: 500; cursor: pointer;
    font-family: inherit;
}}
.btn-cancel {{ background: var(--btn-secondary); color: var(--btn-secondary-fg); }}
.btn-cancel:hover {{ background: var(--btn-secondary-hover); }}
.btn-deploy {{ background: var(--accent); color: #fff; }}
.btn-deploy:hover {{ background: var(--accent-hover); }}
.saved-indicator {{
    position: fixed; top: 1rem; right: 1rem; font-size: 0.8rem;
    color: var(--fg-dim); opacity: 0; transition: opacity 0.3s;
}}
.saved-indicator.visible {{ opacity: 1; }}
</style>
</head>
<body>
<div class="container">
<h1>Configurator <span>v{version}</span></h1>

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
<div class="field">
    <label for="port">Editor port</label>
    <input type="text" id="port" data-key="port" inputmode="numeric" pattern="[0-9]*">
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
</legend>
<div class="live-url" id="ws-link"><a href="#" target="_blank"></a></div>
<div class="field">
    <label>Type</label>
    <div class="radio-group">
        <label><input type="radio" name="ws-type" value="new"> <span>New</span></label>
        <label><input type="radio" name="ws-type" value="existing"> <span>Existing</span></label>
        <label><input type="radio" name="ws-type" value="none"> <span>None</span></label>
    </div>
</div>
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
</fieldset>

<!-- Backend -->
<fieldset>
<legend>Backend
    <span class="badge deployed-badge" id="be-deployed" style="display:none">deployed</span>
    <span class="badge live-badge" id="be-live" style="display:none">live</span>
</legend>
<div class="live-url" id="be-link"><a href="#" target="_blank"></a></div>
<div class="toggle-row">
    <input type="checkbox" id="be-enabled">
    <label for="be-enabled">Enable backend</label>
</div>
<div class="field">
    <label for="be-domain">Backend domain</label>
    <input type="text" id="be-domain">
</div>
<div class="field">
    <div class="toggle-row">
        <input type="checkbox" id="be-docs-enabled">
        <label for="be-docs-enabled">API docs site</label>
    </div>
    <div class="sub-field">
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
</fieldset>

<!-- Admin Sites -->
<fieldset>
<legend>Admin Sites</legend>
<div class="toggle-row">
    <input type="checkbox" id="admin-enabled">
    <label for="admin-enabled">Admin site</label>
    <span class="badge deployed-badge" id="admin-deployed" style="display:none">deployed</span>
    <span class="badge live-badge" id="admin-live" style="display:none">live</span>
</div>
<div class="live-url" id="admin-link"><a href="#" target="_blank"></a></div>
<div class="sub-field">
    <label for="admin-domain">Admin domain</label>
    <input type="text" id="admin-domain">
</div>

<div class="toggle-row" style="margin-top: 0.8rem">
    <input type="checkbox" id="dash-enabled">
    <label for="dash-enabled">Dashboard</label>
    <span class="badge deployed-badge" id="dash-deployed" style="display:none">deployed</span>
    <span class="badge live-badge" id="dash-live" style="display:none">live</span>
</div>
<div class="live-url" id="dash-link"><a href="#" target="_blank"></a></div>
<div class="sub-field">
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

<div class="actions">
    <button type="button" id="btn-cancel" class="btn btn-cancel">Cancel</button>
    <button type="button" id="btn-deploy" class="btn btn-deploy">Deploy</button>
</div>

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

    const port = parseInt($("#port").value, 10);
    if (port && port > 0) cfg.port = port;

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
        el.style.display = "block";
        const a = el.querySelector("a");
        a.href = url;
        a.textContent = url;
    }}
}}

function defaultDomain(prefix) {{
    const d = CONFIG.domain || "";
    return d ? prefix + "." + d : "";
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
    $("#port").value = CONFIG.port || 4040;
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

    if (DEPLOYED.has("website")) {{
        for (const radio of $$('input[name="ws-type"]')) {{
            radio.disabled = true;
        }}
        $("#ws-deployed").style.display = "";
        setLink("ws-link", "main");
    }}
    if (LIVE.has("main")) {{
        $("#ws-live").style.display = "";
    }}

    // Backend — populate defaults even if not enabled
    const be = CONFIG.backend || {{}};
    $("#be-enabled").checked = !!be.enabled;
    $("#be-domain").value = be.domain || defaultDomain("backend");
    $("#be-docs-enabled").checked = !!be.docs_domain;
    $("#be-docs-domain").value = be.docs_domain || defaultDomain("api");

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

    // Admin sites — populate defaults even if not enabled
    const adminSites = CONFIG.admin_sites || {{}};
    const admin = adminSites.admin || {{}};
    $("#admin-enabled").checked = !!admin.enabled;
    $("#admin-domain").value = admin.domain || defaultDomain("admin");

    const dash = adminSites.dashboard || {{}};
    $("#dash-enabled").checked = !!dash.enabled;
    $("#dash-domain").value = dash.domain || defaultDomain("dashboard");

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

    updateDisabledState();
}}

function updateDisabledState() {{
    // Org other (still hide/show since it's a conditional select value)
    $("#org-other-field").style.display = $("#org").value === "other" ? "" : "none";

    // Website fields — disable when type is "none"
    const wsType = document.querySelector('input[name="ws-type"]:checked');
    const wsNone = !wsType || wsType.value === "none";
    $("#ws-domain").disabled = wsNone;
    for (const el of [$("#addon-d1"), $("#addon-kv"), $("#addon-r2")]) {{
        el.disabled = wsNone;
    }}

    // Backend fields — disable when not enabled
    const beEnabled = $("#be-enabled").checked;
    $("#be-domain").disabled = !beEnabled;
    $("#be-docs-enabled").disabled = !beEnabled;
    const docsEnabled = beEnabled && $("#be-docs-enabled").checked;
    $("#be-docs-domain").disabled = !docsEnabled;
    $("#env-staging").disabled = !beEnabled;
    $("#env-testing").disabled = !beEnabled;

    // Admin/Dashboard domains — disable when not enabled
    $("#admin-domain").disabled = !$("#admin-enabled").checked;
    $("#dash-domain").disabled = !$("#dash-enabled").checked;
}}

// Wire up all inputs
document.addEventListener("DOMContentLoaded", () => {{
    populateForm();

    for (const el of $$("input, select")) {{
        const event = el.type === "text" ? "input" : "change";
        el.addEventListener(event, () => {{
            updateDisabledState();
            debounceSave();
        }});
    }}

    // Cancel/Deploy buttons
    $("#btn-cancel").addEventListener("click", () => {{
        const cfg = readForm();
        fetch("/api/config", {{
            method: "PATCH",
            headers: {{"Content-Type": "application/json"}},
            body: JSON.stringify(cfg),
        }}).then(() => fetch("/api/cancel", {{ method: "POST" }}))
          .then(() => {{ document.body.textContent = "Cancelled. You can close this tab."; }});
    }});

    $("#btn-deploy").addEventListener("click", () => {{
        const cfg = readForm();
        fetch("/api/config", {{
            method: "PATCH",
            headers: {{"Content-Type": "application/json"}},
            body: JSON.stringify(cfg),
        }}).then(() => fetch("/api/deploy", {{ method: "POST" }}))
          .then(() => {{ document.body.textContent = "Deploying... check your terminal."; }});
    }});
}});
</script>
</body>
</html>"""


class _Handler(BaseHTTPRequestHandler):
    """Handles GET /, PATCH /api/config, POST /api/deploy, POST /api/cancel."""

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
            self.send_header("Cache-Control", "no-store")
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

    def do_POST(self):
        if self.path in ("/api/deploy", "/api/cancel"):
            action = "deploy" if self.path == "/api/deploy" else "cancel"
            self.server.action = action
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
            # Shut down in a thread so the response completes first
            import threading
            threading.Thread(target=self.server.shutdown, daemon=True).start()
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
    port: int = 4040,
) -> tuple[HTTPServer, int]:
    """Create and bind the server. Returns (httpd, port)."""
    httpd = HTTPServer(("127.0.0.1", port), _Handler, bind_and_activate=False)
    httpd.allow_reuse_address = True
    httpd.server_bind()
    httpd.server_activate()
    httpd.config_name = name
    httpd.cfg = cfg
    httpd.deployed_keys = deployed_keys
    httpd.urls = urls or {}
    httpd.live_domains = live_domains or set()
    httpd.action = "cancel"  # default if Ctrl+C or window closed
    port = httpd.server_address[1]
    return httpd, port


def serve_editor(
    name: str,
    cfg: dict,
    *,
    deployed_keys: set[str] | None = None,
    urls: dict[str, str] | None = None,
    live_domains: set[str] | None = None,
    port: int | None = None,
) -> str:
    """Open the web editor and block until deploy/cancel/Ctrl+C.

    Returns ``"deploy"`` or ``"cancel"``.
    """
    if deployed_keys is None:
        deployed_keys = set()
    if port is None:
        port = cfg.get("port", 4040)
    httpd, port = start_server(
        name, cfg,
        deployed_keys=deployed_keys,
        urls=urls,
        live_domains=live_domains,
        port=port,
    )
    url = f"http://localhost:{port}/"
    print(f"  Editing at {url} — press Ctrl+C to cancel")
    webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.action = "cancel"
    finally:
        httpd.server_close()
    return httpd.action
