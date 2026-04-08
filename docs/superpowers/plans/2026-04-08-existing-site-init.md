# Existing Site Init — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When `site-manager init` is run in a directory containing an existing website, detect it, configure a Cloudflare Worker to serve it, and optionally scaffold backend/admin/dashboard services alongside it — without touching or replacing any existing content files.

**Architecture:** The init flow gains an early detection step that checks for existing web content (index.html, package.json with web deps, framework configs). When detected, a new "existing" project type is used — it only creates Cloudflare Worker config (wrangler.jsonc, worker entry point, manifest) and merges wrangler into package.json. The Python CLI becomes project-type-aware so validation and deployment work correctly for all project types, not just the hardcoded "all 4 services" assumption.

**Tech Stack:** Python (CLI), SKILL.md (Claude-executed init flow), Cloudflare Workers/Wrangler

---

### Task 1: Make manifest validation project-type-aware

**Files:**
- Modify: `cli/site-manager/src/site_manager/manifest.py:76-126`
- Test: `cli/site-manager/tests/test_manifest.py`

Currently `validate_manifest()` hardcodes all 4 services (`backend`, `main`, `admin`, `dashboard`) as required, and always requires `features.auth.providers`. This breaks for worker, existing, and auth-service project types. Make it read `project.type` and only require the services appropriate for that type.

**Service requirements by project type:**

| Type | Required services | Auth required? |
|------|------------------|---------------|
| `full` | backend, main, admin, dashboard | yes |
| `api` | backend, main | no |
| `worker` | main | no |
| `existing` | main | no |
| `auth-service` | backend | yes |
| _(missing/unknown)_ | all 4 (backwards compat) | yes |

- [ ] **Step 1: Write failing tests for type-aware validation**

Add these tests to `cli/site-manager/tests/test_manifest.py`:

