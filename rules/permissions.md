# Permissions Rule

Prerequisite: Read and follow `authoring-ground-rules.md` before applying this rule.

Before starting implementation, you MUST audit the plan for all permissions needed and present them as a single atomic prompt. The user says yes or no once — not per-item, not per-category. The goal is zero mid-execution permission prompts so the user can walk away and come back to completed work.

---

## Before Implementation

1. **Audit the plan**. Read the approved plan and identify every action in the following categories — assume ALL of these require permission:
   - Files to create, modify, or delete (list each path)
   - Bash commands to run (list each command type and why)
   - Skills to invoke
   - Agents to launch
   - External tools (gh, claude, etc.)

   Before presenting the prompt, you MUST verify every plan step has a corresponding permission entry. If any step lacks one, the audit is incomplete — add it.

2. **Present a single atomic permission prompt**. List everything with reasons, then ask one yes/no question:

```
=== Permissions Required ===

This implementation needs the following. Approve all or decline all.

Files:
- Write .claude/rules/cookbook.md — install cookbook rule
- Edit CLAUDE.md — add Agentic Cookbook section

Commands:
- mkdir -p .claude/rules — create rules directory
- cp ../agentic-cookbook/rules/cookbook.md .claude/rules/ — copy rule file
- git add/commit/push — commit changes

Skills:
- /configure-cookbook — preferences and optional rules

Approve all? (yes / no)
```

3. **This is atomic**. If the user says no, do not proceed with any of it. Ask what they want to change.

4. **If the user says yes**, proceed with the full implementation without further permission requests.

## During Implementation

5. You MUST **combine file operations** — copy multiple files in a single `cp` command rather than individual Write calls.

6. If a permission prompt appears mid-execution, you MUST **stop immediately** and tell the user: "I missed this in the permission audit. This needs: [what and why]. Approve to continue."

## For Skills

7. **Skills that modify files** MUST document their permission requirements in a "Permissions" section of their SKILL.md, listing every file and command the skill will use.

## MUST NOT

- You MUST NOT start implementation without the permission audit and user approval.
- You MUST NOT present permissions piecemeal — one prompt, all or nothing.
- You MUST NOT proceed after a "no" — ask what the user wants to change first.
- You MUST NOT trigger predictable permission prompts mid-execution that the audit should have caught.
