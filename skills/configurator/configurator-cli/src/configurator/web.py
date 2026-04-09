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


def _compose_column(features: list[Feature], ctx: RenderContext, column: str) -> str:
    """Compose feature HTML for a single column, grouping features that share a group."""
    col_features = [f for f in features if f.meta().column == column]
    parts: list[str] = []
    current_group: str | None = None

    for f in col_features:
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

    left_html = _compose_column(features, ctx, "left")
    right_html = _compose_column(features, ctx, "right")
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
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Instrument+Serif:ital@0;1&family=Manrope:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
:root {{
    --bg: #0c0c0f; --surface: #14141a; --surface-hover: #1c1c24;
    --fg: #e8e6e3; --fg-muted: #8a8a9a; --fg-dim: #5a5a6a;
    --border: #2a2a36; --border-accent: #3d3d50;
    --input-bg: #1c1c24; --input-border: #3d3d50;
    --disabled-bg: #14141a; --disabled-fg: #5a5a6a;
    --link: #c4a35a; --accent: #c4a35a; --accent-hover: #d4b36a;
    --accent-dim: rgba(196, 163, 90, 0.15);
    --btn-secondary: #2a2a36; --btn-secondary-fg: #8a8a9a; --btn-secondary-hover: #3d3d50;
    --badge-deploy-bg: rgba(92, 178, 112, 0.12); --badge-deploy-fg: #5cb270;
    --badge-live-bg: rgba(90, 143, 212, 0.12); --badge-live-fg: #5a8fd4;
    --green: #5cb270; --red: #d45454;
    --mono: 'DM Mono', monospace; --serif: 'Instrument Serif', serif; --sans: 'Manrope', sans-serif;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
    font-family: var(--sans); background: var(--bg); color: var(--fg);
    font-size: 15px; line-height: 1.7; -webkit-font-smoothing: antialiased;
    padding: 0;
}}
.grain {{
    position: fixed; top: 0; left: 0; width: 100%; height: 100%;
    pointer-events: none; opacity: 0.03;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
    z-index: 9999;
}}
header {{
    padding: 40px 0 32px; text-align: center;
    border-bottom: 1px solid var(--border);
    background: linear-gradient(180deg, rgba(196,163,90,0.04) 0%, var(--bg) 100%);
}}
header h1 {{
    font-family: var(--serif); font-size: 2.4rem; font-weight: 400;
    color: var(--accent); font-style: italic; letter-spacing: -0.02em;
    line-height: 1.1; margin-bottom: 4px;
}}
header .version {{
    font-family: var(--mono); font-size: 0.75rem; color: var(--fg-dim);
    letter-spacing: 0.05em;
}}
.container {{
    max-width: 72rem; margin: 0 auto; padding: 2rem 2rem 1rem;
}}
.columns {{
    display: grid; grid-template-columns: 1fr 1fr; gap: 2rem;
    align-items: start;
}}
@media (max-width: 768px) {{
    .columns {{ grid-template-columns: 1fr; }}
}}
.col-header {{
    font-family: var(--mono); font-size: 0.7rem; font-weight: 500;
    letter-spacing: 0.1em; text-transform: uppercase;
    color: var(--fg-muted); margin-bottom: 1rem;
    padding-bottom: 0.5rem; border-bottom: 1px solid var(--border);
}}
fieldset {{
    border: 1px solid var(--border); border-radius: 8px; padding: 1.2rem;
    margin-bottom: 1rem; background: var(--surface); position: relative;
}}
fieldset:hover {{ border-color: var(--border-accent); }}
legend {{
    font-family: var(--sans); font-weight: 600; font-size: 0.9rem;
    padding: 0 0.4rem; color: var(--fg);
}}
.feature-version {{
    position: absolute; top: 0.5rem; right: 0.7rem;
    font-family: var(--mono); font-size: 0.6rem; color: var(--fg-dim);
    font-weight: 400; letter-spacing: 0.03em;
}}
.field {{ margin-bottom: 0.8rem; }}
.field:last-child {{ margin-bottom: 0; }}
label {{
    display: block; font-size: 0.8rem; color: var(--fg-muted);
    margin-bottom: 0.2rem; font-family: var(--sans);
}}
input[type="text"], select {{
    width: 100%; padding: 0.45rem 0.6rem;
    border: 1px solid var(--input-border); border-radius: 4px;
    font-size: 0.85rem; font-family: var(--mono);
    background: var(--input-bg); color: var(--fg);
}}
input[type="text"]:focus, select:focus {{
    outline: none; border-color: var(--accent);
    box-shadow: 0 0 0 2px var(--accent-dim);
}}
input[type="text"]:disabled, select:disabled {{
    background: var(--disabled-bg); color: var(--disabled-fg);
}}
input[type="checkbox"] {{
    accent-color: var(--accent);
}}
.checkbox-group {{ display: flex; flex-wrap: wrap; gap: 0.6rem; margin-top: 0.3rem; }}
.checkbox-group label {{
    display: flex; align-items: center; gap: 0.3rem;
    font-size: 0.85rem; color: var(--fg); cursor: pointer;
}}
.checkbox-group input:disabled + span {{ color: var(--disabled-fg); }}
.toggle-row {{
    display: flex; align-items: center; gap: 0.5rem;
    margin-bottom: 0.6rem;
}}
.toggle-row label {{ margin-bottom: 0; font-size: 0.85rem; color: var(--fg); }}
.badge {{
    font-family: var(--mono); font-size: 0.65rem;
    padding: 0.15rem 0.5rem; border-radius: 3px; font-weight: 500;
    letter-spacing: 0.03em;
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
    font-size: 0.85rem; color: var(--fg); cursor: pointer;
}}
.sub-field {{ margin-left: 1.4rem; margin-top: 0.4rem; }}
.readonly {{
    font-family: var(--mono); font-size: 0.85rem;
    color: var(--fg-dim); padding: 0.4rem 0;
}}
.actions {{
    display: flex; justify-content: flex-end; gap: 0.8rem;
    margin-top: 0.5rem; margin-bottom: 2rem;
    padding-top: 1.5rem; border-top: 1px solid var(--border);
}}
.btn {{
    padding: 0.5rem 1.6rem; border: 1px solid var(--border);
    border-radius: 6px; font-size: 0.85rem; font-weight: 500;
    cursor: pointer; font-family: var(--sans);
    transition: all 0.15s ease;
}}
.btn-cancel {{
    background: transparent; color: var(--fg-muted);
    border-color: var(--border);
}}
.btn-cancel:hover {{ background: var(--surface-hover); color: var(--fg); border-color: var(--border-accent); }}
.btn-deploy {{
    background: var(--accent); color: var(--bg);
    border-color: var(--accent); font-weight: 600;
}}
.btn-deploy:hover {{ background: var(--accent-hover); border-color: var(--accent-hover); }}
.saved-indicator {{
    position: fixed; top: 1rem; right: 1rem;
    font-family: var(--mono); font-size: 0.75rem;
    color: var(--green); opacity: 0; transition: opacity 0.3s;
    letter-spacing: 0.05em;
}}
.saved-indicator.visible {{ opacity: 1; }}
</style>
</head>
<body>
<div class="grain"></div>

<header>
<h1>Configurator</h1>
<div class="version">v{version}</div>
</header>

<div class="container">
<div class="columns">

<div class="col-left">
<div class="col-header">Infrastructure &amp; Deployments</div>
{left_html}
</div>

<div class="col-right">
<div class="col-header">Settings &amp; Features</div>
{right_html}
</div>

</div>

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