```python
class TestTypeAwareValidation:
    def test_worker_only_requires_main(self, tmp_path, monkeypatch, capsys):
        """Worker projects should validate with only a main service."""
        data = {
            "version": "1.0.0",
            "project": {"name": "my-worker", "domain": "example.com", "type": "worker", "created": "2026-01-01"},
            "services": {
                "main": {"status": "deployed", "platform": "cloudflare"},
            },
            "features": {},
        }
        _write_manifest(tmp_path, data)
        monkeypatch.chdir(tmp_path)
        validate_manifest(output_json=True)
        result = json.loads(capsys.readouterr().out)
        assert result["valid"] is True
        assert result["errors"] == []

    def test_existing_only_requires_main(self, tmp_path, monkeypatch, capsys):
        """Existing projects should validate with only a main service."""
        data = {
            "version": "1.0.0",
            "project": {"name": "my-site", "domain": "example.com", "type": "existing", "created": "2026-01-01"},
            "services": {
                "main": {"status": "deployed", "platform": "cloudflare"},
            },
            "features": {},
        }
        _write_manifest(tmp_path, data)
        monkeypatch.chdir(tmp_path)
        validate_manifest(output_json=True)
        result = json.loads(capsys.readouterr().out)
        assert result["valid"] is True
        assert result["errors"] == []

    def test_api_requires_backend_and_main(self, tmp_path, monkeypatch, capsys):
        """API projects need backend + main, not admin/dashboard."""
        data = {
            "version": "1.0.0",
            "project": {"name": "my-api", "domain": "example.com", "type": "api", "created": "2026-01-01"},
            "services": {
                "backend": {"status": "deployed", "platform": "railway"},
                "main": {"status": "deployed", "platform": "cloudflare"},
            },
            "features": {"auth": {"enabled": True, "providers": ["email"]}},
        }
        _write_manifest(tmp_path, data)
        monkeypatch.chdir(tmp_path)
        validate_manifest(output_json=True)
        result = json.loads(capsys.readouterr().out)
        assert result["valid"] is True

    def test_api_missing_backend_fails(self, tmp_path, monkeypatch, capsys):
        """API projects must have a backend service."""
        data = {
            "version": "1.0.0",
            "project": {"name": "my-api", "domain": "example.com", "type": "api", "created": "2026-01-01"},
            "services": {
                "main": {"status": "deployed", "platform": "cloudflare"},
            },
            "features": {"auth": {"enabled": True, "providers": ["email"]}},
        }
        _write_manifest(tmp_path, data)
        monkeypatch.chdir(tmp_path)
        validate_manifest(output_json=True)
        result = json.loads(capsys.readouterr().out)
        assert result["valid"] is False
        assert any("services.backend" in e for e in result["errors"])

    def test_auth_service_only_requires_backend(self, tmp_path, monkeypatch, capsys):
        """Auth-service projects only need a backend."""
        data = {
            "version": "1.0.0",
            "project": {"name": "my-auth", "domain": "example.com", "type": "auth-service", "created": "2026-01-01"},
            "services": {
                "backend": {"status": "deployed", "platform": "railway"},
            },
            "features": {"auth": {"enabled": True, "providers": ["email"]}},
        }
        _write_manifest(tmp_path, data)
        monkeypatch.chdir(tmp_path)
        validate_manifest(output_json=True)
        result = json.loads(capsys.readouterr().out)
        assert result["valid"] is True

    def test_no_type_falls_back_to_all_services(self, tmp_path, monkeypatch, capsys):
        """Missing project type requires all 4 services for backwards compat."""
        data = {
            "version": "1.0.0",
            "project": {"name": "old-project", "domain": "example.com", "created": "2026-01-01"},
            "services": {
                "backend": {"status": "deployed", "platform": "railway"},
                "main": {"status": "deployed", "platform": "cloudflare"},
            },
            "features": {"auth": {"enabled": True, "providers": ["email"]}},
        }
        _write_manifest(tmp_path, data)
        monkeypatch.chdir(tmp_path)
        validate_manifest(output_json=True)
        result = json.loads(capsys.readouterr().out)
        assert result["valid"] is False
        assert any("services.admin" in e for e in result["errors"])

    def test_worker_skips_auth_validation(self, tmp_path, monkeypatch, capsys):
        """Worker projects don't require auth providers."""
        data = {
            "version": "1.0.0",
            "project": {"name": "my-worker", "domain": "example.com", "type": "worker", "created": "2026-01-01"},
            "services": {
                "main": {"status": "deployed", "platform": "cloudflare"},
            },
            "features": {},
        }
        _write_manifest(tmp_path, data)
        monkeypatch.chdir(tmp_path)
        validate_manifest(output_json=True)
        result = json.loads(capsys.readouterr().out)
        assert result["valid"] is True
        assert not any("providers" in e for e in result["errors"])

    def test_existing_with_optional_backend(self, tmp_path, monkeypatch, capsys):
        """Existing projects can have additional services beyond main."""
        data = {
            "version": "1.0.0",
            "project": {"name": "my-site", "domain": "example.com", "type": "existing", "created": "2026-01-01"},
            "services": {
                "backend": {"status": "deployed", "platform": "railway"},
                "main": {"status": "deployed", "platform": "cloudflare"},
                "admin": {"status": "scaffolded", "platform": "cloudflare"},
            },
            "features": {"auth": {"enabled": True, "providers": ["email"]}},
        }
        _write_manifest(tmp_path, data)
        monkeypatch.chdir(tmp_path)
        validate_manifest(output_json=True)
        result = json.loads(capsys.readouterr().out)
        assert result["valid"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/mfullerton/projects/active/cat-herding && python -m pytest cli/site-manager/tests/test_manifest.py::TestTypeAwareValidation -v`

Expected: FAIL — worker/existing/api/auth-service tests fail because validate_manifest() requires all 4 services and auth providers unconditionally.

- [ ] **Step 3: Implement type-aware validation**

Replace the services and auth validation blocks in `cli/site-manager/src/site_manager/manifest.py:93-112` with:

