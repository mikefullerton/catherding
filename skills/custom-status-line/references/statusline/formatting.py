"""ANSI colors and column alignment helpers."""
import re

# ANSI color constants
BLUE = "\033[38;5;117m"
YELLOW = "\033[38;5;229m"
GREEN = "\033[38;5;151m"
ORANGE = "\033[38;5;214m"
RED = "\033[38;5;210m"
DIM = "\033[38;5;245m"
RST = "\033[0m"

_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def visible_len(s: str) -> int:
    """Return the visible length of a string, ignoring ANSI escape codes."""
    return len(_ANSI_RE.sub("", s))


def pad_right(s: str, width: int) -> str:
    """Pad string to visible width with trailing spaces."""
    pad = width - visible_len(s)
    return s + " " * pad if pad > 0 else s


def pad_left(s: str, width: int) -> str:
    """Pad string to visible width with leading spaces."""
    pad = width - visible_len(s)
    return " " * pad + s if pad > 0 else s


def get_column_widths(rows: list) -> list:
    """Compute column widths from rows of column values.

    Args:
        rows: list of lists, each inner list is one row's column values.

    Returns:
        list of ints, one per column. Each width is the longest visible
        string in that column + 1 (for padding).
    """
    if not rows:
        return []
    num_cols = max(len(row) for row in rows)
    widths = []
    for col in range(num_cols):
        max_w = 0
        for row in rows:
            if col < len(row) and row[col]:
                max_w = max(max_w, visible_len(row[col]))
        widths.append(max_w + 1)
    return widths


def format_columns(rows: list, widths: list) -> list:
    """Format rows into aligned status lines.

    Col 0 is right-aligned (pad_left), all others are left-aligned (pad_right).
    Each line is prefixed with "| " and columns are joined with " | ".
    Trailing empty columns are omitted; interior empty columns are padded.

    Args:
        rows: list of lists, each inner list is one row's column values.
              Rows may have fewer columns than widths — trailing columns are omitted.
        widths: column widths from get_column_widths().

    Returns:
        list of formatted strings, one per row.
    """
    lbor = "| "
    sep = " | "
    result = []
    for row in rows:
        # Find last non-empty column to avoid trailing empty padding
        last_col = len(row) - 1
        while last_col > 0 and not row[last_col]:
            last_col -= 1

        parts = []
        for col in range(last_col + 1):
            val = row[col]
            w = widths[col] if col < len(widths) else 0
            if col == 0:
                parts.append(lbor + pad_left(val or "", w))
            else:
                parts.append(pad_right(val or "", w))
        result.append(sep.join(parts))
    return result


def extract_col_widths(lines):
    """Extract column visible widths from existing status lines.

    Scans backward to prefer the last aligned line (e.g. session line).
    Returns a list of visible widths, or None if no aligned line found.
    """
    sep = " | "
    for idx in range(len(lines) - 1, 0, -1):
        parts = lines[idx].split(sep)
        if len(parts) >= 4:
            widths = [visible_len(parts[0]) - 2]  # subtract "| " border
            widths.extend(visible_len(p) for p in parts[1:])
            return widths
    return None


def reformat_columns(lines, col_widths, new_widths):
    """Reformat all aligned lines when columns widen.

    Handles three line types:
    - Row 1 (path): re-pads path so git:(branch) stays aligned with col3
    - Standard aligned lines: reformat col1-col4
    - Model line with col0 (session name): keep col0, reformat col1+
    """
    lbor = "| "
    sep = " | "

    for i, line in enumerate(lines):
        if not line.startswith(lbor):
            # Row 1: re-pad path to align with new col widths
            if i == 0 and sep in line and len(new_widths) >= 2:
                path_w = new_widths[0] + new_widths[1] + 5
                parts = line.split(sep)
                lines[i] = pad_right(parts[0], path_w) + sep + sep.join(parts[1:])
            continue

        parts = line.split(sep)
        if len(parts) < 3:
            continue

        first_col_w = visible_len(parts[0]) - len(lbor)
        if abs(first_col_w - col_widths[0]) <= 1:
            # Standard aligned line (git, session, usage)
            rebuilt = lbor + pad_left(parts[0][len(lbor):], new_widths[0])
            for j in range(1, len(parts)):
                if j < len(new_widths):
                    rebuilt += sep + pad_right(parts[j], new_widths[j])
                else:
                    rebuilt += sep + parts[j]
            lines[i] = rebuilt
        elif len(parts) >= 4:
            # Model line with col0: keep col0 as-is, reformat col1+
            rebuilt = lbor + parts[0][len(lbor):]
            rebuilt += sep + pad_left(parts[1], new_widths[0])
            for j in range(2, len(parts)):
                w_idx = j - 1
                if w_idx < len(new_widths):
                    rebuilt += sep + pad_right(parts[j], new_widths[w_idx])
                else:
                    rebuilt += sep + parts[j]
            lines[i] = rebuilt
