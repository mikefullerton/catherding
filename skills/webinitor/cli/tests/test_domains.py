"""Tests for webinator domain formatting and filtering helpers."""

from webinator.domains import _format_table, _expires_short, _bool_yn


class TestFormatTable:
    def test_empty_rows(self):
        assert _format_table([], [("A", "a", 5)]) == "No results."

    def test_basic_table(self):
        rows = [{"name": "foo"}, {"name": "barbaz"}]
        columns = [("NAME", "name", 10)]
        result = _format_table(rows, columns)
        lines = result.split("\n")
        assert lines[0].strip() == "NAME"
        assert "foo" in lines[2]
        assert "barbaz" in lines[3]

    def test_callable_column(self):
        rows = [{"x": 42}]
        columns = [("VAL", lambda d: str(d["x"] * 2), 10)]
        result = _format_table(rows, columns)
        assert "84" in result


class TestExpiresShort:
    def test_truncates_to_date(self):
        assert _expires_short({"expires": "2026-12-31T23:59:59Z"}) == "2026-12-31"

    def test_empty_expires(self):
        assert _expires_short({}) == ""
        assert _expires_short({"expires": ""}) == ""


class TestBoolYn:
    def test_true(self):
        fn = _bool_yn("flag")
        assert fn({"flag": True}) == "yes"

    def test_false(self):
        fn = _bool_yn("flag")
        assert fn({"flag": False}) == "no"

    def test_missing(self):
        fn = _bool_yn("flag")
        assert fn({}) == "-"
