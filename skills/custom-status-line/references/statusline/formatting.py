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


class Row:
    """A status line row with raw columns and formatted output.

    Raw column values are stripped of leading/trailing whitespace on init.
    After format_rows(), each Row has a `formatted` list of padded strings.
    """

    _SEP = " | "
    _BORDER = "| "

    def __init__(self, *columns):
        self.columns = [c.strip() if c else "" for c in columns]
        self.formatted = []

    def render(self):
        """Render as '| col0 | col1 | col2 | ...'."""
        return self._BORDER + self._SEP.join(self.formatted)


def compute_column_widths(rows: list) -> list:
    """Compute column widths from a list of Row objects.

    Returns a list of ints, one per column. Each width is the longest
    visible string in that column + 1 (for padding).
    """
    if not rows:
        return []
    num_cols = max(len(r.columns) for r in rows)
    widths = []
    for col in range(num_cols):
        max_w = 0
        for row in rows:
            if col < len(row.columns) and row.columns[col]:
                max_w = max(max_w, visible_len(row.columns[col]))
        widths.append(max_w + 1)
    return widths


def format_rows(rows: list, widths: list) -> None:
    """Pad each Row's columns into row.formatted.

    Col 0 is right-aligned (pad_left), all others left-aligned (pad_right).
    Trailing empty columns are omitted; interior empty columns are padded.
    After formatting, verifies all formatted columns at the same position
    have the same visible length.
    """
    for row in rows:
        # Find last non-empty column
        last_col = len(row.columns) - 1
        while last_col > 0 and not row.columns[last_col]:
            last_col -= 1

        row.formatted = []
        for col in range(last_col + 1):
            val = row.columns[col]
            w = widths[col] if col < len(widths) else 0
            if col == 0:
                row.formatted.append(pad_left(val, w))
            else:
                row.formatted.append(pad_right(val, w))

    # Verify: all formatted columns at the same position have identical visible length
    num_cols = max((len(r.formatted) for r in rows), default=0)
    for col in range(num_cols):
        lengths = set()
        for row in rows:
            if col < len(row.formatted):
                lengths.add(visible_len(row.formatted[col]))
        if len(lengths) > 1:
            raise ValueError(
                f"Column {col} has inconsistent widths after formatting: {lengths}"
            )


# --- Legacy helpers for standalone pipeline modules (usage_costs, version_tracker) ---

def extract_col_widths(lines):
    """Extract column visible widths from already-rendered status lines."""
    sep = " | "
    for idx in range(len(lines) - 1, 0, -1):
        parts = lines[idx].split(sep)
        if len(parts) >= 4:
            widths = [visible_len(parts[0]) - 2]  # subtract "| " border
            widths.extend(visible_len(p) for p in parts[1:])
            return widths
    return None


def reformat_columns(lines, col_widths, new_widths):
    """Reformat already-rendered lines when columns widen."""
    lbor = "| "
    sep = " | "

    for i, line in enumerate(lines):
        if not line.startswith(lbor):
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
            rebuilt = lbor + pad_left(parts[0][len(lbor):], new_widths[0])
            for j in range(1, len(parts)):
                if j < len(new_widths):
                    rebuilt += sep + pad_right(parts[j], new_widths[j])
                else:
                    rebuilt += sep + parts[j]
            lines[i] = rebuilt
        elif len(parts) >= 4:
            rebuilt = lbor + parts[0][len(lbor):]
            rebuilt += sep + pad_left(parts[1], new_widths[0])
            for j in range(2, len(parts)):
                w_idx = j - 1
                if w_idx < len(new_widths):
                    rebuilt += sep + pad_right(parts[j], new_widths[w_idx])
                else:
                    rebuilt += sep + parts[j]
            lines[i] = rebuilt
