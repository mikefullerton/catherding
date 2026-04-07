#!/bin/bash
# Pipeline script: base project/git info (line 1) + model/context stats (line 2) + weekly usage (line 3)
# Input: {"claude": <claude_json>, "lines": [...]}
# Output: {"lines": ["<project+git line>", "<model+stats line>", "<weekly usage line>"]}

INPUT=$(cat)
CLAUDE=$(echo "$INPUT" | jq -r '.claude')

# Model, context, session
MODEL=$(echo "$CLAUDE" | jq -r '.model.display_name // "unknown"')
MODEL_ID=$(echo "$CLAUDE" | jq -r '.model.id // "unknown"')
REM_PCT=$(echo "$CLAUDE" | jq -r '.context_window.remaining_percentage // 100' | cut -d. -f1)
DURATION_MS=$(echo "$CLAUDE" | jq -r '.cost.total_duration_ms // 0')
API_DURATION_MS=$(echo "$CLAUDE" | jq -r '.cost.total_api_duration_ms // 0')
LINES_ADDED=$(echo "$CLAUDE" | jq -r '.cost.total_lines_added // 0')
LINES_REMOVED=$(echo "$CLAUDE" | jq -r '.cost.total_lines_removed // 0')
TOTAL_COST=$(echo "$CLAUDE" | jq -r '.cost.total_cost_usd // 0' | xargs printf '%.2f')
SESSION_NAME=$(echo "$CLAUDE" | jq -r '.session_name // ""')
TOTAL_CHANGES=$(( LINES_ADDED + LINES_REMOVED ))
# Store rates as x10 for one decimal place in bash integer math
RATE_5H_X10=$(echo "$CLAUDE" | jq -r '(.rate_limits.five_hour.used_percentage // 0) * 10 | floor')
RATE_7D_X10=$(echo "$CLAUDE" | jq -r '(.rate_limits.seven_day.used_percentage // 0) * 10 | floor')
RATE_5H_DISPLAY="$(( RATE_5H_X10 / 10 )).$(( RATE_5H_X10 % 10 ))"
RATE_7D_DISPLAY="$(( RATE_7D_X10 / 10 )).$(( RATE_7D_X10 % 10 ))"
RATE_5H_RESETS=$(echo "$CLAUDE" | jq -r '.rate_limits.five_hour.resets_at // 0')
RATE_7D_RESETS=$(echo "$CLAUDE" | jq -r '.rate_limits.seven_day.resets_at // 0')
TRANSCRIPT_PATH=$(echo "$CLAUDE" | jq -r '.transcript_path // ""')
CLAUDE_VERSION=$(echo "$CLAUDE" | jq -r '.version // ""')
PROJECT_DIR=$(echo "$CLAUDE" | jq -r '.workspace.project_dir // ""')
CTX_WINDOW_SIZE=$(echo "$CLAUDE" | jq -r '.context_window.context_window_size // 0')
TOTAL_INPUT_TOKENS=$(echo "$CLAUDE" | jq -r '.context_window.total_input_tokens // 0')
TOTAL_OUTPUT_TOKENS=$(echo "$CLAUDE" | jq -r '.context_window.total_output_tokens // 0')
CACHE_CREATE_TOKENS=$(echo "$CLAUDE" | jq -r '.context_window.current_usage.cache_creation_input_tokens // 0')
CACHE_READ_TOKENS=$(echo "$CLAUDE" | jq -r '.context_window.current_usage.cache_read_input_tokens // 0')

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
ELAPSED_HOURS=$(( ELAPSED_S / 3600 ))
[ "$ELAPSED_HOURS" -lt 1 ] && ELAPSED_HOURS=1
TOTAL_HOURS=168  # 7 days * 24 hours
ELAPSED_DAYS_100=$(( (ELAPSED_S * 100) / 86400 ))
[ "$ELAPSED_DAYS_100" -lt 1 ] && ELAPSED_DAYS_100=1
[ "$ELAPSED_DAYS_100" -gt 700 ] && ELAPSED_DAYS_100=700
ELAPSED_DAYS_DISPLAY="$(( ELAPSED_DAYS_100 / 100 )).$(printf '%02d' $(( ELAPSED_DAYS_100 % 100 )))"
# Math in x10 scale, then format with one decimal
DAILY_AVG_X10=$(( (RATE_7D_X10 * 24 + ELAPSED_HOURS / 2) / ELAPSED_HOURS ))
DAILY_AVG_DISPLAY="$(( DAILY_AVG_X10 / 10 )).$(( DAILY_AVG_X10 % 10 ))"
PREDICTED_X10=$(( (RATE_7D_X10 * TOTAL_HOURS + ELAPSED_HOURS / 2) / ELAPSED_HOURS ))
PREDICTED_DISPLAY_VAL="$(( PREDICTED_X10 / 10 )).$(( PREDICTED_X10 % 10 ))"

