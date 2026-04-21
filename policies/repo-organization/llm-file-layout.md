---
title: "LLM File Layout"
summary: "Where Claude/LLM extensions live: /claude/<type>/ for global, .claude/ for repo-local. General policies go in /policies/."
triggers: [adding-claude-extension, adding-skill, writing-claude-rule, setting-up-graphify, adding-mcp-server]
tags: [claude, llm, organization, extensions, graphify]
---

# LLM File Layout

Where Claude/LLM extensions live: `/claude/<type>/` for global, `.claude/` for repo-local. General policies go in `/policies/`.

## LLM Neutrality

- You MUST NOT assume Claude is the LLM being used in a repo unless the repo is explicitly Claude-specific.
- In repos that are not Claude-specific, any Claude-related files MUST go in a `/claude` directory.

## Graphify

Every repo SHOULD be opted into Graphify (for any LLM that supports it). Opting in requires:

1. Graphify installed on the machine: `pip install graphifyy && graphify install`
2. `graphify-out/` added to `.gitignore` (generated output, never committed)
3. A `.graphifyignore` if any directories should be excluded (same syntax as `.gitignore`)
4. Run `/graphify` in a session to generate the initial graph

## Rules vs Behavioral Instructions

Not all rules are the same:

- **General policies** (like this document) apply regardless of which LLM or tool is being used. These MUST live in `/policies/` and MUST be written in plain language for anyone (human or AI) to follow.
- **Claude-specific behavioral instructions** tell Claude how to behave in specific situations ("when X happens, do Y"). These MUST live in `.claude/CLAUDE.md` (project scope) or `/claude/rules/` (global scope), and MUST be written as directives to Claude specifically.

If a rule would make sense for a human developer to follow, it is a general policy. If it is "Claude, remember to …" it is a behavioral instruction.

## Claude Extensions

Extensions to Claude's functionality (skills, rules, agents, MCP integrations, commands, plugins, hooks, etc.) are scoped by who they affect.

**Global extensions** affect Claude across all projects. These MUST live in `/claude/<type>/`, named for the extension type:

```
/claude/skills/
/claude/plugins/
/claude/rules/
/claude/agents/
/claude/commands/
/claude/hooks/
```

Global extensions MUST be installed and uninstalled by scripts in the `/setup` directory (see [setup-scripts](../general-software-development/setup-scripts.md)).

**Repo-local extensions** only affect Claude when working in this repo. These MUST live in `.claude/`, following Claude Code's own conventions:

```
.claude/skills/
.claude/CLAUDE.md
```

Repo-local extensions do not need install/uninstall scripts — Claude Code picks them up automatically.

**Derived from cookbook:** [separation-of-concerns](../../../agenticcookbook/principles/separation-of-concerns.md), [explicit-over-implicit](../../../agenticcookbook/principles/explicit-over-implicit.md)