```python
    # Determine required services based on project type
    project_type = proj.get("type", "")
    REQUIRED_SERVICES = {
        "full": ("backend", "main", "admin", "dashboard"),
        "api": ("backend", "main"),
        "worker": ("main",),
        "existing": ("main",),
        "auth-service": ("backend",),
    }
    required = REQUIRED_SERVICES.get(project_type, ("backend", "main", "admin", "dashboard"))

    for svc_name in required:
        svc = data.get("services", {}).get(svc_name, {})
        if not svc:
            errors.append(f"services.{svc_name}: missing")
            continue
        if svc.get("status") not in ("scaffolded", "deployed", "error"):
            errors.append(f"services.{svc_name}.status: invalid '{svc.get('status')}'")
        if not svc.get("platform"):
            errors.append(f"services.{svc_name}.platform: missing")

    # Validate any extra services present beyond the required set
    for svc_name, svc in data.get("services", {}).items():
        if svc_name in required:
            continue
        if svc.get("status") and svc.get("status") not in ("scaffolded", "deployed", "error"):
            errors.append(f"services.{svc_name}.status: invalid '{svc.get('status')}'")
        if svc.get("status") and not svc.get("platform"):
            errors.append(f"services.{svc_name}.platform: missing")

    # Auth validation — only for types that require auth
    AUTH_REQUIRED_TYPES = {"full", "auth-service", ""}
    if project_type in AUTH_REQUIRED_TYPES:
        auth = data.get("features", {}).get("auth", {})
        if not isinstance(auth.get("enabled"), bool):
            errors.append("features.auth.enabled: missing or not boolean")
        providers = auth.get("providers", [])
        if not providers:
            errors.append("features.auth.providers: empty or missing")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/mfullerton/projects/active/cat-herding && python -m pytest cli/site-manager/tests/test_manifest.py -v`

Expected: ALL tests pass (both old and new).

- [ ] **Step 5: Update the existing test for missing service**

The existing `test_missing_service` test creates a manifest without `project.type`, which falls back to requiring all 4 services. Verify this still passes (it should, since the backwards-compat fallback requires all 4).

Run: `cd /Users/mfullerton/projects/active/cat-herding && python -m pytest cli/site-manager/tests/test_manifest.py::TestValidateManifest::test_missing_service -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
cd /Users/mfullerton/projects/active/cat-herding
git add cli/site-manager/src/site_manager/manifest.py cli/site-manager/tests/test_manifest.py
git commit -m "feat(site-manager): make manifest validation project-type-aware

Services and auth requirements are now conditional on project.type.
Worker/existing types only require main, api requires backend+main,
auth-service requires backend. Missing type falls back to all 4 for
backwards compat."
git push
```

---

### Task 2: Make deploy pipeline project-type-aware

**Files:**
- Modify: `cli/site-manager/src/site_manager/deploy.py`
- Test: `cli/site-manager/tests/test_deploy.py`

Currently `deploy_all()` always deploys all 4 services and exits with error if any fails. For worker/existing projects, backend and admin/dashboard don't exist — this causes false failures. Make it read `project.type` and the services present in the manifest to decide what to deploy. Also support deploying the main site from the project root (for worker/existing types) vs `sites/main/` (for full/api types).

- [ ] **Step 1: Write failing tests for type-aware deploy**

Add to `cli/site-manager/tests/test_deploy.py`:

