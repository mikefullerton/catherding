---
name: llm-integration-policies
description: Use when a file imports an LLM SDK (anthropic, openai, langchain, etc.), when scaffolding LLM features, or when placing Claude-specific files in a repo. Enforces the "do not assume Claude" rule, the /claude directory convention, Graphify opt-in, and the rules-vs-behavioral-instructions split.
---

# LLM Integration — MANDATORY

## Do not assume Claude

- **Do not assume Claude is the LLM being used** in a repo unless the repo is explicitly Claude-specific (e.g. a Claude skill, plugin, or agent).
- If the repo is *not* Claude-specific, any Claude-related files go in a top-level `/claude` directory — not scattered across the repo.

## Graphify opt-in

Every repo must be opted into Graphify (for every LLM that supports it):

1. Graphify installed on the machine: `pip install graphifyy && graphify install`
2. `graphify-out/` added to `.gitignore` (generated output, not committed)
3. A `.graphifyignore` if any directories should be excluded (same syntax as `.gitignore`)
4. Run `/graphify` in a session to generate the initial graph

## Rules vs Behavioral Instructions

Two different things. Pick the right one:

- **General policies** — apply regardless of which LLM or tool is in use. Written in plain language for anyone (human or AI) to follow. Live in `/docs/rules/`.
- **Claude-specific behavioral instructions** — tell Claude how to behave ("when X happens, do Y"). Live in `.claude/CLAUDE.md` (project scope) or `/claude/rules/` (global scope). Written as directives to Claude specifically.

**Heuristic:** If a rule would make sense for a human developer to follow, it's a general policy. If it's "Claude, remember to...", it's a behavioral instruction.

## Claude Extensions

Extensions (skills, rules, agents, MCP integrations, commands, plugins, hooks) are scoped by who they affect:

- **Global** — affect Claude across all projects. Live in `/claude/<type>/` (e.g. `/claude/skills/`, `/claude/rules/`). **Must have install/uninstall scripts in `/setup/`.**
- **Repo-local** — only affect Claude inside this repo. Live in `.claude/` (e.g. `.claude/skills/`, `.claude/CLAUDE.md`). **No install scripts needed** — Claude Code picks them up automatically.

## Reference

Full rationale: `~/projects/active/cat-herding/docs/rules/development-policies.md` (section: "LLMs").
