#!/bin/bash
# Pipeline script: YOLO indicator (handled by base-info.sh, this is a passthrough)
INPUT=$(cat)
echo "$INPUT" | jq -c '{lines: .lines}'
