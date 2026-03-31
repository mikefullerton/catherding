import { copyFixture, cleanup } from "../lib/fixtures.js";
import { runSkill } from "../lib/runner.js";

describe("/lint-agent", () => {
  let testDir: string;

  beforeEach(() => {
    testDir = copyFixture("lint-agent");
  });

  afterEach(() => {
    cleanup(testDir);
  });

  it("passes a well-structured agent", async () => {
    const result = await runSkill(
      "/lint-agent .claude/agents/good-agent.md",
      { cwd: testDir }
    );

    const output = result.output.toLowerCase();
    // Good agent should not fail hard structural checks
    expect(output).not.toMatch(/fail.*s01/); // has frontmatter
    expect(output).not.toMatch(/fail.*s04/); // has description
    expect(output).not.toMatch(/fail.*a01/); // has name and description
    expect(output).not.toMatch(/fail.*b06/); // not kitchen-sink
  });

  it("catches problems in a bad agent", async () => {
    const result = await runSkill(
      "/lint-agent .claude/agents/bad-agent.md",
      { cwd: testDir }
    );

    const output = result.output.toLowerCase();
    // Bad agent has no frontmatter, vague directives, kitchen-sink scope
    expect(output).toMatch(/fail|warn/);
  });
});
