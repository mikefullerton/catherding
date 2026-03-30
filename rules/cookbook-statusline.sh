#!/bin/bash
# Cookbook pipeline status line for Claude Code
# Reads .claude/cookbook-pipeline.json and displays current step progress.
# Install: copy to .claude/cookbook-statusline.sh and configure in settings.json
#   { "statusLine": { "type": "command", "command": ".claude/cookbook-statusline.sh" } }

input=$(cat)

# Read pipeline progress if active
if [ -f .claude/cookbook-pipeline.json ]; then
  step=$(jq -r '.current_step // empty' .claude/cookbook-pipeline.json 2>/dev/null)
  total=$(jq -r '.total_steps // empty' .claude/cookbook-pipeline.json 2>/dev/null)
  phase=$(jq -r '.phase // empty' .claude/cookbook-pipeline.json 2>/dev/null)

  if [ -n "$step" ] && [ -n "$total" ]; then
    steps_len=$(jq '.steps | length' .claude/cookbook-pipeline.json 2>/dev/null)
    if [ "$step" -le "${steps_len:-0}" ]; then
      concern=$(jq -r '.results[-1].concern // "starting"' .claude/cookbook-pipeline.json 2>/dev/null)
      Phase=$(echo "$phase" | awk '{print toupper(substr($0,1,1)) substr($0,2)}')
      echo "$Phase: Step $step/$total — $concern"
    else
      echo "Pipeline complete"
    fi
  fi
fi