```python
from site_manager.deploy import _services_to_deploy, _site_directory


class TestServicesToDeploy:
    def test_full_deploys_all(self):
        manifest = {
            "project": {"type": "full"},
            "services": {
                "backend": {"status": "deployed", "platform": "railway"},
                "main": {"status": "deployed", "platform": "cloudflare"},
                "admin": {"status": "deployed", "platform": "cloudflare"},
                "dashboard": {"status": "deployed", "platform": "cloudflare"},
            },
        }
        assert _services_to_deploy(manifest) == ["backend", "main", "admin", "dashboard"]

    def test_worker_deploys_main_only(self):
        manifest = {
            "project": {"type": "worker"},
            "services": {
                "main": {"status": "deployed", "platform": "cloudflare"},
            },
        }
        assert _services_to_deploy(manifest) == ["main"]

    def test_existing_deploys_main_only(self):
        manifest = {
            "project": {"type": "existing"},
            "services": {
                "main": {"status": "deployed", "platform": "cloudflare"},
            },
        }
        assert _services_to_deploy(manifest) == ["main"]

    def test_existing_with_backend_deploys_both(self):
        manifest = {
            "project": {"type": "existing"},
            "services": {
                "backend": {"status": "deployed", "platform": "railway"},
                "main": {"status": "deployed", "platform": "cloudflare"},
            },
        }
        assert _services_to_deploy(manifest) == ["backend", "main"]

    def test_api_deploys_backend_and_main(self):
        manifest = {
            "project": {"type": "api"},
            "services": {
                "backend": {"status": "deployed", "platform": "railway"},
                "main": {"status": "deployed", "platform": "cloudflare"},
            },
        }
        assert _services_to_deploy(manifest) == ["backend", "main"]

    def test_auth_service_deploys_backend_only(self):
        manifest = {
            "project": {"type": "auth-service"},
            "services": {
                "backend": {"status": "deployed", "platform": "railway"},
            },
        }
        assert _services_to_deploy(manifest) == ["backend"]

    def test_no_type_deploys_all_present(self):
        """Missing type deploys whatever services exist in the manifest."""
        manifest = {
            "project": {},
            "services": {
                "backend": {"status": "deployed", "platform": "railway"},
                "main": {"status": "deployed", "platform": "cloudflare"},
                "admin": {"status": "deployed", "platform": "cloudflare"},
                "dashboard": {"status": "deployed", "platform": "cloudflare"},
            },
        }
        result = _services_to_deploy(manifest)
        assert result == ["backend", "main", "admin", "dashboard"]


class TestSiteDirectory:
    def test_full_main_in_sites(self):
        manifest = {"project": {"type": "full"}}
        assert _site_directory("main", manifest) == "sites/main"

    def test_full_admin_in_sites(self):
        manifest = {"project": {"type": "full"}}
        assert _site_directory("admin", manifest) == "sites/admin"

    def test_worker_main_at_root(self):
        manifest = {"project": {"type": "worker"}}
        assert _site_directory("main", manifest) == "."

    def test_existing_main_at_root(self):
        manifest = {"project": {"type": "existing"}}
        assert _site_directory("main", manifest) == "."

    def test_api_main_in_sites(self):
        manifest = {"project": {"type": "api"}}
        assert _site_directory("main", manifest) == "sites/main"

    def test_custom_directory_from_manifest(self):
        manifest = {
            "project": {"type": "existing"},
            "services": {"main": {"directory": "frontend"}},
        }
        assert _site_directory("main", manifest) == "frontend"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/mfullerton/projects/active/cat-herding && python -m pytest cli/site-manager/tests/test_deploy.py::TestServicesToDeploy -v && python -m pytest cli/site-manager/tests/test_deploy.py::TestSiteDirectory -v`

Expected: FAIL — `_services_to_deploy` and `_site_directory` don't exist yet.

- [ ] **Step 3: Implement _services_to_deploy and _site_directory**

Add these two functions to `cli/site-manager/src/site_manager/deploy.py` after the `_now_iso` function (before `_deploy_backend`):

```python
# Canonical service order for deploy
_ALL_SERVICES = ("backend", "main", "admin", "dashboard")

# Types where the main site lives at project root instead of sites/main/
_ROOT_SITE_TYPES = {"worker", "existing"}


def _services_to_deploy(manifest: dict) -> list[str]:
    """Return the ordered list of services to deploy based on manifest."""
    services = manifest.get("services", {})
    return [s for s in _ALL_SERVICES if s in services]


def _site_directory(name: str, manifest: dict) -> str:
    """Return the directory for a site service.

    Checks for an explicit directory in the service entry first,
    then falls back to type-based defaults.
    """
    svc = manifest.get("services", {}).get(name, {})
    if svc.get("directory"):
        return svc["directory"]

    project_type = manifest.get("project", {}).get("type", "")
    if name == "main" and project_type in _ROOT_SITE_TYPES:
        return "."
    return f"sites/{name}"
```

- [ ] **Step 4: Run the new tests to verify they pass**

Run: `cd /Users/mfullerton/projects/active/cat-herding && python -m pytest cli/site-manager/tests/test_deploy.py -v`

Expected: ALL tests pass.

- [ ] **Step 5: Update deploy_all to use _services_to_deploy**

Replace the body of `deploy_all()` in `cli/site-manager/src/site_manager/deploy.py`:

```python
def deploy_all(output_json: bool = False) -> None:
    manifest = _read_manifest()
    services = _services_to_deploy(manifest)
    results = {}

    for name in services:
        if name == "backend":
            results[name] = _deploy_backend(manifest)
        else:
            results[name] = _deploy_site(name, manifest)

    _save_manifest(manifest)

    if output_json:
        print(json.dumps(results))
        return

    print("\nDeploy complete:")
    for name, ok in results.items():
        icon = "+" if ok else "-"
        print(f"  [{icon}] {name}")
    print()

    if not all(results.values()):
        sys.exit(1)
```

