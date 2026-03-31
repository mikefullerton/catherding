---
name: optimize-rules
version: "1.1.0"
description: "Optimize Claude Code rules by consolidating into a single efficient file. Triggers on 'optimize rules', 'optimize my rules', or /optimize-rules."
argument-hint: "[path] [--revert] [--dry-run]"
allowed-tools: Read, Glob, Grep, Write, Edit, Bash(wc *, rm, cp, mkdir, ls, cat), AskUserQuestion
disable-model-invocation: true
model: sonnet
---

## Version Check

If `$ARGUMENTS` is `--version`, respond with exactly:

> optimize-rules v1.1.0

Then stop. Do not continue with the rest of the skill.

Otherwise, print `optimize-rules v1.1.0` as the first line of output, then proceed.

**Version check**: Read `${CLAUDE_SKILL_DIR}/SKILL.md` from disk and extract the `version:` field from frontmatter. If it differs from this skill's version (1.1.0), print:

> ⚠ This skill is running v1.1.0 but vA.B.C is installed. Restart the session to use the latest version.

Continue running — do not stop.

---

# Optimize Rules

Consolidate multiple Claude Code rule files into a single optimized file, reducing per-turn context cost while preserving all behavioral constraints.

## Guards

- This skill **modifies files** — it copies, creates, and deletes rule files
- **Always** prompts for confirmation before modifying files — there is no auto mode
- **Never** deletes original rule files without first verifying the backup is complete (file count matches)
- If validation fails (a constraint is missing from the output), automatically revert
- **`--dry-run` mode is read-only** — it never modifies, creates, or deletes any files

---

## Step 1: Parse Arguments

Parse `$ARGUMENTS` for flags and path:

1. **`--revert`** → jump to the **Revert Workflow** (Step 3)
2. **`--dry-run`** → set dry-run mode (run audit and proposal only, no modifications)
3. **Remaining text** → treat as the path to the rules directory

If no path is provided, default to `.claude/rules/`.

Resolve the path to an absolute path. Verify the directory exists. If it does not exist, print:

> ERROR: Directory not found: `<path>`

And stop.

---

## Step 2: Disclaimer

**If `--dry-run` is set**, skip this step entirely — proceed directly to Step 4.

Before any work, print:

> **Rule Optimization**
>
> This skill will consolidate your rule files into a single optimized file.
> Your originals will be backed up and can be restored at any time with `/optimize-rules --revert`.

Use AskUserQuestion: "Continue with rule optimization?"

Options:
1. **Yes, continue** — proceed to Step 4
2. **No, cancel** — print "Cancelled." and stop

---

## Step 3: Revert Workflow

_Runs when `--revert` is present, or called internally by Step 4 during re-optimization._

1. **Resolve target** — use the path from Step 1 (or default `.claude/rules/`)
2. **Compute backup path** — the backup directory is a sibling of the target with the name `unoptimized-rules/`. For example:
   - `.claude/rules/` → `.claude/unoptimized-rules/`
   - `foo/rules/` → `foo/unoptimized-rules/`
3. **Verify backup exists** — if the backup directory does not exist, print:
   > No backup found at `<backup path>`. Nothing to revert.

   And stop.
4. **Delete `optimized-rules.md`** from the target directory. If it does not exist, print a warning but continue.
5. **Copy all `.md` files** from the backup directory back to the target directory.
6. **Remove the backup directory**.
7. **Print confirmation**:
   ```
   === REVERTED ===
   Restored <n> rule files to <target path>
   Removed backup at <backup path>
   ```
8. **If invoked via `--revert`**: stop here — do not continue to optimization phases.
   **If invoked internally by Step 4**: continue to Phase 1.

---

## Step 4: Pre-flight Checks

1. Use Glob to find all `*.md` files in the target directory. If none found, print:
   > No `.md` files found in `<path>`. Nothing to optimize.

   And stop.

2. **Skip if `--dry-run`**. Check if the backup directory already exists. If it does:
   - Print: "Previous optimization detected. Reverting to originals first..."
   - Run the **Revert Workflow** (Step 3) internally.
   - After revert completes, re-glob the target directory to pick up the restored files.

3. Read all `.md` files. Count total files, lines, and bytes. Store as the baseline.

---

## Phase 1: Audit

Read every `.md` rule file in the target directory. For each file, extract:

- **File path**, line count, byte count
- **Frontmatter** fields (especially `globs`, `description`)
- **All behavioral constraints**: scan for MUST, MUST NOT, SHOULD, "Do not", "Never", "Always" patterns. Record each constraint with its source file and line.
- **Cross-file duplication**: compare constraints across files. Flag exact and semantic duplicates.
- **Mandatory external reads**: find instructions that mandate reading external files (patterns: "read", "load", "review", "check" followed by a file path or glob).
- **Ungated rules**: flag rules with content-specific scope but no `globs` frontmatter.

Print the audit summary:

