# Skill Versioning Rule

Prerequisite: Read and follow `authoring-ground-rules.md` before applying this rule.

Every Claude Code skill and rule file in this repo uses a `version` field in its YAML frontmatter. You MUST follow these rules when modifying any skill, agent, or rule file.

---

## Version Field

The `version` field in frontmatter tracks changes to the extension. It is NOT a recognized Claude Code runtime field — it is metadata maintained by convention.

## Rules

1. **Always increment version** when you modify a skill's SKILL.md, any of its reference files, or a rule file. Use semver:
   - **Patch** (x.y.Z): fix typos, clarify wording, update stale references
   - **Minor** (x.Y.0): add new criteria, new steps, new reference files, expand scope
   - **Major** (X.0.0): rename, restructure, change inputs/outputs, break compatibility

2. **Update the --version output** to match. Every skill MUST have a version check in its Startup section:
   ```
   If `$ARGUMENTS` is `--version`, respond with exactly:
   > skill-name vX.Y.Z
   Then stop.
   ```

3. **Print version on invocation**. Every skill MUST print its name and version as the first line of output when invoked normally (not just for --version):
   ```
   skill-name vX.Y.Z
   ```

4. **Update title headings** if the version appears in them (e.g., `# Import Agentic Cookbook v4.0.0`).

5. **Do not skip versioning** because the change is small. Every change gets a version bump.

6. **Session version check**. Every skill MUST check whether the running version matches the on-disk version during Startup. Add this to the Startup section after the version print:

   ```
   **Version check**: Read `${CLAUDE_SKILL_DIR}/SKILL.md` from disk and extract the `version:` field from frontmatter. Compare to this skill's version (X.Y.Z). If they differ, print:

   > ⚠ This skill is running vX.Y.Z but vA.B.C is installed. Restart the session to use the latest version.

   Then continue running — do not stop. The user may choose to continue with the older version.
   ```

   This catches cases where a skill was updated mid-session but the session loaded the old version at startup.

## MUST NOT

- You MUST NOT ship a modified skill without bumping the version.
- You MUST NOT leave the frontmatter `version:` and `--version` output mismatched.
- You MUST NOT skip the title heading version update when bumping.
- You MUST NOT ignore the session version check warning — it means you are running stale code.
