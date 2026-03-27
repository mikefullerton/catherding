# Claude Code Rule File Structure Reference

> Source: https://code.claude.com/docs/en/best-practices

## What is a Rule File?

Rules are standalone markdown files containing imperative instructions for an LLM. Unlike skills (which have `SKILL.md` + directory structure) or agents (which have specialized frontmatter), rules are plain `.md` files that get loaded into context — either via CLAUDE.md references, `.claude/` drop-in, or direct inclusion.

Rules enforce behavior: "You MUST do X", "Do not skip Y", "Read Z before proceeding."

## File Format

A rule file is a single `.md` file. No required directory structure, no required frontmatter schema. The file name should be descriptive and UPPER-KEBAB-CASE by convention (e.g., `AGENTIC-COOKBOOK-PLANNING-RULE.md`).

Optional frontmatter may include a title or version, but there is no enforced schema.

## Common Locations

- `rules/` at the project root — project-level rules
- `.claude/` — drop-in rules loaded by Claude Code
- `~/.claude/` — personal global rules
- Referenced from `CLAUDE.md` — loaded via instruction

## Quality Criteria

### Structure
- Clear title/heading identifying the rule's purpose
- Numbered or clearly separated steps if procedural
- Sections with headings for distinct concerns

### Content
- **Imperative tone**: Uses MUST, MUST NOT, SHOULD, MAY (RFC 2119)
- **Deterministic**: The LLM should be able to follow the rule without ambiguity
- **Explicit file references**: If the rule says "read the principles," it lists every file path
- **Self-contained or clearly scoped**: Either contains all needed information or explicitly references where to find it
- **No vague directives**: "Handle errors appropriately" is bad. "Validate user input at the API boundary, return HTTP 400 with a message for invalid input" is good.

### Anti-patterns
- **Vague rules**: "Write good code" — not actionable
- **Contradictory rules**: "Always do X" then later "Never do X"
- **Unbounded scope**: Rule tries to govern everything instead of a specific concern
- **Missing file paths**: Rule says "read the guidelines" without listing which files
- **Duplicating CLAUDE.md**: Rule content that belongs in project instructions, not a standalone rule
- **No enforcement mechanism**: Rule states preferences but provides no steps to verify compliance

## Comparison: Skills vs Agents vs Rules

| Aspect | Skill | Agent | Rule |
|--------|-------|-------|------|
| Format | Directory with `SKILL.md` | Single `.md` with agent frontmatter | Single `.md`, plain markdown |
| Frontmatter | Skill-specific (name, description, allowed-tools, etc.) | Agent-specific (tools, permissionMode, maxTurns, etc.) | None required |
| Invocation | `/command` or auto-invoked | Via Agent tool or `--agent` CLI | Loaded into context passively |
| Execution | Runs as task or reference | Runs as isolated subagent | Shapes behavior of the main session |
| Purpose | Do a specific task | Delegate a specific task | Enforce behavioral constraints |
