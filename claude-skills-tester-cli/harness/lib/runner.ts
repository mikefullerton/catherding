/**
 * Skill runner — invokes Claude Code skills via `claude -p` (CLI).
 *
 * Uses the CLI instead of the Agent SDK so test runs go through
 * the Claude Max subscription, not API billing.
 */

import { execFile } from "child_process";

export interface RunResult {
  output: string;
  exitCode: number;
  raw: string;
}

export interface RunOptions {
  cwd: string;
  timeout?: number;
  /** Map of AskUserQuestion prompts to the answer to select. */
  answers?: Record<string, string>;
}

const DEFAULT_TIMEOUT = 300_000; // 5 minutes

/**
 * Run a skill in a directory via `claude -p`.
 *
 * Each call creates a new session with `cwd` set to the fixture directory.
 * Skills are discovered from the fixture's `.claude/skills/`.
 * Uses --dangerously-skip-permissions to auto-approve tool use.
 *
 * If `opts.answers` is provided, a system prompt instruction tells Claude
 * to match AskUserQuestion calls against the mapping and select the
 * specified answer. This enables testing every decision branch.
 *
 * Runs through Claude Max subscription — no API billing.
 */
export async function runSkill(
  prompt: string,
  opts: RunOptions
): Promise<RunResult> {
  const timeout = opts.timeout ?? DEFAULT_TIMEOUT;

  const args = [
    "-p", prompt,
    "--output-format", "json",
    "--dangerously-skip-permissions",
  ];

  if (opts.answers && Object.keys(opts.answers).length > 0) {
    const mapping = JSON.stringify(opts.answers);
    args.push(
      "--append-system-prompt",
      `TESTING MODE: When AskUserQuestion is called, match the question text against this mapping and select the specified answer:\n${mapping}\nIf no match is found, select the first option. Do not hesitate or ask for clarification.`
    );
  } else {
    args.push(
      "--append-system-prompt",
      "TESTING MODE: When AskUserQuestion is called, always select the first option. Do not hesitate or ask for clarification."
    );
  }

  return new Promise((resolve) => {
    execFile(
      "claude",
      args,
      {
        cwd: opts.cwd,
        timeout,
        maxBuffer: 1024 * 1024 * 5, // 5MB
      },
      (error, stdout, stderr) => {
        if (error && !stdout) {
          resolve({
            output: stderr || error.message,
            exitCode: error.code ?? 1,
            raw: stdout || "",
          });
          return;
        }

        try {
          const parsed = JSON.parse(stdout);
          resolve({
            output: parsed.result ?? "",
            exitCode: 0,
            raw: stdout,
          });
        } catch {
          resolve({
            output: stdout || stderr || "",
            exitCode: error?.code ?? 0,
            raw: stdout,
          });
        }
      }
    );
  });
}
