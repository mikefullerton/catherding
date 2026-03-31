# yolo

Toggle per-session YOLO mode for Claude Code — auto-approve all tool calls with a configurable deny list.

## Skills

- `/yolo on` — Enable YOLO for the current session
- `/yolo off` — Disable YOLO for the current session
- `/yolo status` — Show current YOLO state
- `/yolo configure` — Edit the deny list

## How it works

When enabled, a PermissionRequest hook auto-approves tool calls unless they match a deny rule. Session markers ensure YOLO is scoped to individual sessions. A cleanup hook removes stale markers on session end.

Default deny list blocks force pushes, hard resets, force branch deletes, and dangerous `rm -rf` patterns.
