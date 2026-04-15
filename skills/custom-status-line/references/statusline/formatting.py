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

    A heading row (`heading=True`) is single-column and left-justified,
    meant to label the block that follows. Heading rows do not contribute
    to col-0 width and are rendered as bare `| <text>` with no padding or
    column separators.
    """

    _SEP = " | "
    _BORDER = "| "

    def __init__(self, *columns, heading=False, trailing=""):
        self.columns = [c.strip() if c else "" for c in columns]
        self.formatted = []
        self.heading = heading
        # Free-form text appended after the last column with a " | "
        # separator. Unlike a regular column, trailing text does not
        # participate in width calculation, so a long annotation on one
        # row (e.g. a repo-hygiene warning after the git detail row) can
        # sit at the end of that row without forcing every other row's
        # matching column to pad out to its width.
        self.trailing = trailing.strip() if trailing else ""

    def render(self):
        """Render as '| col0 | col1 | col2 | ...', or '| col0' for headings."""
        out = self._BORDER + self._SEP.join(self.formatted)
        if self.trailing:
            out += self._SEP + self.trailing
        return out


def compute_column_widths(rows: list) -> list:
    """Compute column widths from a list of Row objects.

    Returns a list of ints, one per column. Each width equals the longest
    visible string in that column — no extra padding. The separator " | "
    provides the spacing between columns.

    Heading rows are excluded: a short label like "git" should not force
    column 0 wider than the data rows beneath it, and heading text does
    not participate in column alignment regardless of its length.
    """
    if not rows:
        return []
    data_rows = [r for r in rows if not getattr(r, "heading", False)]
    if not data_rows:
        return []
    num_cols = max(len(r.columns) for r in data_rows)
    widths = []
    for col in range(num_cols):
        max_w = 0
        for row in data_rows:
            if col < len(row.columns) and row.columns[col]:
                max_w = max(max_w, visible_len(row.columns[col]))
        widths.append(max_w)
    # Visual gutter: right-aligned col 0 normally renders flush against the
    # leading "| " border, which cramps the section against the pipe. Pad
    # col 0 so the *longest* label has 4 leading spaces before its first
    # char (shorter labels get proportionally more since col 0 is
    # right-aligned). Only column 0, only data rows.
    if widths and widths[0] > 0:
        widths[0] += 4
    return widths


def format_rows(rows: list, widths: list) -> None:
    """Pad each Row's columns into row.formatted.

    Col 0 is right-aligned (pad_left), all others left-aligned (pad_right).
    Trailing empty columns are omitted; interior empty columns are padded.
    Heading rows render their col-0 text raw (left-flush against the border,
    no padding, no separators) and are skipped by the width-consistency check.
    After formatting, verifies all formatted columns at the same position
    have the same visible length across non-heading rows.
    """
    for row in rows:
        if getattr(row, "heading", False):
            # Heading rows stand alone: render their columns raw with the
            # standard separator, but don't participate in global column
            # alignment. Single-col headings act as section labels; multi-col
            # headings act as left-flush detail/warning rows decoupled from
            # the main grid.
            row.formatted = [c for c in row.columns if c]
            if not row.formatted:
                row.formatted = [""]
            continue

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
    data_rows = [r for r in rows if not getattr(r, "heading", False)]
    num_cols = max((len(r.formatted) for r in data_rows), default=0)
    for col in range(num_cols):
        lengths = set()
        for row in data_rows:
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
