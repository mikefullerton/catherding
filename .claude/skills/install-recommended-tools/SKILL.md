---
name: install-recommended-tools
version: "1.0.0"
description: "Walk through installing recommended Claude Code plugins, LSPs, and MCP servers based on your development type and languages."
argument-hint: "[--version]"
allowed-tools: Read, Glob, Grep, Bash(cat *), Bash(ls *), Bash(jq *), AskUserQuestion
---

# Install Recommended Tools v1.0.0

## Startup

**First action**: If `$ARGUMENTS` is `--version`, print `install-recommended-tools v1.0.0` and stop.

Otherwise, print `install-recommended-tools v1.0.0` as the first line of output, then proceed.

## Overview

An interactive guide that recommends Claude Code plugins, LSP integrations, and MCP servers based on what you build and the languages you use. It detects what's already installed and only recommends what's missing.

The recommendations come from the developer-tools research catalog at `developer-tools/research/` in the agentic-cookbook repo.

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

| Tool | Tier | Description | Install |
|------|------|-------------|---------|
| `superpowers` | Essential | TDD, systematic debugging, brainstorming, subagent workflows | `/plugin install superpowers@claude-plugins-official` |
| `security-guidance` | Essential | Scans file writes for 8 vulnerability categories | `/plugin install security-guidance@claude-plugins-official` |
| `semgrep` | Essential | Real-time SAST scanning via MCP server | `/plugin install semgrep@claude-plugins-official` |
| `code-review` | Essential | Multi-agent PR code review with confidence filtering | `/plugin install code-review@claude-plugins-official` |
| `pr-review-toolkit` | Essential | Specialized review agents across 6 domains | `/plugin install pr-review-toolkit@claude-plugins-official` |
| `hookify` | Recommended | Create custom hooks from natural language | `/plugin install hookify@claude-plugins-official` |
| `context7` | Recommended | Real, version-specific library docs in context | `/plugin install context7@claude-plugins-official` |
| `github` | Recommended | GitHub API: issues, PRs, code search | `/plugin install github@claude-plugins-official` |
| `claude-code-setup` | Recommended | Analyze codebase and recommend automations | `/plugin install claude-code-setup@claude-plugins-official` |
| `commit-commands` | Optional | Git commit, push, PR commands | `/plugin install commit-commands@claude-plugins-official` |
| `claude-md-management` | Optional | Maintain and audit CLAUDE.md files | `/plugin install claude-md-management@claude-plugins-official` |
| `remember` | Optional | Continuous cross-session memory via daily logs | `/plugin install remember@claude-plugins-official` |

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

All LSP plugins are **Essential** tier for their language.

### By Dev Type

**Web frontend** (selection 1):
| Tool | Tier | Description | Install |
|------|------|-------------|---------|
| `frontend-design` | Essential | Production-grade UI with distinctive design quality | `/plugin install frontend-design@claude-plugins-official` |
| `figma` | Essential | Read Figma designs for design-to-code translation | `/plugin install figma@claude-plugins-official` |
| `playwright` | Essential | Browser automation, E2E testing, screenshots | `/plugin install playwright@claude-plugins-official` |
| `playground` | Recommended | Interactive HTML playgrounds with live preview | `/plugin install playground@claude-plugins-official` |
| `accesslint` | Recommended | WCAG accessibility compliance checking | `/plugin marketplace add accesslint && /plugin install accesslint@accesslint` |
| `stagehand` | Optional | Natural language browser automation | `/plugin install stagehand@claude-plugins-official` |

**Web backend** (selection 2):
| Tool | Tier | Description | Install |
|------|------|-------------|---------|
| `feature-dev` | Recommended | 7-phase multi-agent feature development | `/plugin install feature-dev@claude-plugins-official` |
| `postman` | Recommended | Full API lifecycle: collections, tests, mocks, docs | `/plugin install postman@claude-plugins-official` |
| `sentry` | Optional | Error monitoring, stack traces, issue search | `/plugin install sentry@claude-plugins-official` |
| `prisma` | Optional | Prisma ORM, migrations, PostgreSQL management | `/plugin install prisma@claude-plugins-official` |

**iOS / macOS** (selection 3):
| Tool | Tier | Description | Install |
|------|------|-------------|---------|
| `figma` | Recommended | Design-to-code for iOS UI | `/plugin install figma@claude-plugins-official` |

