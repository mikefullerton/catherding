import { copyFixture, cleanup } from "../lib/fixtures.js";
import { runSkill } from "../lib/runner.js";

describe("/lint-rule", () => {
  let testDir: string;

  beforeEach(() => {
    testDir = copyFixture("lint-rule");
  });

  afterEach(() => {
    cleanup(testDir);
  });

  it("passes a well-structured rule", async () => {
    const result = await runSkill(
      "/lint-rule .claude/rules/good-rule.md",
      { cwd: testDir }
    );

    const output = result.output.toLowerCase();
    // Good rule should not fail major structural checks
    expect(output).not.toMatch(/fail.*r01/); // has title
    expect(output).not.toMatch(/fail.*r04/); // no vague directives
    expect(output).not.toMatch(/fail.*r07/); // single concern
  });

  it("catches vague directives in a bad rule", async () => {
    const result = await runSkill(
      "/lint-rule .claude/rules/bad-rule.md",
      { cwd: testDir }
    );

    const output = result.output.toLowerCase();
    // Bad rule has "handle errors appropriately" and no structure
    expect(output).toMatch(/fail|warn/);
  });
});
