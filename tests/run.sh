#!/bin/bash
set -e

# Cat Herding Skill & Rule Test Harness
# Copies tests to a disposable sandbox and runs them there.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Find the sandbox: use TEST_SANDBOX env var if set,
# otherwise look for cat-herding-tests next to the main repo.
# Uses git's common dir to resolve correctly from worktrees.
if [ -n "$TEST_SANDBOX" ]; then
  TEST_SANDBOX="$TEST_SANDBOX"
else
  GIT_COMMON="$(cd "$SCRIPT_DIR/.." && git rev-parse --git-common-dir 2>/dev/null)"
  MAIN_REPO="$(cd "$SCRIPT_DIR/.." && cd "$GIT_COMMON/.." && pwd)"
  TEST_SANDBOX="$(dirname "$MAIN_REPO")/cat-herding-tests"
fi

if [ ! -d "$TEST_SANDBOX" ]; then
  echo "Error: Test sandbox not found at $TEST_SANDBOX"
  echo "Create it with: mkdir -p $TEST_SANDBOX"
  exit 1
fi

echo "=== Preparing test sandbox ==="

# Clean the sandbox (preserve .git and node_modules for speed)
find "$TEST_SANDBOX" -mindepth 1 -maxdepth 1 \
  ! -name '.git' \
  ! -name 'node_modules' \
  ! -name 'research' \
  -exec rm -rf {} +

# Copy harness (package.json, vitest config, tsconfig, lib/)
cp "$SCRIPT_DIR/harness/package.json" "$TEST_SANDBOX/"
cp "$SCRIPT_DIR/harness/vitest.config.ts" "$TEST_SANDBOX/"
cp "$SCRIPT_DIR/harness/tsconfig.json" "$TEST_SANDBOX/"
mkdir -p "$TEST_SANDBOX/lib"
cp "$SCRIPT_DIR/harness/lib/"*.ts "$TEST_SANDBOX/lib/"

# Copy fixtures
cp -r "$SCRIPT_DIR/fixtures" "$TEST_SANDBOX/fixtures"

# Copy specs
cp -r "$SCRIPT_DIR/specs" "$TEST_SANDBOX/specs"

echo "=== Installing dependencies ==="
cd "$TEST_SANDBOX"
npm install --silent 2>&1 | tail -3

echo "=== Running tests ==="
npx vitest run "$@"

# Show cost report if it exists
if [ -f "cost-report.json" ]; then
  echo ""
  echo "=== Cost Report ==="
  cat cost-report.json
fi