**Android** (selection 4):
| Tool | Tier | Description | Install |
|------|------|-------------|---------|
| `figma` | Recommended | Design-to-code for Android UI | `/plugin install figma@claude-plugins-official` |

**Windows / .NET** (selection 5):
| Tool | Tier | Description | Install |
|------|------|-------------|---------|
| `microsoft-docs` | Recommended | Azure and .NET documentation lookup | `/plugin install microsoft-docs@claude-plugins-official` |

**CLI / terminal** (selection 6):
| Tool | Tier | Description | Install |
|------|------|-------------|---------|
| `ralph-loop` | Recommended | Autonomous multi-hour coding sessions | `/plugin install ralph-loop@claude-plugins-official` |

**Data / ML** (selection 7):
| Tool | Tier | Description | Install |
|------|------|-------------|---------|
| `huggingface-skills` | Recommended | Build and train ML models with Hugging Face | `/plugin install huggingface-skills@claude-plugins-official` |

**Infrastructure / DevOps** (selection 8):
| Tool | Tier | Description | Install |
|------|------|-------------|---------|
| `deploy-on-aws` | Recommended | 5-step AWS deployment with cost estimation | `/plugin install deploy-on-aws@claude-plugins-official` |
| `terraform` | Recommended | Terraform IaC automation | `/plugin install terraform@claude-plugins-official` |
| `vercel` | Optional | Vercel deployment integration | `/plugin install vercel@claude-plugins-official` |
| `railway` | Optional | Railway container deployment | `/plugin install railway@claude-plugins-official` |
| `netlify-skills` | Optional | Netlify serverless/edge/databases | `/plugin install netlify-skills@claude-plugins-official` |

**API development** (selection 9):
| Tool | Tier | Description | Install |
|------|------|-------------|---------|
| `postman` | Essential | API collections, testing, mocks, documentation | `/plugin install postman@claude-plugins-official` |
| `feature-dev` | Recommended | Multi-agent feature development workflow | `/plugin install feature-dev@claude-plugins-official` |

## Step 5: Present Recommendations

Deduplicate the combined list (a tool recommended by multiple dev types appears once, at its highest tier).

Group by tier and present:

```
=== Recommended Tools ===

ESSENTIAL (install these for a strong baseline)
  1. [plugin-name] — one-line description
     /plugin install plugin-name@claude-plugins-official
  2. ...

RECOMMENDED (strong value for your workflow)
  3. ...

OPTIONAL (specialized, install when needed)
  5. ...

Total: X new tools (Y already installed, skipped)
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

- **Options 1-3**: Print each install command as you go. Note: plugins are installed via the `/plugin install` slash command which the user must run themselves — Claude Code cannot programmatically install plugins. So for each tool, print the command and ask the user to run it.
- **Option 4**: For each tool, show description + command and ask "Install? (y/n)" before moving to the next.
- **Option 5**: Print the full list with commands and stop.

For LSP plugins, also note if the language server binary needs to be installed separately (e.g., `npm install -g typescript-language-server`).

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

install-recommended-tools v1.0.0

=== Installed Tools ===
Plugins: 33 installed (typescript-lsp, swift-lsp, semgrep, superpowers, ...)
MCP servers: 1 configured (playwright)

What types of development do you work on?
> 1, 2

What languages do you primarily use?
> 1, 3

=== Recommended Tools ===

ESSENTIAL (install these for a strong baseline)
  1. frontend-design — Production-grade UI with distinctive design quality
     /plugin install frontend-design@claude-plugins-official
  2. figma — Read Figma designs for design-to-code translation
     /plugin install figma@claude-plugins-official
  ...

RECOMMENDED (strong value for your workflow)
  5. feature-dev — 7-phase multi-agent feature development
     /plugin install feature-dev@claude-plugins-official
  ...

Total: 8 new tools (25 already installed, skipped)

How would you like to proceed?
> 1
```

## Notes

- The user runs `/plugin install` commands themselves — Claude Code cannot programmatically install plugins.
- Recommendations are curated from the research catalog in the agentic-cookbook repo (`developer-tools/research/claude/plugins-and-skills-catalog.md`, relative to repo root).
- MCP server configuration (adding to `.mcp.json`) can be done by Claude Code directly if the user approves.
- For deeper info on any tool, the user can ask and the relevant research file will be referenced.
