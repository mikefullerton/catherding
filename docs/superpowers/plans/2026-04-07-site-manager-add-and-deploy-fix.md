# site-manager add + deploy fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new `add` subcommand to site-manager that lets users enhance existing projects with new services, auth providers, features, storage, and infrastructure. Also fix deploy.py to use the correct manifest path and add a deploy→verify→repair loop.

**Architecture:** The `add` command is Claude-only (like `init`). The CLI registers the subcommand and routes to Claude via `invoke_claude()`. The skill handles intent matching, manifest scanning, user confirmation, and orchestration. Deploy gets fixed to read from `.site/manifest.json` and the skill's deploy sections get a verify→repair loop.

**Tech Stack:** Python (CLI), Markdown (SKILL.md skill definition)

**Spec:** `docs/superpowers/specs/2026-04-07-site-manager-add-and-deploy-fix-design.md`

---

### Task 1: Fix deploy.py manifest path

**Files:**
- Modify: `cli/site-manager/src/site_manager/deploy.py:15-23`
- Modify: `cli/site-manager/tests/test_cli.py` (no deploy path tests exist, but verify existing tests still pass)

This is a bug fix — deploy.py hardcodes `site-manifest.json` but should use `.site/manifest.json` (with legacy fallback). The constants already exist in `__init__.py`.

- [ ] **Step 1: Write test for deploy manifest path resolution**

Create `cli/site-manager/tests/test_deploy.py`:

```python
"""Tests for deploy manifest path resolution."""

import json
import pytest
from unittest.mock import patch
from site_manager.deploy import _read_manifest, _save_manifest


class TestReadManifest:
    def test_reads_from_site_dir(self, tmp_path, monkeypatch):
        site_dir = tmp_path / ".site"
        site_dir.mkdir()
        manifest = {"version": "1.0.0", "project": {"name": "test"}}
        (site_dir / "manifest.json").write_text(json.dumps(manifest))
        monkeypatch.chdir(tmp_path)
        result = _read_manifest()
        assert result["project"]["name"] == "test"

    def test_falls_back_to_legacy_path(self, tmp_path, monkeypatch):
        manifest = {"version": "1.0.0", "project": {"name": "legacy"}}
        (tmp_path / "site-manifest.json").write_text(json.dumps(manifest))
        monkeypatch.chdir(tmp_path)
        result = _read_manifest()
        assert result["project"]["name"] == "legacy"

    def test_prefers_site_dir_over_legacy(self, tmp_path, monkeypatch):
        site_dir = tmp_path / ".site"
        site_dir.mkdir()
        (site_dir / "manifest.json").write_text(json.dumps({"project": {"name": "new"}}))
        (tmp_path / "site-manifest.json").write_text(json.dumps({"project": {"name": "old"}}))
        monkeypatch.chdir(tmp_path)
        result = _read_manifest()
        assert result["project"]["name"] == "new"

    def test_exits_when_no_manifest(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc:
            _read_manifest()
        assert exc.value.code == 1


class TestSaveManifest:
    def test_saves_to_site_dir(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _save_manifest({"version": "1.0.0"})
        saved = json.loads((tmp_path / ".site" / "manifest.json").read_text())
        assert saved["version"] == "1.0.0"

    def test_creates_site_dir_if_missing(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _save_manifest({"version": "1.0.0"})
        assert (tmp_path / ".site").is_dir()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd cli/site-manager && python -m pytest tests/test_deploy.py -v`
Expected: FAIL — `_read_manifest` looks for `site-manifest.json`, not `.site/manifest.json`

- [ ] **Step 3: Fix `_read_manifest` and `_save_manifest` in deploy.py**

Replace lines 15-23 of `cli/site-manager/src/site_manager/deploy.py`:

Old:
```python
def _read_manifest() -> dict:
    p = Path("site-manifest.json")
    if not p.exists():
        print("error: no site-manifest.json found", file=sys.stderr)
        print("Run: site-manager init", file=sys.stderr)
        sys.exit(1)
    return json.loads(p.read_text())


def _save_manifest(data: dict) -> None:
    Path("site-manifest.json").write_text(json.dumps(data, indent=2))
```