- [ ] **Step 6: Update _deploy_site to use _site_directory**

Replace the site_dir line in `_deploy_site()`:

```python
def _deploy_site(name: str, manifest: dict) -> bool:
    site_dir = _site_directory(name, manifest)
    if site_dir != "." and not Path(site_dir).exists():
        print(f"  {name}: directory not found, skipping")
        return False

    print(f"Deploying {name} (Wrangler)...")

    # Build — use custom command if specified, otherwise default
    svc = manifest.get("services", {}).get(name, {})
    build_cmd = svc.get("buildCommand", "npx vite build")
    build = _run(build_cmd.split(), cwd=site_dir if site_dir != "." else None)
    if build.returncode != 0:
        print(f"  {name} build FAILED: {build.stderr.strip()}", file=sys.stderr)
        return False

    # Deploy
    out = _run(["npx", "wrangler", "deploy"], cwd=site_dir if site_dir != "." else None)
    if out.returncode != 0:
        print(f"  {name} deploy FAILED: {out.stderr.strip()}", file=sys.stderr)
        return False

    print(f"  {name}: deployed")
    manifest["services"][name]["status"] = "deployed"
    manifest["services"][name]["lastDeployed"] = _now_iso()
    return True
```

- [ ] **Step 7: Run all deploy tests**

Run: `cd /Users/mfullerton/projects/active/cat-herding && python -m pytest cli/site-manager/tests/test_deploy.py -v`

Expected: ALL tests pass.

- [ ] **Step 8: Run all CLI tests**

Run: `cd /Users/mfullerton/projects/active/cat-herding && python -m pytest cli/site-manager/tests/ -v`

Expected: ALL tests pass.

- [ ] **Step 9: Commit**

```bash
cd /Users/mfullerton/projects/active/cat-herding
git add cli/site-manager/src/site_manager/deploy.py cli/site-manager/tests/test_deploy.py
git commit -m "feat(site-manager): make deploy pipeline project-type-aware

deploy_all() now reads project.type and only deploys services present
in the manifest. _site_directory() resolves where each service lives —
worker/existing types deploy main from project root. Supports custom
buildCommand and directory overrides in service entries."
git push
```

---

### Task 3: Add existing-site init flow to SKILL.md

**Files:**
- Modify: `plugins/site-manager/skills/site-manager/SKILL.md`

This is the main feature — modifying the Claude-executed init flow to detect existing websites and configure them for Cloudflare without scaffolding content files.

- [ ] **Step 1: Add "existing" to the route table and project types**

In the `## Help` section of SKILL.md, update the project types list to include:

```
Project types:
  auth-service                      Shared auth service (Railway + Postgres, RS256 JWT)
  full                              Backend + main + admin + dashboard (multi-user)
  api                               Backend + main site (single-user with API)
  worker                            Single Cloudflare Worker (frontend-only)
  existing                          Existing website configured for Cloudflare
```

- [ ] **Step 2: Add existing-site detection to Init Step 1**

Insert a new detection phase at the very beginning of Init, before Phase 1 questions. Add this after the `### Step 1: Gather project info` heading and before `**Phase 1 — basics**`:

```markdown
**Phase 0 — detect existing website:**

Before asking any questions, check if the current working directory already contains a website. Look for these signals:

| Signal | Weight | What it means |
|--------|--------|--------------|
| `index.html` exists | strong | Static site or SPA entry point |
| `package.json` with web deps (`react`, `vue`, `svelte`, `next`, `nuxt`, `astro`, `vite`, `webpack`) | strong | JavaScript web project |
| `vite.config.*` or `next.config.*` or `webpack.config.*` or `astro.config.*` | strong | Build tool configured |
| `public/` or `static/` directory | moderate | Static assets present |
| `src/` with `.tsx`, `.jsx`, `.vue`, `.svelte` files | moderate | Component-based web app |
| `tsconfig.json` | weak | TypeScript project (could be backend) |
| `.site/manifest.json` exists | **abort** | Already a site-manager project — print "This is already a site-manager project. Use `/site-manager update` instead." and stop |

If **2+ strong signals** or **1 strong + 2 moderate signals** are detected, report the findings and enter the existing-site flow:

```
=== Existing website detected ===

  Framework:  React + Vite (from package.json + vite.config.ts)
  Entry:      index.html
  Source:     src/ (14 .tsx files)
  Build:      npm run build → dist/
  Git:        mikefullerton/my-site (main)

