"""Local web editor for configurator configs."""

from __future__ import annotations

import json
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler

from configurator.cli import save_config
from configurator import __version__
from configurator.features import discover_features
from configurator.features.base import Feature, RenderContext


def _inject_version_badge(html: str, version: str) -> str:
    """Inject a version badge after the <legend> tag in a feature's fieldset."""
    legend_end = html.find("</legend>")
    if legend_end == -1:
        return html
    insert_at = legend_end + len("</legend>")
    badge = f'\n<span class="feature-version">v{version}</span>'
    return html[:insert_at] + badge + html[insert_at:]


def _compose_html_sections(features: list[Feature], ctx: RenderContext) -> str:
    """Compose feature HTML, grouping features that share a group into a single fieldset."""
    parts: list[str] = []
    current_group: str | None = None

    for f in features:
        meta = f.meta()
        feature_html = _inject_version_badge(f.config_html(ctx), meta.version)

        if meta.group and meta.group == current_group:
            parts.append(feature_html)
        else:
            if current_group is not None:
                parts.append("</fieldset>")

            if meta.group:
                group_label = meta.group.replace("_", " ").title()
                parts.append(f'<fieldset>\n<legend>{group_label}</legend>')
                current_group = meta.group
            else:
                current_group = None

            parts.append(feature_html)

    if current_group is not None:
        parts.append("</fieldset>")

    return "\n\n".join(parts)


def build_page(
    cfg: dict,
    *,
    deployed_keys: set[str],
    urls: dict[str, str] | None = None,
    live_domains: set[str] | None = None,
) -> str:
    """Build the HTML page by composing feature fragments."""
    features = discover_features()
    ctx = RenderContext(
        deployed_keys=deployed_keys,
        urls=urls or {},
        live_domains=live_domains or set(),
        config=cfg,
    )

    html_body = _compose_html_sections(features, ctx)
    js_read = "\n".join(f.config_js_read() for f in features)
    js_populate = "\n".join(f.config_js_populate() for f in features)
    js_update = "\n".join(
        block for f in features if (block := f.config_js_update_disabled())
    )

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
    margin-bottom: 1rem; background: var(--card); position: relative;
}}
legend {{ font-weight: 600; font-size: 0.95rem; padding: 0 0.4rem; }}
.feature-version {{
    position: absolute; top: 0.5rem; right: 0.7rem;
    font-size: 0.65rem; color: var(--fg-dim); font-weight: 400;
}}
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

{html_body}

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
{js_read}
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
{js_populate}

    updateDisabledState();
}}

function updateDisabledState() {{
{js_update}
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
            import threading
            threading.Thread(target=self.server.shutdown, daemon=True).start()
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        pass


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
    httpd.action = "cancel"
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
