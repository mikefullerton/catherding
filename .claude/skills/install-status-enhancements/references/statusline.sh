#!/bin/zsh
# Claude Code status line — two-line: project/git info + model/context
input=$(cat)

# Model and context
MODEL=$(echo "$input" | jq -r '.model.display_name // "unknown"')
PCT=$(echo "$input" | jq -r '.context_window.used_percentage // 0' | cut -d. -f1)

# Project and git info
CWD=$(echo "$input" | jq -r '.cwd // ""')
CWD="${CWD%%/.claude/worktrees/*}"
CWD="${CWD%%/.worktrees/*}"
CWD="${CWD/#$HOME/~}"
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")

BLUE=$'\033[38;5;117m'
YELLOW=$'\033[38;5;229m'
RST=$'\033[0m'

# Detect git worktree
IS_WORKTREE=false
GIT_DIR=$(git rev-parse --git-dir 2>/dev/null)
if [[ "$GIT_DIR" == *"/worktrees/"* ]]; then
  IS_WORKTREE=true
fi

LINE1="${BLUE}${CWD}${RST}"
if [[ -n "$BRANCH" ]]; then
  DIRTY=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
  if $IS_WORKTREE; then
    GREEN=$'\033[38;5;151m'
    LINE1="${LINE1}  ${GREEN}git-worktree${RST}:(${YELLOW}${BRANCH}${RST})"
  else
    LINE1="${LINE1}  git:(${YELLOW}${BRANCH}${RST})"
  fi
  STATS=()
  if [[ "$DIRTY" -gt 0 ]]; then
    STATS+=("${DIRTY} files changed")
  fi
  if [[ "$BRANCH" != "main" && "$BRANCH" != "master" ]]; then
    COMMITS=$(git rev-list --count main..HEAD 2>/dev/null || echo 0)
    if [[ "$COMMITS" -gt 0 ]]; then
      STATS+=("${COMMITS} commits")
    fi
    BEHIND=$(git rev-list --count HEAD..main 2>/dev/null || echo 0)
    if [[ "$BEHIND" -gt 0 ]]; then
      STATS+=("${BEHIND} behind main")
    fi
  else
    AHEAD_REMOTE=$(git rev-list --count origin/main..HEAD 2>/dev/null || echo 0)
    if [[ "$AHEAD_REMOTE" -gt 0 ]]; then
      STATS+=("${AHEAD_REMOTE} ahead of remote")
    fi
    BEHIND_REMOTE=$(git rev-list --count HEAD..origin/main 2>/dev/null || echo 0)
    if [[ "$BEHIND_REMOTE" -gt 0 ]]; then
      STATS+=("${BEHIND_REMOTE} behind remote")
    fi
  fi
  if [[ ${#STATS[@]} -gt 0 ]]; then
    LINE1="${LINE1}  [${(j:, :)STATS}]"
  else
    LINE1="${LINE1}  [up to date]"
  fi
fi

# Detect YOLO mode
SESSION_ID=$(echo "$input" | jq -r '.session_id // empty')
YOLO=""
MARKER="$HOME/.claude-yolo-sessions/${SESSION_ID}.json"
if [ -f "$MARKER" ]; then
  RED=$'\033[38;5;210m'
  DIM=$'\033[38;5;245m'
  NEEDS_RESTART=$(jq -r '.needs_restart // false' "$MARKER" 2>/dev/null)
  if [ "$NEEDS_RESTART" = "true" ]; then
    YOLO=" ${RED}☠ YOLO${RST} ${DIM}(needs session restart)${RST}"
  else
    YOLO=" ${RED}☠ YOLO${RST}"
  fi
fi

print "$LINE1"
echo "[${MODEL}] ${PCT}% context${YOLO}"
