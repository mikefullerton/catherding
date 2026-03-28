# Lint Checklist for Claude Code Rules

> Last updated: 2026-03-27
> Sources:
> - https://code.claude.com/docs/en/best-practices

Severity levels:
- **FAIL** — violates a hard requirement; must fix
- **WARN** — departs from best practice; should fix
- **INFO** — suggestion for improvement; nice to have

---

## Content Quality

| ID  | Criterion | How to check | Severity |
|-----|-----------|-------------|----------|
| C01 | Single responsibility | Rule addresses one coherent concern — not a grab-bag of unrelated instructions | WARN |
| C07 | Instructions are actionable and specific | Every instruction tells the LLM what to do concretely, not vague directives like "handle errors appropriately" | WARN |
| C08 | No conflicting instructions | Rule does not contradict itself (e.g., "always do X" then later "never do X") | FAIL |
| C09 | Well-structured markdown | Uses headings, lists, code blocks; not a wall of unstructured text | WARN |

---

## Best Practices

| ID  | Criterion | How to check | Severity |
|-----|-----------|-------------|----------|
| B02 | Does not replicate native capabilities | Rule doesn't teach Claude things it already knows (basic git, standard coding, etc.) | WARN |
| B06 | No kitchen-sink anti-pattern | Rule doesn't try to govern everything — stays focused on its stated concern | FAIL |
| B08 | Not a CLAUDE.md dump | Content is rule-appropriate, not project configuration that belongs in CLAUDE.md | WARN |

---

## Rule-Specific

| ID  | Criterion | How to check | Severity |
|-----|-----------|-------------|----------|
| R01 | Clear title/heading | File starts with a heading that identifies the rule's purpose | WARN |
| R02 | Imperative tone throughout | Uses RFC 2119 keywords (MUST, MUST NOT, SHOULD, MAY); not advisory or suggestive | WARN |
| R03 | Steps are numbered or clearly separated | If procedural, steps are in a clear sequence with headings or numbered list | WARN |
| R04 | No vague directives | Every instruction is concrete and actionable; no "handle appropriately" or "write good code" | FAIL |
| R05 | File references are explicit | If the rule says to read files, every file path is listed explicitly — no "read the principles" without paths | FAIL |
| R06 | No contradictory instructions | Rule does not say "always do X" then later "never do X" or otherwise conflict with itself | FAIL |
| R07 | Single concern | Rule addresses one coherent concern (planning, implementing, reviewing) — not a grab-bag | WARN |
| R08 | Enforcement mechanism present | Rule includes steps to verify compliance — not just "do X" but "verify X was done" | WARN |
| R09 | Not a CLAUDE.md dump | Content is rule-appropriate, not project configuration that belongs in CLAUDE.md | WARN |
| R10 | Reasonable length | Rule is long enough to be complete but not so long it gets ignored; under ~300 lines for a single rule file | WARN |
| R11 | "MUST NOT" section present | Rule explicitly states what the LLM must NOT do — common mistakes and anti-patterns | WARN |
| R12 | Deterministic — no ambiguity | An LLM following the rule would produce consistent behavior across sessions; no room for interpretation on critical steps | WARN |
| R13 | Filename is lowercase kebab-case | Filename matches `^[a-z][a-z0-9-]*\.md$` (e.g., `testing.md`, `api-design.md`); UPPERCASE stems are reserved for identity files like `SKILL.md` and `CLAUDE.md` | WARN |
