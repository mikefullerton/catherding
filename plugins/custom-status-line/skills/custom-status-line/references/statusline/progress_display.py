#!/usr/bin/env python3
"""Pipeline module: boxed progress bar display."""
import json
import os
import shutil

from statusline.formatting import BLUE, GREEN, DIM, RST


def run(claude_data: dict, lines: list) -> list:
    """Render a progress bar box if session has active progress."""
    session_id = claude_data.get("session_id", "")
    if not session_id:
        return lines

    progress_dir = os.path.expanduser("~/.claude-status-line/progress")
    progress_file = os.path.join(progress_dir, f"{session_id}.json")

    if not os.path.isfile(progress_file):
        return lines

    try:
        with open(progress_file) as f:
            progress = json.load(f)
    except (OSError, json.JSONDecodeError):
        return lines

    title = progress.get("title", "")
    subtitle = progress.get("subtitle", "")
    count = progress.get("count", 0)
    max_val = progress.get("max", 0)

    if not title or max_val <= 0:
        return lines

    count = max(0, min(count, max_val))
    pct = count * 100 // max_val

    cols = progress.get("cols")
    if not cols:
        cols = shutil.get_terminal_size((80, 24)).columns

    inner = max(20, cols - 4)

    def center_line(text: str, text_vis_len: int) -> str:
        pad_l = max(0, (inner - text_vis_len) // 2)
        pad_r = max(0, inner - text_vis_len - pad_l)
        return f"{DIM}|{RST}{' ' * pad_l}{text}{' ' * pad_r}{DIM}|{RST}"

    border = f"{DIM}|{'-' * inner}|{RST}"
    empty = f"{DIM}|{RST}{' ' * inner}{DIM}|{RST}"

    title_text = f"{BLUE}{title}{RST}"
    title_line = center_line(title_text, len(title))

    bar_width = max(10, inner - 6)
    filled = count * bar_width // max_val
    empty_bar = bar_width - filled
    bar_content = f"  {DIM}[{RST}{GREEN}{'=' * filled}{RST}{' ' * empty_bar}{DIM}]{RST}  "
    bar_vis_len = bar_width + 6
    bar_line = center_line(bar_content, bar_vis_len)

    sub_text = f"{subtitle} {count}/{max_val} ({pct}%)"
    sub_styled = f"{DIM}{sub_text}{RST}"
    sub_line = center_line(sub_styled, len(sub_text))

    return lines + [border, empty, title_line, bar_line, sub_line, border]
