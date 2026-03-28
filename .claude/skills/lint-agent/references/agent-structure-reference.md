# Claude Code Agent Structure Reference

> Source: https://code.claude.com/docs/en/sub-agents

## File Format

Agents are markdown files with YAML frontmatter, placed in `.claude/agents/`.

```
.claude/agents/<agent-name>.md
```

The markdown body serves as the agent's system prompt.

The filename should be lowercase kebab-case (e.g., `build-runner.md`). Uppercase stems are reserved for identity files like `SKILL.md` and `CLAUDE.md`.

## Frontmatter Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | string | filename | Display name for the agent |
| `description` | string | — | When to use this agent; helps Claude select the right agent |
| `tools` | list | all tools | Allowlist of tools the agent can use |
| `disallowedTools` | list | none | Denylist of tools (mutually exclusive with `tools`) |
| `model` | string | parent model | Override the model for this agent |
| `permissionMode` | string | inherit | `plan` (read-only), `bypassPermissions` (no prompts), or inherit from parent |
| `maxTurns` | number | unlimited | Maximum turns before the agent stops |
| `skills` | list | none | Skills preloaded into the agent's context |
| `mcpServers` | list | none | MCP servers available to the agent |
| `hooks` | object | — | Lifecycle hooks |
| `memory` | string | — | Memory scope for the agent |
| `background` | boolean | `false` | Whether the agent runs in the background |
| `effort` | string | inherit | Override effort level |
| `isolation` | string | — | Set to `worktree` for git worktree isolation |

## Agent Locations (Priority Order)

1. CLI flag (`--agent`)
2. Project agents: `.claude/agents/`
3. Personal agents: `~/.claude/agents/`
4. Plugin agents

## Tool Access Patterns

- **Unrestricted**: Omit both `tools` and `disallowedTools` — agent has access to all tools
- **Allowlist**: Set `tools` to a specific list — agent can ONLY use those tools
- **Denylist**: Set `disallowedTools` — agent can use everything EXCEPT those tools
- `tools` and `disallowedTools` are mutually exclusive

## Permission Modes

| Mode | Behavior | Use case |
|------|----------|----------|
| (inherit) | Same as parent session | General-purpose agents |
| `plan` | Read-only, no edits | Research and exploration agents |
| `bypassPermissions` | No user prompts | Fully automated pipelines |

## Key Differences from Skills and Rules

| Aspect | Skill | Agent | Rule |
|--------|-------|-------|------|
| Location | `.claude/skills/` | `.claude/agents/` | `rules/`, `.claude/`, or referenced |
| Format | Directory with `SKILL.md` | Single `.md` file | Single `.md`, plain markdown |
| Execution | Runs in current context (or fork) | Always runs as subagent | Loaded into context passively |
| Context | Shares parent context (unless forked) | Isolated context | Shapes main session |
| Tool access | `allowed-tools` in frontmatter | `tools` / `disallowedTools` | N/A |
| Invocation | Auto or `/command` | Via Agent tool or CLI `--agent` | Passive |
| State | No persistent state | Can have `memory` scope | N/A |
