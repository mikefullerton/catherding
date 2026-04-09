import pytest
from statusline.formatting import (
    BLUE, YELLOW, GREEN, ORANGE, RED, DIM, RST,
    visible_len, pad_right, pad_left,
)


class TestVisibleLen:
    def test_plain_text(self):
        assert visible_len("hello") == 5

    def test_ansi_colored(self):
        assert visible_len(f"{BLUE}hello{RST}") == 5

    def test_multiple_colors(self):
        s = f"{RED}err{RST} {GREEN}ok{RST}"
        assert visible_len(s) == 6  # "err ok"

    def test_empty(self):
        assert visible_len("") == 0

    def test_only_ansi(self):
        assert visible_len(f"{BLUE}{RST}") == 0


class TestPadRight:
    def test_pads_plain(self):
        result = pad_right("hi", 5)
        assert result == "hi   "
        assert visible_len(result) == 5

    def test_pads_ansi(self):
        result = pad_right(f"{RED}hi{RST}", 5)
        assert visible_len(result) == 5
        assert result.startswith("\033[")

    def test_no_pad_when_exact(self):
        result = pad_right("hello", 5)
        assert result == "hello"

    def test_no_pad_when_over(self):
        result = pad_right("hello!", 5)
        assert result == "hello!"


class TestPadLeft:
    def test_pads_plain(self):
        result = pad_left("hi", 5)
        assert result == "   hi"
        assert visible_len(result) == 5

    def test_pads_ansi(self):
        result = pad_left(f"{RED}hi{RST}", 5)
        assert visible_len(result) == 5

    def test_no_pad_when_exact(self):
        result = pad_left("hello", 5)
        assert result == "hello"
