# Claude Code Skill Structure Reference

> Source: https://code.claude.com/docs/en/skills

## Directory Layout

```
.claude/skills/<skill-name>/
  SKILL.md              # Required — main skill definition
  references/           # Optional — templates, guides, examples
  scripts/              # Optional — helper scripts
  examples/             # Optional — example inputs/outputs
```

## Frontmatter Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | string | directory name | Display name and slash-command trigger (kebab-case, lowercase, ≤64 chars) |
| `description` | string | — | When to use this skill; shown in context for auto-invocation matching |
| `argument-hint` | string | — | Hint for expected arguments (e.g., `<path>`, `<issue-number>`) |
| `disable-model-invocation` | boolean | `false` | If `true`, Claude will not auto-invoke; user must use `/name` |
| `user-invocable` | boolean | `true` | If `false`, skill is hidden from slash-command menu (background knowledge only) |
| `allowed-tools` | list | all tools | Restrict which tools the skill can use |
| `model` | string | session model | Override the model for this skill |
| `effort` | string | session effort | Override effort level |
| `context` | string | — | Set to `fork` to run in an isolated subagent context |
| `agent` | string | — | Specify subagent type when using `context: fork` |
| `hooks` | object | — | Lifecycle hooks (preInvoke, postInvoke) |
| `paths` | list | — | Glob patterns limiting auto-activation to matching file paths |
| `shell` | string | `bash` | Shell for inline commands (`bash` or `powershell`) |

## String Substitutions

| Variable | Expands to |
|----------|-----------|
| `$ARGUMENTS` | Full argument string passed after `/skill-name` |
| `$0`, `$1`, ... `$N` | Positional arguments (0-based, space-separated) |
| `${CLAUDE_SESSION_ID}` | Current session ID |
| `${CLAUDE_SKILL_DIR}` | Absolute path to this skill's directory |

## Invocation Control Matrix

| `disable-model-invocation` | `user-invocable` | Behavior |
|---------------------------|-----------------|----------|
| `false` (default) | `true` (default) | Auto-invoked by Claude + available as `/command` |
| `true` | `true` | Only via `/command` — never auto-invoked |
| `false` | `false` | Auto-invoked as background knowledge — not in menu |
| `true` | `false` | Never invoked — effectively disabled |

## Skill Locations (Priority Order)

1. Enterprise managed skills (highest priority)
2. Personal skills: `~/.claude/skills/`
3. Project skills: `.claude/skills/`
4. Plugin skills (lowest priority)

## Content Types

- **Reference content**: Background knowledge, conventions, style guides. Runs inline. Use `user-invocable: false` if it should only load automatically.
- **Task content**: Step-by-step instructions for specific actions. Use `disable-model-invocation: true` for side-effect operations.

## Key Guidelines

- Keep SKILL.md under 500 lines; put detailed content in references/
- Use `${CLAUDE_SKILL_DIR}` to reference supporting files
- Description should use keywords users would naturally say
- Skill descriptions are loaded into context to help Claude decide what's available
- Full skill content only loads when invoked
- The main file MUST be named `SKILL.md` (uppercase stem) — Claude Code looks for this exact filename
- Supporting files in references/, scripts/, examples/ should use lowercase descriptive names
