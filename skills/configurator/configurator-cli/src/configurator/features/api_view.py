"""API View feature — displays backend API endpoints and parameters."""

from __future__ import annotations

import re
from pathlib import Path

from configurator.features.base import Feature, FeatureMeta, RenderContext

_VERSION = "1.0.0"


class ApiViewFeature(Feature):
    def meta(self) -> FeatureMeta:
        return FeatureMeta(
            id="api_view",
            label="API",
            version=_VERSION,
            order=26,
            dependencies=["backend"],
            category="api-view",
        )

    def config_html(self, ctx: RenderContext) -> str:
        backend = ctx.config.get("backend", {})
        if not backend.get("enabled"):
            return (
                '<fieldset>\n<legend>API</legend>\n'
                '<p class="readonly" style="color: var(--fg-dim);">'
                'No backend configured. Enable a backend to view API endpoints.'
                '</p>\n</fieldset>'
            )

        endpoints = _read_endpoints(ctx.config.get("local_path"))
        auth_providers = ctx.config.get("auth_providers", [])
        backend_domain = backend.get("domain", "")

        # Header with backend domain
        header = ""
        if backend_domain:
            header = f'<div class="api-base-url">Base URL: <code>https://{_esc(backend_domain)}</code></div>\n'

        if not endpoints:
            # Show default endpoints based on config
            endpoints = _default_endpoints(ctx.config)

        if not endpoints:
            return (
                '<fieldset>\n<legend>API</legend>\n'
                f'{header}'
                '<p class="readonly" style="color: var(--fg-dim);">'
                'No API endpoints found. Deploy the backend to generate routes.'
                '</p>\n</fieldset>'
            )

        # Group endpoints by prefix
        groups: dict[str, list[dict]] = {}
        for ep in endpoints:
            prefix = ep["path"].split("/")[2] if ep["path"].count("/") >= 2 else "general"
            groups.setdefault(prefix, []).append(ep)

        rows = ""
        for group_name, group_eps in groups.items():
            rows += f'<div class="api-group">\n'
            rows += f'<div class="api-group-name">/{_esc(group_name)}</div>\n'
            rows += '<table class="api-endpoints">\n'
            rows += '<tr><th>Method</th><th>Path</th><th>Auth</th><th>Description</th></tr>\n'
            for ep in group_eps:
                method_class = f'api-method-{ep["method"].lower()}'
                rows += (
                    f'<tr>'
                    f'<td><span class="{method_class}">{_esc(ep["method"])}</span></td>'
                    f'<td class="api-path">{_esc(ep["path"])}</td>'
                    f'<td class="api-auth">{_esc(ep["auth"])}</td>'
                    f'<td>{_esc(ep["description"])}</td>'
                    f'</tr>\n'
                )
                # Show parameters if any
                if ep.get("params"):
                    rows += (
                        f'<tr><td colspan="4" class="api-params">'
                        f'<span class="api-params-label">Params:</span> '
                    )
                    for p in ep["params"]:
                        required = ' <span class="api-required">required</span>' if p.get("required") else ""
                        rows += (
                            f'<span class="api-param">'
                            f'<code>{_esc(p["name"])}</code>'
                            f' <span class="api-param-type">{_esc(p["type"])}</span>'
                            f'{required}'
                            f'</span> '
                        )
                    rows += '</td></tr>\n'
            rows += '</table>\n</div>\n'

        return (
            '<fieldset>\n<legend>API</legend>\n'
            f'{header}{rows}'
            '</fieldset>'
        )

    def config_js_read(self) -> str:
        return ""

    def config_js_populate(self) -> str:
        return ""

    def config_js_update_disabled(self) -> str:
        return ""

    def default_config(self) -> dict:
        return {}

    def manifest_to_config(self, manifest: dict) -> dict:
        return {}

    def deployed_keys(self, manifest: dict) -> set[str]:
        return set()


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _read_endpoints(local_path: str | None) -> list[dict]:
    """Read API endpoints from the project's route files."""
    if not local_path:
        return []

    base = Path(local_path)
    endpoints: list[dict] = []

    # Look for Hono route files
    for pattern in [
        "backend/src/routes/**/*.ts",
        "src/routes/**/*.ts",
    ]:
        for route_file in sorted(base.glob(pattern)):
            endpoints.extend(_parse_hono_routes(route_file))
        if endpoints:
            return endpoints

    return []


