import { copyFixture, cleanup } from "../lib/fixtures.js";
import { runSkill } from "../lib/runner.js";

describe("/lint-skill", () => {
  let testDir: string;

  beforeEach(() => {
    testDir = copyFixture("lint-skill");
  });

  afterEach(() => {
    cleanup(testDir);
  });

  it("passes a well-structured skill", async () => {
    const result = await runSkill(
      "/lint-skill .claude/skills/good-skill",
      { cwd: testDir }
    );

    const output = result.output.toLowerCase();
    // Good skill should not fail hard structural checks
    expect(output).not.toMatch(/fail.*s01/); // has frontmatter
    expect(output).not.toMatch(/fail.*s04/); // has description
    expect(output).not.toMatch(/fail.*c08/); // no conflicting instructions
  });

  it("catches problems in a bad skill", async () => {
    const result = await runSkill(
      "/lint-skill .claude/skills/bad-skill",
      { cwd: testDir }
    );

    const output = result.output.toLowerCase();
    // Bad skill has no frontmatter, vague directives, no structure
    expect(output).toMatch(/fail|warn/);
  });
});
