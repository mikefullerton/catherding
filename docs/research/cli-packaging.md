# CLI Packaging Research

Date: 2026-04-06
Status: Decided
Decision: Python + `uv tool install -e`

## Problem

site-manager and webinator are Python CLIs in this repo. They were installed via venvs with symlinks into `/opt/homebrew/bin/`. When the repo moved from `projects/personal/` to `projects/active/`, the symlinks broke — and even after fixing the symlinks, the venv shebangs had hardcoded absolute paths to the old location.

We needed a packaging approach that:
- Survives repo directory changes
- Keeps source edits live (no rebuild step)
- Scales as the CLIs grow in complexity
- Is the professional standard, not a workaround

## What These CLIs Are

Both are lightweight command dispatchers:
- **site-manager**: 8 commands, ~620 lines, manages multi-site web deployments
- **webinator**: 11 command groups (20+ subcommands), ~780 lines, manages domains/DNS/infrastructure

Key characteristics:
- Zero external dependencies (stdlib only)
- Mostly shell out to other CLIs (railway, wrangler, claude, gh)
- Direct HTTP API calls via urllib (GoDaddy, Cloudflare)
- Python 3.11+ required

## Language Evaluation

### Python (chosen)
These are glue CLIs — they parse args and shell out. Python is the right tool. The problem was never the language, it was the packaging.

### Swift
Native macOS binaries, Keychain access for credentials, fast startup. But: verbose JSON handling (Codable structs), Foundation's URLSession is heavy for simple sync HTTP, and Swift on Windows is experimental. Would require two codebases for cross-platform.

### Go
Best cross-platform story: `GOOS=windows go build` produces a Windows binary from macOS. Excellent stdlib for HTTP/JSON/subprocess. Fast compile. But: verbose error handling, and overkill for tools that mostly shell out.

### Rust
Best type system, excellent `clap` CLI framework, good cross-compile. But: steep learning curve, slower compile, safety guarantees don't buy much for subprocess-heavy glue code.

### Verdict
Keep Python. If we ever need single binaries or cross-platform distribution, port to Go.

## Packaging Options Evaluated

### 1. Shell wrappers + symlinks
2-line shell script sets PYTHONPATH, runs `python3 -m module`. Symlink into PATH.
- Pro: No Python packaging needed, survives repo moves (re-point symlink)
- Con: Two-language entry point (shell + Python)

### 2. Python wrapper scripts + symlinks
Python script uses `__file__` to resolve source path, adds to `sys.path`, calls `main()`.
- Pro: Pure Python, survives repo moves
- Con: `sys.path.insert()` is a code smell

### 3. `__main__.py` + shell wrapper
Add `__main__.py` to enable `python3 -m module`. Shell script in PATH sets env and calls it.
- Pro: Standard Python convention, clean internals
- Con: Still needs a shell script for the PATH entry

### 4. Single-file scripts
Collapse each CLI into one .py file with a shebang. `chmod +x` and symlink.
- Pro: Zero indirection, simplest possible
- Con: 600-800 line monoliths, lose file-per-command organization

### 5. `uv tool install -e` (chosen)
Let `uv` manage isolated envs per tool, install to `~/.local/bin/`, editable mode for live source changes.
- Pro: Professional standard, declarative, idempotent, no repo clutter
- Con: Dependent on `uv` being installed
- Recovery: `uv tool install -e ./cli/<name> --force`

### 6. `pip install -e .` into system Python
Standard editable install into Homebrew's site-packages.
- Pro: Standard Python packaging
- Con: Requires `--break-system-packages`, generated wrappers bake in absolute Python paths

## Chosen Approach

**`uv tool install -e`** with the existing `pyproject.toml` + `src/` layout.

```bash
uv tool install -e ./cli/site-manager
uv tool install -e ./cli/webinator
```

Additionally added `__main__.py` to both packages for `python3 -m` debugging support.

### Why this works
- `uv` creates a managed env per tool under `~/.local/share/uv/tools/`
- Executables go to `~/.local/bin/` (in PATH via shell config)
- Editable mode (`-e`) means source changes are live — no reinstall needed
- If anything breaks: `uv tool install -e ./cli/<name> --force` is a one-command fix
- The `pyproject.toml` `[project.scripts]` entry is the single source of truth for the CLI entry point

### Scaling path
When both CLIs need shared code:
```
cli/
  shared/                 # new shared package
    pyproject.toml
    src/cli_shared/
      http.py
      claude.py
  site-manager/
    pyproject.toml        # adds dependency: cli-shared
  webinator/
    pyproject.toml        # adds dependency: cli-shared
```
Install shared as editable too: `uv tool install -e ./cli/site-manager -e ./cli/shared`

## Project Structure (current)

```
cli/
  site-manager/
    pyproject.toml
    src/site_manager/
      __init__.py
      __main__.py          # enables python3 -m site_manager
      cli.py               # entry point, arg routing
      deploy.py
      status.py
      manifest.py
      test.py
      verify.py
      claude.py
  webinator/
    pyproject.toml
    src/webinator/
      __init__.py
      __main__.py          # enables python3 -m webinator
      cli.py               # entry point, arg routing
      api.py
      config.py
      configure.py
      domains.py
      dns.py
      status.py
      deploy.py
      claude.py
```

## Development Flow

Edit source files and run the command — changes are live immediately. No reinstall, no rebuild.

```bash
# Edit code
vim cli/webinator/src/webinator/domains.py

# Run it — picks up the change instantly
webinator domains list
```

For debugging, run via Python module directly:

```bash
PYTHONPATH=cli/webinator/src python3 -m webinator domains list
```

### When you need to re-run `uv tool install -e`

- Changed the entry point in `pyproject.toml`
- Added a new external dependency to `pyproject.toml`
- Moved the repo directory
