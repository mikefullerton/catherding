"""Local web editor for configurator configs."""

from __future__ import annotations

import json
from pathlib import Path
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler

from configurator.cli import save_config
from configurator import __version__
from configurator.features import discover_features
from configurator.features.base import Feature, RenderContext

SITES_DIR = Path.home() / ".local-server" / "sites"
CADDY_URL = "http://localhost:2080/configurator.html"

# Category definitions: (id, label) in display order
CATEGORIES = [
    ("project", "Project"),
    ("website", "Website"),
    ("backend", "Backend"),
    ("data-model", "Data Model"),
    ("api-view", "API"),
    ("auth", "Auth & Access"),
    ("ux", "User Experience"),
    ("comms", "Communications"),
    ("analytics", "Analytics & Flags"),
    ("secrets", "Secrets"),
    ("history", "History"),
    ("manifest", "Manifest"),
]


def _inject_version_badge(html: str, version: str) -> str:
    """Inject a version badge after the <legend> tag in a feature's fieldset."""
    legend_end = html.find("</legend>")
    if legend_end == -1:
        return html
    insert_at = legend_end + len("</legend>")
    badge = f'\n<span class="feature-version">v{version}</span>'
    return html[:insert_at] + badge + html[insert_at:]


def _compose_category(features: list[Feature], ctx: RenderContext, category: str) -> str:
    """Compose feature HTML for a single category, grouping features that share a group."""
    cat_features = [f for f in features if f.meta().category == category]
    parts: list[str] = []
    current_group: str | None = None

    for f in cat_features:
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
    api_base: str = "",
    author: dict[str, str] | None = None,
) -> str:
    """Build the HTML page by composing feature fragments."""
    features = discover_features()
    ctx = RenderContext(
        deployed_keys=deployed_keys,
        urls=urls or {},
        live_domains=live_domains or set(),
        config=cfg,
    )

    # Build panels per category
    panels_html = ""
    for cat_id, cat_label in CATEGORIES:
        if cat_id == "history":
            panels_html += (
                '<div class="panel" id="cat-history" style="display:none">\n'
                '<fieldset>\n<legend>Change History</legend>\n'
                '<div id="history-content" class="history-content">'
                '<p class="readonly" style="color: var(--fg-dim);">No changes yet.</p>'
                '</div>\n'
                '</fieldset>\n</div>\n\n'
            )
            continue
        if cat_id == "manifest":
            # Manifest panel is JS-driven, not feature-composed
            panels_html += (
                '<div class="panel" id="cat-manifest" style="display:none">\n'
                '<fieldset>\n<legend>Manifest</legend>\n'
                '<pre id="manifest-json" class="manifest-pre"></pre>\n'
                '</fieldset>\n</div>\n\n'
            )
            continue
        cat_html = _compose_category(features, ctx, cat_id)
        if not cat_html:
            continue
        hidden = "" if cat_id == "project" else ' style="display:none"'
        panels_html += f'<div class="panel" id="cat-{cat_id}"{hidden}>\n{cat_html}\n</div>\n\n'

    # Build nav links
    nav_html = ""
    for cat_id, cat_label in CATEGORIES:
        if cat_id in ("history", "manifest"):
            nav_html += f'    <a href="#" data-cat="{cat_id}">{cat_label}</a>\n'
            continue
        cat_features = [f for f in features if f.meta().category == cat_id]
        if not cat_features:
            continue
        active = ' class="active"' if cat_id == "project" else ""
        nav_html += f'    <a href="#" data-cat="{cat_id}"{active}>{cat_label}</a>\n'

    js_read = "\n".join(f.config_js_read() for f in features)
    js_populate = "\n".join(f.config_js_populate() for f in features)
    js_update = "\n".join(
        block for f in features if (block := f.config_js_update_disabled())
    )

    import uuid
    config_json = json.dumps(cfg, indent=2)
    deployed_json = json.dumps(sorted(deployed_keys))
    urls_json = json.dumps(urls or {})
    live_json = json.dumps(sorted(live_domains or set()))
    author_json = json.dumps(author or {})
    session_id = str(uuid.uuid4())
    # Build identifier map from all features
    all_identifiers: dict[str, str] = {}
    for f in features:
        all_identifiers.update(f.config_identifiers())
    identifiers_json = json.dumps(all_identifiers)
    change_history_json = json.dumps(cfg.get("_change_history", []))
    version = __version__
    project_name = cfg.get("repo") or cfg.get("display_name") or "Untitled"
    page_title = f"Configurator — {project_name}"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{page_title}</title>