RED=$'\033[38;5;210m'
L3C6=""
PREDICTED_DISPLAY="${PREDICTED_DISPLAY_VAL}% projected"
if [ "$PREDICTED_X10" -gt 1000 ] 2>/dev/null; then
  OVERAGE_X10=$(( PREDICTED_X10 - 1000 ))
  OVERAGE_DOLLARS=$(( OVERAGE_X10 / 5 ))
  L3C6="~\$${OVERAGE_DOLLARS} overage"
  PREDICTED_DISPLAY="${RED}${PREDICTED_DISPLAY_VAL}%${RST} projected"
fi

L3C1="Weekly usage ${RATE_7D_DISPLAY}%"
L3C2="day: ${ELAPSED_DAYS_DISPLAY}"
L3C3="daily ave: ${DAILY_AVG_DISPLAY}%"
L3C4="5h: ${RATE_5H_DISPLAY}%"
L3C5="${PREDICTED_DISPLAY}"

# Line 2 col4+ (context is the last col on line 2)
L2C4="${CONTEXT_COL}"

# === Calculate column widths: exact max visible length (no extra padding) ===
COL1_W=$(max $(max $(visible_len "$L1C1") $(visible_len "$L2C1")) $(visible_len "$L3C1"))
COL2_W=$(max $(max $(visible_len "$L1C2") $(visible_len "$L2C2")) $(visible_len "$L3C2"))
COL3_W=$(max $(max $(visible_len "$L1C3") $(visible_len "$L2C3")) $(visible_len "$L3C3"))
COL4_W=$(max $(visible_len "$L2C4") $(visible_len "$L3C4"))
COL5_W=$(visible_len "$L3C5")

# === Assemble lines with | border ===
LBOR="${ORANGE}|${RST} "

LINE1="${LBOR}$(pad_right "$L1C1" $COL1_W)"
if [ -n "$BRANCH" ]; then
  LINE1="${LINE1}${SEP}$(pad_right "$L1C2" $COL2_W)${SEP}$(pad_right "$L1C3" $COL3_W)"
fi

LINE2="${LBOR}$(pad_right "$L2C1" $COL1_W)${SEP}$(pad_right "$L2C2" $COL2_W)${SEP}$(pad_right "$L2C3" $COL3_W)${SEP}$(pad_right "$L2C4" $COL4_W)"

LINE3="${LBOR}$(pad_left "$L3C1" $COL1_W)${SEP}$(pad_right "$L3C2" $COL2_W)${SEP}$(pad_right "$L3C3" $COL3_W)${SEP}$(pad_right "$L3C4" $COL4_W)${SEP}$(pad_right "$L3C5" $COL5_W)"
[ -n "$L3C6" ] && LINE3="${LINE3}${SEP}${L3C6}"

# Log usage stats to SQLite
USAGE_DB="$HOME/claude-usage.db"
WEEK_START=$(date -j -f "%s" "$LAST_WED_10AM" "+%Y-%m-%d" 2>/dev/null)
CONTEXT_PCT=$(( 100 - REM_PCT ))
DB_VERSION=$(sqlite3 "$USAGE_DB" "PRAGMA user_version;" 2>/dev/null || echo 0)
if [ "$DB_VERSION" -lt 3 ] 2>/dev/null; then
  sqlite3 "$USAGE_DB" "
    DROP TABLE IF EXISTS sessions;
    DROP TABLE IF EXISTS weekly_usage;
    DROP TABLE IF EXISTS usage;
    CREATE TABLE sessions (
      session_id TEXT PRIMARY KEY,
      session_name TEXT,
      model_id TEXT NOT NULL,
      model_display TEXT NOT NULL,
      claude_version TEXT,
      cwd TEXT,
      project_dir TEXT,
      transcript_path TEXT,
      context_window_size INTEGER NOT NULL DEFAULT 0,
      first_seen TEXT NOT NULL,
      last_seen TEXT NOT NULL,
      duration_s INTEGER NOT NULL,
      api_duration_ms INTEGER NOT NULL DEFAULT 0,
      lines_added INTEGER NOT NULL,
      lines_removed INTEGER NOT NULL,
      total_cost_usd TEXT NOT NULL,
      total_input_tokens INTEGER NOT NULL DEFAULT 0,
      total_output_tokens INTEGER NOT NULL DEFAULT 0,
      cache_create_tokens INTEGER NOT NULL DEFAULT 0,
      cache_read_tokens INTEGER NOT NULL DEFAULT 0,
      context_used_pct INTEGER NOT NULL
    );
    CREATE TABLE weekly_usage (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      timestamp TEXT NOT NULL,
      session_id TEXT NOT NULL,
      week_start TEXT NOT NULL,
      elapsed_hours INTEGER NOT NULL,
      day INTEGER NOT NULL,
      weekly_pct INTEGER NOT NULL,
      daily_avg_pct INTEGER NOT NULL,
      five_hour_pct INTEGER NOT NULL,
      five_hour_resets_at INTEGER,
      seven_day_resets_at INTEGER,
      projected_pct INTEGER NOT NULL
    );
    -- v3: all pct/day columns store x10 values (divide by 10 for display)
    PRAGMA user_version=3;
  "