New:
```python
from site_manager import MANIFEST_PATH, LEGACY_MANIFEST_PATH


def _read_manifest() -> dict:
    for path in (MANIFEST_PATH, LEGACY_MANIFEST_PATH):
        p = Path(path)
        if p.exists():
            return json.loads(p.read_text())
    print("error: no .site/manifest.json found", file=sys.stderr)
    print("Run: site-manager init", file=sys.stderr)
    sys.exit(1)


def _save_manifest(data: dict) -> None:
    p = Path(MANIFEST_PATH)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2) + "\n")
```

Note: `MANIFEST_PATH` is `".site/manifest.json"` and `LEGACY_MANIFEST_PATH` is `"site-manifest.json"` — both already defined in `cli/site-manager/src/site_manager/__init__.py`. However, `LEGACY_MANIFEST_PATH` does not exist yet, so add it to `__init__.py`:

Add after line 5 of `__init__.py`:
```python
LEGACY_MANIFEST_PATH = "site-manifest.json"
```

The full `__init__.py` becomes:
```python
__version__ = "0.3.0"

SITE_DIR = ".site"
MANIFEST_PATH = f"{SITE_DIR}/manifest.json"
LEGACY_MANIFEST_PATH = "site-manifest.json"
ISSUES_PATH = f"{SITE_DIR}/issues.json"
DEVELOPER_FLAG = "~/.site-manager/developer"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd cli/site-manager && python -m pytest tests/test_deploy.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Run all existing tests to check for regressions**

Run: `cd cli/site-manager && python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 6: Also fix manifest.py to use the same path constants**

`cli/site-manager/src/site_manager/manifest.py` has the same bug — it hardcodes `MANIFEST_FILE = "site-manifest.json"` on line 9.

Replace lines 1-17 of `manifest.py`:

Old:
```python
"""Read, display, and validate site-manifest.json."""

import json
import re
import sys
from pathlib import Path

MANIFEST_FILE = "site-manifest.json"


def _find_manifest() -> dict:
    p = Path(MANIFEST_FILE)
    if not p.exists():
        print("error: no site-manifest.json found in current directory", file=sys.stderr)
        print("Run: site-manager init", file=sys.stderr)
        sys.exit(1)
    return json.loads(p.read_text())
```

New:
```python
"""Read, display, and validate .site/manifest.json."""

import json
import re
import sys
from pathlib import Path

from site_manager import MANIFEST_PATH, LEGACY_MANIFEST_PATH


def _find_manifest() -> dict:
    for path in (MANIFEST_PATH, LEGACY_MANIFEST_PATH):
        p = Path(path)
        if p.exists():
            return json.loads(p.read_text())
    print("error: no .site/manifest.json found in current directory", file=sys.stderr)
    print("Run: site-manager init", file=sys.stderr)
    sys.exit(1)
```

- [ ] **Step 7: Update manifest tests to use `.site/manifest.json`**

In `cli/site-manager/tests/test_manifest.py`, update `_write_manifest` (line 23-25) to write to `.site/manifest.json`:

Old:
```python
def _write_manifest(tmp_path, data):
    p = tmp_path / "site-manifest.json"
    p.write_text(json.dumps(data))
    return p
```

New:
```python
def _write_manifest(tmp_path, data):
    site_dir = tmp_path / ".site"
    site_dir.mkdir(exist_ok=True)
    p = site_dir / "manifest.json"
    p.write_text(json.dumps(data))
    return p
```

- [ ] **Step 8: Run all tests**

Run: `cd cli/site-manager && python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 9: Commit**

```bash
git add cli/site-manager/src/site_manager/__init__.py cli/site-manager/src/site_manager/deploy.py cli/site-manager/src/site_manager/manifest.py cli/site-manager/tests/test_deploy.py cli/site-manager/tests/test_manifest.py
git commit -m "fix(site-manager): use .site/manifest.json in deploy.py and manifest.py"
```

---

### Task 2: Add `add` subcommand to CLI

**Files:**
- Modify: `cli/site-manager/src/site_manager/cli.py:12,43-78,127-176`
- Modify: `cli/site-manager/tests/test_cli.py:111-117`

- [ ] **Step 1: Write tests for the `add` subcommand parser**

Add to the end of `TestParser` class in `cli/site-manager/tests/test_cli.py`:

```python
    def test_add_requires_claude(self):
        args = self.parser.parse_args(["add"])
        assert args.command in CLAUDE_COMMANDS

    def test_add_no_args(self):
        args = self.parser.parse_args(["add"])
        assert args.command == "add"
        assert args.description == []

    def test_add_with_description(self):
        args = self.parser.parse_args(["add", "github", "auth"])
        assert args.description == ["github", "auth"]

    def test_add_single_word(self):
        args = self.parser.parse_args(["add", "admin"])
        assert args.description == ["admin"]
