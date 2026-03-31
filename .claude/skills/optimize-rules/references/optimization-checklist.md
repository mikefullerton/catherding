# Optimization Checklist

Reference for Phase 3 (Execute). Apply these techniques when generating the consolidated `optimized-rules.md`.

---

## Consolidation Technique

When merging multiple rule files into one:

1. **Group by concern** — identify logical themes across all rules (e.g., git workflow, authoring discipline, permissions, versioning). Each theme becomes a section (H2) in the output.
2. **Preserve prerequisite ordering** — if rule A says "read rule B first," inline B's content before A's content in the output.
3. **Use a single MUST NOT section** — collect all MUST NOT items from every rule into one unified section at the end.
4. **Keep the heading hierarchy flat** — H1 for the title, H2 for each concern section, H3 for subsections. No deeper nesting.

## Deduplication Technique

When two or more rules express the same constraint:

1. **Exact duplicates** — identical sentences or paragraphs across files. Keep one instance, delete the rest.
2. **Semantic duplicates** — different wording, same behavioral constraint (e.g., "always commit after each change" and "do not accumulate uncommitted work"). Merge into the strongest phrasing. Prefer MUST over SHOULD, and specific over vague.
3. **Subset duplicates** — one rule says "do X" and another says "do X, Y, and Z." Keep the superset, drop the subset.

## MUST NOT Consolidation

1. Collect every MUST NOT / "Do not" / "Never" constraint from all input rules.
2. Remove items that restate a positive constraint already in the rule body (e.g., body says "commit after each change" and MUST NOT says "do not accumulate uncommitted work" — the MUST NOT is redundant).
3. Merge items with the same intent into one statement.
4. Sort alphabetically or by concern group for scannability.

## Inline Summary Technique

When a rule mandates reading an external file:

1. If the external file is primarily metadata (>50% frontmatter), replace the mandatory read with a 1-2 sentence inline summary of the behavioral content, plus the file path as an optional reference.
2. If the external file contains actionable behavioral content, keep the mandatory read but note it in the audit.
3. Never inline large files verbatim — summarize the constraints, not the content.

## Output Structure Template

```markdown
# Project Rules

## [Concern 1 — e.g., Authoring Discipline]
[Merged constraints from all rules related to this concern]

## [Concern 2 — e.g., Git Workflow]
[Merged constraints]

## [Concern N]
[Merged constraints]

## MUST NOT
- [Unified list of all prohibitions, deduplicated]
```

## Constraint Preservation Checklist

During generation, maintain a running tally:
- For each MUST in the originals: note where it appears in the output
- For each MUST NOT in the originals: note where it appears in the output
- For each SHOULD in the originals: note where it appears in the output
- If any constraint has no mapping → stop and flag it before writing the file
