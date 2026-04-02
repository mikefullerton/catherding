#!/bin/bash
# Pipeline script: progress bar display (after status lines, per-session)
# Input: {"claude": <claude_json>, "lines": [...]}
# Output: {"lines": [...existing..., box with progress]}
# Reads ~/.claude-status-line/progress/<session_id>.json for current session

INPUT=$(cat)
LINES=$(echo "$INPUT" | jq -c '.lines')

PROGRESS_DIR="$HOME/.claude-status-line/progress"
SESSION_ID=$(echo "$INPUT" | jq -r '.claude.session_id // empty')

if [ -z "$SESSION_ID" ]; then
  echo "{\"lines\":$LINES}"
  exit 0
fi

PROGRESS_FILE="$PROGRESS_DIR/${SESSION_ID}.json"

if [ ! -f "$PROGRESS_FILE" ]; then
  echo "{\"lines\":$LINES}"
  exit 0
fi

PROGRESS=$(cat "$PROGRESS_FILE" 2>/dev/null)
if [ -z "$PROGRESS" ]; then
  echo "{\"lines\":$LINES}"
  exit 0
fi

TITLE=$(echo "$PROGRESS" | jq -r '.title // empty')
SUBTITLE=$(echo "$PROGRESS" | jq -r '.subtitle // empty')
COUNT=$(echo "$PROGRESS" | jq -r '.count // 0')
MAX=$(echo "$PROGRESS" | jq -r '.max // 0')

if [ -z "$TITLE" ] || [ "$MAX" -le 0 ] 2>/dev/null; then
  echo "{\"lines\":$LINES}"
  exit 0
fi

# Clamp count
if [ "$COUNT" -gt "$MAX" ]; then
  COUNT=$MAX
fi
if [ "$COUNT" -lt 0 ]; then
  COUNT=0
fi

# Calculate percentage
PCT=$(( COUNT * 100 / MAX ))

# Terminal width — read from progress file if provided, else detect
COLS=$(echo "$PROGRESS" | jq -r '.cols // empty')
if [ -z "$COLS" ]; then
  COLS=$(tput cols 2>/dev/null || echo 80)
fi

# Colors
BLUE=$'\033[38;5;117m'
GREEN=$'\033[38;5;151m'
DIM=$'\033[38;5;245m'
RST=$'\033[0m'

# Box inner width (subtract "| " and " |" = 4 chars)
INNER=$(( COLS - 4 ))
[ "$INNER" -lt 20 ] && INNER=20

# Helper: center text within INNER width, wrapped with "| " and " |"
center_line() {
  local TEXT="$1"
  local TEXT_LEN="$2"  # visible length without ANSI
  local PAD_LEFT=$(( (INNER - TEXT_LEN) / 2 ))
  local PAD_RIGHT=$(( INNER - TEXT_LEN - PAD_LEFT ))
  [ "$PAD_LEFT" -lt 0 ] && PAD_LEFT=0
  [ "$PAD_RIGHT" -lt 0 ] && PAD_RIGHT=0
  local LEFT=$(printf '%*s' "$PAD_LEFT" '')
  local RIGHT=$(printf '%*s' "$PAD_RIGHT" '')
  echo "${DIM}|${RST}${LEFT}${TEXT}${RIGHT}${DIM}|${RST}"
}

# Top border
BORDER_FILL=$(printf '%0.s-' $(seq 1 $INNER))
LINE_TOP="${DIM}|${BORDER_FILL}|${RST}"

# Empty line
EMPTY_FILL=$(printf '%*s' "$INNER" '')
LINE_EMPTY="${DIM}|${RST}${EMPTY_FILL}${DIM}|${RST}"

# Title line (centered)
TITLE_TEXT="${BLUE}${TITLE}${RST}"
TITLE_VIS_LEN=${#TITLE}
LINE_TITLE=$(center_line "$TITLE_TEXT" "$TITLE_VIS_LEN")

# Progress bar: [======       ] with 2-space indent on each side
BAR_WIDTH=$(( INNER - 6 ))  # subtract "  [" and "]  "
[ "$BAR_WIDTH" -lt 10 ] && BAR_WIDTH=10
FILLED=$(( COUNT * BAR_WIDTH / MAX ))
EMPTY_BAR=$(( BAR_WIDTH - FILLED ))
FILL_STR=""
EMPTY_STR=""
[ "$FILLED" -gt 0 ] && FILL_STR=$(printf '%0.s=' $(seq 1 $FILLED))
[ "$EMPTY_BAR" -gt 0 ] && EMPTY_STR=$(printf '%*s' "$EMPTY_BAR" '')
BAR_CONTENT="  ${DIM}[${RST}${GREEN}${FILL_STR}${RST}${EMPTY_STR}${DIM}]${RST}  "
BAR_VIS_LEN=$(( BAR_WIDTH + 6 ))  # "  [" + bar + "]  "
LINE_BAR=$(center_line "$BAR_CONTENT" "$BAR_VIS_LEN")

# Subtitle line (centered)
SUB_TEXT="${SUBTITLE} ${COUNT}/${MAX} (${PCT}%)"
SUB_VIS_LEN=${#SUB_TEXT}
SUB_STYLED="${DIM}${SUB_TEXT}${RST}"
LINE_SUB=$(center_line "$SUB_STYLED" "$SUB_VIS_LEN")

# Bottom border
LINE_BOTTOM="$LINE_TOP"

# Append box after existing lines
LINES=$(echo "$LINES" | jq -c \
  --arg l1 "$LINE_TOP" \
  --arg l2 "$LINE_EMPTY" \
  --arg l3 "$LINE_TITLE" \
  --arg l4 "$LINE_BAR" \
  --arg l5 "$LINE_SUB" \
  --arg l6 "$LINE_BOTTOM" \
  '. + [$l1, $l2, $l3, $l4, $l5, $l6]')
echo "{\"lines\":$LINES}"
