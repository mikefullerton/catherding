# site-manager add command + deploy fix

**Date:** 2026-04-07
**Scope:** New `add` subcommand, fix `deploy.py` manifest path, deploy→verify→repair loop

---

## 1. `site-manager add`

### Purpose

Add any capability site-manager supports to an existing project. Reads `.site/manifest.json` to understand current state, diffs against what's possible, and lets the user pick what to add.

### Invocation

| Form | Behavior |
|------|----------|
| `site-manager add` | Scan manifest, show numbered menu of addable items |
| `site-manager add <description>` | Interpret intent, confirm in plain language, execute |

Examples:
- `/site-manager add` → shows menu
- `/site-manager add github auth` → "Do you want to add GitHub authentication?"
- `/site-manager add admin` → "Do you want to add an admin website?"
- `/site-manager add monitoring` → "Do you want to add observability?"

### Addable catalog (initial)

The catalog is a structured table in SKILL.md. Adding a new addable = adding a row + scaffold instructions. No code changes needed.

**Services** (project-type boundaries are soft — an `api` project can add `admin`):

| Addable | Key | Applies to | What it does |
|---------|-----|------------|--------------|
| Backend API | `service:backend` | worker | Add Railway backend + Postgres |
| Main site | `service:main` | auth-service | Add Cloudflare Worker main site |
| Admin site | `service:admin` | api, worker | Add Cloudflare Worker admin site |
| Dashboard | `service:dashboard` | api, worker | Add Cloudflare Worker + D1 dashboard |

**Auth:**

| Addable | Key | Applies to | What it does |
|---------|-----|------------|--------------|
| Built-in auth | `auth:builtin` | projects without auth | Add email/password auth to backend |
| GitHub OAuth | `auth:github` | projects with auth | Add GitHub OAuth provider |
| Google OAuth | `auth:google` | projects with auth | Add Google OAuth provider |
| External auth service | `auth:external` | any with backend | Connect to shared auth service |

**Features:**

| Addable | Key | Applies to | What it does |
|---------|-----|------------|--------------|
| Feature flags | `feature:flags` | any with backend | Add feature flag system |
| Email service | `feature:email` | any with backend | Add email sending capability |
| SMS service | `feature:sms` | any with backend | Add SMS capability |
| A/B testing | `feature:abtesting` | any with backend | Add A/B testing framework |
| Observability | `feature:observability` | any | Add health/metrics endpoints |
| Structured logging | `feature:logging` | any | Add structured JSON logging |

**Storage (worker projects):**

| Addable | Key | Applies to | What it does |
|---------|-----|------------|--------------|
| D1 SQLite | `storage:d1` | worker | Add D1 database binding |
| KV store | `storage:kv` | worker | Add KV namespace binding |
| R2 bucket | `storage:r2` | worker | Add R2 storage binding |

**Infrastructure:**

| Addable | Key | Applies to | What it does |
|---------|-----|------------|--------------|
| GitHub repo | `infra:github` | any without repo | Create GitHub repo, push |
| GitHub Actions | `infra:actions` | any with GitHub repo | Add deploy workflows |
| DNS / go-live | `infra:dns` | any deployed | Set up custom domain |

### Determining what's addable

Read `.site/manifest.json` and build the "missing" list:

- **Services:** check `services` object — if a service key is absent or has `"status": "not-deployed"`, it's addable
- **Auth:** check `features.auth` — if `enabled: false` or providers list is missing github/google, those are addable
- **Features:** check each key in `features` — if absent or `enabled: false`, it's addable
- **Storage:** check `services.main` (or root for worker) for D1/KV/R2 bindings in wrangler config
- **Infrastructure:** check for `.git` remote, `.github/workflows/`, `dns.zoneId`

Items that are already present are excluded from the menu.

### Flow

