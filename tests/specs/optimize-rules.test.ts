import { copyFixture, cleanup } from "../lib/fixtures.js";
import { runSkill } from "../lib/runner.js";
import { fileExists, fileContains, listFiles } from "../lib/assertions.js";

const ACCEPT_ALL = {
  "Continue with rule optimization?": "Yes, continue",
  "Proceed with optimization?": "Yes, optimize",
};

describe("/optimize-rules", () => {
  let testDir: string;

  beforeEach(() => {
    testDir = copyFixture("optimize-rules");
  });

  afterEach(() => {
    cleanup(testDir);
  });

  // --- Happy path: user confirms everything ---

  it("creates a backup directory", async () => {
    await runSkill("/optimize-rules .claude/rules/", {
      cwd: testDir,
      answers: ACCEPT_ALL,
    });

    expect(fileExists(testDir, ".claude/unoptimized-rules")).toBe(true);
  });

  it("backs up all original rule files", async () => {
    await runSkill("/optimize-rules .claude/rules/", {
      cwd: testDir,
      answers: ACCEPT_ALL,
    });

    const backups = listFiles(testDir, ".claude/unoptimized-rules");
    expect(backups).toContain("rule-a.md");
    expect(backups).toContain("rule-b.md");
    expect(backups).toContain("rule-c.md");
  });

  it("produces a single optimized-rules.md", async () => {
    await runSkill("/optimize-rules .claude/rules/", {
      cwd: testDir,
      answers: ACCEPT_ALL,
    });

    const rules = listFiles(testDir, ".claude/rules");
    expect(rules).toEqual(["optimized-rules.md"]);
  });

  it("preserves key constraints in the optimized output", async () => {
    await runSkill("/optimize-rules .claude/rules/", {
      cwd: testDir,
      answers: ACCEPT_ALL,
    });

    expect(fileContains(testDir, ".claude/rules/optimized-rules.md", "commit")).toBe(true);
    expect(fileContains(testDir, ".claude/rules/optimized-rules.md", "verify")).toBe(true);
  });

  // --- Revert path ---

  it("--revert restores original rule files", async () => {
    // First optimize
    await runSkill("/optimize-rules .claude/rules/", {
      cwd: testDir,
      answers: ACCEPT_ALL,
    });
    // Then revert
    await runSkill("/optimize-rules --revert .claude/rules/", { cwd: testDir });

    const rules = listFiles(testDir, ".claude/rules");
    expect(rules).toContain("rule-a.md");
    expect(rules).toContain("rule-b.md");
    expect(rules).toContain("rule-c.md");
    expect(rules).not.toContain("optimized-rules.md");
    expect(fileExists(testDir, ".claude/unoptimized-rules")).toBe(false);
  });

  // --- Cancellation paths ---

  it("does nothing when user declines at disclaimer", async () => {
    await runSkill("/optimize-rules .claude/rules/", {
      cwd: testDir,
      answers: {
        "Continue with rule optimization?": "No, cancel",
      },
    });

    // Nothing should have changed
    expect(fileExists(testDir, ".claude/unoptimized-rules")).toBe(false);
    expect(listFiles(testDir, ".claude/rules")).toContain("rule-a.md");
  });

  it("does nothing when user declines optimization plan", async () => {
    await runSkill("/optimize-rules .claude/rules/", {
      cwd: testDir,
      answers: {
        "Continue with rule optimization?": "Yes, continue",
        "Proceed with optimization?": "No, cancel",
      },
    });

    // Audit ran but no files changed
    expect(fileExists(testDir, ".claude/unoptimized-rules")).toBe(false);
    expect(listFiles(testDir, ".claude/rules")).toContain("rule-a.md");
  });
});
