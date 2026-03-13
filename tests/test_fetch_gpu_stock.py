"""Tests for fetch_gpu_stock function."""

import os
import sys

import pytest
import responses

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from queue_submit import fetch_gpu_stock


class TestFetchGpuStockSuccess:
    """Test successful GPU stock fetching."""

    @responses.activate
    def test_dict_format(self):
        """Test GPU stock in dict format."""
        responses.add(
            responses.GET,
            "https://private.autodl.com/api/v1/dev/machine/gpu_stock",
            json={
                "code": "Success",
                "data": {
                    "RTX 4090": {"idle_gpu_num": 5, "total_gpu_num": 10},
                    "RTX 3090": {"idle_gpu_num": 0, "total_gpu_num": 8}
                }
            },
            status=200
        )

        result = fetch_gpu_stock("token")
        assert result["RTX 4090"]["idle"] == 5
        assert result["RTX 4090"]["total"] == 10
        assert result["RTX 3090"]["idle"] == 0
        assert result["RTX 3090"]["total"] == 8

    @responses.activate
    def test_list_format(self):
        """Test GPU stock in list format."""
        responses.add(
            responses.GET,
            "https://private.autodl.com/api/v1/dev/machine/gpu_stock",
            json={
                "code": "Success",
                "data": [
                    {"RTX 4090": {"idle_gpu_num": 3, "total_gpu_num": 6}},
                    {"RTX 3090": {"idle_gpu_num": 1, "total_gpu_num": 4}}
                ]
            },
            status=200
        )

        result = fetch_gpu_stock("token")
        assert result["RTX 4090"]["idle"] == 3
        assert result["RTX 4090"]["total"] == 6
        assert result["RTX 3090"]["idle"] == 1
        assert result["RTX 3090"]["total"] == 4

    @responses.activate
    def test_empty_response(self):
        """Test with empty response."""
        responses.add(
            responses.GET,
            "https://private.autodl.com/api/v1/dev/machine/gpu_stock",
            json={
                "code": "Success",
                "data": {}
            },
            status=200
        )

        result = fetch_gpu_stock("token")
        assert result == {}

    @responses.activate
    def test_empty_list_response(self):
        """Test with empty list response."""
        responses.add(
            responses.GET,
            "https://private.autodl.com/api/v1/dev/machine/gpu_stock",
            json={
                "code": "Success",
                "data": []
            },
            status=200
        )

        result = fetch_gpu_stock("token")
        assert result == {}


class TestFetchGpuStockFieldHandling:
    """Test field handling in GPU stock data."""

    @responses.activate
    def test_missing_idle_gpu_num(self):
        """Test handling missing idle_gpu_num field."""
        responses.add(
            responses.GET,
            "https://private.autodl.com/api/v1/dev/machine/gpu_stock",
            json={
                "code": "Success",
                "data": {
                    "RTX 4090": {"total_gpu_num": 10}
                }
            },
            status=200
        )

        result = fetch_gpu_stock("token")
        assert result["RTX 4090"]["idle"] == 0
        assert result["RTX 4090"]["total"] == 10

    @responses.activate
    def test_missing_total_gpu_num(self):
        """Test handling missing total_gpu_num field."""
        responses.add(
            responses.GET,
            "https://private.autodl.com/api/v1/dev/machine/gpu_stock",
            json={
                "code": "Success",
                "data": {
                    "RTX 4090": {"idle_gpu_num": 5}
                }
            },
            status=200
        )

        result = fetch_gpu_stock("token")
        assert result["RTX 4090"]["idle"] == 5
        assert result["RTX 4090"]["total"] == 0


class TestFetchGpuStockEdgeCases:
    """Test edge cases for branch coverage."""

    @responses.activate
    def test_skip_invalid_gpu_info(self):
        """Test skipping GPU entries where info is not a dict."""
        responses.add(
            responses.GET,
            "https://private.autodl.com/api/v1/dev/machine/gpu_stock",
            json={
                "code": "Success",
                "data": {
                    "RTX 4090": {"idle_gpu_num": 5, "total_gpu_num": 10},
                    "InvalidGPU": "not a dict",  # Should be skipped
                    "RTX 3090": {"idle_gpu_num": 3, "total_gpu_num": 8}
                }
            },
            status=200
        )

        result = fetch_gpu_stock("token")
        # Should only contain GPUs with valid dict info
        assert "RTX 4090" in result
        assert "RTX 3090" in result
        assert "InvalidGPU" not in result
        assert result["RTX 4090"]["idle"] == 5

    @responses.activate
    def test_neither_dict_nor_list_data(self):
        """Test when data is neither dict nor list (returns empty stock)."""
        responses.add(
            responses.GET,
            "https://private.autodl.com/api/v1/dev/machine/gpu_stock",
            json={
                "code": "Success",
                "data": "unexpected string format"
            },
            status=200
        )

        result = fetch_gpu_stock("token")
        assert result == {}


class TestFetchGpuStockFailure:
    """Test failure handling."""

    @responses.activate
    def test_api_error_code(self, capsys):
        """Test handling API error response."""
        responses.add(
            responses.GET,
            "https://private.autodl.com/api/v1/dev/machine/gpu_stock",
            json={
                "code": "Error",
                "msg": "Service unavailable"
            },
            status=200
        )

        with pytest.raises(SystemExit) as exc_info:
            fetch_gpu_stock("token")

        assert exc_info.value.code == 3

    @responses.activate
    def test_api_error_message(self, capsys):
        """Test that API error message is included."""
        responses.add(
            responses.GET,
            "https://private.autodl.com/api/v1/dev/machine/gpu_stock",
            json={
                "code": "Error",
                "msg": "Invalid credentials"
            },
            status=200
        )

        with pytest.raises(SystemExit):
            fetch_gpu_stock("token")

        captured = capsys.readouterr()
        import json
        output = json.loads(captured.out)
        assert "查询 GPU 库存失败" in output["message"]
        assert "Invalid credentials" in output["message"]
