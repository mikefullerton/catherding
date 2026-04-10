# Claude Code Plugins: Local Development & Distribution

Research conducted 2026-04-02.

## Plugin Structure

Every plugin requires this layout:

```
my-plugin/
  .claude-plugin/
    plugin.json          # Manifest: name, description, version, author, license
  skills/
    skill-name/
      SKILL.md           # Skill definition with YAML frontmatter
      references/        # Scripts and resources used by the skill
  README.md
```

### plugin.json

```json
{
  "name": "my-plugin",
  "description": "What this plugin does",
  "version": "1.0.0",
  "author": { "name": "Your Name" },
  "license": "MIT"
}
```

### SKILL.md Frontmatter

```yaml
---
name: skill-name
description: "What this skill does"
version: "1.0.0"
argument-hint: "<arg1|arg2> [--flag]"
allowed-tools: Read, Write, Edit, Bash(chmod *), AskUserQuestion
model: sonnet
disable-model-invocation: true
---
```

Key fields:
- **argument-hint** — shown in autocomplete
- **allowed-tools** — precise permission whitelist (prevents prompts)
- **model** — which Claude model runs the skill (haiku, sonnet, opus)
- **disable-model-invocation** — if true, Claude follows instructions literally without inference

## Three Ways to Load Plugins

### 1. `--plugin-dir` (Development)

```bash
claude --plugin-dir ./plugins/my-plugin
```

- Loads plugin directly from filesystem — edits take effect immediately
- Session-only — must be passed every launch
- Use `/reload-plugins` inside a session to pick up changes without restarting
- `${CLAUDE_PLUGIN_ROOT}` resolves correctly for reference files
- Best for active development

### 2. Local Marketplace (Persistent Local Install)

Create a marketplace manifest at your repo root:

```
my-repo/
  .claude-plugin/
    marketplace.json
  plugins/
    plugin-a/
    plugin-b/
```

**marketplace.json:**

```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "my-marketplace",
  "description": "Description of this collection",
  "owner": { "name": "Your Name" },
  "plugins": [
    {
      "name": "plugin-a",
      "description": "What plugin-a does",
      "source": "./plugins/plugin-a",
      "category": "development"
    }
  ]
}
```

Register and install:

```bash
# Register marketplace (one-time, persists across sessions)
claude plugin marketplace add ~/path/to/my-repo

# Install plugins
claude plugin install plugin-a@my-marketplace

# Update after editing source files
claude plugin update plugin-a@my-marketplace
```

The marketplace registration persists in `~/.claude/plugins/known_marketplaces.json`. Plugins are copied to `~/.claude/plugins/cache/` on install — source edits require `plugin update` to take effect.

### 3. GitHub Marketplace (Public Distribution)

Push your marketplace repo to GitHub, then users add it:

```bash
claude plugin marketplace add --source github --repo owner/my-marketplace
claude plugin install plugin-a@my-marketplace
```

Or configure in `~/.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "my-marketplace": {
      "source": { "source": "github", "repo": "owner/my-marketplace" },
      "autoUpdate": true
    }
  }
}
```

### Marketplace Source Types

Plugins within a marketplace can use different source types:

```json
// Relative path (within the marketplace repo)
"source": "./plugins/my-plugin"

// Git URL
"source": { "source": "url", "url": "https://github.com/owner/repo.git", "sha": "abc123" }

// Git subdirectory
"source": { "source": "git-subdir", "url": "owner/repo", "path": "plugins/my-plugin", "ref": "main", "sha": "abc123" }
```

## Recommended Development Workflow

Use **both** approaches together:

1. **`--plugin-dir`** during active editing — instant feedback, no update step
2. **Local marketplace** for testing the full install/update flow as users experience it

Convenience alias for development:

```bash
alias claude-dev='claude --plugin-dir ~/path/to/plugins/a --plugin-dir ~/path/to/plugins/b'
```

## Plugin Management Commands

```bash
# Marketplace management
claude plugin marketplace add <path-or-source>
claude plugin marketplace list
claude plugin marketplace remove <name>

# Plugin lifecycle
claude plugin install <name>@<marketplace> [--scope user|project|local]
claude plugin uninstall <name>@<marketplace>
claude plugin update <name>@<marketplace>
claude plugin enable <name>@<marketplace>
claude plugin disable <name>@<marketplace>
claude plugin list
claude plugin validate    # Validate plugin structure
```

## Plugin Scopes

| Scope | Location | Visibility |
|-------|----------|------------|
| `user` | `~/.claude/settings.json` | All sessions, all projects |
| `project` | `.claude/settings.json` | Anyone working in this repo |
| `local` | `.claude/settings.local.json` | Only you, only this repo (gitignored) |

## Key Files

| File | Purpose |
|------|---------|
| `~/.claude/settings.json` | `enabledPlugins`, `extraKnownMarketplaces`, hooks |
| `~/.claude/plugins/installed_plugins.json` | Registry of all installed plugins (auto-managed) |
| `~/.claude/plugins/known_marketplaces.json` | Registered marketplace sources |
| `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/` | Installed plugin copies |
| `~/.claude/plugins/marketplaces/<name>/` | Cloned marketplace repos |

## Naming Conventions

- Installed plugins are identified as `plugin-name@marketplace-name`
- Skills appear as `/plugin-name:skill-name` when skill name differs from plugin name
- Skills appear as `/skill-name` when skill name matches plugin name (collapsed form)
- Plugin name shown in parentheses in skill list: `/skill-name (plugin-name)`

## What Plugins Can Contain

| Component | Location | Purpose |
|-----------|----------|---------|
| Skills | `skills/<name>/SKILL.md` | Slash commands (`/name`) |
| Agents | `agents/<name>.md` | Autonomous agent definitions |
| Commands | `commands/<name>.md` | Simple slash commands |
| Rules | `rules/<name>.md` | Context rules loaded automatically |
| Hooks | Configured in settings | Shell scripts triggered by events |
| MCP servers | `.mcp.json` | External tool integrations |

## Hooks

Plugins can register hooks that fire on lifecycle events:

```json
{
  "hooks": {
    "PermissionRequest": [{ "matcher": "", "hooks": [{ "type": "command", "command": "script.sh" }] }],
    "SessionStart": [{ "matcher": "", "hooks": [{ "type": "command", "command": "script.sh" }] }],
    "SessionEnd": [{ "matcher": "", "hooks": [{ "type": "command", "command": "script.sh" }] }]
  }
}
```

Hook scripts are typically installed to `~/.claude/hooks/` by the plugin's install skill.

## Environment Variables Available in Skills

| Variable | Value |
|----------|-------|
| `${CLAUDE_SKILL_DIR}` | Path to the skill's directory (where SKILL.md lives) |
| `${CLAUDE_PLUGIN_ROOT}` | Path to the plugin's root directory |
| `${CLAUDE_PLUGIN_DATA}` | Persistent data directory for the plugin |
| `$ARGUMENTS` | Arguments passed to the skill by the user |

## Things That Don't Work

- **Manual `installed_plugins.json` edits** — auto-managed by Claude Code, manual changes can break loading
- **Symlinks in cache** — plugin system expects canonical paths, not symlinks
- **`"source": "local"` or `"source": "file"`** — not supported in marketplace definitions; use relative paths within a marketplace instead
- **`pluginDirs` or `localPlugins` in settings** — no such config keys exist; use `--plugin-dir` flag or local marketplace