I'll configure this for Cloudflare Workers without modifying your existing code.
```

Then skip to **Phase 1E** (existing site info gathering). If no existing website is detected, continue to Phase 1 as before.

**Phase 1E — existing site basics:**

| Field | Validation | Default |
|-------|-----------|---------|
| Project name | lowercase, `[a-z0-9-]+` | from `package.json` name, or directory name |
| Display name | free text | from `package.json` description, or title-cased project name |
| Domain | valid domain name | from `$ARGUMENTS` if provided |
| GitHub repo | detected from `git remote -v` | auto-detected |

Do not ask about target directory (we're already in it).

**Phase 2E — services:**

Ask: **What would you like to deploy?**

| Choice | Description |
|--------|------------|
| **Just this site** | Deploy to Cloudflare Workers (no backend) |
| **This site + backend API** | Add a Railway backend alongside the site |
| **Full suite** | Add backend + admin site + dashboard alongside the site |

Based on the choice:

- **Just this site** → project type `existing`, only `main` service
- **This site + backend API** → project type `existing`, `main` + `backend` services. Ask about auth service (same as current API type questions).
- **Full suite** → project type `existing`, all services. Ask about auth service (same as current full type questions).

**Phase 2E storage (just this site only):**

If "just this site" was chosen, ask about persistent storage (same as current worker type):

| Storage | Use case |
|---------|----------|
| D1 SQLite | Structured data |
| KV | Key-value |
| R2 | Files and blobs |
| None | Static site or external APIs only |

**Phase 3E — confirm:**

```
Project:   my-site
Name:      My Cool Site
Domain:    mysite.com
Type:      existing (your code + Cloudflare Worker)
Services:  main only
Storage:   none
GitHub:    mikefullerton/my-site (detected)
Build:     npm run build → dist/

No files will be added or modified except:
  + .site/manifest.json
  + wrangler.jsonc
  + src/worker.ts (Cloudflare entry point)
  ~ package.json (add wrangler dependency)
  + .site/ added to .gitignore (if not present)
```

Wait for the user to confirm before proceeding.
```

- [ ] **Step 3: Add existing-site scaffold step (new Step 3E)**

Add this as an alternative to Step 3 when the project type is `existing`. Insert it after the existing Step 3:

