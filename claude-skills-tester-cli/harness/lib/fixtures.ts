/**
 * Fixture management — copy synthetic projects to temp directories.
 */

import { cpSync, mkdtempSync, rmSync, existsSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";

const FIXTURES_DIR = join(import.meta.dirname, "../fixtures");

/**
 * Copy a named fixture to a temp directory.
 * Returns the path to the temp directory.
 */
export function copyFixture(name: string): string {
  const src = join(FIXTURES_DIR, name);
  if (!existsSync(src)) {
    throw new Error(`Fixture not found: ${name} (looked in ${FIXTURES_DIR})`);
  }

  const dest = mkdtempSync(join(tmpdir(), `cookbook-test-${name}-`));
  cpSync(src, dest, { recursive: true });
  return dest;
}

/**
 * Delete a temp directory created by copyFixture.
 */
export function cleanup(dir: string | undefined): void {
  if (dir && dir.startsWith(tmpdir())) {
    rmSync(dir, { recursive: true, force: true });
  }
}
