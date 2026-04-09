# Configurator Web Editor

Replace the terminal Q&A flow with a local web form for editing project configs. All options visible at once, changes saved immediately, deployed features shown as locked.

## Architecture

New module: `src/configurator/web.py`

Single entry point `serve_editor(name: str, cfg: dict)`:
- Starts `http.server.HTTPServer` on a random available port
- Two routes:
  - `GET /` — serves the HTML form with `cfg` embedded as inline JSON
  - `PATCH /api/config` — receives partial config updates, merges into cfg, calls `save_config(name, cfg)`
- Opens browser via `webbrowser.open()`
- Blocks until Ctrl+C (prints "Editing at http://localhost:PORT — press Ctrl+C when done")
- On exit, just returns — no clipboard copy, no deploy prompt

HTML/CSS/JS embedded as a Python string constant in `web.py`. No external dependencies.

## CLI Integration

`cmd_configure()` calls `serve_editor()` by default instead of `run_questions()`.

New `--tui` flag: `configurator --tui` falls back to the terminal Q&A flow. The `run_questions()` function and all `ask_*` helpers remain untouched.

Arg parsing adds:
```
parser.add_argument("--tui", action="store_true", help="Use terminal Q&A instead of web editor")
```

## Form Layout

Five sections, each a card/fieldset:

1. **Project** — repo name (text), org (select from ORGS + "other"), domain (text), local path (read-only if set)
2. **Website** — type (radio: new/existing/none), domain (text), addons (checkboxes: sqlite database, key-value storage, file storage). Domain and addons disabled when type=none.
3. **Backend** — enabled (checkbox), domain (text), API docs site (checkbox + domain), environments (checkboxes: staging, testing). All sub-fields disabled when backend not enabled.
4. **Admin Sites** — admin (checkbox + domain), dashboard (checkbox + domain). Domain disabled when not enabled.
5. **Auth** — providers (checkboxes: email/password, github, google, apple)

## Form Behavior

- Fields pre-populated from config JSON embedded in the page at load time
- Already-deployed features (present in manifest): the enable toggle is checked and disabled with a "deployed" label. Sub-options (domains, addons) remain editable.
- Toggling a parent off disables its children (backend unchecked greys out domain, docs, environments)
- Every field change fires a debounced (300ms) `fetch("PATCH", "/api/config")` with the full form state serialized to the config JSON shape
- No submit button, no save button — always saved on change
- Minimal styling: system font, light background, ~60ch centered, clean fieldsets

## Server Details

- Port: `0` (OS-assigned random available port)
- The server reads the assigned port after binding, uses it for the browser URL
- `PATCH /api/config` expects JSON body matching the config structure, merges it into the in-memory cfg dict, writes to disk via `save_config()`
- No CORS needed — same origin

## Files Changed

- `src/configurator/web.py` — new module, ~300-400 lines (HTML template + server)
- `src/configurator/cli.py` — add `--tui` flag, call `serve_editor()` from `cmd_configure()`
- `src/configurator/__init__.py` — version bump
