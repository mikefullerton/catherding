# Scripts

Single-call scripts that collapse multi-step operations Claude repeats often. The goal: replace 5–10 Bash turns (and their output accumulation in the conversation cache) with one script call that returns tight, structured output.

Every file is named `cc-<name>.py`. Both installers (`install.sh`, `cc-install`) simply strip the `.py` extension to produce the installed command `cc-<name>` on your PATH. Exception: files matching `cc-*-hook.py` are installed into `~/.claude/hooks/cc-*-hook.py` instead (Claude Code hook protocol, not a CLI).

## Layout — one category per directory

| Directory | Count | What lives here |
|---|---|---|
| `scripts-git/` | 10 | Git / PR workflow: worktree merge, commit-push, PR status, rebase, submodules, branch hygiene |
| `scripts-bash/` | 2 | Shell helpers: `cc-grep`, `cc-rename` |
| `scripts-xcode/` | 9 | macOS / Xcode: xcodebuild, xcodegen, schemes, settings, logs, app paths, plist, DerivedData |
| `scripts-claude/` | 5 | Claude Code meta: usage stats, memory, graphify, version fields, project index |
| `scripts-meta/` | 3 | Self-management of the scripts themselves: `cc-install`, `cc-doctor`, `cc-help` |
| `scripts-hooks/` | 1 | Claude Code hook scripts (`cc-*-hook.py`). Installed into `~/.claude/hooks/`, not `$PATH` |
| `skill-scripts/` | 2 | Skill-coupled scripts whose lifecycle tracks a specific skill (`cc-install-statusline`, `cc-verify`) |

**Total:** 32 `cc-*` entries.

## Design principles

- **Python only** — per global `CLAUDE.md` rule.
- **Structured output** — concise, parseable, no verbose prose.
- **Non-zero exit on failure** — Claude can check `$?` deterministically.
- **Idempotent where possible** — re-running should be safe.
- **Atomic where necessary** — all-or-nothing for destructive operations.

## Adding a new script

1. Pick the right category dir (`scripts-git/`, `scripts-xcode/`, …). If your script doesn't fit cleanly into an existing one, create a new `scripts-<area>/` dir — the installers glob `scripts-*`, so no loop updates are needed.
2. Create `scripts-<area>/cc-<name>.py` with the standard `#!/usr/bin/env python3` shebang and a short docstring.
3. `chmod +x`.
4. Run `cc-install` to symlink it into `~/.local/bin/` (or into `~/.claude/hooks/` if the name ends in `-hook`).
5. Add a row to the category table above and to the catalog block in `~/.claude/CLAUDE.md`.

## Hook scripts — the `-hook` suffix

Files whose stem matches `cc-*-hook` are detected by `install.sh`, `cc-install`, and `cc-doctor` and routed to `~/.claude/hooks/cc-*-hook.py` instead of `~/.local/bin/`. This matches Claude Code's hook protocol: the harness invokes hooks with JSON on stdin and uses the exit code as a signal. Such scripts don't belong on `$PATH` — they're not CLI commands.

Only one exists today: `scripts-hooks/cc-repo-hygiene-hook.py` (the `Stop` hook enforcer).

`skills/custom-status-line/references/hooks/session-tracker.py` is also a Claude Code hook, but it's installed by the custom-status-line skill (`cc-install-statusline`) rather than by the generic installer, because its lifecycle tracks the skill.
