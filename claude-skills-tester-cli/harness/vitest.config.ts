import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    globals: true,
    include: ["specs/**/*.test.ts"],
    testTimeout: 300_000,
    hookTimeout: 30_000,
    reporters: ["verbose"],
    pool: "threads",
    poolOptions: {
      threads: { maxThreads: 2 },
    },
  },
});