```
1. Read .site/manifest.json
   - If missing: "This is not a site-manager project. Run /site-manager init first." Stop.

2. If args provided:
   - Fuzzy-match against addable catalog
   - If no match: "I don't know how to add that. Here's what I can add:" → show menu
   - If match: confirm in plain language
   If no args:
   - Build list of missing/addable items
   - Present numbered menu
   - Ask user to pick (can pick multiple)

3. Confirm in plain language:
   "Do you want to add GitHub authentication?"

4. Ask execution mode:
   "How would you like to proceed?"
     1. Scaffold, deploy, and verify (default)
     2. Scaffold only
     3. Let's chat about it first
   (Enter for default)

5. Execute chosen mode:
   - Mode 1: scaffold → commit → deploy → verify loop (see Deploy section)
   - Mode 2: scaffold → commit → done
   - Mode 3: discuss details, then re-enter at step 4

6. Update .site/manifest.json with new state

7. Commit all changes
```

### CLI registration

Add `add` to `cli.py`:

```python
# In CLAUDE_COMMANDS set:
CLAUDE_COMMANDS = {"init", "migrate", "go-live", "deploy", "seed-admin", "update", "verify", "repair", "add"}

# In _build_parser():
add_p = sub.add_parser("add", help="Add capabilities to an existing project (requires Claude)")
add_p.add_argument("description", nargs="*", help="What to add (e.g., 'github auth', 'admin site')")

# In main():
elif args.command == "add":
    from site_manager.claude import invoke_claude
    desc = " ".join(args.description) if args.description else ""
    invoke_claude(f"add {desc}".strip())
```

### SKILL.md changes

Add `add` to the route table and add a new `## Add` section with:
- The addable catalog table
- Logic for scanning the manifest
- Per-item scaffold instructions (reference existing template/scaffold instructions from Init)
- The 3-option execution mode prompt

---

## 2. Fix deploy.py manifest path

### Problem

`deploy.py` reads from `site-manifest.json` (legacy path). Should read from `.site/manifest.json` with fallback to legacy path.

### Fix

Replace `_read_manifest()` and `_save_manifest()`:

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

---

## 3. Deploy → verify → repair loop

### Problem

`deploy` currently deploys and stops. The user has no confidence that things actually work. Verify and repair are separate manual steps.

### Design

After deploying, `deploy` automatically runs the verify→repair loop until all checks pass or a max iteration limit is hit.

**Flow:**

```
1. Deploy all requested services
2. Run verify (all suites: manifest, DNS, e2e, smoke)
3. If all pass → done, report success
4. If issues found:
   a. Attempt automatic repair for each issue
   b. Re-deploy any services that were repaired
   c. Re-run verify
5. Repeat steps 3-4 up to 3 iterations
6. If still failing after 3 iterations:
   - Report remaining issues
   - Save to .site/issues.json
   - Exit with non-zero status
```

### Implementation

This loop lives in the **skill** (SKILL.md), not in `deploy.py`. The CLI `deploy.py` handles the mechanical deploy step. The skill orchestrates:

1. Call `deploy` (CLI)
2. Call `verify` (CLI)
3. Read `.site/issues.json`
4. If issues: analyze, fix code/config, re-deploy affected services
5. Re-verify
6. Loop up to 3 times

This keeps the CLI simple and lets Claude do the intelligent repair work.

### SKILL.md changes

Update the **Deploy All** and **Deploy Single** sections to include the verify loop:

```
After deploying:
1. Run: site-manager verify
2. If all checks pass → report success and stop
3. If issues found:
   - Read .site/issues.json
   - For each issue: diagnose and fix (code, config, env vars, etc.)
   - Re-deploy affected services
   - Re-run: site-manager verify
4. Repeat up to 3 times
5. If still failing: report remaining issues to user
```

---

## 4. Version bump

Bump CLI version to `0.4.0` (new command = minor bump) in `cli/site-manager/src/site_manager/__init__.py`.

Bump skill version to `1.4.0` in SKILL.md frontmatter and startup output.

---

## Summary of files to modify

| File | Change |
|------|--------|
| `cli/site-manager/src/site_manager/__init__.py` | Version → `0.4.0` |
| `cli/site-manager/src/site_manager/cli.py` | Add `add` subcommand, add to `CLAUDE_COMMANDS` |
| `cli/site-manager/src/site_manager/deploy.py` | Fix manifest path to `.site/manifest.json` |
| `plugins/site-manager/skills/site-manager/SKILL.md` | Add `add` route + section, update deploy with verify loop, version → `1.4.0` |
