---
name: new-project
description: "Create a new GitHub repo with project scaffolding, CLAUDE.md, and docs"
version: "1.0.0"
argument-hint: "<project-name> [in <org>] [--help] [--version]"
allowed-tools: Bash(gh *, git *, python3 *, test *, ls *), AskUserQuestion
model: sonnet
---

# New Project v1.0.0

Create a new GitHub repo, clone it locally, and scaffold standard project files.

## Startup

If `$ARGUMENTS` is `--version`, respond with exactly:
> new-project v1.0.0

Then stop.

**CRITICAL**: Print the version line first:

new-project v1.0.0

**Version check**: Read `${CLAUDE_SKILL_DIR}/SKILL.md` from disk and extract the `version:` field from frontmatter. Compare to this skill's version (1.0.0). If they differ, print:
> ⚠ This skill is running v1.0.0 but vA.B.C is installed. Restart the session to use the latest version.

## Route by argument

| `$ARGUMENTS` | Action |
|---|---|
| `--help` | Go to **Help** |
| `--version` | Print version and stop |
| `<name>` | Set name, org = `agentic-cookbook`, go to **Get Description** |
| `<name> in <org>` | Set name and org, go to **Get Description** |
| *(empty)* | Go to **Prompt** |

**Parsing rule**: Split `$ARGUMENTS` on spaces. If the token `in` appears, everything before it is the project name and everything after it is the org. Otherwise the entire argument is the project name.

---

## Help

Print the following exactly, then stop:

> ## New Project
>
> Create a new GitHub repo with project scaffolding.
>
> **Usage:**
> - `/new-project my-foo-project` — creates in agentic-cookbook (default org)
> - `/new-project my-foo-project in my-org` — creates in specified org
> - `/new-project` — interactive prompts for all fields
>
> **What it creates:**
> - Private GitHub repo
> - Clones to `~/projects/active/<name>/`
> - README.md, .claude/CLAUDE.md, .gitignore, .claude/settings.json
> - docs/planning/planning.md, docs/project/description.md
> - Initial commit pushed to remote

---

## Prompt

No arguments were provided. Use AskUserQuestion to ask for each field one at a time:

1. **Project name** (required, kebab-case)
2. **GitHub org** (default: `agentic-cookbook`)
3. **Brief description** (1-2 sentences)

Then go to **Execute**.

---

## Get Description

Name and org are set from arguments. Use AskUserQuestion to ask:

> What's a brief description for this project? (1-2 sentences)

Then go to **Execute**.

---

## Execute

You now have: `name`, `org`, and `description`.

Run these steps sequentially. If any step fails, stop and report the error.

### Step 1 — Verify prerequisites

```bash
test -d ~/projects/active/ && echo "OK" || echo "MISSING"
```

If `~/projects/active/` does not exist, stop and tell the user.

Check the project doesn't already exist locally:
```bash
test -d ~/projects/active/<name> && echo "EXISTS" || echo "OK"
```

If it already exists, stop and tell the user.

### Step 2 — Create GitHub repo

```bash
gh repo create <org>/<name> --private
```

### Step 3 — Clone repo

```bash
gh repo clone <org>/<name> ~/projects/active/<name>
```

### Step 4 — Scaffold project files

```bash
python3 ${CLAUDE_SKILL_DIR}/references/setup-project.py "<name>" "<org>" "<description>"
```

### Step 5 — Initial commit and push

```bash
git -C ~/projects/active/<name> add -A && git -C ~/projects/active/<name> commit -m "Initial project scaffolding" && git -C ~/projects/active/<name> push
```

### Step 6 — Summary

Print a summary:

> **Project created!**
>
> - **Repo**: https://github.com/`<org>`/`<name>`
> - **Local**: ~/projects/active/`<name>`/
>
> Files created:
> - README.md
> - .claude/CLAUDE.md
> - .claude/settings.json
> - .gitignore
> - docs/planning/planning.md
> - docs/project/description.md
