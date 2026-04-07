#!/bin/bash
# Pipeline script: base project/git info (line 1) + model/context stats (line 2) + weekly usage (line 3)
# Input: {"claude": <claude_json>, "lines": [...]}
# Output: {"lines": ["<project+git line>", "<model+stats line>", "<weekly usage line>"]}

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

# --- Column alignment helpers ---
visible_len() {
  printf '%s' "$1" | sed $'s/\033\[[0-9;]*m//g' | wc -m | tr -d ' '
}

pad_right() {
  local str="$1" target="$2"
  local vlen pad
  vlen=$(visible_len "$str")
  pad=$(( target - vlen ))
  if [ "$pad" -gt 0 ]; then
    printf '%s%*s' "$str" "$pad" ""
  else
    printf '%s' "$str"
  fi
}

pad_left() {
  local str="$1" target="$2"
  local vlen pad
  vlen=$(visible_len "$str")
  pad=$(( target - vlen ))
  if [ "$pad" -gt 0 ]; then
    printf '%*s%s' "$pad" "" "$str"
  else
    printf '%s' "$str"
  fi
}

max() { [ "$1" -gt "$2" ] && echo "$1" || echo "$2"; }

# Detect git worktree
IS_WORKTREE=false
GIT_DIR=$(git rev-parse --git-dir 2>/dev/null)
if [ -n "$GIT_DIR" ] && echo "$GIT_DIR" | grep -q "/worktrees/"; then
  IS_WORKTREE=true
fi

# === Compute all column values ===

# LINE 1 columns
L1C1="${BLUE}${CWD}${RST}"
[ -n "$SESSION_NAME" ] && L1C1="${L1C1} ${DIM}(${SESSION_NAME})${RST}"

L1C2=""
L1C3=""
if [ -n "$BRANCH" ]; then
  DIRTY=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
  if $IS_WORKTREE; then
    GREEN=$'\033[38;5;151m'
    L1C2="${GREEN}git-worktree${RST}:(${YELLOW}${BRANCH}${RST})"
  else
    L1C2="git:(${YELLOW}${BRANCH}${RST})"
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
  [ -z "$STATS" ] && STATS="up to date"
  L1C3="[${STATS}]"
fi

# LINE 2 columns
SETTINGS="$HOME/.claude/settings.json"
EFFORT=$(jq -r '.effortLevel // empty' "$SETTINGS" 2>/dev/null)

L2C1="${MODEL}"
[ -n "$EFFORT" ] && L2C1="${L2C1}, ${EFFORT}"

# YOLO indicator — append to model column
SESSION_ID=$(echo "$CLAUDE" | jq -r '.session_id // empty')
if [ -n "$SESSION_ID" ]; then
  YOLO_MARKER="$HOME/.claude-yolo-sessions/${SESSION_ID}.json"
  if [ -f "$YOLO_MARKER" ]; then
    RED=$'\033[38;5;210m'
    NEEDS_RESTART=$(jq -r '.needs_restart // false' "$YOLO_MARKER" 2>/dev/null)
    if [ "$NEEDS_RESTART" = "true" ]; then
      L2C1="${L2C1} ${RED}YOLO${RST} ${DIM}(needs restart)${RST}"
    else
      L2C1="${L2C1} ${RED}YOLO${RST}"
    fi
  fi
fi

L2C2="${DURATION}"
L2C3="${TOTAL_CHANGES} lines changed"

USED_PCT=$(( 100 - REM_PCT ))
YELLOW=$'\033[38;5;220m'
RED=$'\033[38;5;210m'
IS_OPUS_1M=false
if echo "$MODEL" | grep -qi "opus" && echo "$MODEL" | grep -q "1M"; then
  IS_OPUS_1M=true
fi
if $IS_OPUS_1M && [ "$USED_PCT" -gt 20 ] 2>/dev/null; then
  CONTEXT_COL="${RED}${USED_PCT}% context used (compact needed)${RST}"
elif $IS_OPUS_1M && [ "$USED_PCT" -ge 18 ] 2>/dev/null; then
  CONTEXT_COL="${YELLOW}${USED_PCT}% context used${RST}"