```markdown
### Step 3E: Configure existing site for Cloudflare (existing type only)

**This step replaces Step 2 and Step 3 for existing projects. Do NOT create directories, copy templates, or scaffold content files.**

**3E.1 — Detect build configuration:**

Read `package.json` to determine:
- **Build command**: Look for `scripts.build`. Common patterns:
  - `vite build` → output: `dist/`
  - `next build` → output: `.next/` (needs `next export` for static, or use `out/`)
  - `npm run build` → check what it runs
  - No build script → treat as static site, assets in current directory or `public/`

- **Output directory**: Look for build tool config:
  - `vite.config.*` → `build.outDir` (default: `dist`)
  - `next.config.*` → check for `output: 'export'` (uses `out/`)
  - If unclear, default to `dist/`

Record the build command and output directory for wrangler config.

**3E.2 — Create `.site/manifest.json`:**

```json
{
  "version": "1.0.0",
  "_site_manager_version": "<current version>",
  "project": {
    "name": "<project-name>",
    "displayName": "<display-name>",
    "domain": "<domain>",
    "type": "existing",
    "created": "<ISO 8601 timestamp>"
  },
  "services": {
    "main": {
      "platform": "cloudflare",
      "status": "scaffolded",
      "directory": ".",
      "buildCommand": "<detected build command, e.g. npx vite build>"
    }
  },
  "features": {},
  "dns": {
    "provider": "cloudflare",
    "zoneId": null,
    "nameservers": [],
    "status": "pending",
    "records": []
  },
  "storage": {
    "d1": false,
    "kv": false,
    "r2": false
  }
}
```

If backend/admin/dashboard were selected in Phase 2E, add those service entries too (with `"status": "scaffolded"` and appropriate platform).

**3E.3 — Create `wrangler.jsonc`:**

Only create if `wrangler.jsonc` and `wrangler.toml` do not already exist.

```jsonc
{
  "name": "<project-name>-main",
  "main": "src/worker.ts",
  "compatibility_date": "2024-12-01",
  "assets": {
    "directory": "<detected output dir, e.g. dist>",
    "binding": "ASSETS"
  },
  "routes": [
    {
      "pattern": "<domain>",
      "custom_domain": true
    }
  ]
}
```

If backend was selected, add `vars.API_BACKEND_URL` (will be filled after Railway deploy).

If D1 was selected, add `d1_databases` binding (placeholder ID — real ID after `wrangler d1 create`).
If KV was selected, add `kv_namespaces` binding.
If R2 was selected, add `r2_buckets` binding.

**3E.4 — Create `src/worker.ts`:**

Only create if `src/worker.ts` does not already exist. If the user's source files are in `src/`, use a different path like `worker.ts` at the root and update `wrangler.jsonc` `main` to match.

**Without backend:**

```typescript
interface Env {
  ASSETS: Fetcher;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const response = await env.ASSETS.fetch(request);
    if (response.status === 404) {
      return env.ASSETS.fetch(new URL("/index.html", request.url));
    }
    return response;
  },
};
```

**With backend:**

```typescript
interface Env {
  API_BACKEND_URL: string;
  ASSETS: Fetcher;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/auth/")) {
      const backendUrl = new URL(url.pathname + url.search, env.API_BACKEND_URL);
      const headers = new Headers(request.headers);
      headers.set("X-Forwarded-For", request.headers.get("cf-connecting-ip") ?? "");
      headers.set("X-Forwarded-Proto", "https");
      return fetch(backendUrl.toString(), {
        method: request.method,
        headers,
        body: request.body,
      });
    }

    const response = await env.ASSETS.fetch(request);
    if (response.status === 404) {
      return env.ASSETS.fetch(new URL("/index.html", request.url));
    }
    return response;
  },
};
```

**3E.5 — Update `package.json`:**

Merge these dependencies into the existing `package.json` (do not overwrite other fields):

```json
{
  "devDependencies": {
    "wrangler": "^4.0.0",
    "@cloudflare/workers-types": "^4.0.0"
  }
}
```

If `package.json` doesn't have a `build` script, add one based on what was detected. If it already has one, leave it alone.

**3E.6 — Update `.gitignore`:**

Append these lines if not already present:

```
.site/
.wrangler/
```

**3E.7 — Scaffold backend/admin/dashboard (if selected):**

If the user selected additional services in Phase 2E:

- **Backend**: Create `backend/` directory and copy templates from `templates/backend/` (same as Init Step 3 for full/api types). Also copy `templates/root/Dockerfile.tmpl`, `templates/root/railway.toml.tmpl`, and `templates/root/docker-compose.yml.tmpl` to the project root. Add `"workspaces"` to root package.json if not present.
- **Admin**: Create `sites/admin/` and copy templates from `templates/sites/admin/` (same as Init Step 3).
- **Dashboard**: Create `sites/dashboard/` and copy templates from `templates/sites/dashboard/` (same as Init Step 3).
- **Shared**: If backend was added, create `shared/` and copy templates from `templates/shared/`.

Do NOT create `sites/main/` — the main site stays at the project root.
```

- [ ] **Step 4: Add existing-site deploy steps**

Add deployment instructions specific to existing sites. Insert after the existing Step 9 as an alternative path:

```markdown
### Step 9E: Deploy existing site to Cloudflare (existing type only)

**This step replaces Steps 7-9 for existing projects without additional services.**

Remove the `routes` block from `wrangler.jsonc` for the initial deploy (routes are re-added during go-live after DNS is configured).

Install dependencies and build:

```bash
npm install
```

If a build command exists:
```bash
npm run build
```

Create Cloudflare resources if storage was selected:

- D1: `npx wrangler d1 create <project-name>-db` → update wrangler.jsonc with real database ID
- KV: `npx wrangler kv namespace create <project-name>-kv` → update wrangler.jsonc with namespace ID
- R2: `npx wrangler r2 bucket create <project-name>-storage`

Deploy:

```bash
npx wrangler deploy
```

Capture the deployed URL from wrangler output.

**If backend was also selected**, follow Init Steps 7-8 for the backend (Railway setup, deploy, seed admin).

**If admin/dashboard were also selected**, follow Init Step 9 for those sites (they live in `sites/admin/` and `sites/dashboard/` as usual).
```