def _parse_hono_routes(path: Path) -> list[dict]:
    """Parse Hono-style route definitions from a TypeScript file."""
    try:
        content = path.read_text()
    except (OSError, UnicodeDecodeError):
        return []

    endpoints = []

    # Match patterns like: app.get('/path', ...) or .get('/path', ...)
    for match in re.finditer(
        r'\.(get|post|put|patch|delete)\s*\(\s*["\']([^"\']+)["\']',
        content,
        re.IGNORECASE,
    ):
        method = match.group(1).upper()
        route_path = match.group(2)

        # Try to find a comment above or beside
        line_start = content.rfind("\n", 0, match.start()) + 1
        line = content[line_start:match.start()].strip()
        description = ""
        if "//" in line:
            description = line.split("//", 1)[1].strip()

        # Detect auth requirement
        auth = "none"
        # Check for middleware in the route
        route_context = content[match.start():match.start() + 200]
        if "auth" in route_context.lower() or "bearer" in route_context.lower():
            auth = "bearer"
        if "admin" in route_path.lower():
            auth = "bearer (admin)"

        # Detect path parameters
        params = []
        for param_match in re.finditer(r':(\w+)', route_path):
            params.append({
                "name": param_match.group(1),
                "type": "string",
                "required": True,
            })

        endpoints.append({
            "method": method,
            "path": route_path,
            "auth": auth,
            "description": description or _infer_description(method, route_path),
            "params": params,
        })

    return endpoints


def _infer_description(method: str, path: str) -> str:
    """Infer a description from method + path."""
    parts = [p for p in path.split("/") if p and not p.startswith(":")]
    resource = parts[-1] if parts else "resource"

    descs = {
        "GET": f"Get {resource}",
        "POST": f"Create {resource}",
        "PUT": f"Update {resource}",
        "PATCH": f"Update {resource}",
        "DELETE": f"Delete {resource}",
    }
    return descs.get(method, resource)


def _default_endpoints(config: dict) -> list[dict]:
    """Generate default endpoint list based on config."""
    endpoints = [
        {"method": "GET", "path": "/api/health", "auth": "none",
         "description": "Health check", "params": []},
    ]

    auth_providers = config.get("auth_providers", [])
    if auth_providers:
        endpoints.extend([
            {"method": "POST", "path": "/api/auth/register", "auth": "none",
             "description": "Create account",
             "params": [
                 {"name": "email", "type": "string", "required": True},
                 {"name": "password", "type": "string", "required": True},
             ]},
            {"method": "POST", "path": "/api/auth/login", "auth": "none",
             "description": "Get access + refresh tokens",
             "params": [
                 {"name": "email", "type": "string", "required": True},
                 {"name": "password", "type": "string", "required": True},
             ]},
            {"method": "POST", "path": "/api/auth/refresh", "auth": "none",
             "description": "Exchange refresh token",
             "params": [{"name": "refreshToken", "type": "string", "required": True}]},
            {"method": "POST", "path": "/api/auth/logout", "auth": "bearer",
             "description": "Revoke refresh token", "params": []},
            {"method": "GET", "path": "/api/auth/me", "auth": "bearer",
             "description": "Get current user", "params": []},
            {"method": "GET", "path": "/.well-known/jwks.json", "auth": "none",
             "description": "Public key for JWT verification", "params": []},
        ])

    admin_sites = config.get("admin_sites", {})
    if admin_sites.get("admin", {}).get("enabled"):
        endpoints.extend([
            {"method": "GET", "path": "/api/admin/users", "auth": "bearer (admin)",
             "description": "List all users", "params": []},
            {"method": "PATCH", "path": "/api/admin/users/:id", "auth": "bearer (admin)",
             "description": "Update user role",
             "params": [{"name": "id", "type": "uuid", "required": True}]},
            {"method": "DELETE", "path": "/api/admin/users/:id", "auth": "bearer (admin)",
             "description": "Delete user",
             "params": [{"name": "id", "type": "uuid", "required": True}]},
        ])

    return endpoints