fi

# Sessions table: upsert (cumulative per session)
sqlite3 "$USAGE_DB" "
  INSERT INTO sessions (session_id, session_name, model_id, model_display, claude_version,
    cwd, project_dir, transcript_path, context_window_size, first_seen, last_seen,
    duration_s, api_duration_ms, lines_added, lines_removed, total_cost_usd,
    total_input_tokens, total_output_tokens, cache_create_tokens, cache_read_tokens, context_used_pct)
  VALUES ('${SESSION_ID}', '$(echo "$SESSION_NAME" | sed "s/'/''/g")',
    '${MODEL_ID}', '${MODEL}', '${CLAUDE_VERSION}',
    '$(echo "$CWD" | sed "s/'/''/g")', '$(echo "$PROJECT_DIR" | sed "s/'/''/g")',
    '$(echo "$TRANSCRIPT_PATH" | sed "s/'/''/g")', ${CTX_WINDOW_SIZE},
    datetime('now','localtime'), datetime('now','localtime'),
    ${DURATION_S}, ${API_DURATION_MS}, ${LINES_ADDED}, ${LINES_REMOVED}, '${TOTAL_COST}',
    ${TOTAL_INPUT_TOKENS}, ${TOTAL_OUTPUT_TOKENS}, ${CACHE_CREATE_TOKENS}, ${CACHE_READ_TOKENS}, ${CONTEXT_PCT})
  ON CONFLICT(session_id) DO UPDATE SET
    session_name='$(echo "$SESSION_NAME" | sed "s/'/''/g")',
    last_seen=datetime('now','localtime'),
    duration_s=${DURATION_S},
    api_duration_ms=${API_DURATION_MS},
    lines_added=${LINES_ADDED},
    lines_removed=${LINES_REMOVED},
    total_cost_usd='${TOTAL_COST}',
    total_input_tokens=${TOTAL_INPUT_TOKENS},
    total_output_tokens=${TOTAL_OUTPUT_TOKENS},
    cache_create_tokens=${CACHE_CREATE_TOKENS},
    cache_read_tokens=${CACHE_READ_TOKENS},
    context_used_pct=${CONTEXT_PCT};
"

# Weekly usage table: append only when values change
# Weekly usage table: append only when values change (stores x10 values)
LAST_ROW=$(sqlite3 "$USAGE_DB" "SELECT weekly_pct, five_hour_pct, projected_pct
  FROM weekly_usage WHERE session_id='${SESSION_ID}' ORDER BY id DESC LIMIT 1;" 2>/dev/null)
NEW_ROW="${RATE_7D_X10}|${RATE_5H_X10}|${PREDICTED_X10}"
if [ "$LAST_ROW" != "$NEW_ROW" ]; then
  sqlite3 "$USAGE_DB" "INSERT INTO weekly_usage
    (timestamp, session_id, week_start, elapsed_hours, day, weekly_pct, daily_avg_pct,
     five_hour_pct, five_hour_resets_at, seven_day_resets_at, projected_pct)
    VALUES (datetime('now','localtime'), '${SESSION_ID}', '${WEEK_START}',
    ${ELAPSED_HOURS}, ${ELAPSED_DAYS_100}, ${RATE_7D_X10}, ${DAILY_AVG_X10},
    ${RATE_5H_X10}, ${RATE_5H_RESETS}, ${RATE_7D_RESETS}, ${PREDICTED_X10});"
fi

# Output pipeline JSON
jq -n --arg l1 "$LINE1" --arg l2 "$LINE2" --arg l3 "$LINE3" '{"lines": [$l1, $l2, $l3]}'
