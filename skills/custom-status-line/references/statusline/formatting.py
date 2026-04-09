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
