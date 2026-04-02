---
description: Plugin development and installation workflow for cat-herding plugins
globs: plugins/**/*
---

# Plugin Development Workflow

This repo is a **local marketplace** (`cat-herding`). The plugins under `plugins/` (yolo, custom-status-line, show-project-setup) are registered via `.claude-plugin/marketplace.json`.

## Installing plugins (as a user would)

```bash
# Register the marketplace (one-time)
claude plugin marketplace add ~/projects/personal/cat-herding

# Install plugins
claude plugin install yolo@cat-herding
claude plugin install status-enhancements@cat-herding
claude plugin install show-project-setup@cat-herding
```

Plugins persist across sessions once installed. They appear as namespaced skills (e.g., `/yolo:yolo`).

## Developing plugins (instant feedback)

Launch Claude with `--plugin-dir` to load plugins directly from disk — edits take effect immediately without `plugin update`:

```bash
claude --plugin-dir ./plugins/yolo --plugin-dir ./plugins/status-enhancements --plugin-dir ./plugins/show-project-setup
```

Or load a single plugin you're actively editing:

```bash
claude --plugin-dir ./plugins/yolo
```

Use `/reload-plugins` inside a session to pick up changes without restarting.

## Pushing changes to installed users

After editing plugin files, installed copies (in `~/.claude/plugins/cache/`) are stale. Update them:

```bash
claude plugin update yolo@cat-herding
claude plugin update status-enhancements@cat-herding
claude plugin update show-project-setup@cat-herding
```

## Plugin structure

Each plugin must follow this layout:

```
plugins/<name>/
  .claude-plugin/
    plugin.json          # name, description, version, author, license
  skills/
    <skill-name>/
      SKILL.md           # skill definition with YAML frontmatter
      references/        # scripts and resources used by the skill
  README.md
```

The marketplace manifest at `.claude-plugin/marketplace.json` lists all plugins with relative `"source": "./plugins/<name>"` paths.

## Adding a new plugin

1. Create the directory structure above under `plugins/<name>/`
2. Add an entry to `.claude-plugin/marketplace.json`
3. Test with `claude --plugin-dir ./plugins/<name>`
4. Install with `claude plugin install <name>@cat-herding`
