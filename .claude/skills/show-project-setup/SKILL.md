---
name: show-project-setup
version: "2.0.0"
description: "Generate an HTML dashboard showing all rules, skills, plugins, MCP servers, and dev tools installed locally and globally."
argument-hint: "[--version]"
disable-model-invocation: true
context: fork
allowed-tools: Read, Glob, Grep, Bash(which *), Bash(node *), Bash(python3 *), Bash(swift *), Bash(git *), Bash(gh *), Bash(npm *), Bash(docker *), Bash(go *), Bash(rustc *), Bash(java *), Bash(dotnet *), Bash(kubectl *), Bash(terraform *), Bash(wrangler *), Bash(code *), Bash(ls *), Bash(cat *), Bash(jq *), Bash(open *), Bash(uname *), Bash(sw_vers *), Bash(bun *), Bash(bash *), Write
---

# Show Project Setup v2.0.0

## Startup

**First action**: If `$ARGUMENTS` is `--version`, print `show-project-setup v2.0.0` and stop.

Otherwise, print `show-project-setup v2.0.0` as the first line of output, then proceed.

## Overview

Generates a self-contained HTML dashboard that shows the complete Claude Code environment for the current project. Writes to `/tmp/claude-project-setup.html` and opens it in the browser.

## Step 1: Gather All Data

Read these data sources. If any file doesn't exist or a command fails, skip that section gracefully — never error out.

### 1a: Git info
```bash
git remote get-url origin 2>/dev/null    # repo URL
git branch --show-current 2>/dev/null    # current branch
basename "$(git rev-parse --show-toplevel 2>/dev/null)" # project name
```

### 1b: CLAUDE.md files
- Read `./CLAUDE.md` — extract first 10 non-empty lines as project summary
- Read `~/.claude/CLAUDE.md` — extract first 10 non-empty lines as global summary
- Note: present or absent for each

### 1c: Project rules
- Glob `.claude/rules/*.md`
- For each file, extract YAML frontmatter fields: `description`, `globs`
- Use the filename (without extension) as the rule name

### 1d: Project skills
- Glob `.claude/skills/*/SKILL.md`
- For each, extract frontmatter: `name`, `version`, `description`, `allowed-tools`

### 1e: Global skills
- Run `ls ~/.claude/skills/` to list directories
- For each, try to read `SKILL.md` frontmatter for name and description
- If no SKILL.md, just list the directory name

### 1f: Global settings
- Read `~/.claude/settings.json`
- Extract:
  - `enabledPlugins` — object keys are `plugin-name@marketplace`. These are **global plugins**.
  - `hooks` — object with event names as keys, arrays of hook configs as values. These are **global hooks**.
  - `effortLevel` — string
  - `permissions.allow` — array of **global permissions**

### 1g: Project settings
- Read `.claude/settings.json` — extract `permissions.allow` as **project permissions**
- Read `.claude/settings.local.json` — extract `permissions.allow` as **local permission overrides**
- Also check for `enabledPlugins` in project settings — these are **project-local plugins** (distinct from global)

### 1h: MCP servers
- Read `.mcp.json` — extract `mcpServers` object (name → command/args). These are **project MCP servers**.
- Read `~/.claude.json` — extract any user-scoped MCP servers. These are **global MCP servers**.

### 1i: Dev tools and environment

Run a **single bash script** to detect all tools and environment info at once. This avoids 30+ individual tool calls.

```bash
bash -c '
check() {
  if which "$2" >/dev/null 2>&1; then
    local v; v=$($3 2>&1 | head -1)
    echo "$1|installed|$v"
  else
    echo "$1|not installed|"
  fi
}
check "Node.js" "node" "node --version"
check "Python" "python3" "python3 --version"
check "Swift" "swift" "swift --version"
check "Git" "git" "git --version"
check "GitHub CLI" "gh" "gh --version"
check "npm" "npm" "npm --version"
check "Bun" "bun" "bun --version"
check "Docker" "docker" "docker --version"
check "Go" "go" "go version"
check "Rust" "rustc" "rustc --version"
check "Java" "java" "java --version"
check ".NET" "dotnet" "dotnet --version"
check "kubectl" "kubectl" "kubectl version --client --short"
check "Terraform" "terraform" "terraform version"
check "Wrangler" "wrangler" "wrangler --version"
check "VS Code" "code" "code --version"
echo "---ENV---"
echo "os|$(uname -s)"
echo "os_version|$(sw_vers --productVersion 2>/dev/null || echo unknown)"
echo "shell|$SHELL"
echo "api_key|$([ -n "$ANTHROPIC_API_KEY" ] && echo present || echo absent)"
'
```