```

Update `TestClaudeGating.test_claude_commands_set` (line 113):

Old:
```python
    def test_claude_commands_set(self):
        assert CLAUDE_COMMANDS == {"init", "migrate", "go-live", "deploy", "seed-admin", "update", "verify", "repair"}
```

New:
```python
    def test_claude_commands_set(self):
        assert CLAUDE_COMMANDS == {"init", "migrate", "go-live", "deploy", "seed-admin", "update", "verify", "repair", "add"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd cli/site-manager && python -m pytest tests/test_cli.py -v -k "add or claude_commands"`
Expected: FAIL — `add` not recognized, not in CLAUDE_COMMANDS

- [ ] **Step 3: Add `add` to CLAUDE_COMMANDS and parser**

In `cli/site-manager/src/site_manager/cli.py`:

Line 12 — add `"add"` to CLAUDE_COMMANDS:
```python
CLAUDE_COMMANDS = {"init", "migrate", "go-live", "deploy", "seed-admin", "update", "verify", "repair", "add"}
```

In `_build_parser()`, after the `repair` subparser (after line 77), add:
```python
    add_p = sub.add_parser("add", help="Add capabilities to an existing project (requires Claude)")
    add_p.add_argument("description", nargs="*", default=[], help="What to add (e.g., 'github auth', 'admin site')")
```

In `main()`, after the `repair` elif block (after line 172), add:
```python
    elif args.command == "add":
        from site_manager.claude import invoke_claude
        desc = " ".join(args.description) if args.description else ""
        invoke_claude(f"add {desc}".strip())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd cli/site-manager && python -m pytest tests/test_cli.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add cli/site-manager/src/site_manager/cli.py cli/site-manager/tests/test_cli.py
git commit -m "feat(site-manager): add 'add' subcommand to CLI"
```

---

### Task 3: Bump versions

**Files:**
- Modify: `cli/site-manager/src/site_manager/__init__.py:1`
- Modify: `plugins/site-manager/skills/site-manager/SKILL.md:3,4,9,25,28`

- [ ] **Step 1: Bump CLI version**

In `cli/site-manager/src/site_manager/__init__.py`, line 1:

Old: `__version__ = "0.3.0"`
New: `__version__ = "0.4.0"`

- [ ] **Step 2: Bump skill version**

In `plugins/site-manager/skills/site-manager/SKILL.md`:

Line 3 — frontmatter version:
Old: `version: "1.3.0"`
New: `version: "1.4.0"`

Line 4 — argument-hint (add `add`):
Old: `argument-hint: "[init|deploy|update|verify|repair|status|manifest|seed-admin|--help|--version]"`
New: `argument-hint: "[init|add|deploy|update|verify|repair|status|manifest|seed-admin|--help|--version]"`

Line 9 — heading:
Old: `# Site Manager v1.1.0`
New: `# Site Manager v1.4.0`

Line 25 — startup version:
Old: `site-manager v1.3.0`
New: `site-manager v1.4.0`

Line 28 — `--version` response:
Old: `> site-manager v1.3.0`
New: `> site-manager v1.4.0`

- [ ] **Step 3: Update version test**

In `cli/site-manager/tests/test_version.py`, check if it hardcodes a version and update accordingly. Read the file first.

- [ ] **Step 4: Run tests**

Run: `cd cli/site-manager && python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add cli/site-manager/src/site_manager/__init__.py plugins/site-manager/skills/site-manager/SKILL.md cli/site-manager/tests/test_version.py
git commit -m "chore(site-manager): bump CLI to 0.4.0, skill to 1.4.0"
```

---

### Task 4: Add deploy→verify→repair loop to SKILL.md

**Files:**
- Modify: `plugins/site-manager/skills/site-manager/SKILL.md:770-791` (Deploy All and Deploy Single sections)

- [ ] **Step 1: Replace Deploy All section**

Replace lines 770-780 of SKILL.md:

Old:
```markdown
## Deploy All

Delegate to the `site-manager` CLI:

\```bash
site-manager deploy all
\```

Print the output as-is.

---
```

New:
```markdown
## Deploy All

Deploy all services, then verify and repair until clean.

### Step 1: Deploy

\```bash
site-manager deploy all
\```

If deploy fails for any service, report the error but continue with remaining services.

### Step 2: Verify→repair loop

After deploy completes:

1. Run `site-manager verify`
2. If all checks pass → report success, stop
3. If issues found:
   a. Read `.site/issues.json`
   b. For each issue: diagnose root cause and fix (code, config, env vars, wrangler bindings, etc.)
   c. Re-deploy only the affected services: `site-manager deploy <service>`
   d. Re-run `site-manager verify`
4. Repeat up to 3 iterations
5. If still failing after 3 iterations: report remaining issues to the user and stop

**Important:** Each iteration should fix different issues. If the same issue persists after a fix attempt, investigate deeper rather than retrying the same fix.

---
```

- [ ] **Step 2: Replace Deploy Single section**

Replace lines 782-792 of SKILL.md:

Old:
```markdown
## Deploy Single

Delegate to the `site-manager` CLI:

\```bash
site-manager deploy <service>
\```

Print the output as-is.

---
```

New:
```markdown
## Deploy Single

Deploy a single service, then verify and repair until clean.

### Step 1: Deploy

\```bash
site-manager deploy <service>
\```

### Step 2: Verify→repair loop

After deploy completes, run the same verify→repair loop as Deploy All (up to 3 iterations). Only verify and repair the deployed service's checks — use the relevant verify flags:

- `backend` → `site-manager verify --manifest`
- `main` / `admin` / `dashboard` → `site-manager verify --manifest --dns`

---
```

- [ ] **Step 3: Commit**

```bash
git add plugins/site-manager/skills/site-manager/SKILL.md
git commit -m "feat(site-manager): add verify→repair loop to deploy commands"
```

---

### Task 5: Add `add` route and section to SKILL.md

**Files:**
- Modify: `plugins/site-manager/skills/site-manager/SKILL.md:2,33-53,1215-1257`

This is the main feature. Add the route table entry and a new `## Add` section.

- [ ] **Step 1: Update skill description**

Line 2 of SKILL.md:

Old:
```
description: "Scaffold, deploy, and manage a suite of websites (backend + main + admin + dashboard) as a unified platform. /site-manager init, /site-manager deploy, /site-manager status, /site-manager manifest, /site-manager seed-admin, /site-manager --help"
```

New:
```
description: "Scaffold, deploy, and manage a suite of websites (backend + main + admin + dashboard) as a unified platform. /site-manager init, /site-manager add, /site-manager deploy, /site-manager status, /site-manager manifest, /site-manager seed-admin, /site-manager --help"
```

- [ ] **Step 2: Add route table entry**

In the route table (lines 33-53), add after the `go-live` row (after line 38):

```markdown
| `add` or `add <description>` | Go to **Add** |
```

- [ ] **Step 3: Add the `## Add` section**

Insert a new section before `## Deploy All` (before line 770). This is the full Add section:

```markdown
## Add

Add capabilities to an existing project. Reads `.site/manifest.json` to determine what's already present, offers what's missing.

### Step 1: Read manifest

```bash
cat .site/manifest.json
```

If `.site/manifest.json` does not exist, print:
> This is not a site-manager project. Run `/site-manager init` first.

Then stop.

Parse the manifest to determine:
- `project.type` — the project type (auth-service, full, api, worker)
- `services` — which services exist and their status
- `features` — which features are enabled
- `dns` — whether DNS/go-live is configured

### Step 2: Determine what's addable

Compare the manifest against the addable catalog. An item is **addable** if it's not already present/enabled and is compatible with the project.

**Addable catalog:**

| Item | Manifest check | Compatible types |
|------|---------------|-----------------|
| Backend API | `services.backend` absent or not deployed | worker |
| Main site | `services.main` absent or not deployed | auth-service |
| Admin site | `services.admin` absent or not deployed | api, worker, auth-service |
| Dashboard | `services.dashboard` absent or not deployed | api, worker, auth-service |
| Built-in auth | `features.auth.enabled` is false/absent | any with backend |
| GitHub OAuth | `"github"` not in `features.auth.providers` | any with auth enabled |
| Google OAuth | `"google"` not in `features.auth.providers` | any with auth enabled |
| External auth service | `features.auth.mode` is not `"external"` | any with backend |
| Feature flags | `features.featureFlags.enabled` is false/absent | any with backend |
| Email service | `features.email.enabled` is false/absent | any with backend |
| SMS service | `features.sms.enabled` is false/absent | any with backend |
| A/B testing | `features.abTesting.enabled` is false/absent | any with backend |
| Observability | `features.observability.enabled` is false/absent | any |
| Structured logging | `features.logging.enabled` is false/absent | any |
| D1 SQLite | no D1 binding in wrangler config | worker |
| KV store | no KV binding in wrangler config | worker |
| R2 bucket | no R2 binding in wrangler config | worker |
| GitHub repo | no `.git` remote | any |
| GitHub Actions | no `.github/workflows/` | any with GitHub repo |
| DNS / go-live | `dns.zoneId` is null/absent | any deployed |

### Step 3: Match or present menu

**If `$ARGUMENTS` contains a description** (e.g., `add github auth`):
- Match the description against addable items using natural language understanding
- If a clear match: proceed to Step 4 with that item
- If ambiguous: show the top 2-3 matches and ask the user to pick
- If no match: "I don't know how to add that. Here's what I can add:" → show full menu

**If no description** (just `add`):
- Build a numbered menu of all addable items (exclude items already present)
- Group by category (Services, Auth, Features, Storage, Infrastructure)
- Present the menu and ask the user to pick one or more (comma-separated numbers)

Menu format:
```
Your project (<type>) can add:

  Services
    1. Admin site (admin.<domain>)
    2. Dashboard (dashboard.<domain>)

  Auth
    3. GitHub OAuth
    4. Google OAuth

  Features
    5. Email service
    6. SMS service

  Infrastructure
    7. GitHub Actions workflows
    8. DNS / go-live

What would you like to add? (enter number, or describe what you want)
```

### Step 4: Confirm

Confirm in plain language what you're about to do:

> Do you want to add GitHub authentication?

Wait for the user to confirm.

### Step 5: Choose execution mode

Ask:

> How would you like to proceed?
>   1. Scaffold, deploy, and verify (default)
>   2. Scaffold only
>   3. Let's chat about it first
>
> (Enter for default)

### Step 6: Execute

**Mode 1 — Scaffold, deploy, and verify:**
1. Scaffold the code (see Scaffold Instructions below)
2. Update `.site/manifest.json` with the new state
3. Commit changes
4. Deploy the affected service(s): `site-manager deploy <service>`
5. The deploy command runs the verify→repair loop automatically

**Mode 2 — Scaffold only:**
1. Scaffold the code (see Scaffold Instructions below)
2. Update `.site/manifest.json` with the new state
3. Commit changes
4. Print: "Code scaffolded and committed. Run `/site-manager deploy <service>` when ready."

**Mode 3 — Chat:**
1. Discuss the addition with the user — answer questions, explain trade-offs
2. When the user is ready, re-enter at Step 5

### Scaffold Instructions

Each addable item has specific scaffold steps. Reference existing scaffold logic from **Init** where applicable.

**Adding a service (admin, dashboard, main, backend):**
- Copy the relevant templates from `${CLAUDE_SKILL_DIR}/references/templates/` (same as Init Step 3)
- Wire the new service into the root `package.json` workspaces array
- Add the service entry to `.site/manifest.json` with `"status": "scaffolded"`
- If adding admin or dashboard: also add the GitHub Actions deploy workflow from `templates/github/`
- Run `npm install` to install dependencies

**Adding GitHub OAuth:**
- Copy `templates/backend/src/auth/github.ts.tmpl` → `backend/src/auth/github.ts`
- Wire into `backend/src/app.ts` (add import and route — see Init Step 3 conditional wiring)
- Add "Sign in with GitHub" button to login pages (main and admin if they exist)
- Add `"github"` to `features.auth.providers` in manifest
- Set `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` env vars on Railway

**Adding Google OAuth:**
- Same pattern as GitHub OAuth but with `google.ts.tmpl` and Google-specific env vars

**Adding built-in auth:**
- Copy auth templates: `password.ts`, `session.ts`, `routes/auth.ts`
- Wire auth routes into `backend/src/app.ts`
- Add auth middleware to protected routes
- Set `features.auth.enabled: true` and `features.auth.providers: ["email"]` in manifest
- Generate JWT secret: `railway variables set JWT_SECRET="$(openssl rand -hex 32)"`

**Adding external auth service:**
- Ask for the auth service URL
- Fetch the public key from `<auth-service-url>/.well-known/jwks.json`
- Set `AUTH_SERVICE_URL` and `AUTH_PUBLIC_KEY` env vars on Railway
- Add JWT verification middleware using the public key
- Set `features.auth.mode: "external"` in manifest

**Adding feature flags:**
- Copy `templates/backend/src/services/feature-flags.ts.tmpl` and `templates/backend/src/routes/admin/flags.ts.tmpl`
- Wire routes into `backend/src/app.ts`
- If admin site exists, copy `templates/sites/admin/src/routes/flags.tsx.tmpl`
- Set `features.featureFlags.enabled: true` in manifest

**Adding storage (D1, KV, R2):**
- Add the binding to `wrangler.jsonc`
- For D1: also create the database with `wrangler d1 create <name>` and add a `migrations/` directory
- Update manifest accordingly

**Adding GitHub repo:**
- `gh repo create <name> --private`
- `git remote add origin <url>`
- `git push -u origin main`

**Adding GitHub Actions:**
- Copy relevant workflow templates from `templates/github/`
- Only add workflows for services that exist in the project

**Adding DNS / go-live:**
- Delegate to the existing **Go Live** section of this skill
```

- [ ] **Step 4: Update Help section**

In the Help section (around line 1215), add the `add` command to the Claude session commands list. Insert after the `go-live` line:

```
  /site-manager add [description]   Add services, auth, features to existing project
```

Also update the version references in the Help section from `v1.3.0` to `v1.4.0`.

- [ ] **Step 5: Commit**

```bash
git add plugins/site-manager/skills/site-manager/SKILL.md
git commit -m "feat(site-manager): add 'add' command to skill with addable catalog"
```

---

### Task 6: Update plugin.json version

**Files:**
- Modify: `plugins/site-manager/.claude-plugin/plugin.json`

- [ ] **Step 1: Read plugin.json**

Read `plugins/site-manager/.claude-plugin/plugin.json` to find the current version.

- [ ] **Step 2: Bump version to match skill version**

Update the `"version"` field to `"1.4.0"`.

- [ ] **Step 3: Commit**

```bash
git add plugins/site-manager/.claude-plugin/plugin.json
git commit -m "chore(site-manager): bump plugin version to 1.4.0"
```

---

### Task 7: Update CLAUDE.md skills table

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add `add` command to skills table**

In the Skills table in `CLAUDE.md`, update the site-manager entries. Add a row for `/site-manager add`:

```markdown
| `/site-manager add [description]` | Add services, auth, features, storage to existing project |
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add site-manager add command to skills table"
```

---

### Task 8: Final verification

- [ ] **Step 1: Run all CLI tests**

Run: `cd cli/site-manager && python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 2: Verify skill loads correctly**

Run: `claude --plugin-dir ./plugins/site-manager -p "/site-manager --version"`
Expected: Output contains `site-manager v1.4.0`

- [ ] **Step 3: Verify add subcommand parses**

Run: `cd cli/site-manager && python -m site_manager add --help`
Expected: Shows help for add subcommand (will print Claude-required message since not in Claude session)
