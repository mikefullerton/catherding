/**
 * Filesystem assertions for testing skill outcomes.
 */

import { existsSync, readFileSync, readdirSync, statSync } from "fs";
import { join } from "path";

/**
 * Check if a path exists within a test directory.
 */
export function fileExists(testDir: string, relativePath: string): boolean {
  return existsSync(join(testDir, relativePath));
}

/**
 * Check if a file contains a string (case-sensitive).
 */
export function fileContains(
  testDir: string,
  relativePath: string,
  substring: string
): boolean {
  const fullPath = join(testDir, relativePath);
  if (!existsSync(fullPath)) return false;
  const content = readFileSync(fullPath, "utf-8");
  return content.includes(substring);
}

/**
 * Check if a file matches a regex pattern.
 */
export function fileMatches(
  testDir: string,
  relativePath: string,
  pattern: RegExp
): boolean {
  const fullPath = join(testDir, relativePath);
  if (!existsSync(fullPath)) return false;
  const content = readFileSync(fullPath, "utf-8");
  return pattern.test(content);
}

/**
 * List files in a directory within the test directory.
 * Returns filenames only (not full paths), sorted.
 */
export function listFiles(testDir: string, relativePath: string): string[] {
  const fullPath = join(testDir, relativePath);
  if (!existsSync(fullPath)) return [];
  return readdirSync(fullPath)
    .filter((f) => statSync(join(fullPath, f)).isFile())
    .sort();
}

/**
 * List directories in a directory within the test directory.
 * Returns directory names only, sorted.
 */
export function listDirs(testDir: string, relativePath: string): string[] {
  const fullPath = join(testDir, relativePath);
  if (!existsSync(fullPath)) return [];
  return readdirSync(fullPath)
    .filter((f) => statSync(join(fullPath, f)).isDirectory())
    .sort();
}

/**
 * Read a file's content from the test directory.
 */
export function readFile(testDir: string, relativePath: string): string {
  return readFileSync(join(testDir, relativePath), "utf-8");
}
