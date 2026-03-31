---
name: install-recommended-tools
version: "2.0.0"
description: "Walk through installing recommended Claude Code plugins, LSPs, and MCP servers based on your development type and languages."
argument-hint: "[--version]"
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, Bash(cat *), Bash(ls *), Bash(jq *), AskUserQuestion
model: haiku
---

# Install Recommended Tools v1.0.0

## Startup

**First action**: If `$ARGUMENTS` is `--version`, print `install-recommended-tools v2.0.0` and stop.

Otherwise, print `install-recommended-tools v2.0.0` as the first line of output, then proceed.

## Overview

An interactive guide that recommends Claude Code plugins, LSP integrations, and MCP servers based on what you build and the languages you use. It detects what's already installed and only recommends what's missing.

**Each recommendation specifies a scope — global or local:**
- **Global**: universally useful plugins with no hooks or only SessionStart hooks. Install once, available in every project.
- **Local**: language-specific, platform-specific, deployment-specific, or hook-heavy plugins. Install per-project to avoid overhead in irrelevant projects.

The recommendations come from the developer-tools research catalog at `research/developer-tools/` in the agentic-cookbook repo.

### Hook-Heavy Plugins — Install Locally Only

These plugins register hooks that fire on every tool call or prompt. Never install them globally — the hooks run in every project whether relevant or not.

| Plugin | Hooks | Fires on |
|--------|-------|----------|
| `semgrep` | PostToolUse, UserPromptSubmit, SessionStart (3) | Every write + every prompt |
| `security-guidance` | PreToolUse (1) | Every Write/Edit |
| `hookify` | PreToolUse, PostToolUse, UserPromptSubmit, Stop (4) | Everything |
| `vercel` | 13 hooks across all events | Everything + telemetry |
| `railway` | PreToolUse (1) | Every Bash command |

When recommending any of these, always set scope to `local` and include the warning: "Has hooks that fire continuously — install per-project only."

## Step 1: Detect Installed Tools

Read these files to build the installed inventory:

1. **Global plugins**: Read `~/.claude/settings.json` — extract the `enabledPlugins` array. Each entry is `<plugin-name>@<marketplace>`. If the file doesn't exist or is malformed, treat the list as empty.
2. **Project MCP servers**: Read `.mcp.json` in the project root (if it exists) — extract keys from `mcpServers`. If missing, treat as empty.
3. **User MCP servers**: Read `~/.claude.json` (if it exists) — extract MCP servers configured at user scope. If missing, treat as empty.

Build two lists:
- `installed_plugins`: plugin names (without marketplace suffix)
- `installed_mcp`: MCP server names

Print a compact summary:

```
=== Installed Tools ===
Plugins: 33 installed (typescript-lsp, swift-lsp, semgrep, superpowers, ...)
MCP servers: 1 configured (playwright)
```

## Step 2: Ask Development Type

Use AskUserQuestion to ask:

