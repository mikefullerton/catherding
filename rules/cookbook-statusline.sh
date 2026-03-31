#!/bin/bash
# Cookbook pipeline status line for Claude Code
# Reads .cookbook/pipeline.json and displays current step progress.
# Install: copy to .cookbook/statusline.sh and configure in settings.json
#   { "statusLine": { "type": "command", "command": ".cookbook/statusline.sh" } }

input=$(cat)

# Read pipeline progress if active
if [ -f .cookbook/pipeline.json ]; then
  step=$(jq -r '.current_step // empty' .cookbook/pipeline.json 2>/dev/null)
  total=$(jq -r '.total_steps // empty' .cookbook/pipeline.json 2>/dev/null)
  phase=$(jq -r '.phase // empty' .cookbook/pipeline.json 2>/dev/null)

  if [ -n "$step" ] && [ -n "$total" ]; then
    steps_len=$(jq '.steps | length' .cookbook/pipeline.json 2>/dev/null)
    if [ "$step" -le "${steps_len:-0}" ]; then
      concern=$(jq -r '.results[-1].concern // "starting"' .cookbook/pipeline.json 2>/dev/null)
      Phase=$(echo "$phase" | awk '{print toupper(substr($0,1,1)) substr($0,2)}')
      echo "$Phase: Step $step/$total — $concern"
    else
      echo "Pipeline complete"
    fi
  fi
fi
