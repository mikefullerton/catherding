# Skill Scripts

Scripts tied to a specific skill or plugin in this repo — they install alongside the general workflow scripts in `~/.local/bin/cc-*`, but live separately because their lifecycle is coupled to a skill's source tree (templates, tests, install targets) rather than to the generic Claude workflow.

Same naming convention as `scripts/` — files are `cc-<name>.py`; `install.sh` and `cc-install` strip only the `.py` extension.

## Scripts

| Script | Skill | Purpose |
|--------|-------|---------|
| `cc-install-statusline.py` | `custom-status-line` | Copy status line source files to `~/.claude-status-line/`, clear pycache, run the skill's pytest suite |
| `cc-verify.py` | `custom-status-line` | Run tests + lint + typecheck for the status-line package (tests live under `skills/custom-status-line/tests/`) |

## Why a separate directory

- **Lifecycle:** these scripts are meaningless without their skill's source tree — e.g. `cc-verify` hard-codes `skills/custom-status-line/tests` as `TESTS_DIR`. Generic workflow scripts in `scripts/` don't assume anything about which skills are present.
- **Pairing:** when a skill is added or removed, its scripts move with it. Keeping them here makes that coupling visible.
- **Install semantics are identical.** Both dirs are picked up by `install.sh` and `cc-install` by default.

## Adding a new skill script

1. Create `skill-scripts/cc-<name>.py` with the standard shebang and docstring.
2. `chmod +x`.
3. Run `cc-install` to symlink it into `~/.local/bin/`.
4. Add a row to the table above.