else
  CONTEXT_COL="${USED_PCT}% context used"
fi

# LINE 3 columns
NOW_EPOCH=$(date +%s)
DOW=$(date +%u)
HOUR=$(date +%H)
DAYS_SINCE_WED=$(( (DOW - 3 + 7) % 7 ))
if [ "$DAYS_SINCE_WED" -eq 0 ] && [ "$HOUR" -lt 10 ]; then
  DAYS_SINCE_WED=7
fi
LAST_WED_10AM=$(( NOW_EPOCH - (DAYS_SINCE_WED * 86400) ))
LAST_WED_10AM=$(date -j -f "%s" "$LAST_WED_10AM" "+%Y%m%d" 2>/dev/null)
LAST_WED_10AM=$(date -j -f "%Y%m%d%H%M%S" "${LAST_WED_10AM}100000" "+%s" 2>/dev/null)
ELAPSED_S=$(( NOW_EPOCH - LAST_WED_10AM ))
ELAPSED_DAYS=$(( (ELAPSED_S + 86399) / 86400 ))
[ "$ELAPSED_DAYS" -lt 1 ] && ELAPSED_DAYS=1
[ "$ELAPSED_DAYS" -gt 7 ] && ELAPSED_DAYS=7
DAILY_AVG=$(( RATE_7D / ELAPSED_DAYS ))
PREDICTED_7D=$(( DAILY_AVG * 7 ))

RED=$'\033[38;5;210m'
L3C5=""
PREDICTED_DISPLAY="${PREDICTED_7D}% projected"
if [ "$PREDICTED_7D" -gt 100 ] 2>/dev/null; then
  OVERAGE_DOLLARS=$(( (PREDICTED_7D - 100) * 2 ))
  L3C5="~\$${OVERAGE_DOLLARS} overage"
  PREDICTED_DISPLAY="${RED}${PREDICTED_7D}%${RST} projected"
fi

L3C1="Weekly usage ${RATE_7D}%"
L3C2="day: ${ELAPSED_DAYS}"
L3C3="daily ave usage: ${DAILY_AVG}%"
L3C4="${PREDICTED_DISPLAY}"

# Line 2 col4+ (context is the last col on line 2)
L2C4="${CONTEXT_COL}"

# === Calculate column widths: exact max visible length (no extra padding) ===
COL1_W=$(max $(max $(visible_len "$L1C1") $(visible_len "$L2C1")) $(visible_len "$L3C1"))
COL2_W=$(max $(max $(visible_len "$L1C2") $(visible_len "$L2C2")) $(visible_len "$L3C2"))
COL3_W=$(max $(max $(visible_len "$L1C3") $(visible_len "$L2C3")) $(visible_len "$L3C3"))
COL4_W=$(max $(visible_len "$L2C4") $(visible_len "$L3C4"))

# === Assemble lines with | borders ===
LBOR="${ORANGE}|${RST} "
RBOR=" ${ORANGE}|${RST}"

LINE1="${LBOR}$(pad_right "$L1C1" $COL1_W)"
if [ -n "$BRANCH" ]; then
  LINE1="${LINE1}${SEP}$(pad_right "$L1C2" $COL2_W)${SEP}$(pad_right "$L1C3" $COL3_W)"
fi
LINE1="${LINE1}${RBOR}"

LINE2="${LBOR}$(pad_right "$L2C1" $COL1_W)${SEP}$(pad_right "$L2C2" $COL2_W)${SEP}$(pad_right "$L2C3" $COL3_W)${SEP}$(pad_right "$L2C4" $COL4_W)${RBOR}"

LINE3="${LBOR}$(pad_left "$L3C1" $COL1_W)${SEP}$(pad_right "$L3C2" $COL2_W)${SEP}$(pad_right "$L3C3" $COL3_W)${SEP}$(pad_right "$L3C4" $COL4_W)"
[ -n "$L3C5" ] && LINE3="${LINE3}${SEP}${L3C5}"
LINE3="${LINE3}${RBOR}"

# Output pipeline JSON
jq -n --arg l1 "$LINE1" --arg l2 "$LINE2" --arg l3 "$LINE3" '{"lines": [$l1, $l2, $l3]}'
