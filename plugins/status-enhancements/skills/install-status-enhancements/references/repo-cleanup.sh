#!/bin/bash
# Pipeline script: append repo cleanup status to line 1
# Input: {"claude": <claude_json>, "lines": [...]}
# Output: {"lines": [...]}

INPUT=$(cat)
LINES=$(echo "$INPUT" | jq -c '.lines')

# Must be in a git repo
git rev-parse --git-dir &>/dev/null || { echo "{\"lines\":$LINES}"; exit 0; }

# Detect default branch
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's|refs/remotes/origin/||')
if [ -z "$DEFAULT_BRANCH" ]; then
  if git show-ref --verify --quiet refs/heads/main 2>/dev/null; then
    DEFAULT_BRANCH="main"
  elif git show-ref --verify --quiet refs/heads/master 2>/dev/null; then
    DEFAULT_BRANCH="master"
  else
    echo "{\"lines\":$LINES}"
    exit 0
  fi
fi

ITEMS=()

# Stale branches — remote tracking branch deleted
STALE=$(git branch -vv 2>/dev/null | grep -c ': gone]')
[ "$STALE" -gt 0 ] && ITEMS+=("${STALE} stale")

# Merged branches — fully merged into default, safe to delete
MERGED=$(git branch --merged "$DEFAULT_BRANCH" 2>/dev/null | grep -v "^\*\|^  ${DEFAULT_BRANCH}$\|^  master$\|^  main$" | wc -l | tr -d ' ')
[ "$MERGED" -gt 0 ] && ITEMS+=("${MERGED} merged")

# Prunable worktrees
PRUNABLE=$(git worktree prune --dry-run 2>/dev/null | wc -l | tr -d ' ')
[ "$PRUNABLE" -gt 0 ] && ITEMS+=("${PRUNABLE} prunable wt")

# Finished worktrees — branch merged but worktree still exists
FINISHED=0
MAIN_PATH=$(git rev-parse --show-toplevel 2>/dev/null)
while IFS= read -r wt_line; do
  [ -z "$wt_line" ] && continue
  WT_PATH="${wt_line%% *}"
  WT_BRANCH=$(echo "$wt_line" | sed -n 's/.*\[\(.*\)\].*/\1/p')
  [ "$WT_PATH" = "$MAIN_PATH" ] && continue
  [ -z "$WT_BRANCH" ] && continue
  git merge-base --is-ancestor "$WT_BRANCH" "$DEFAULT_BRANCH" 2>/dev/null && (( FINISHED++ ))
done < <(git worktree list 2>/dev/null)
[ "$FINISHED" -gt 0 ] && ITEMS+=("${FINISHED} done wt")

# If there are issues, append to line 1
if [ ${#ITEMS[@]} -gt 0 ]; then
  WARN=$'\033[38;5;208m'
  ORANGE=$'\033[38;5;214m'
  RST=$'\033[0m'
  SEP=" ${ORANGE}|${RST} "
  STATUS=$(IFS=', '; echo "${ITEMS[*]}")
  LINES=$(echo "$LINES" | jq -c --arg s "${SEP}${WARN}⚠ ${STATUS}${RST}" '.[0] = (.[0] // "") + $s')
fi

echo "{\"lines\":$LINES}"
