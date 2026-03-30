#!/bin/zsh
# Claude Code status line — two-line: project/git info + model/context
input=$(cat)

# Model, context, session
MODEL=$(echo "$input" | jq -r '.model.display_name // "unknown"')
REM_PCT=$(echo "$input" | jq -r '.context_window.remaining_percentage // 100' | cut -d. -f1)
DURATION_MS=$(echo "$input" | jq -r '.cost.total_duration_ms // 0')
LINES_ADDED=$(echo "$input" | jq -r '.cost.total_lines_added // 0')
LINES_REMOVED=$(echo "$input" | jq -r '.cost.total_lines_removed // 0')
TOTAL_COST=$(echo "$input" | jq -r '.cost.total_cost_usd // 0' | xargs printf '%.2f')
SESSION_NAME=$(echo "$input" | jq -r '.session_name // ""')
TOTAL_CHANGES=$(( LINES_ADDED + LINES_REMOVED ))
RATE_5H=$(echo "$input" | jq -r '.rate_limits.five_hour.used_percentage // 0' | cut -d. -f1)
RATE_7D=$(echo "$input" | jq -r '.rate_limits.seven_day.used_percentage // 0' | cut -d. -f1)

# Format duration as readable string
DURATION_S=$(( DURATION_MS / 1000 ))
if [[ $DURATION_S -ge 3600 ]]; then
  DURATION="$(( DURATION_S / 3600 ))h $(( (DURATION_S % 3600) / 60 ))m"
elif [[ $DURATION_S -ge 60 ]]; then
  DURATION="$(( DURATION_S / 60 ))m"
else
  DURATION="${DURATION_S}s"
fi

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

DIM=$'\033[38;5;245m'
ORANGE=$'\033[38;5;214m'
SEP=" ${ORANGE}|${RST} "

LINE1="${BLUE}${CWD}${RST}"
if [[ -n "$SESSION_NAME" ]]; then
  LINE1="${LINE1} ${DIM}(${SESSION_NAME})${RST}"
fi
if [[ -n "$BRANCH" ]]; then
  DIRTY=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
  if $IS_WORKTREE; then
    GREEN=$'\033[38;5;151m'
    LINE1="${LINE1}${SEP}${GREEN}git-worktree${RST}:(${YELLOW}${BRANCH}${RST})"
  else
    LINE1="${LINE1}${SEP}git:(${YELLOW}${BRANCH}${RST})"
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
    LINE1="${LINE1}${SEP}[${(j:, :)STATS}]"
  else
    LINE1="${LINE1}${SEP}[up to date]"
  fi
fi

# Detect YOLO mode
SESSION_ID=$(echo "$input" | jq -r '.session_id // empty')
YOLO=""
MARKER="$HOME/.claude-yolo-sessions/${SESSION_ID}.json"
if [ -f "$MARKER" ]; then
  RED=$'\033[38;5;210m'
  NEEDS_RESTART=$(jq -r '.needs_restart // false' "$MARKER" 2>/dev/null)
  if [ "$NEEDS_RESTART" = "true" ]; then
    YOLO=" ${RED}☠ YOLO${RST} ${DIM}(needs session restart)${RST}"
  else
    YOLO=" ${RED}☠ YOLO${RST}"
  fi
fi

print "$LINE1"
echo "${MODEL}${SEP}${REM_PCT}% context remaining${SEP}duration ${DURATION}${SEP}${TOTAL_CHANGES} changes${SEP}\$${TOTAL_COST}${SEP}5h: ${RATE_5H}%${SEP}7d: ${RATE_7D}%${YOLO}"
