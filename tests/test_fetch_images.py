"""Tests for fetch_all_images function."""

import os
import sys
from unittest.mock import patch

import pytest
import responses

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from queue_submit import fetch_all_images


class TestFetchAllImagesSuccess:
    """Test successful image fetching."""

    @responses.activate
    def test_single_page(self):
        """Test fetching single page of images."""
        responses.add(
            responses.POST,
            "https://private.autodl.com/api/v1/dev/image/private/list",
            json={
                "code": "Success",
                "data": {
                    "list": [
                        {"image_uuid": "img-1", "image_name": "Image 1"},
                        {"image_uuid": "img-2", "image_name": "Image 2"}
                    ],
                    "max_page": 1
                }
            },
            status=200
        )

        result = fetch_all_images("token")
        assert len(result) == 2
        assert result[0]["uuid"] == "img-1"
        assert result[0]["name"] == "Image 1"
        assert result[1]["uuid"] == "img-2"
        assert result[1]["name"] == "Image 2"

    @responses.activate
    def test_empty_list(self):
        """Test with empty image list."""
        responses.add(
            responses.POST,
            "https://private.autodl.com/api/v1/dev/image/private/list",
            json={
                "code": "Success",
                "data": {
                    "list": [],
                    "max_page": 1
                }
            },
            status=200
        )

        result = fetch_all_images("token")
        assert result == []

    @responses.activate
    def test_multiple_pages(self):
        """Test fetching multiple pages."""
        # Page 1
        responses.add(
            responses.POST,
            "https://private.autodl.com/api/v1/dev/image/private/list",
            json={
                "code": "Success",
                "data": {
                    "list": [
                        {"image_uuid": "img-1", "image_name": "Image 1"}
                    ],
                    "max_page": 2
                }
            },
            status=200
        )
        # Page 2
        responses.add(
            responses.POST,
            "https://private.autodl.com/api/v1/dev/image/private/list",
            json={
                "code": "Success",
                "data": {
                    "list": [
                        {"image_uuid": "img-2", "image_name": "Image 2"}
                    ],
                    "max_page": 2
                }
            },
            status=200
        )

        result = fetch_all_images("token")
        assert len(result) == 2
        assert result[0]["uuid"] == "img-1"
        assert result[1]["uuid"] == "img-2"

    @responses.activate
    def test_pagination_parameters(self):
        """Test that correct pagination parameters are sent."""
        responses.add(
            responses.POST,
            "https://private.autodl.com/api/v1/dev/image/private/list",
            json={
                "code": "Success",
                "data": {"list": [], "max_page": 1}
            },
            status=200
        )

        fetch_all_images("token")

        import json
        request = responses.calls[0]
        body = json.loads(request.request.body)
        assert body["page_index"] == 1
        assert body["page_size"] == 100


class TestFetchAllImagesFieldHandling:
    """Test field handling in image data."""

    @responses.activate
    def test_missing_image_uuid(self):
        """Test handling missing image_uuid field."""
        responses.add(
            responses.POST,
            "https://private.autodl.com/api/v1/dev/image/private/list",
            json={
                "code": "Success",
                "data": {
                    "list": [
                        {"image_name": "No UUID"}
                    ],
                    "max_page": 1
                }
            },
            status=200
        )

        result = fetch_all_images("token")
        assert result[0]["uuid"] == ""
        assert result[0]["name"] == "No UUID"

    @responses.activate
    def test_missing_image_name(self):
        """Test handling missing image_name field."""
        responses.add(
            responses.POST,
            "https://private.autodl.com/api/v1/dev/image/private/list",
            json={
                "code": "Success",
                "data": {
                    "list": [
                        {"image_uuid": "img-1"}
                    ],
                    "max_page": 1
                }
            },
            status=200
        )

        result = fetch_all_images("token")
        assert result[0]["uuid"] == "img-1"
        assert result[0]["name"] == ""


class TestFetchAllImagesFailure:
    """Test failure handling."""

    @responses.activate
    def test_api_error_code(self, capsys):
        """Test handling API error response."""
        responses.add(
            responses.POST,
            "https://private.autodl.com/api/v1/dev/image/private/list",
            json={
                "code": "Error",
                "msg": "Authentication failed"
            },
            status=200
        )

        with pytest.raises(SystemExit) as exc_info:
            fetch_all_images("token")

        assert exc_info.value.code == 3

    @responses.activate
    def test_api_error_message_in_output(self, capsys):
        """Test that API error message is included in output."""
        responses.add(
            responses.POST,
            "https://private.autodl.com/api/v1/dev/image/private/list",
            json={
                "code": "Error",
                "msg": "Invalid token"
            },
            status=200
        )

        with pytest.raises(SystemExit):
            fetch_all_images("token")

        captured = capsys.readouterr()
        import json
        output = json.loads(captured.out)
        assert "Invalid token" in output["message"]
