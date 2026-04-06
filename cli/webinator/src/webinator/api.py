"""HTTP helpers using only stdlib urllib."""

import json
import sys
import urllib.request
import urllib.error


def _request(url: str, auth_header: str, *, method: str = "GET",
             data: dict | list | None = None,
             headers: dict | None = None) -> tuple[int, bytes]:
    """Low-level HTTP request. Returns (status_code, body_bytes)."""
    body_bytes = None
    if data is not None:
        body_bytes = json.dumps(data).encode()

    req = urllib.request.Request(url, data=body_bytes, method=method)
    req.add_header("Authorization", auth_header)
    req.add_header("Accept", "application/json")
    if body_bytes is not None:
        req.add_header("Content-Type", "application/json")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)

    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except urllib.error.URLError as e:
        print(f"error: {e.reason}", file=sys.stderr)
        sys.exit(1)


def api_request(url: str, auth_header: str, *, method: str = "GET",
                data: dict | list | None = None) -> tuple[int, dict | list]:
    """HTTP request returning (status_code, parsed_json)."""
    code, body = _request(url, auth_header, method=method, data=data)
    try:
        parsed = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        parsed = {"raw": body.decode(errors="replace")}
    return code, parsed


def api_get(url: str, auth_header: str) -> list | dict:
    """GET request that exits on error. Returns parsed JSON."""
    code, parsed = api_request(url, auth_header)
    if code != 200:
        print(f"error: API returned HTTP {code}", file=sys.stderr)
        if isinstance(parsed, dict):
            print(json.dumps(parsed, indent=2), file=sys.stderr)
        sys.exit(1)
    return parsed
