#!/usr/bin/env python3
"""Pipeline module: progress bar display (standard or compact)."""
import json
import os
import shutil
from typing import Optional

from statusline.formatting import BLUE, GREEN, ORANGE, DIM, RST, visible_len


def _load_progress(claude_data: dict) -> Optional[dict]:
    """Load progress file for the current session, or None."""
    session_id = claude_data.get("session_id", "")
    if not session_id:
        return None

    progress_dir = os.path.expanduser("~/.claude-status-line/progress")
    progress_file = os.path.join(progress_dir, f"{session_id}.json")

    if not os.path.isfile(progress_file):
        return None

    try:
        with open(progress_file) as f:
            progress = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

    title = progress.get("title", "")
    max_val = progress.get("max", 0)
    if not title or max_val <= 0:
        return None

    progress["count"] = max(0, min(progress.get("count", 0), max_val))
    return progress


def _get_progress_style() -> str:
    """Read progress_style from pipeline.json, default 'standard'."""
    config_path = os.path.expanduser("~/.claude-status-line/pipeline.json")
    try:
        with open(config_path) as f:
            return json.load(f).get("progress_style", "standard")
    except (OSError, json.JSONDecodeError):
        return "standard"


def _render_standard(progress: dict, lines: list) -> list:
    """Render the original boxed progress bar."""
    title = progress.get("title", "")
    subtitle = progress.get("subtitle", "")
    count = progress["count"]
    max_val = progress["max"]
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


def _render_compact(progress: dict, lines: list) -> list:
    """Render a 2-line compact progress bar sized to the status lines above."""
    title = progress.get("title", "")
    count = progress["count"]
    max_val = progress["max"]
    pct = count * 100 // max_val

    # Width = longest status line + 1
    max_w = max((visible_len(line) for line in lines), default=40)
    total_w = max_w + 1
    inner_w = total_w - 2  # between left and right border |'s

    # Line 1: progress bar of | chars
    filled = count * inner_w // max_val
    bar_line = (
        f"{ORANGE}{'|' * (filled + 1)}{RST}"
        f"{' ' * (inner_w - filled)}"
        f"{ORANGE}|{RST}"
    )

    # Line 2: centered title, right-justified [count/total] (pct%)
    right_text = f"[{count}/{max_val}] ({pct}%)"
    right_len = len(right_text)

    title_center = (inner_w - len(title)) // 2
    count_pos = inner_w - right_len - 1

    # Prevent overlap
    if title_center + len(title) >= count_pos:
        title_center = max(1, count_pos - len(title) - 1)

    left_pad = title_center
    mid_pad = count_pos - title_center - len(title)
    end_pad = 1

    info_line = (
        f"{ORANGE}|{RST}"
        f"{' ' * left_pad}{BLUE}{title}{RST}"
        f"{' ' * mid_pad}{DIM}{right_text}{RST}"
        f"{' ' * end_pad}{ORANGE}|{RST}"
    )

    return lines + [bar_line, info_line]


def run(claude_data: dict, lines: list) -> list:
    """Render progress bar if session has active progress."""
    progress = _load_progress(claude_data)
    if not progress:
        return lines

    style = _get_progress_style()
    if style == "compact":
        return _render_compact(progress, lines)
    return _render_standard(progress, lines)