```
=== AUDIT ===
Rules: <n> files, <lines> lines, <bytes> bytes
Constraints: <n> MUST, <n> MUST NOT, <n> SHOULD
Duplicates: <n> cross-file duplicates found
Mandatory reads: <n> external file references
Ungated rules: <n> (content-specific but no globs)
```

List the per-file breakdown:

```
  <filename>  <lines> lines  <bytes> bytes  <constraint count> constraints
  ...
```

**If `--dry-run` is set**, also print a detailed landscape report after the audit summary:

```
=== RULES LANDSCAPE ===
Directory: <absolute path>
Previously optimized: yes/no (backup directory exists: yes/no)

--- File Details ---
<For each .md file, print:>
  <filename>
    Type: <symlink → target | regular file>
    Frontmatter: <list key frontmatter fields: globs, description>
    Lines: <n>  Bytes: <n>
    Constraints: <n> MUST, <n> MUST NOT, <n> SHOULD
    External reads: <list any mandatory file references, or "none">
    Scope: <"gated by globs: <pattern>" or "ungated (applies to all files)">

--- Cross-File Analysis ---
Duplicate constraints: <n>
  <For each duplicate group, list the constraint text and which files contain it>

Semantic overlaps: <n>
  <For each overlap, list the constraint variants and which files contain them>

--- Symlink Map ---
<For each symlink, show: filename → absolute target path>
<For each regular file, show: filename (regular file)>
```

---

## Phase 2: Propose Optimizations

Based on audit findings, propose how to consolidate all rules into one `optimized-rules.md`:

- Which files will be merged
- How many duplicate constraints will be deduplicated
- How many MUST NOT items will be consolidated
- Any mandatory reads that will be inlined as summaries
- Any other specific optimizations

Print the proposal:

```
=== OPTIMIZATION PLAN ===
Input: <n> rule files (<lines> lines, <bytes> bytes)
Output: 1 file (optimized-rules.md)

Strategy:
  - Merge <n> files into unified structure with <n> concern sections
  - Deduplicate <n> overlapping constraints
  - Consolidate <n> MUST NOT items into unified section
  - Inline <n> mandatory read summaries
  - [any other specific proposals]

Estimated reduction: ~<pct>%
```

**If `--dry-run` is set**, print:

```
=== DRY RUN COMPLETE ===
No files were modified. Run `/optimize-rules` (without --dry-run) to execute.
```

Then stop. Do not continue to Phase 3.

**Otherwise**, use AskUserQuestion to confirm:

> "Proceed with optimization?"

Options:
1. **Yes, optimize** — continue to Phase 3
2. **No, cancel** — print "Optimization cancelled." and stop

---

## Phase 3: Execute

1. **Create backup directory** (sibling to target, named `unoptimized-rules/`).
2. **Copy all `.md` files** from target to backup directory.
3. **Verify backup** — count files in backup. If count does not match source count, print error and stop. Do NOT proceed to deletion.
4. **Load the optimization checklist** — read `${CLAUDE_SKILL_DIR}/references/optimization-checklist.md`.
5. **Generate `optimized-rules.md`**:
   - Follow the checklist's consolidation technique to group by concern
   - Apply deduplication technique to merge overlapping constraints
   - Apply MUST NOT consolidation to unify prohibitions
   - Apply inline summary technique for metadata-heavy mandatory reads
   - Use the output structure template from the checklist
   - Maintain the constraint preservation tally as you write — every original constraint MUST appear in the output
6. **Write `optimized-rules.md`** to the target directory.
7. **Remove the original `.md` files** from the target directory (do NOT remove `optimized-rules.md`).

---

## Phase 4: Validate

1. **Constraint mapping** — for every MUST, MUST NOT, and SHOULD constraint recorded in the audit:
   - Find its equivalent in `optimized-rules.md`
   - Record the mapping (original file:line → optimized file:line)
2. **Check for gaps** — if any constraint cannot be mapped:
   - Print: `VALIDATION FAILED: Missing constraint from <source file>: "<constraint text>"`
   - **Automatically revert** — run the Revert Workflow (Step 3)
   - Stop
3. **Measure result** — count lines and bytes of `optimized-rules.md`
4. **Calculate reduction** — compare to baseline from Pre-flight

---

## Phase 5: Report

Print the final report:

```
=== OPTIMIZATION COMPLETE ===
Before: <n> files, <lines> lines, <bytes> bytes
After:  1 file, <lines> lines, <bytes> bytes
Reduction: <pct>% lines, <pct>% bytes

Constraints preserved: <n>/<n> ✓
Backup: <backup dir path>

To revert: /optimize-rules --revert [path]
```

---

## Examples

**Optimize the default rules directory:**
```
/optimize-rules
```

**Optimize a custom rules path:**
```
/optimize-rules path/to/my/rules/
```

**Preview what optimization would do (read-only):**
```
/optimize-rules --dry-run
```

**Dry-run a custom rules path:**
```
/optimize-rules --dry-run path/to/my/rules/
```

**Restore original rules after optimization:**
```
/optimize-rules --revert
```

---

## Done

The optimization is complete. The original rules are backed up and can be restored with `/optimize-rules --revert`.
