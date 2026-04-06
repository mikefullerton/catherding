"""Tests for webinator API helpers."""

import json
from unittest.mock import patch, MagicMock
import pytest
from webinator.api import api_request, api_get


class TestApiRequest:
    @patch("webinator.api.urllib.request.urlopen")
    def test_parses_json_response(self, mock_urlopen):
        body = json.dumps({"result": "ok"}).encode()
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = body
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        code, data = api_request("https://example.com/api", "Bearer tok")
        assert code == 200
        assert data == {"result": "ok"}

    @patch("webinator.api.urllib.request.urlopen")
    def test_handles_non_json_response(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b"not json"
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        code, data = api_request("https://example.com/api", "Bearer tok")
        assert code == 200
        assert "raw" in data


class TestApiGet:
    @patch("webinator.api.api_request")
    def test_returns_data_on_200(self, mock_req):
        mock_req.return_value = (200, [{"domain": "example.com"}])
        result = api_get("https://example.com/api", "Bearer tok")
        assert result == [{"domain": "example.com"}]

    @patch("webinator.api.api_request")
    def test_exits_on_error(self, mock_req):
        mock_req.return_value = (403, {"message": "Forbidden"})
        with pytest.raises(SystemExit) as exc:
            api_get("https://example.com/api", "Bearer tok")
        assert exc.value.code == 1
