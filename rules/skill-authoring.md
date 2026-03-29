# Skill Authoring Rule

Prerequisite: Read and follow `authoring-ground-rules.md` before applying this rule.

You are creating, renaming, or modifying a Claude Code skill. You MUST follow every step below.

---

## Before Creating a Skill

1. **Read the skill inventory** in this repo's `./CLAUDE.md`. It lists every skill, its tier, and its purpose.
2. **Check for overlap**. If an existing skill already covers the functionality you're about to create, stop. Do not create a duplicate. Propose modifying the existing skill instead.
3. **Check for naming conflicts**. If the name you're about to use is similar to an existing skill name, stop and confirm with the user. "Similar" means: shares a verb or noun prefix, could be confused at a glance, or has overlapping trigger keywords in the description.
4. **If the skill is not in the inventory**, confirm the name and purpose with the user before creating it. Do not create skills that are not in the agreed inventory without explicit approval.

## Creating the Skill

5. **Follow the skill structure reference** at `.claude/skills/lint-skill/references/skill-structure-reference.md` for frontmatter fields, directory layout, and conventions.
6. **Follow the versioning rule** at `rules/skill-versioning.md` — version in frontmatter, --version parameter, print version on invocation.
7. **Use `$ARGUMENTS`** for any skill that accepts input. Do not describe argument handling in prose without referencing `$ARGUMENTS` or positional variables (`$0`, `$1`).
8. **Use `${CLAUDE_SKILL_DIR}`** for references to the skill's own supporting files. Use repo-relative or `../agentic-cookbook/` paths for cookbook content.
9. **Include a Usage section** with at least one example invocation.
10. **Include error handling** for missing files, invalid arguments, and prerequisite failures.

## After Creating the Skill

11. **Update `CLAUDE.md`** — add the skill to the skills table with its tier and purpose.
12. **Update `./README.md` at the repo root** — add the skill to the skills table.
13. **Run the appropriate lint skill** to verify quality: `/lint-skill <path>` for skills, `/lint-agent <path>` for agents, `/lint-rule <path>` for rules.

## MUST NOT

- You MUST NOT create a skill that duplicates an existing skill's purpose.
- You MUST NOT create a skill that is not in the CLAUDE.md inventory without user approval.
- You MUST NOT name a skill without checking for conflicts with existing names.
- You MUST NOT skip updating CLAUDE.md and README.md after creating a skill.