- [ ] **Step 5: Add existing-site final report**

Add to the Step 13 report section:

```markdown
**Existing project (site only):**
```
=== {{DISPLAY_NAME}} is deployed! ===

  Type:          existing (your code on Cloudflare Workers)
  Site:          <project>.<account>.workers.dev
  Storage:       <D1, KV, R2, or none>
  GitHub:        <repo-url>

  Files added:
    .site/manifest.json
    wrangler.jsonc
    src/worker.ts
    (package.json updated)

  To connect your custom domain:
    /site-manager go-live
```

**Existing project (with backend):**
```
=== {{DISPLAY_NAME}} is deployed! ===

  Type:          existing (your code + backend API)
  Site:          <project>-main.<account>.workers.dev
  Backend API:   <railway-url>
  GitHub:        <repo-url>

  Admin login:
    Email:    <admin-email>
    Password: <admin-password>

  To connect your custom domain:
    /site-manager go-live
```

**Existing project (full suite):**
```
=== {{DISPLAY_NAME}} is deployed! ===

  Type:          existing (your code + full suite)
  Main site:     <project>-main.<account>.workers.dev
  Admin site:    <project>-admin.<account>.workers.dev
  Dashboard:     <project>-dashboard.<account>.workers.dev
  Backend API:   <railway-url>
  GitHub:        <repo-url>

  Admin login:
    Email:    <admin-email>
    Password: <admin-password>

  To connect your custom domain:
    /site-manager go-live
```
```

- [ ] **Step 6: Update the Go Live section for existing type**

In the `## Go Live` Step 5 section, add handling for the existing project type:

```markdown
**Existing project:**
- If main only: `wrangler.jsonc` (at project root): `"routes": [{"pattern": "<domain>", "custom_domain": true}]`
- If has admin: `sites/admin/wrangler.jsonc`: `"routes": [{"pattern": "admin.<domain>", "custom_domain": true}]`
- If has dashboard: `sites/dashboard/wrangler.jsonc`: `"routes": [{"pattern": "dashboard.<domain>", "custom_domain": true}]`
```

- [ ] **Step 7: Commit**

```bash
cd /Users/mfullerton/projects/active/cat-herding
git add plugins/site-manager/skills/site-manager/SKILL.md
git commit -m "feat(site-manager): add existing-site detection to init flow

When init runs in a directory with an existing website, it detects the
framework and build config, then configures a Cloudflare Worker to serve
it without touching content files. Only adds wrangler.jsonc, worker.ts,
and .site/manifest.json. Optionally scaffolds backend/admin/dashboard
alongside the existing site."
git push
```

---

### Task 4: Version bumps

**Files:**
- Modify: `cli/site-manager/src/site_manager/__init__.py`
- Modify: `plugins/site-manager/skills/site-manager/SKILL.md` (version in frontmatter + body)

- [ ] **Step 1: Bump CLI version**

In `cli/site-manager/src/site_manager/__init__.py`, change:

```python
__version__ = "0.5.0"
```

This is a minor bump (new feature: type-aware validation and deploy).

- [ ] **Step 2: Bump SKILL.md version**

In `plugins/site-manager/skills/site-manager/SKILL.md`:

- Frontmatter: `version: "1.5.0"`
- Line 10 (Site Manager heading): `# Site Manager v1.5.0`
- All version references in the body (help text, etc.): update to `v1.5.0`

This is a minor bump (new feature: existing-site init).

- [ ] **Step 3: Run all tests**

Run: `cd /Users/mfullerton/projects/active/cat-herding && python -m pytest cli/site-manager/tests/ -v`

Expected: ALL tests pass.

- [ ] **Step 4: Commit**

```bash
cd /Users/mfullerton/projects/active/cat-herding
git add cli/site-manager/src/site_manager/__init__.py plugins/site-manager/skills/site-manager/SKILL.md
git commit -m "chore(site-manager): bump CLI to 0.5.0, skill to 1.5.0"
git push
```