Parse the pipe-delimited output into structured data for the HTML. Each line is `name|status|version`.

### 1j: Scan plugin hooks

For each installed plugin, check if it has a `hooks/hooks.json` file in the plugin cache:

```bash
bash -c '
for dir in ~/.claude/plugins/cache/claude-plugins-official/*/; do
  name=$(basename "$dir")
  latest=$(ls "$dir" 2>/dev/null | sort -V | tail -1)
  hfile="$dir$latest/hooks/hooks.json"
  if [ -f "$hfile" ]; then
    count=$(python3 -c "
import json
with open(\"$hfile\") as f:
    d=json.load(f)
hooks=d.get(\"hooks\",{})
total=0
continuous=[]
for event,hlist in hooks.items():
    n=len(hlist) if isinstance(hlist,list) else 1
    total+=n
    if event in (\"PreToolUse\",\"PostToolUse\",\"UserPromptSubmit\"):
        continuous.append(event)
print(f\"$name|{total}|{\",\".join(continuous)}\")
" 2>/dev/null)
    [ -n "$count" ] && echo "$count"
  else
    echo "$name|0|"
  fi
done
'
```

Parse into a map of `plugin-name -> {hook_count, continuous_events[]}`. A plugin is "hook-heavy" if it has any continuous events (PreToolUse, PostToolUse, or UserPromptSubmit).

Also check the accesslint marketplace: `~/.claude/plugins/cache/accesslint/*/`.

### 1k: Detect project type and suggest tools

Scan the codebase to detect what kind of project this is, then suggest tools that aren't installed yet. Check these signals:

| Signal | Check | Project type |
|--------|-------|-------------|
| `package.json` | Glob for `package.json` | Web / Node.js |
| React/Vue/Svelte | Grep for `react`, `vue`, `svelte` in package.json dependencies | Web frontend |
| Express/Fastify/Hono | Grep for `express`, `fastify`, `hono` in package.json | Web backend |
| `*.swift` files or `Package.swift` | Glob for `**/*.swift` or `Package.swift` | Apple / iOS / macOS |
| `*.xcodeproj` or `*.xcworkspace` | Glob for `**/*.xcodeproj` | Apple / Xcode |
| `build.gradle` or `build.gradle.kts` | Glob for `**/build.gradle*` | Android |
| `*.kt` files | Glob for `**/*.kt` | Kotlin / Android |
| `*.csproj` or `*.sln` | Glob for `**/*.csproj` or `**/*.sln` | Windows / .NET |
| `Dockerfile` | Glob for `**/Dockerfile` | Infrastructure |
| `terraform/` or `*.tf` | Glob for `**/*.tf` | DevOps / IaC |
| `requirements.txt` or `pyproject.toml` | Glob for these files | Python / Data-ML |
| `go.mod` | Glob for `go.mod` | Go |
| `Cargo.toml` | Glob for `Cargo.toml` | Rust |
| `wrangler.jsonc` or `wrangler.toml` | Glob for these files | Cloudflare Workers |

Based on detected project types and currently installed plugins, build a list of **suggested tools** (not installed yet, but relevant). Use this mapping:

| Project type | Suggest if not installed |
|-------------|------------------------|
| Web frontend | `frontend-design`, `figma`, `playwright`, `accesslint`, `playground` |
| Web backend | `feature-dev`, `postman`, `sentry`, `prisma` |
| Apple | `swift-lsp` |
| Android | `kotlin-lsp` |
| Windows/.NET | `csharp-lsp`, `microsoft-docs` |
| Python | `pyright-lsp` |
| Go | `gopls-lsp` |
| Rust | `rust-analyzer-lsp` |
| Infrastructure | `deploy-on-aws`, `terraform` |
| Any | `superpowers`, `security-guidance`, `semgrep`, `code-review`, `hookify`, `context7` |

