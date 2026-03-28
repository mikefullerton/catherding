# Extension Authoring Rule

Optional guidance for creating Claude Code skills, agents, and rules in your project. This rule applies the agentic cookbook's authoring best practices. It is not mandatory -- adopt what fits your workflow.

For full details, read: `../agentic-cookbook/cookbook/guidelines/skills-and-agents/authoring-skills-and-rules.md`

---

## When Creating a Skill

1. **Check for duplicates** -- read your project's CLAUDE.md skills table before creating. Confirm the name/purpose with the user if not listed.
2. **Version it** -- add `version` in frontmatter, support `--version`, print version on invocation.
3. **Add session version check** -- compare loaded version to on-disk version, warn if stale.
4. **Use `$ARGUMENTS`** for input -- don't describe argument handling in prose.
5. **Atomic permission prompt** -- before writing files, list everything in a single yes/no prompt.
6. **Include error handling** -- check prerequisites, handle invalid arguments, provide useful error messages.
7. **Include a Usage section** -- with example invocations.
8. **Lint it** -- run `/lint-skill <path>` and fix FAILs.

## When Creating a Rule

1. **Imperative tone** -- use MUST, MUST NOT, SHOULD, MAY throughout.
2. **Explicit file paths** -- list every path the LLM needs to read. No hunting.
3. **Single concern** -- one rule per topic.
4. **Include a MUST NOT section** -- list anti-patterns and common mistakes.
5. **Include verification steps** -- don't just say "do X," confirm it was done.
6. **Lint it** -- run `/lint-rule <path>` and fix FAILs.

## When Creating an Agent

1. **Restrict tool access** -- use `tools` or `disallowedTools`.
2. **Set `maxTurns`** for bounded tasks.
3. **Lint it** -- run `/lint-agent <path>`.

## This Rule is Optional

These are recommendations, not strict requirements. Your project may have different conventions. Adopt what helps, ignore what doesn't. The full guideline at `../agentic-cookbook/cookbook/guidelines/skills-and-agents/authoring-skills-and-rules.md` explains the reasoning behind each recommendation.
