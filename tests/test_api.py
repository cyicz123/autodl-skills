"""Tests for api function."""

import os
import sys
from unittest.mock import patch

import pytest
import responses

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from queue_submit import api


class TestApiSuccess:
    """Test successful API calls."""

    @responses.activate
    def test_get_request_success(self):
        """Test successful GET request."""
        responses.add(
            responses.GET,
            "https://private.autodl.com/api/v1/dev/test",
            json={"code": "Success", "data": {"key": "value"}},
            status=200
        )

        result = api("GET", "/api/v1/dev/test", "test-token")
        assert result["code"] == "Success"
        assert result["data"]["key"] == "value"

    @responses.activate
    def test_post_request_success(self):
        """Test successful POST request with body."""
        responses.add(
            responses.POST,
            "https://private.autodl.com/api/v1/dev/deployment",
            json={"code": "Success", "data": {"deployment_uuid": "abc123"}},
            status=200
        )

        body = {"name": "test", "deployment_type": "ReplicaSet"}
        result = api("POST", "/api/v1/dev/deployment", "test-token", body)
        assert result["code"] == "Success"

    @responses.activate
    def test_request_headers(self):
        """Test that correct headers are sent."""
        responses.add(
            responses.GET,
            "https://private.autodl.com/api/v1/dev/test",
            json={"code": "Success"},
            status=200
        )

        api("GET", "/api/v1/dev/test", "my-auth-token")

        request = responses.calls[0].request
        assert request.headers["Authorization"] == "my-auth-token"
        assert request.headers["Content-Type"] == "application/json"

    @responses.activate
    def test_post_request_body(self):
        """Test that POST body is sent correctly."""
        responses.add(
            responses.POST,
            "https://private.autodl.com/api/v1/dev/test",
            json={"code": "Success"},
            status=200
        )

        body = {"key": "value", "number": 42}
        api("POST", "/api/v1/dev/test", "token", body)

        import json
        request = responses.calls[0]
        sent_body = json.loads(request.request.body)
        assert sent_body == body


class TestApiFailure:
    """Test API failure handling."""

    @responses.activate
    def test_http_404_error(self, capsys):
        """Test handling of 404 error."""
        responses.add(
            responses.GET,
            "https://private.autodl.com/api/v1/dev/test",
            json={"error": "Not found"},
            status=404
        )

        with pytest.raises(SystemExit) as exc_info:
            api("GET", "/api/v1/dev/test", "token")

        assert exc_info.value.code == 3

    @responses.activate
    def test_http_500_error(self, capsys):
        """Test handling of 500 error."""
        responses.add(
            responses.GET,
            "https://private.autodl.com/api/v1/dev/test",
            json={"error": "Server error"},
            status=500
        )

        with pytest.raises(SystemExit) as exc_info:
            api("GET", "/api/v1/dev/test", "token")

        assert exc_info.value.code == 3

    @responses.activate
    def test_timeout_error(self, capsys):
        """Test handling of timeout."""
        responses.add(
            responses.GET,
            "https://private.autodl.com/api/v1/dev/test",
            body=requests.Timeout("Request timed out")
        )

        with pytest.raises(SystemExit) as exc_info:
            api("GET", "/api/v1/dev/test", "token")

        assert exc_info.value.code == 3

    @responses.activate
    def test_connection_error(self, capsys):
        """Test handling of connection error."""
        responses.add(
            responses.GET,
            "https://private.autodl.com/api/v1/dev/test",
            body=requests.ConnectionError("Connection failed")
        )

        with pytest.raises(SystemExit) as exc_info:
            api("GET", "/api/v1/dev/test", "token")

        assert exc_info.value.code == 3

    @responses.activate
    def test_error_output_format(self, capsys):
        """Test that error output is valid JSON."""
        responses.add(
            responses.GET,
            "https://private.autodl.com/api/v1/dev/test",
            status=500
        )

        with pytest.raises(SystemExit):
            api("GET", "/api/v1/dev/test", "token")

        captured = capsys.readouterr()
        import json
        output = json.loads(captured.out)
        assert output["status"] == "error"
        assert output["error_type"] == "api_error"
        assert "API 请求失败" in output["message"]


# Need to import requests for exception types
import requests