<meta name="description" content="Deployment config for {project_name} — domain, backend, auth, and service settings">
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
    --nav-w: 200px; --header-h: 80px;
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

/* Header */
header {{
    height: var(--header-h); display: flex; align-items: center;
    padding: 0 32px; border-bottom: 1px solid var(--border);
    background: linear-gradient(180deg, rgba(196,163,90,0.04) 0%, var(--bg) 100%);
}}
header h1 {{
    font-family: var(--serif); font-size: 1.6rem; font-weight: 400;
    color: var(--accent); font-style: italic; letter-spacing: -0.02em;
}}
header .version {{
    font-family: var(--mono); font-size: 0.7rem; color: var(--fg-dim);
    letter-spacing: 0.05em; margin-left: 12px;
}}

/* Sidebar nav */
nav {{
    position: fixed; top: var(--header-h); left: 0; z-index: 200;
    width: var(--nav-w);
    height: calc(100vh - var(--header-h));
    background: rgba(12, 12, 15, 0.96);
    backdrop-filter: blur(12px);
    border-right: 1px solid var(--border);
    padding: 24px 0; overflow-y: auto;
    display: flex; flex-direction: column;
}}
nav a {{
    display: block; padding: 10px 24px;
    font-family: var(--mono); font-size: 0.75rem;
    color: var(--fg-muted); text-decoration: none;
    letter-spacing: 0.04em;
    border-left: 2px solid transparent;
    transition: all 0.15s;
}}
nav a:hover {{ color: var(--fg); border-left-color: var(--accent); }}
nav a.active {{
    color: var(--accent); border-left-color: var(--accent);
    background: var(--accent-dim);
}}

/* Main content */
main {{
    margin-left: var(--nav-w);
    padding: 2rem 2.5rem 5rem;
    max-width: 48rem;
}}
.panel {{ animation: fadeIn 0.15s ease; }}
@keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}

/* Form elements */
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
input[type="checkbox"] {{ accent-color: var(--accent); }}
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