For each suggestion, include the plugin name and its install command. Render these in a "Suggested Tools" card in the sidebar, below Dev Tools. If no suggestions (everything relevant is installed), show "All recommended tools installed" in the card.

Also include the detected project types in the "Current Configuration" card as a row.

## Step 2: Generate HTML

Use `${CLAUDE_SKILL_DIR}/references/reference-dashboard.html` as the visual reference for the dashboard design — match its layout, typography, colors, and section structure.

Build a single self-contained HTML file. Everything is inline — no external stylesheets, no CDN, no imports.

### Design rules

**Theme** (dark, Serena-inspired):
- Page background: `#1a1a1a`
- Card background: `#242424`
- Card border: `1px solid #333`
- Card border-radius: `8px`
- Card padding: `20px`
- Card margin-bottom: `16px`
- Accent color: `#c4a35a` (gold)
- Text primary: `#e0e0e0`
- Text secondary: `#888`
- Text accent: `#c4a35a`
- Success: `#4caf50`
- Error/missing: `#e57373`
- Font body: `system-ui, -apple-system, sans-serif`
- Font mono: `'SF Mono', 'Menlo', 'Monaco', monospace`
- Font size base: `14px`

**Layout**:
- Max width: `1200px`, centered
- Two-column grid on `min-width: 900px`: main `2fr`, sidebar `1fr`, gap `16px`
- Single column below `900px`
- Header spans full width

**Header bar**:
- Full-width card at top
- Project name as `h1` in accent color, `font-size: 1.5rem`
- Branch, repo URL, timestamp as secondary text below

**Collapsible sections**:
- Header row: section title (left) + item count badge (right) + chevron
- Chevron: inline SVG `>` character, rotates 90deg when expanded
- Click header to toggle body visibility
- Default state: all sections expanded (disclosed). Users collapse what they don't need.
- CSS transition on the chevron rotation

**Tables inside cards**:
- Full width, no outer border
- Header row: `text-transform: uppercase; font-size: 0.7rem; letter-spacing: 0.05em; color: #888`
- Cell padding: `8px 12px`
- Row border-bottom: `1px solid #2a2a2a`
- Monospace font for paths, versions, commands

**Status badges**:
- Installed: green dot + version text
- Not installed: red dot + "not installed" in secondary color
- Present/absent: same pattern

**Plugin categories** (group `enabledPlugins` by prefix/known names):
- LSP: any name ending in `-lsp`
- Security: `security-guidance`, `semgrep`, `aikido`, `autofix-bot`, `coderabbit`, `optibot`, `nightvision`, `opsera-devsecops`, `sonatype-guide`
- Code Review: `code-review`, `pr-review-toolkit`, `code-simplifier`
- Workflow: `superpowers`, `feature-dev`, `ralph-loop`, `commit-commands`, `hookify`, `claude-code-setup`, `claude-md-management`, `remember`
- Design: `frontend-design`, `figma`, `playground`
- Dev Tools: `plugin-dev`, `agent-sdk-dev`, `mcp-server-dev`, `skill-creator`, `ai-firstify`
- Source Control: `github`, `gitlab`, `linear`, `atlassian`, `asana`, `notion`
- Deployment: `deploy-on-aws`, `aws-serverless`, `migration-to-aws`, `vercel`, `railway`, `firebase`, `supabase`, `terraform`, `netlify-skills`
- Testing: `playwright`, `stagehand`, `chrome-devtools-mcp`
- Search: `context7`, `greptile`, `sourcegraph`, `serena`
- Accessibility: `accesslint`
- Other: everything else

**Hook indicators on each plugin** (from step 1j data):
- If `hook_count > 0`: show a gold badge after the plugin name: `⚡N hooks`
- If `hook_count == 0`: no badge
- If the plugin has continuous events AND is in global `enabledPlugins`: show an amber warning: `⚠ not recommended globally`
- Continuous events are: `PreToolUse`, `PostToolUse`, `UserPromptSubmit`

