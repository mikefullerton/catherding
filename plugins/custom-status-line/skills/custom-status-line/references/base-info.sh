#!/bin/bash
# Pipeline script: base project/git info (line 1) + model/context stats (line 2)
# Input: {"claude": <claude_json>, "lines": [...]}
# Output: {"lines": ["<project+git line>", "<model+stats line>"]}

INPUT=$(cat)
CLAUDE=$(echo "$INPUT" | jq -r '.claude')

# Model, context, session
MODEL=$(echo "$CLAUDE" | jq -r '.model.display_name // "unknown"')
REM_PCT=$(echo "$CLAUDE" | jq -r '.context_window.remaining_percentage // 100' | cut -d. -f1)
DURATION_MS=$(echo "$CLAUDE" | jq -r '.cost.total_duration_ms // 0')
LINES_ADDED=$(echo "$CLAUDE" | jq -r '.cost.total_lines_added // 0')
LINES_REMOVED=$(echo "$CLAUDE" | jq -r '.cost.total_lines_removed // 0')
TOTAL_COST=$(echo "$CLAUDE" | jq -r '.cost.total_cost_usd // 0' | xargs printf '%.2f')
SESSION_NAME=$(echo "$CLAUDE" | jq -r '.session_name // ""')
TOTAL_CHANGES=$(( LINES_ADDED + LINES_REMOVED ))
RATE_5H=$(echo "$CLAUDE" | jq -r '.rate_limits.five_hour.used_percentage // 0' | cut -d. -f1)
RATE_7D=$(echo "$CLAUDE" | jq -r '.rate_limits.seven_day.used_percentage // 0' | cut -d. -f1)

# Format duration
DURATION_S=$(( DURATION_MS / 1000 ))
if [ $DURATION_S -ge 3600 ]; then
  DURATION="$(( DURATION_S / 3600 ))h:$(printf '%02d' $(( (DURATION_S % 3600) / 60 )))m"
elif [ $DURATION_S -ge 60 ]; then
  DURATION="0h:$(printf '%02d' $(( DURATION_S / 60 )))m"
else
  DURATION="${DURATION_S}s"
fi

# Project and git info
CWD=$(echo "$CLAUDE" | jq -r '.cwd // ""')
CWD="${CWD%%/.claude/worktrees/*}"
CWD="${CWD%%/.worktrees/*}"
CWD="${CWD/#$HOME/~}"
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")

BLUE=$'\033[38;5;117m'
YELLOW=$'\033[38;5;229m'
RST=$'\033[0m'
DIM=$'\033[38;5;245m'
ORANGE=$'\033[38;5;214m'
SEP=" ${ORANGE}|${RST} "

# Detect git worktree
IS_WORKTREE=false
GIT_DIR=$(git rev-parse --git-dir 2>/dev/null)
if [ -n "$GIT_DIR" ] && echo "$GIT_DIR" | grep -q "/worktrees/"; then
  IS_WORKTREE=true
fi

LINE1="${BLUE}${CWD}${RST}"
if [ -n "$SESSION_NAME" ]; then
  LINE1="${LINE1} ${DIM}(${SESSION_NAME})${RST}"
fi
if [ -n "$BRANCH" ]; then
  DIRTY=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
  if $IS_WORKTREE; then
    GREEN=$'\033[38;5;151m'
    LINE1="${LINE1}${SEP}${GREEN}git-worktree${RST}:(${YELLOW}${BRANCH}${RST})"
  else
    LINE1="${LINE1}${SEP}git:(${YELLOW}${BRANCH}${RST})"
  fi
  STATS=""
  if [ "$DIRTY" -gt 0 ]; then
    STATS="${DIRTY} files changed"
  fi
  if [ "$BRANCH" != "main" ] && [ "$BRANCH" != "master" ]; then
    COMMITS=$(git rev-list --count main..HEAD 2>/dev/null || echo 0)
    if [ "$COMMITS" -gt 0 ]; then
      [ -n "$STATS" ] && STATS="${STATS}, "
      STATS="${STATS}${COMMITS} commits"
    fi
    BEHIND=$(git rev-list --count HEAD..main 2>/dev/null || echo 0)
    if [ "$BEHIND" -gt 0 ]; then
      [ -n "$STATS" ] && STATS="${STATS}, "
      STATS="${STATS}${BEHIND} behind main"
    fi
  else
    AHEAD_REMOTE=$(git rev-list --count origin/main..HEAD 2>/dev/null || echo 0)
    if [ "$AHEAD_REMOTE" -gt 0 ]; then
      [ -n "$STATS" ] && STATS="${STATS}, "
      STATS="${STATS}${AHEAD_REMOTE} ahead of remote"
    fi
    BEHIND_REMOTE=$(git rev-list --count HEAD..origin/main 2>/dev/null || echo 0)
    if [ "$BEHIND_REMOTE" -gt 0 ]; then
      [ -n "$STATS" ] && STATS="${STATS}, "
      STATS="${STATS}${BEHIND_REMOTE} behind remote"
    fi
  fi
  if [ -n "$STATS" ]; then
    LINE1="${LINE1}${SEP}[${STATS}]"
  else
    LINE1="${LINE1}${SEP}[up to date]"
  fi