> **What types of development do you work on?** (select all that apply)
>
> 1. Web frontend (React, Vue, Svelte, etc.)
> 2. Web backend (APIs, servers, databases)
> 3. iOS / macOS (Swift, Xcode)
> 4. Android (Kotlin, Gradle)
> 5. Windows / .NET (C#, WinUI)
> 6. CLI / terminal apps
> 7. Data / ML pipelines
> 8. Infrastructure / DevOps
> 9. API development (REST, GraphQL, gRPC)

Accept comma-separated numbers (e.g., "1, 2, 9"). If the user provides invalid input (non-numeric, out of range), ask again with a clarifying note.

## Step 3: Ask Languages

Use AskUserQuestion to ask:

> **What languages do you primarily use?** (select all that apply)
>
> 1. TypeScript / JavaScript
> 2. Python
> 3. Swift
> 4. Kotlin
> 5. C# / .NET
> 6. Go
> 7. Rust
> 8. Java
> 9. Ruby
> 10. PHP
> 11. C / C++
> 12. Elixir
> 13. Lua

Accept comma-separated numbers.

## Step 4: Build Recommendations

Assemble a recommendation list based on selections. Each recommendation has a tier (**Essential**, **Recommended**, or **Optional**), a one-line description, and an install command.

Skip any tool already in `installed_plugins` or `installed_mcp`.

### Universal (everyone gets these)

| Tool | Tier | Scope | Description |
|------|------|-------|-------------|
| `superpowers` | Essential | global | TDD, systematic debugging, brainstorming, subagent workflows |
| `code-review` | Essential | global | Multi-agent PR code review with confidence filtering |
| `pr-review-toolkit` | Essential | global | Specialized review agents across 6 domains |
| `context7` | Essential | global | Real, version-specific library docs in context |
| `github` | Essential | global | GitHub API: issues, PRs, code search |
| `security-guidance` | Recommended | local | Scans file writes for 8 vulnerability categories. Has PreToolUse hook — install per-project only. |
| `semgrep` | Recommended | local | Real-time SAST scanning via MCP server. Has 3 continuous hooks — install per-project only. Requires SEMGREP_APP_TOKEN. |
| `claude-code-setup` | Recommended | global | Analyze codebase and recommend automations |
| `commit-commands` | Optional | global | Git commit, push, PR commands |
| `claude-md-management` | Optional | global | Maintain and audit CLAUDE.md files |
| `feature-dev` | Optional | global | 7-phase multi-agent feature development |
| `remember` | Optional | global | Continuous cross-session memory via daily logs |

### By Language (LSP plugins)

Map each selected language to its LSP plugin:

| Language | Plugin | Binary Required | Install |
|----------|--------|-----------------|---------|
| TypeScript/JavaScript | `typescript-lsp` | `typescript-language-server` | `/plugin install typescript-lsp@claude-plugins-official` |
| Python | `pyright-lsp` | `pyright-langserver` | `/plugin install pyright-lsp@claude-plugins-official` |
| Swift | `swift-lsp` | `sourcekit-lsp` | `/plugin install swift-lsp@claude-plugins-official` |
| Kotlin | `kotlin-lsp` | `kotlin-language-server` | `/plugin install kotlin-lsp@claude-plugins-official` |
| C# / .NET | `csharp-lsp` | `csharp-ls` | `/plugin install csharp-lsp@claude-plugins-official` |
| Go | `gopls-lsp` | `gopls` | `/plugin install gopls-lsp@claude-plugins-official` |
| Rust | `rust-analyzer-lsp` | `rust-analyzer` | `/plugin install rust-analyzer-lsp@claude-plugins-official` |
| Java | `jdtls-lsp` | `jdtls` | `/plugin install jdtls-lsp@claude-plugins-official` |
| Ruby | `ruby-lsp` | `ruby-lsp` | `/plugin install ruby-lsp@claude-plugins-official` |
| PHP | `php-lsp` | `intelephense` | `/plugin install php-lsp@claude-plugins-official` |
| C / C++ | `clangd-lsp` | `clangd` | `/plugin install clangd-lsp@claude-plugins-official` |
| Elixir | `elixir-ls-lsp` | `elixir-ls` | `/plugin install elixir-ls-lsp@claude-plugins-official` |
| Lua | `lua-lsp` | `lua-language-server` | `/plugin install lua-lsp@claude-plugins-official` |

All LSP plugins are **Essential** tier for their language and always **local** scope (language-specific).

### By Dev Type

All dev-type-specific plugins are **local** scope unless noted otherwise.

**Web frontend** (selection 1):
| Tool | Tier | Description |
|------|------|-------------|
| `frontend-design` | Essential | Production-grade UI with distinctive design quality |
| `figma` | Essential | Read Figma designs for design-to-code translation |
| `playwright` | Essential | Browser automation, E2E testing, screenshots |
| `playground` | Recommended | Interactive HTML playgrounds with live preview |
| `accesslint` | Recommended | WCAG accessibility compliance checking |
| `stagehand` | Optional | Natural language browser automation |

**Web backend** (selection 2):
| Tool | Tier | Description |
|------|------|-------------|
| `postman` | Recommended | Full API lifecycle: collections, tests, mocks, docs |
| `sentry` | Optional | Error monitoring, stack traces, issue search |
| `prisma` | Optional | Prisma ORM, migrations, PostgreSQL management |

**iOS / macOS** (selection 3):
| Tool | Tier | Description |
|------|------|-------------|
| `figma` | Recommended | Design-to-code for iOS UI |

**Android** (selection 4):
| Tool | Tier | Description |
|------|------|-------------|
| `figma` | Recommended | Design-to-code for Android UI |

**Windows / .NET** (selection 5):
| Tool | Tier | Description |
|------|------|-------------|
| `microsoft-docs` | Recommended | Azure and .NET documentation lookup |

**CLI / terminal** (selection 6):
| Tool | Tier | Description |
|------|------|-------------|
| `ralph-loop` | Recommended | Autonomous multi-hour coding sessions. Has Stop hook. |

**Data / ML** (selection 7):
| Tool | Tier | Description |
|------|------|-------------|
| `huggingface-skills` | Recommended | Build and train ML models with Hugging Face |

**Infrastructure / DevOps** (selection 8):
| Tool | Tier | Description |
|------|------|-------------|
| `deploy-on-aws` | Recommended | 5-step AWS deployment with cost estimation |
| `terraform` | Recommended | Terraform IaC automation |
| `vercel` | Optional | Vercel deployment. Has 13 continuous hooks — install per-project only. |
| `railway` | Optional | Railway container deployment. Has PreToolUse hook on every Bash — install per-project only. |
| `netlify-skills` | Optional | Netlify serverless/edge/databases |

**API development** (selection 9):
| Tool | Tier | Description |
|------|------|-------------|
| `postman` | Essential | API collections, testing, mocks, documentation |

## Step 5: Present Recommendations

Deduplicate the combined list (a tool recommended by multiple dev types appears once, at its highest tier).

Group by scope first, then by tier within each scope:

```
=== Recommended Tools ===

GLOBAL (install once, available in every project)
  Essential:
    1. superpowers — TDD, debugging, brainstorming, subagent workflows
    2. code-review — Multi-agent PR code review
    ...
  Recommended:
    5. claude-code-setup — Analyze codebase and recommend automations
    ...

LOCAL (install in this project only)
  Essential:
    7. typescript-lsp — TypeScript/JS type checking and diagnostics
    8. frontend-design — Production-grade UI generation
    ...
  Recommended:
    11. security-guidance — File write scanning. Has PreToolUse hook.
    ...

Total: X new tools (Y already installed, skipped)
  Global: N plugins    Local: M plugins
```

For any plugin with continuous hooks (PreToolUse, PostToolUse, UserPromptSubmit), append a warning after its description:
```
  ⚡ Has N continuous hooks — install per-project only
```

Then ask:

> **How would you like to proceed?**
>
> 1. Install all Essential tools now
> 2. Install all Essential + Recommended tools now
> 3. Install everything
> 4. Walk me through one by one (ask for each)
> 5. Just show me the list, I'll install manually

## Step 6: Execute Installation

Based on the user's choice:

- **Options 1-3**: Print each install command as you go. The user runs the commands themselves.
- **Option 4**: For each tool, show description + scope + command and ask "Install? (y/n)".
- **Option 5**: Print the full list with commands and stop.

**Install commands by scope:**
- **Global**: `/plugin install <name>@marketplace` (default scope — goes to `~/.claude/settings.json`)
- **Local**: The user should run `/plugin install <name>@marketplace` from within the project directory. Note: Claude Code installs to the project scope when run from a project context.

For LSP plugins, also note if the language server binary needs to be installed separately (e.g., `npm install -g typescript-language-server`).

For hook-heavy plugins, always print the warning:
```
Note: This plugin has continuous hooks. It is installed locally for this project only.
```

## Step 7: Verify and Summarize

Re-read `~/.claude/settings.json` to get the updated `enabledPlugins` list. Compare against the recommendations to confirm what was actually installed.

Print the summary:

```
=== Installation Summary ===
Installed: X new plugins
Already had: Y plugins
Skipped: Z plugins

Your updated toolkit covers:
- Languages: TypeScript, Swift, ...
- Workflow: TDD, code review, debugging, ...
- Security: SAST scanning, vulnerability detection
- Frontend: design, accessibility, browser testing
```

If any recommended plugin doesn't appear in the updated settings, note it:

```
Note: plugin-name may not have installed — verify with /plugin list
```

## Example

```
> /install-recommended-tools

install-recommended-tools v2.0.0

=== Installed Tools ===
Plugins: 12 global, 0 local
MCP servers: 1 configured (playwright)

What types of development do you work on?
> 1, 2

What languages do you primarily use?
> 1, 3

=== Recommended Tools ===

GLOBAL (install once, available everywhere)
  Essential:
    1. superpowers — TDD, debugging, brainstorming          [already installed]
    2. code-review — Multi-agent PR code review              [already installed]
    ...

LOCAL (install in this project only)
  Essential:
    5. typescript-lsp — TS/JS type checking and diagnostics
       /plugin install typescript-lsp@claude-plugins-official
    6. frontend-design — Production-grade UI generation
       /plugin install frontend-design@claude-plugins-official
    ...
  Recommended:
    9. security-guidance — File write vulnerability scanning
       /plugin install security-guidance@claude-plugins-official
       ⚡ Has 1 continuous hook — install per-project only

Total: 6 new tools (8 already installed, skipped)
  Global: 0 new    Local: 6 new

How would you like to proceed?
> 1
```

## Notes

- The user runs `/plugin install` commands themselves — Claude Code cannot programmatically install plugins.
- Recommendations are curated from the research catalog in the agentic-cookbook repo (`research/developer-tools/claude/plugins-and-skills-catalog.md`, relative to repo root).
- MCP server configuration (adding to `.mcp.json`) can be done by Claude Code directly if the user approves.
- For deeper info on any tool, the user can ask and the relevant research file will be referenced.