Example rendering in the plugin tree:
```
Workflow (6)
  ├── superpowers        ⚡1 hook (SessionStart)
  ├── feature-dev
  ├── hookify            ⚡4 hooks  ⚠ not recommended globally
  ├── commit-commands
  ├── claude-code-setup
  └── claude-md-management
```

**Suggested Tools scope indicator** — in the Suggested Tools card, for each suggestion note whether it should be installed globally or locally:
```
pyright-lsp                        [LSP — install locally]
No hooks. Language-specific — install per-project.
/plugin install pyright-lsp@claude-plugins-official

security-guidance                  [Security — install locally]
⚡1 hook (PreToolUse). Has continuous hooks — install per-project only.
/plugin install security-guidance@claude-plugins-official
```

### HTML section order

The dashboard is organized into two scopes after the header and config:

```
1. Header (project name + environment)
2. Current Configuration (stats, detected types)
3. Suggested Tools (based on detected project types)

── PROJECT (LOCAL) ──────────────────────────
4. Project Rules          (.claude/rules/*.md)
5. Project Skills         (.claude/skills/*/SKILL.md)
6. Project Plugins        (enabledPlugins in .claude/settings.json, if any)
7. Project MCP Servers    (.mcp.json)
8. Project Permissions    (.claude/settings.json + settings.local.json)

── GLOBAL ──────────────────────────────────
9.  Global Plugins        (enabledPlugins in ~/.claude/settings.json)
10. Global Skills         (~/.claude/skills/, excluding project-symlinked dupes)
11. Global Hooks          (hooks in ~/.claude/settings.json + plugin hooks)
12. Global Permissions    (permissions in ~/.claude/settings.json)

── ENVIRONMENT ─────────────────────────────
13. Dev Tools             (detected binaries + versions)
```

Each scope section gets a visual divider — a thin horizontal rule with the scope label ("Project" or "Global") in small monospace uppercase text, like a section separator. This makes it immediately clear which scope you're looking at.

For **Global Plugins**, show hook count badges and "not recommended globally" warnings as described above.

For **Global Skills**, deduplicate against project skills — if a global skill is a symlink that points into the current project, show it only in the Project Skills section. Show the remaining non-project global skills here.

### Collapsible JS (inline)

```javascript
document.querySelectorAll('.card-header').forEach(header => {
  header.addEventListener('click', () => {
    const body = header.nextElementSibling;
    const chevron = header.querySelector('.chevron');
    const isHidden = body.style.display === 'none';
    body.style.display = isHidden ? '' : 'none';
    chevron.style.transform = isHidden ? 'rotate(90deg)' : '';
  });
});
```

## Step 3: Write and Open

1. Write the complete HTML string to `/tmp/claude-project-setup.html` using the Write tool
2. Run: `open /tmp/claude-project-setup.html`
3. Print: `Dashboard opened at /tmp/claude-project-setup.html`

## Important rules

- **NEVER display secret values** — for API keys, tokens, or credentials, only show "present" or "absent"
- **Graceful degradation** — if any data source is missing, show "not configured" in that section instead of erroring
- **Self-contained** — the HTML file must work offline with zero external dependencies
- **No framework** — plain HTML, CSS, and vanilla JS only
- **Escape HTML** — any user-provided content (file paths, descriptions, etc.) must be escaped to prevent XSS in the generated file
- **Cap global skills** — read up to 50 global skills to avoid excessive file reads

## Example

```
> /show-project-setup

show-project-setup v2.0.0
Gathering data... rules, skills, plugins, MCP servers, dev tools...
Detected project types: Web frontend, Web backend, Cloudflare Workers
Dashboard opened at /tmp/claude-project-setup.html
```

A dark-themed HTML dashboard opens in your browser with sections organized by scope:
- **Config**: stats bar, detected project types, suggested tools
- **Project**: 5 rules, 13 skills, 0 local plugins, 1 MCP server, project permissions
- **Global**: 12 plugins (with hook count badges), 14 additional skills, 6 hook events, global permissions
- **Environment**: 8 installed dev tools, 8 not installed