fi

# Settings
SETTINGS="$HOME/.claude/settings.json"
EFFORT=$(jq -r '.effortLevel // empty' "$SETTINGS" 2>/dev/null)
THINKING=$(jq -r '.alwaysThinkingEnabled // false' "$SETTINGS" 2>/dev/null)

LINE2="${MODEL}"
if [ "$THINKING" = "true" ]; then
  LINE2="${LINE2} | thinking"
fi
if [ -n "$EFFORT" ]; then
  LINE2="${LINE2}${SEP}${EFFORT}"
fi
# Calculate daily average for 7-day quota (resets every Wed 10am)
NOW_EPOCH=$(date +%s)
DOW=$(date +%u)  # 1=Mon ... 7=Sun
HOUR=$(date +%H)
# Days since last Wednesday (dow=3)
DAYS_SINCE_WED=$(( (DOW - 3 + 7) % 7 ))
# If it's Wednesday but before 10am, go back to previous Wednesday
if [ "$DAYS_SINCE_WED" -eq 0 ] && [ "$HOUR" -lt 10 ]; then
  DAYS_SINCE_WED=7
fi
# Calculate epoch of last Wednesday 10am
LAST_WED_10AM=$(( NOW_EPOCH - (DAYS_SINCE_WED * 86400) ))
LAST_WED_10AM=$(date -j -f "%s" "$LAST_WED_10AM" "+%Y%m%d" 2>/dev/null)
LAST_WED_10AM=$(date -j -f "%Y%m%d%H%M%S" "${LAST_WED_10AM}100000" "+%s" 2>/dev/null)
ELAPSED_S=$(( NOW_EPOCH - LAST_WED_10AM ))
ELAPSED_DAYS=$(( (ELAPSED_S + 86399) / 86400 ))
[ "$ELAPSED_DAYS" -lt 1 ] && ELAPSED_DAYS=1
DAILY_AVG=$(( RATE_7D / ELAPSED_DAYS ))
PREDICTED_7D=$(( DAILY_AVG * 7 ))

RED=$'\033[38;5;210m'
OVERAGE_DISPLAY=""
PREDICTED_DISPLAY="${PREDICTED_7D}% projected"
if [ "$PREDICTED_7D" -gt 100 ] 2>/dev/null; then
  OVERAGE_DOLLARS=$(( (PREDICTED_7D - 100) * 2 ))
  OVERAGE_DISPLAY="${SEP}\$${OVERAGE_DOLLARS} overage"
  PREDICTED_DISPLAY="${RED}${PREDICTED_7D}%${RST} projected"
fi
LINE3="- Weekly usage ${RATE_7D}%${SEP}day: ${ELAPSED_DAYS}${SEP}daily ave usage: ${DAILY_AVG}%${SEP}${PREDICTED_DISPLAY}${OVERAGE_DISPLAY}"

LINE2="${LINE2}${SEP}${DURATION}${SEP}${TOTAL_CHANGES} changes${SEP}\$${TOTAL_COST}${SEP}5h: ${RATE_5H}%"

# Context used — yellow at 18%+, red at 20%+ (Opus 1M only)
USED_PCT=$(( 100 - REM_PCT ))
YELLOW=$'\033[38;5;220m'
RED=$'\033[38;5;210m'
IS_OPUS_1M=false
if echo "$MODEL" | grep -qi "opus" && echo "$MODEL" | grep -q "1M"; then
  IS_OPUS_1M=true
fi
if $IS_OPUS_1M && [ "$USED_PCT" -gt 20 ] 2>/dev/null; then
  LINE2="${LINE2}${SEP}${RED}${USED_PCT}% context used (compact needed)${RST}"
elif $IS_OPUS_1M && [ "$USED_PCT" -ge 18 ] 2>/dev/null; then
  LINE2="${LINE2}${SEP}${YELLOW}${USED_PCT}% context used${RST}"
else
  LINE2="${LINE2}${SEP}${USED_PCT}% context used"
fi

# Output pipeline JSON
jq -n --arg l1 "$LINE1" --arg l2 "$LINE2" --arg l3 "$LINE3" '{"lines": [$l1, $l2, $l3]}'