/* Actions bar — pinned to bottom */
.actions {{
    position: fixed; bottom: 0; left: var(--nav-w); right: 0;
    display: flex; justify-content: flex-end; gap: 0.8rem;
    padding: 1rem 2.5rem;
    background: var(--bg);
    border-top: 1px solid var(--border);
    z-index: 100;
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

/* Data Model */
.db-table {{ margin-bottom: 1.2rem; }}
.db-table-name {{
    font-family: var(--mono); font-size: 0.85rem; font-weight: 600;
    color: var(--accent); margin-bottom: 0.4rem;
}}
.db-columns {{
    width: 100%; border-collapse: collapse; font-size: 0.8rem;
}}
.db-columns th {{
    text-align: left; padding: 0.3rem 0.6rem;
    font-family: var(--mono); font-size: 0.7rem; color: var(--fg-dim);
    border-bottom: 1px solid var(--border); font-weight: 500;
    letter-spacing: 0.04em; text-transform: uppercase;
}}
.db-columns td {{
    padding: 0.3rem 0.6rem; border-bottom: 1px solid var(--border);
    font-family: var(--mono);
}}
.db-col-name {{ color: var(--fg); }}
.db-col-type {{ color: var(--fg-muted); }}
.db-col-constraints {{ color: var(--fg-dim); font-size: 0.75rem; }}

/* API */
.api-base-url {{
    font-size: 0.8rem; color: var(--fg-muted); margin-bottom: 1rem;
}}
.api-base-url code {{
    font-family: var(--mono); color: var(--accent); font-size: 0.8rem;
}}
.api-group {{ margin-bottom: 1.2rem; }}
.api-group-name {{
    font-family: var(--mono); font-size: 0.8rem; font-weight: 600;
    color: var(--fg-muted); margin-bottom: 0.4rem;
}}
.api-endpoints {{
    width: 100%; border-collapse: collapse; font-size: 0.8rem;
}}
.api-endpoints th {{
    text-align: left; padding: 0.3rem 0.6rem;
    font-family: var(--mono); font-size: 0.7rem; color: var(--fg-dim);
    border-bottom: 1px solid var(--border); font-weight: 500;
    letter-spacing: 0.04em; text-transform: uppercase;
}}
.api-endpoints td {{
    padding: 0.3rem 0.6rem; border-bottom: 1px solid var(--border);
}}
.api-path {{ font-family: var(--mono); color: var(--fg); }}
.api-auth {{ font-family: var(--mono); font-size: 0.75rem; color: var(--fg-dim); }}
.api-method-get {{ font-family: var(--mono); color: var(--green); font-weight: 600; font-size: 0.75rem; }}
.api-method-post {{ font-family: var(--mono); color: var(--accent); font-weight: 600; font-size: 0.75rem; }}
.api-method-put, .api-method-patch {{ font-family: var(--mono); color: #5a8fd4; font-weight: 600; font-size: 0.75rem; }}
.api-method-delete {{ font-family: var(--mono); color: var(--red); font-weight: 600; font-size: 0.75rem; }}
.api-params {{
    padding: 0.2rem 0.6rem 0.4rem; font-size: 0.75rem;
    color: var(--fg-dim); border-bottom: 1px solid var(--border);
}}
.api-params-label {{ color: var(--fg-dim); font-style: italic; }}
.api-param {{
    display: inline-block; margin-right: 0.8rem;
}}
.api-param code {{ font-family: var(--mono); color: var(--fg-muted); font-size: 0.75rem; }}
.api-param-type {{ color: var(--fg-dim); font-size: 0.7rem; }}
.api-required {{ color: var(--red); font-size: 0.65rem; font-weight: 500; }}

/* Manifest */
.manifest-pre {{
    font-family: var(--mono); font-size: 0.8rem;
    color: var(--fg); line-height: 1.6;
    white-space: pre-wrap; word-break: break-word;
    padding: 0.4rem 0; margin: 0;
}}
.manifest-dim {{ color: var(--fg-dim); }}
.manifest-new {{ color: var(--green); }}
.manifest-changed {{ color: var(--accent); }}

/* History */
.history-content {{ max-height: 600px; overflow-y: auto; }}
.history-table {{
    width: 100%; border-collapse: collapse; font-size: 0.85rem;
}}
.history-table th {{
    text-align: left; padding: 0.4rem 0.6rem; color: var(--fg-muted);
    border-bottom: 1px solid var(--border); font-weight: 500;
}}
.history-table td {{
    padding: 0.4rem 0.6rem; border-bottom: 1px solid var(--border);
}}
.history-date {{ color: var(--fg-muted); white-space: nowrap; font-size: 0.8rem; }}
.history-item code {{ font-size: 0.8rem; color: var(--accent); }}
.history-value {{ font-family: var(--mono); font-size: 0.8rem; }}
.history-author {{ color: var(--fg-muted); font-size: 0.8rem; }}
.history-add {{ color: var(--green); }}
.history-remove {{ color: var(--red); }}
.history-change {{ color: var(--accent); }}

/* Secrets */
.secret-list {{ display: flex; flex-direction: column; gap: 0.5rem; }}
.secret-row {{
    display: flex; align-items: center; gap: 0.8rem;
    font-size: 0.85rem;
}}
.secret-name {{
    font-family: var(--mono); font-size: 0.8rem; color: var(--fg);
    min-width: 140px;
}}
.secret-ok {{
    font-family: var(--mono); font-size: 0.75rem; color: var(--green);
    font-weight: 500; letter-spacing: 0.03em;
}}
.secret-missing {{
    font-family: var(--mono); font-size: 0.75rem; color: var(--red);
    font-weight: 500; letter-spacing: 0.03em;
}}
.secret-reason {{
    font-size: 0.75rem; color: var(--fg-dim); font-style: italic;
}}
.secret-hint {{
    margin-top: 0.8rem; padding: 0.6rem 0.8rem;
    background: rgba(212, 84, 84, 0.08); border: 1px solid rgba(212, 84, 84, 0.2);
    border-radius: 4px; font-size: 0.8rem; color: var(--fg-muted);
}}
.secret-hint code {{
    font-family: var(--mono); font-size: 0.75rem; color: var(--accent);
}}

/* Mobile */
@media (max-width: 640px) {{
    nav {{ display: none; }}
    main {{ margin-left: 0; padding: 1.5rem 1.5rem 5rem; }}
    .panel {{ display: block !important; }}
}}
</style>
</head>
<body>
<div class="grain"></div>

<header>
<h1>Configurator</h1>
<span class="version">v{version}</span>
</header>

<nav>
{nav_html}
</nav>

<main>
{panels_html}
</main>

<div class="actions">
    <button type="button" id="btn-cancel" class="btn btn-cancel">Cancel</button>
    <button type="button" id="btn-deploy" class="btn btn-deploy">Deploy</button>
</div>

<div class="saved-indicator" id="saved">Saved</div>

<script>
const CONFIG = {config_json};
const ORIGINAL_CONFIG = JSON.parse(JSON.stringify(CONFIG));
const DEPLOYED = new Set({deployed_json});
const URLS = {urls_json};
const LIVE = new Set({live_json});
const AUTHOR = {author_json};
const SESSION_ID = "{session_id}";
const CONFIGURATOR_VERSION = "{version}";
const IDENTIFIERS = {identifiers_json};
let CHANGE_HISTORY = {change_history_json};
let LAST_CONFIG = JSON.parse(JSON.stringify(CONFIG));

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

let saveTimer = null;

function debounceSave() {{
    clearTimeout(saveTimer);
    saveTimer = setTimeout(saveConfig, 300);
}}

function configToIdentifier(path) {{
    // Map config dict paths to formal identifiers
    // e.g., "admin_sites.admin.enabled" -> "admin.enabled"
    const map = {{
        "displayName": "project.display-name",
        "repo": "project.repo",
        "org": "project.org",
        "domain": "project.domain",
    }};
    if (map[path]) return map[path];
    // admin_sites.admin.X -> admin.X, admin_sites.dashboard.X -> dashboard.X
    const adminMatch = path.match(/^admin_sites\\.([^.]+)\\.(.+)$/);
    if (adminMatch) return adminMatch[1] + "." + adminMatch[2].replace(/_/g, "-");
    // auth_providers -> auth.providers
    if (path === "auth_providers") return "auth.providers";
    // Regular: feature_id.key -> feature-id.key (underscores to hyphens)
    return path.replace(/_/g, "-");
}}

function diffConfigs(oldCfg, newCfg, prefix) {{
    prefix = prefix || "";
    const changes = [];
    const allKeys = new Set([...Object.keys(oldCfg || {{}}), ...Object.keys(newCfg || {{}})]);
    for (const key of allKeys) {{
        if (key.startsWith("_") || key === "configurator_version" || key === "local_path" || key === "create_repo") continue;
        const path = prefix ? prefix + "." + key : key;
        const oldVal = oldCfg ? oldCfg[key] : undefined;
        const newVal = newCfg ? newCfg[key] : undefined;
        if (typeof oldVal === "object" && !Array.isArray(oldVal) && oldVal !== null &&
            typeof newVal === "object" && !Array.isArray(newVal) && newVal !== null) {{
            changes.push(...diffConfigs(oldVal, newVal, path));
        }} else if (JSON.stringify(oldVal) !== JSON.stringify(newVal)) {{
            const identifier = configToIdentifier(path);
            let changeType = "change";
            if (oldVal === undefined || oldVal === "" || oldVal === false) changeType = "add";
            if (newVal === undefined || newVal === "" || newVal === false) changeType = "remove";
            changes.push({{
                date: new Date().toISOString(),
                author: AUTHOR,
                item: identifier,
                change_type: changeType,
                old_value: oldVal === undefined ? null : oldVal,
                new_value: newVal === undefined ? null : newVal,
                summary: "",
                configurator_version: CONFIGURATOR_VERSION,
                session_id: SESSION_ID,
            }});
        }}
    }}
    return changes;
}}

function saveConfig() {{
    const cfg = readForm();
    const changes = diffConfigs(LAST_CONFIG, cfg);
    if (changes.length > 0) {{
        CHANGE_HISTORY.push(...changes);
    }}
    LAST_CONFIG = JSON.parse(JSON.stringify(cfg));
    cfg._change_history = CHANGE_HISTORY;
    fetch("{api_base}/api/config", {{
        method: "PATCH",
        headers: {{"Content-Type": "application/json"}},
        body: JSON.stringify(cfg),
    }}).then(() => {{
        const el = $("#saved");
        el.classList.add("visible");
        setTimeout(() => el.classList.remove("visible"), 1500);
        updateHistoryPanel();
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

function filterConfig(obj) {{
    if (Array.isArray(obj)) return obj.length ? obj : undefined;
    if (obj && typeof obj === "object") {{
        const out = {{}};
        for (const [k, v] of Object.entries(obj)) {{
            const fv = filterConfig(v);
            if (fv !== undefined && fv !== "" && fv !== false) out[k] = fv;
        }}
        return Object.keys(out).length ? out : undefined;
    }}
    if (obj === "" || obj === false || obj === null || obj === undefined) return undefined;
    return obj;
}}

// Manifest diff renderer — escapes all user content before inserting
function escHtml(s) {{
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}}

function renderManifestDiff(current, original) {{
    const lines = JSON.stringify(current, null, 2).split("\\n");
    const origStr = JSON.stringify(filterConfig(original), null, 2) || "{{}}";
    const hasDeployed = DEPLOYED.size > 0;

    if (!hasDeployed) {{
        return lines.map(l => escHtml(l)).join("\\n");
    }}

    return lines.map(line => {{
        const m = line.match(/^(\\s*)"([^"]+)":\\s*(.+?)\\s*,?$/);
        if (!m) return '<span class="manifest-dim">' + escHtml(line) + '</span>';

        const key = m[2];
        const valStr = m[3].replace(/,$/, "");

        if (origStr.includes('"' + key + '"') && origStr.includes(valStr)) {{
            return '<span class="manifest-dim">' + escHtml(line) + '</span>';
        }}
        if (origStr.includes('"' + key + '"')) {{
            return '<span class="manifest-changed">' + escHtml(line) + '</span>';
        }}
        return '<span class="manifest-new">' + escHtml(line) + '</span>';
    }}).join("\\n");
}}

// History panel
function updateHistoryPanel() {{
    const el = $("#history-content");
    if (!CHANGE_HISTORY.length) {{
        el.innerHTML = '<p class="readonly" style="color: var(--fg-dim);">No changes yet.</p>';
        return;
    }}
    // Show most recent first
    const entries = [...CHANGE_HISTORY].reverse();
    let html = '<table class="history-table"><tr><th>Date</th><th>Item</th><th>Change</th><th>Value</th><th>Author</th></tr>';
    for (const e of entries) {{
        const date = new Date(e.date).toLocaleString();
        const typeClass = "history-" + e.change_type;
        let valueStr = "";
        if (e.change_type === "change") {{
            valueStr = escHtml(String(e.old_value)) + " → " + escHtml(String(e.new_value));
        }} else if (e.change_type === "add") {{
            valueStr = escHtml(String(e.new_value));
        }} else {{
            valueStr = '<span style="text-decoration: line-through;">' + escHtml(String(e.old_value)) + '</span>';
        }}
        const authorStr = e.author && e.author.name ? escHtml(e.author.name) : "unknown";
        html += '<tr>'
            + '<td class="history-date">' + escHtml(date) + '</td>'
            + '<td class="history-item"><code>' + escHtml(e.item) + '</code></td>'
            + '<td class="' + typeClass + '">' + escHtml(e.change_type) + '</td>'
            + '<td class="history-value">' + valueStr + '</td>'
            + '<td class="history-author">' + authorStr + '</td>'
            + '</tr>';
    }}
    html += '</table>';
    el.innerHTML = html;  // nosec: all content escaped via escHtml
}}

// Nav switching
function switchPanel(cat) {{
    for (const p of $$(".panel")) p.style.display = "none";
    const target = $(`#cat-${{cat}}`);
    if (target) target.style.display = "";
    for (const a of $$("nav a")) a.classList.toggle("active", a.dataset.cat === cat);
    if (cat === "history") {{
        updateHistoryPanel();
    }}
    if (cat === "manifest") {{
        const cfg = filterConfig(readForm());
        const el = $("#manifest-json");
        el.textContent = "";
        // Safe: renderManifestDiff escapes all user content via escHtml
        el.innerHTML = renderManifestDiff(cfg, ORIGINAL_CONFIG);  // nosec: content escaped via escHtml
    }}
}}

// Wire up
document.addEventListener("DOMContentLoaded", () => {{
    populateForm();

    for (const el of $$("input, select")) {{
        const event = el.type === "text" ? "input" : "change";
        el.addEventListener(event, () => {{
            updateDisabledState();
            debounceSave();
        }});
    }}

    // Nav
    for (const a of $$("nav a")) {{
        a.addEventListener("click", (e) => {{
            e.preventDefault();
            switchPanel(a.dataset.cat);
        }});
    }}

    // Cancel/Deploy
    $("#btn-cancel").addEventListener("click", () => {{
        const cfg = readForm();
        fetch("{api_base}/api/config", {{
            method: "PATCH",
            headers: {{"Content-Type": "application/json"}},
            body: JSON.stringify(cfg),
        }}).then(() => fetch("{api_base}/api/cancel", {{ method: "POST" }}))
          .then(() => {{ document.body.textContent = "Cancelled. You can close this tab."; }});
    }});

    $("#btn-deploy").addEventListener("click", () => {{
        const cfg = readForm();
        fetch("{api_base}/api/config", {{
            method: "PATCH",
            headers: {{"Content-Type": "application/json"}},
            body: JSON.stringify(cfg),
        }}).then(() => fetch("{api_base}/api/deploy", {{ method: "POST" }}))
          .then(() => {{ document.body.textContent = "Deploying... check your terminal."; }});
    }});
}});
</script>
</body>
</html>"""


class _Handler(BaseHTTPRequestHandler):
    """Handles PATCH /api/config, POST /api/deploy, POST /api/cancel."""

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, PATCH, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def do_PATCH(self):
        if self.path == "/api/config":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            new_cfg = json.loads(body)
            self.server.cfg.update(new_cfg)
            save_config(self.server.config_name, self.server.cfg)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._cors_headers()
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
            self._cors_headers()
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
    author: dict[str, str] | None = None,
) -> str:
    """Open the web editor and block until deploy/cancel/Ctrl+C.

    Returns ``"deploy"`` or ``"cancel"``.
    """
    if deployed_keys is None:
        deployed_keys = set()
    if port is None:
        port = 4040

    # Start API server first so we know the port
    httpd, port = start_server(
        name, cfg,
        deployed_keys=deployed_keys,
        urls=urls,
        live_domains=live_domains,
        port=port,
    )

    # Build HTML with API base pointing directly at the API server
    api_base = f"http://localhost:{port}"
    html = build_page(
        cfg,
        deployed_keys=deployed_keys,
        urls=urls,
        live_domains=live_domains,
        api_base=api_base,
        author=author,
    )

    # Copy to Caddy sites directory
    html_file = SITES_DIR / "configurator.html"
    SITES_DIR.mkdir(parents=True, exist_ok=True)
    html_file.write_text(html, encoding="utf-8")

    print(f"  Editing at {CADDY_URL} — press Ctrl+C to cancel")
    webbrowser.open(CADDY_URL)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.action = "cancel"
    finally:
        html_file.unlink(missing_ok=True)
        httpd.server_close()
    return httpd.action
